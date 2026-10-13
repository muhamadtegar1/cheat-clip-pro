# CHEAT-29: Klip fallback heatmap salah saat rentang khusus dipakai
Status: DONE
Risiko: rendah (jalur fallback, prompt tidak berubah)

## Tujuan
Saat analisis memakai `range_start`/`range_end` dan jatuh ke klip fallback heatmap, klip fallback berada di dalam rentang dengan panjang sesuai target durasi, bukan terbalik lalu dijepit guardrail menjadi satu klip panjang.

## Kondisi sekarang (diverifikasi di kode dan direproduksi)
- `backend/routers/analyze.py` L811: setelah transkrip difilter ke rentang, `duration = end_bound - start_bound` (panjang relatif). Pemakaian ini benar untuk hitungan jumlah klip (L895-936) dan teks prompt (L1003).
- L1368 (klip fallback heatmap, L1345-1420): `et = min(duration, st + min(90.0, target_len))`. `st` adalah detik absolut dari transkrip, sedangkan `duration` relatif. Dengan rentang 60-110 s, `duration` = 50, jadi semua `et` = 50 dan setiap klip terbalik (mis. 105→50 s).
- L1349-1355: `candidate_starts` diambil dari baris transkrip yang hanya beririsan dengan rentang, jadi `st` bisa lebih kecil dari `start_bound`.
- Sejak #12, `guard_clips` menukar start/end dan menjepit ke rentang, sehingga klip terbalik tidak lagi error tetapi menjadi klip yang salah.
- Reproduksi (video sintetis 120 s, 24 baris transkrip @5 s, klien Gemini palsu yang mengembalikan klip di luar rentang, sesi review #12):
  - Tanpa rentang, durasi `15s`: 4 klip fallback 15 s (benar).
  - Rentang 60-110, durasi `15s` dan `auto`: hanya 1 klip, 60-105 s (45 s), catatan `timestamp adjusted from 105.0-50.0s to 60.0-105.0s`, klip lain digabung atau dibuang.

## Area yang boleh disentuh
- `backend/routers/analyze.py`, blok klip fallback heatmap (L1345-1420): batas akhir klip memakai `end_bound` (bukan `duration`), `st` dijepit ke `start_bound`, kandidat yang sisa rentangnya terlalu pendek dilewati.
- `scripts/smoke_test.py`: satu cek baru, analisis dengan `range_start`/`range_end` lewat klien Gemini palsu mode `out_of_range` (sudah ada) sehingga jatuh ke fallback. Cek lama tidak diubah.
- `docs/codemap/analisis-ai.md` (rentang baris, risiko), `CLAUDE.md` (deskripsi smoke test bila perlu).

## Di luar scope (jangan dikerjakan)
- Arti variabel `duration` di tempat lain: hitungan jumlah klip, teks prompt, mode mock (L878), dan `duration` di respons (L1508).
- Prompt, `ViralClipGemini`/`VideoAnalysis`, `backend/utils/clip_guardrails.py`, `guard_clips`.
- Cara memilih kandidat (urutan engagement, jarak 25 s, maksimal 5), judul dan caption fallback, `target_len` per durasi.
- Frontend.

## Keputusan yang boleh diambil AI sendiri
- Panjang minimum sisa rentang agar kandidat dipakai (selaras `MIN_CLIP_SECONDS` 5 s di guardrail).
- Apakah kandidat yang terlalu dekat ke `end_bound` dilewati atau digeser mundur.
- Rentang dan kata-kata cek smoke test.

## Kriteria selesai (ya/tidak)
- [x] Dengan rentang khusus, semua klip fallback berada di `[range_start, range_end]`, `start < end`, dan panjangnya sama dengan `target_len` kecuali terpotong `range_end`.
- [x] Tidak ada catatan `timestamp adjusted` pada klip fallback dalam skenario reproduksi (artinya fallback sudah benar sebelum guardrail).
- [x] Tanpa rentang, perilaku fallback sama seperti sebelumnya (cek "guardrail buang semua -> fallback" tetap lulus).
- [x] Smoke test lulus (9 cek lama + cek baru), `check_codemap.py` lulus.
- [x] `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py` (termasuk cek fallback dengan rentang).
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock` (alur tetap jalan).
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Golden fixtures dengan Gemini tidak wajib: prompt dan pasca-proses klip Gemini tidak berubah, dan jalur fallback hanya aktif bila tidak ada klip yang lolos.
- Uji manual di UI sulit memicu jalur ini (key `mock` berhenti sebelum fallback, dan Gemini jarang mengembalikan 0 klip), jadi bukti utama ada di smoke test.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/routers/analyze.py` (blok klip fallback heatmap, L1350-1373): kandidat `s = max(start_bound, l['start'])`, kandidat dengan `end_bound - s < 5.0` dilewati (sebelum cek jarak 25 s dan batas 5 kandidat), akhir klip `et = min(end_bound, st + min(90.0, target_len))`.
- `scripts/smoke_test.py`: konstanta `FALLBACK_RANGE = (22.0, 38.0)`, cek baru "analyze fallback heatmap dengan rentang" (mode palsu `out_of_range` + `range_start`/`range_end`), docstring daftar cek. Cek lama tidak diubah.
- `docs/codemap/analisis-ai.md`, `CLAUDE.md` (rentang `analyze_video` L225-1533, deskripsi smoke test).
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: 10/10 lulus (9 cek lama + 1 baru). Cek baru: "rentang 22-38s: 1 klip fallback (22-37)", artinya baris 20-25 s dijepit ke 22 s, panjang 15 s. Cek "guardrail buang semua -> fallback" tetap "2 klip fallback heatmap".
- Cek baru dijalankan pada `analyze.py` dari HEAD (kode lama): GAGAL "tidak ada klip" (klip 20->16 terbalik, dijepit ke rentang lalu dibuang < 5 s). Jadi cek menangkap bug.
- Skenario reproduksi kontrak (skrip sementara di scratchpad: video 120 s, 24 baris @5 s, klien palsu `out_of_range`):
  - Tanpa rentang, `15s`: lama dan baru identik, 4 klip 15 s (10-25, 55-70, 105-120, 80-95). `auto`: identik, 10-35, 55-100, 105-120, 80-115.
  - Rentang 60-110, `15s`: lama 1 klip 60-105 dengan "timestamp adjusted from 105.0-50.0s"; baru 2 klip 105-110 (terpotong `range_end`) dan 65-80, tanpa catatan penjepitan.
  - Rentang 60-110, `auto`: lama 1 klip 60-105 (dijepit); baru 1 klip 105-110 tanpa catatan penjepitan (lihat CATATAN).
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock`: exit 0, 9 klip, valid 100%.
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS.
- `npm run build` tidak dijalankan: `src/` tidak berubah. Golden fixtures dengan Gemini tidak dijalankan: prompt dan pasca-proses klip Gemini tidak berubah (sesuai kontrak).
CODEMAP_DIPERBARUI: ya, `analisis-ai.md` (rentang `analyze_video` L225-1533, fallback L1345-1425 + deskripsi #29, SSE L1427-1450, rekonstruksi L1452-1482, `AnalyzeResponse` L1483-1523, risiko `duration` relatif saat rentang, cakupan smoke test). `CLAUDE.md` jebakan no. 5 (L225-1533).
CATATAN:
- Keputusan sendiri: ambang sisa rentang 5 s (sama dengan `MIN_CLIP_SECONDS`, ditulis literal dengan komentar agar import di L50 tidak tersentuh). Kandidat dekat `end_bound` dilewati, tidak digeser mundur, karena geser mundur bisa menimpa kandidat lain yang hanya berjarak 25 s. Kandidat yang dilewati tidak dihitung ke batas 5 kandidat. Tanpa rentang `start_bound` = 0 dan `end_bound` = `duration`, jadi hasilnya identik (dibuktikan di atas).
- Rentang smoke test 22-38 dipilih supaya panjang relatif (16 s) lebih kecil dari detik absolut kandidat, sehingga kode lama pasti gagal. Rentang 3-38 sempat dicoba tetapi lolos juga di kode lama (klip 10-25), jadi diganti.
- Video sintetis 40 s hanya memberi ruang 1 klip fallback dalam rentang (jarak kandidat 25 s), jadi cek baru tidak mewajibkan >= 2 klip.
- Perlu dicek pemilik: rentang 60-110 dengan `auto` hanya menghasilkan 1 klip 5 s (105-110). Klip 65-110 (target 45 s) tumpang tindih 100% dengan 105-110 sehingga digabung guardrail dan yang tersisa skor tertinggi. Ini bawaan cara memilih kandidat (jarak 25 s vs target `auto` sampai 85 s, juga terlihat tanpa rentang: 55-100 dan 80-115 ditandai overlap) dan di luar scope kontrak. Kandidat task lanjutan bila dianggap perlu.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
