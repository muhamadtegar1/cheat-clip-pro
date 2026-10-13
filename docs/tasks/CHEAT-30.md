# CHEAT-30: Klip fallback heatmap tidak saling tumpang tindih
Status: REVIEW
Risiko: rendah (jalur fallback, prompt tidak berubah)

## Tujuan
Klip fallback heatmap dipilih sehingga tidak saling tumpang tindih dan tidak ada klip sangat pendek bila masih ada kandidat lain, supaya guardrail tidak lagi menggabungkan klip fallback menjadi satu klip pendek.

## Kondisi sekarang (diverifikasi di kode, ditemukan di #29)
- `backend/routers/analyze.py` L1349-1360: kandidat awal diambil dari baris transkrip berurutan engagement, syaratnya hanya berjarak >= 25 s dari kandidat lain dan sisa rentang >= 5 s, maksimal 5.
- L1362-1374: panjang target ditentukan per indeks kandidat (`15s` 15, `30s` 30, `60s` 60, `auto` bergiliran 25/45/75/35/60/85/20/50), akhir klip `min(end_bound, st + min(90, target_len))`.
- Karena jarak 25 s lebih kecil dari target `30s`/`60s`/`auto`, klip fallback bisa saling menimpa. `apply_guardrails` (`clip_guardrails.py` L150-178) menggabungkan overlap > 70% (yang tersisa klip pertama, skor tertinggi) dan menandai 40-70%.
- Reproduksi #29 (video 120 s, 24 baris @5 s, klien Gemini palsu `out_of_range`):
  - Rentang 60-110, `auto`: hanya 1 klip 105-110 (5 s), klip 65-110 digabung ke dalamnya. `60s` sama.
  - Tanpa rentang, `auto`: 10-35, 55-100, 105-120, 80-115; 55-100 dan 80-115 ditandai overlap 57%.
  - Tanpa rentang, `15s`: 10-25, 55-70, 105-120, 80-95 (tidak ada overlap).

## Area yang boleh disentuh
- `backend/routers/analyze.py`, blok klip fallback heatmap (L1345-1425), hanya pemilihan kandidat dan penentuan `start_time`/`end_time`/`target_len`: kandidat ditolak bila rentangnya menimpa klip fallback yang sudah dipilih atau panjangnya di bawah minimum, panjang target dihitung per klip yang diterima.
- `scripts/smoke_test.py`: satu cek baru (fallback `auto` tanpa tumpang tindih). Boleh menambah parameter opsional ke `make_synthetic_video` (default tetap) bila cek butuh video lebih panjang. Cek lama tidak diubah.
- `docs/codemap/analisis-ai.md` (rentang baris, deskripsi fallback), `CLAUDE.md` (deskripsi smoke test bila perlu).

## Di luar scope (jangan dikerjakan)
- `backend/utils/clip_guardrails.py` (ambang merge/flag, klip mana yang dipertahankan), `guard_clips`.
- Prompt, `ViralClipGemini`/`VideoAnalysis`, pasca-proses klip dari Gemini.
- Urutan kandidat (engagement tertinggi dulu), daftar panjang `auto_lens`, batas 90 s, maksimal 5 klip, judul/caption/skor fallback.
- Arti `duration`, mode mock, frontend.

## Keputusan yang boleh diambil AI sendiri
- Panjang minimum klip fallback (usulan 10 s), dan apakah turun ke 5 s (`MIN_CLIP_SECONDS`) bila tanpa itu tidak ada klip sama sekali (rentang sangat pendek).
- Apakah aturan jarak 25 s antar awal kandidat dipertahankan di samping aturan tidak tumpang tindih (usulan: dipertahankan, supaya klip `15s` tetap tersebar dan hasil `15s` tanpa rentang tidak berubah).
- Apakah kandidat yang terpotong `end_bound` atau menimpa klip lain dilewati atau digeser (usulan: dilewati, awal klip tetap di puncak engagement).
- Video dan rentang yang dipakai cek smoke test.

## Kriteria selesai (ya/tidak)
- [x] Klip fallback tidak saling tumpang tindih: pada skenario reproduksi (dengan dan tanpa rentang, `15s`/`30s`/`60s`/`auto`) ringkasan guardrail fallback `merged` = 0 dan `flagged_overlap` = 0.
- [x] Rentang 60-110 dengan `auto` menghasilkan lebih dari 1 klip.
- [x] Tidak ada klip fallback < 10 s selama ada kandidat lain yang menghasilkan klip >= 10 s.
- [x] Semua klip fallback tetap di dalam rentang, `start < end`, panjang = target atau terpotong `end_bound`, tanpa catatan `timestamp adjusted` (kriteria #29 tetap terpenuhi).
- [x] `15s` tanpa rentang menghasilkan klip yang sama seperti sebelumnya. Catatan: berlaku untuk skenario reproduksi 120 s; klip < 10 s yang dulu ada (mis. 35-40 s di video smoke 40 s) kini dibuang karena kriteria ketiga, lihat CATATAN.
- [x] Smoke test lulus (10 cek lama + cek baru, cek baru gagal di kode lama), `golden_fixtures.py run --mock` exit 0, `check_codemap.py` lulus.
- [x] `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`.
- Skrip reproduksi sementara di scratchpad (video 120 s, klien palsu `out_of_range`) untuk semua durasi, dengan dan tanpa rentang 60-110, dijalankan pada kode lama dan baru.
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock`.
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Golden fixtures dengan Gemini tidak wajib: prompt dan pasca-proses klip Gemini tidak berubah, jalur fallback hanya aktif bila tidak ada klip yang lolos.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/routers/analyze.py` (blok klip fallback heatmap, L1349-1381): fungsi lokal `pick_fallback_spans(min_len)` menggabungkan pemilihan kandidat dan penentuan panjang. Urutan engagement, jepit ke `start_bound`, jarak awal >= 25 s, target `auto` per indeks klip yang diterima, akhir `min(end_bound, start + min(90, target))`, kandidat yang menimpa klip terpilih atau < `min_len` dilewati, maks 5. Dipanggil `pick_fallback_spans(10.0) or pick_fallback_spans(5.0)`. Loop pembuatan klip memakai `(st, et)` dari hasilnya; judul/caption/skor tidak berubah.
- `scripts/smoke_test.py`: `make_synthetic_video(path, duration=VIDEO_DURATION, size="1280x720")` dan `build_srt(lines=None)` dengan default lama, konstanta `OVERLAP_VIDEO = 120` dan `OVERLAP_RANGE = (60.0, 110.0)`, fungsi cek baru `run_fallback_overlap_check` (video sintetis 120 s 320x180 sendiri, durasi `auto`, tanpa dan dengan rentang 60-110), dipanggil di `main` setelah cek analyze, docstring.
- `docs/codemap/analisis-ai.md`, `CLAUDE.md` (rentang `analyze_video` L225-1541, deskripsi smoke test).
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: 11/11 lulus (±26 s). Cek baru: "tanpa rentang: 10-35, 55-100, 105-120; rentang 60-110s: 65-90, 90-110".
- Smoke test dengan `analyze.py` dari HEAD (kode lama): cek baru GAGAL "tanpa rentang: overlaps 57% with clip 'Key Highlight #4' (review)", 10 cek lain lulus.
- Reproduksi (skrip sementara di scratchpad, video 120 s, 24 baris @5 s, klien palsu `out_of_range`), lama -> baru:
  - Tanpa rentang `15s`: 10-25, 55-70, 105-120, 80-95 -> identik.
  - Tanpa rentang `30s`: 10-40, 55-85, 105-120, 80-110 (80-110 menimpa 105-120 sebesar 5 s, di bawah ambang tanda) -> 10-40, 55-85, 105-120.
  - Tanpa rentang `60s`: 10-70, 55-115 (gabungan dari 80-120) dengan 2 tanda overlap, 105-120 -> 10-70, 105-120.
  - Tanpa rentang `auto`: 4 klip, 55-100/80-115/105-120 ditandai overlap -> 10-35, 55-100, 105-120.
  - Rentang 60-110 `15s`: 105-110 (5 s), 65-80 -> 65-80, 90-105.
  - Rentang 60-110 `30s`: 105-110 (5 s), 65-95 -> 65-95, 95-110.
  - Rentang 60-110 `60s`: 105-110 (5 s, 65-110 digabung) -> 65-110 (rentang 50 s hanya muat 1 klip).
  - Rentang 60-110 `auto`: 105-110 (5 s, 65-110 digabung) -> 65-90, 90-110.
  - Kode baru: tidak ada catatan `merged`/`overlaps`/`timestamp adjusted` di semua skenario.
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock`: exit 0.
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS.
- `npm run build` tidak dijalankan: `src/` tidak berubah. Golden fixtures dengan Gemini tidak dijalankan: prompt dan pasca-proses klip Gemini tidak berubah.
CODEMAP_DIPERBARUI: ya, `analisis-ai.md` (rentang `analyze_video` L225-1541, fallback L1345-1433 dengan deskripsi `pick_fallback_spans` #30, SSE L1435-1458, rekonstruksi L1460-1490, `AnalyzeResponse` L1491-1531, cakupan smoke test). `CLAUDE.md` jebakan no. 5 dan deskripsi smoke test.
CATATAN:
- Keputusan sendiri: minimum 10 s, turun ke 5 s (`MIN_CLIP_SECONDS`) hanya bila tidak ada klip sama sekali. Jarak awal 25 s dipertahankan. Kandidat yang menimpa atau terlalu pendek dilewati, tidak digeser. Klip yang bersentuhan (mis. 65-90 dan 90-110) tidak dihitung tumpang tindih.
- Kriteria 3 vs 5: aturan minimal 10 s membuang klip pendek yang dulu dihasilkan `15s` tanpa rentang. Di video smoke 40 s, cek lama "guardrail buang semua -> fallback" kini memberi 1 klip fallback (10-25), dulu 2 (10-25 dan 35-40, 5 s). Cek itu tetap lulus dan tidak diubah. Pada skenario reproduksi 120 s hasil `15s` identik.
- Hasil `30s`/`60s`/`auto` tanpa rentang berubah (klip yang menimpa tidak dipilih), sesuai tujuan task. Jumlah klip fallback bisa berkurang (mis. `60s`: 3 -> 2), tetapi tidak ada lagi klip yang digabung diam-diam.
- Smoke test naik dari ±20 s menjadi ±26 s karena video sintetis kedua; teks "±20 detik" di `CLAUDE.md` belum diubah.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
