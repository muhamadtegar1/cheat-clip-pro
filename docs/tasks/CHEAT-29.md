# CHEAT-29: Klip fallback heatmap salah saat rentang khusus dipakai
Status: TODO
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
- [ ] Dengan rentang khusus, semua klip fallback berada di `[range_start, range_end]`, `start < end`, dan panjangnya sama dengan `target_len` kecuali terpotong `range_end`.
- [ ] Tidak ada catatan `timestamp adjusted` pada klip fallback dalam skenario reproduksi (artinya fallback sudah benar sebelum guardrail).
- [ ] Tanpa rentang, perilaku fallback sama seperti sebelumnya (cek "guardrail buang semua -> fallback" tetap lulus).
- [ ] Smoke test lulus (9 cek lama + cek baru), `check_codemap.py` lulus.
- [ ] `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py` (termasuk cek fallback dengan rentang).
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock` (alur tetap jalan).
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Golden fixtures dengan Gemini tidak wajib: prompt dan pasca-proses klip Gemini tidak berubah, dan jalur fallback hanya aktif bila tidak ada klip yang lolos.
- Uji manual di UI sulit memicu jalur ini (key `mock` berhenti sebelum fallback, dan Gemini jarang mengembalikan 0 klip), jadi bukti utama ada di smoke test.

## Laporan implementer
STATUS:
FILE_DIUBAH:
HASIL_TEST:
CODEMAP_DIPERBARUI: ya/tidak (sebutkan catatan)
CATATAN:

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
