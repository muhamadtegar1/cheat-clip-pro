# CHEAT-17b: Golden fixtures analisis AI (Tahap 1, cek objektif)
Status: REVIEW

## Tujuan
Satu perintah menjalankan analisis AI pada 3 transkrip tersimpan (K3) dan memberi nilai objektif (kutipan tidak dikarang, timestamp valid, tanpa duplikat, tidak memilih intro/sponsor/outro), sehingga perubahan prompt di #1, #2, #12 bisa dibandingkan dengan angka.

## Data K3 (Tahap 1)
| Kode | Video | Jenis | Bahasa | Durasi | Jangan dipilih |
| --- | --- | --- | --- | --- | --- |
| A | `hbZbPHjE8NE` Colin and Samir, "The Rise of Diary of a CEO" | podcast | EN | 52:26 | 00:00-01:31 intro, 13:33-15:06 sponsor, 52:04-52:26 outro |
| B | `094y1Z2wpJg` Veritasium, "Collatz Conjecture" | edukasi | EN | 22:09 | 00:00-00:20 intro, 01:23-01:32 low-context, 20:42-22:09 sponsor |
| C | `YzDyjAsd4Z8` Billy Samuel, "House 2" | gaming | ID | 29:16 | 00:00-00:30 intro, 08:48-09:30 low-context, 27:48-29:16 outro |

Label dibantu Gemini dan diverifikasi pemilik. Cek awal: ketiga video punya caption (B punya subtitle manual EN) dan heatmap "Most replayed" (100 titik). Tahap 2 (Shorts resmi + pilihan pemilik, untuk recall momen) menyusul sebelum #1/#2.

## Area yang boleh disentuh
- Baru: `scripts/golden_fixtures.py` dengan subperintah:
  - `fetch`: ambil metadata (judul, channel, durasi), heatmap, dan caption (manual dulu, lalu otomatis, bahasa asli video) lewat yt-dlp, simpan ke `tests/golden/data/<video_id>/`. Sekali jalan; data tidak diambil ulang kecuali `--force`.
  - `run`: jalankan `POST /api/analyze` lewat `TestClient` (seperti `scripts/smoke_test.py`) dengan `subtitles` = transkrip tersimpan, dan `fetch_video_metadata` diganti fungsi yang mengembalikan metadata/heatmap tersimpan (monkeypatch di skrip, tanpa jaringan YouTube). Model default `gemini-2.5-flash`, key dari `backend/.env`. Opsi `--mock` (key `mock`, tanpa Gemini) dan `--repeat N`.
  - `score`: nilai hasil per video dan total, simpan laporan ke `tests/golden/data/runs/<waktu>.json`.
  - `--compare`: bandingkan dengan `tests/golden/baseline.json` dan tampilkan selisih.
  - `selftest`: uji fungsi penilai dengan kasus buatan (tanpa jaringan, tanpa Gemini).
- Baru: `tests/golden/labels.json` (di-commit): ID video, kode, jenis, bahasa, rentang "jangan dipilih" + alasan, tempat kosong untuk referensi Tahap 2. Tanpa isi transkrip.
- Baru: `tests/golden/baseline.json` (di-commit): hanya angka metrik dari prompt saat ini, tanpa kutipan atau transkrip.
- `.gitignore`: tambah `tests/golden/data/` (transkrip, metadata, hasil run).
- `CLAUDE.md`: bagian baru "Golden fixtures" (cara menjalankan) dan aturan kerja prompt AI menunjuk perintahnya.
- `docs/codemap/analisis-ai.md` (risiko/cara uji prompt), `docs/codemap/index.md` (link), catatan baru `docs/codemap/golden-fixtures.md` bila diperlukan check codemap.
- `TASKS.md`: K3 (sudah diisi), status #17b.

## Di luar scope (jangan dikerjakan)
- Semua file di `backend/` (prompt, skema, router). Skrip hanya memanggil kode yang ada.
- `scripts/smoke_test.py` (smoke test tetap offline dan tidak memanggil fixture ini).
- Label Tahap 2 (Shorts resmi, pilihan pemilik) dan metrik recall momen berbasis label itu. Struktur JSON-nya disiapkan, metriknya menampilkan "n/a" selama kosong.
- CI/otomatis menjalankan fixture. Dijalankan manual saat prompt berubah.

## Keputusan yang boleh diambil AI sendiri
- Format penyimpanan transkrip (SRT/JSON) dan cara memilih trek caption, asal hasil `parse_manual_subtitles` benar (baris dan waktu) dan sama setiap run.
- Definisi rinci metrik dan ambang, dengan batas berikut:
  - **Kutipan grounded**: `key_quotes` dicocokkan (dinormalisasi, fuzzy) ke transkrip di sekitar rentang klip. Ambang kecocokan ditentukan AI, dicatat di laporan.
  - **Timestamp valid**: `0 ≤ start < end ≤ durasi`, `start ≤ hook_time ≤ end`.
  - **Duplikat**: pasangan klip dengan overlap > 70% dari klip yang lebih pendek (sesuai #12).
  - **Zona terlarang**: klip yang > 50% durasinya berada di rentang "jangan dipilih".
  - **Heatmap lift** (informasi): rata-rata heatmap klip terpilih dibanding rata-rata video.
- Nilai ringkas per video dan total (mis. persen lulus per metrik), dan apa yang dianggap "lebih buruk" di `--compare`.
- Cek kewajaran label: rentang dalam durasi, tidak tumpang tindih. Bila batas sponsor/outro tampak meleset terhadap transkrip, dicatat di laporan untuk pemilik, label tidak diubah sendiri.

## Kriteria selesai (ya/tidak)
- [x] `fetch` menyimpan metadata, heatmap, dan transkrip ketiga video di `tests/golden/data/`, dan `git check-ignore tests/golden/data/x` menunjukkan folder itu diabaikan. Tidak ada transkrip di commit.
- [x] `selftest` lulus: setiap metrik diuji dengan kasus lulus dan gagal buatan (kutipan karangan, timestamp di luar durasi, dua klip overlap 80%, klip di zona sponsor).
- [x] `run --mock` jalan tanpa jaringan dan tanpa Gemini, menghasilkan laporan untuk 3 video, exit 0.
- [x] `run` dengan Gemini flash menghasilkan laporan untuk 3 video tanpa memanggil YouTube (dibuktikan: metadata dari file, bukan `fetch_video_metadata` asli). Waktu dan jumlah klip dicatat.
- [x] `tests/golden/baseline.json` berisi metrik prompt saat ini (hanya angka), dan `--compare` terhadap run baru menampilkan selisih per metrik.
- [x] `git diff` tidak menyentuh `backend/` maupun `scripts/smoke_test.py`.
- [x] Smoke test 7/7 dan `check_codemap.py` lulus.
- [x] `CLAUDE.md` menjelaskan cara menjalankan fixture dalam 1-3 perintah.

## Cara menguji
- `venv\Scripts\python.exe scripts\golden_fixtures.py selftest`
- `venv\Scripts\python.exe scripts\golden_fixtures.py fetch`, lalu periksa isi `tests/golden/data/` dan `git status` (folder data tidak muncul).
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock`
- `venv\Scripts\python.exe scripts\golden_fixtures.py run` (Gemini flash, kuota pemilik), simpan sebagai baseline, lalu `run --compare` sekali lagi untuk melihat variasi antar run.
- `venv\Scripts\python.exe scripts\smoke_test.py` dan `venv\Scripts\python.exe scripts\check_codemap.py`.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: baru `scripts/golden_fixtures.py` (subperintah `fetch`, `run`, `score`, `selftest`), `tests/golden/labels.json`, `tests/golden/baseline.json`, `docs/codemap/golden-fixtures.md`; diubah `.gitignore` (`tests/golden/data/`), `CLAUDE.md` (bagian "Golden fixtures" + aturan prompt AI), `docs/codemap/index.md`, `docs/codemap/analisis-ai.md`, kontrak, `TASKS.md` (K3, status). Tidak ada perubahan di `backend/` maupun `scripts/smoke_test.py`.
HASIL_TEST:
- `golden_fixtures.py selftest`: 18/18 lulus (kutipan persis, fuzzy, bersambung "...", karangan, salah tempat, timestamp/hook di luar, overlap 90% vs 30%, zona sponsor 100%/80%/9%, heatmap lift, recall 50% dan n/a, compare dengan toleransi, deteksi model berbeda, model dari event SSE, SRT, hms).
- `fetch`: A 1528 baris (caption otomatis EN), B 492 baris (subtitle manual EN), C 651 baris (caption otomatis ID), heatmap 100 titik masing-masing, ±6-7 s per video. `git check-ignore -v tests/golden/data/hbZbPHjE8NE/transcript.json` → `.gitignore:56`. `git status --untracked-files=all tests` hanya `labels.json` dan `baseline.json`.
- `run --mock`: 3 video, exit 0, "Metadata dari file: 3 kali, YouTube tidak dipanggil". Klip mock dinilai buruk (karangan 18, zona terlarang 8), membuktikan penilai menangkap hasil palsu.
- `run` Gemini sebelum perbaikan model (4 run): run 1 gagal di A karena Gemini 503 "high demand" → ditambah retry. Run variasi (11:06 vs 11:10, prompt sama): karangan/salah tempat 0-1, zona terlarang 1, "tidak ada metrik yang lebih buruk".
- Setelah temuan reviewer (model yang tercatat bukan model yang dipakai): run 11:52 `--model auto` memilih `gemini-3.8-flash`, tetapi backend fallback ke `gemini-3.7-flash` untuk A dan B (terdeteksi, PERINGATAN tercetak). Ditambah ulang otomatis bila fallback. **Baseline akhir** (`run --save-baseline`, 11:57): `auto` melewati 3.8 (429 kuota habis), semua video `gemini-3.7-flash`; 36 klip (A 16, B 11, C 9), grounded 100% (salah tempat 0, karangan 0), valid 100%, duplikat 0, zona terlarang 1, heat lift 1,46, 32-133 s per video (B 2 kali retry 503).
- `--compare` tanpa Gemini (`score`): laporan 11:57 (model sama) exit 0; laporan 11:52 (C beda model) PERINGATAN + exit 3; laporan lama tanpa model exit 3.
- `venv\Scripts\python.exe scripts\smoke_test.py`: 7/7 lulus. `check_codemap.py`: SEMUA CEK LULUS (16 catatan, 217 simbol).
- `git diff --stat -- backend scripts/smoke_test.py`: kosong.
CODEMAP_DIPERBARUI: ya. Catatan baru `golden-fixtures.md` (17 simbol dengan rentang dari AST termasuk `resolve_model`, `model_used`, `model_mismatch`, `print_compare`, `unique_path`; input/output; risiko kuota dan fallback model), `index.md` (bagian "Pengujian"), `analisis-ai.md` (perubahan prompt wajib diukur, nama fungsi yang dipatch jangan diubah).
CATATAN:
- Keputusan sendiri: transkrip disimpan sebagai `transcript.json` hasil `fetch_transcript` (jalur yang sama dengan app), dikirim ke analisis sebagai SRT. Metadata asli disimpan utuh di `metadata.json`.
- Penilai versi pertama terlalu ketat (grounded A 76,7%): kutipan asli yang disambung "..." dan yang kata pengisinya dibuang ikut gagal. Diperbaiki: kutipan dipecah per potongan "...", kegagalan dibagi `misplaced` (ada di video, bukan di klip) dan `fabricated`. Dua kasus nyata di baseline dicek manual dan tepat: kutipan diucapkan di ±677 s padahal klip berakhir 673 s; potongan "they all say the same thing" tidak pernah diucapkan (asli: "but it's true...").
- Variasi antar run Gemini (prompt sama): karangan/salah tempat 0-1. `compare` menandai hitungan lebih buruk hanya bila naik > 1 (`COUNT_NOISE`), rate bila turun > 5 poin. Untuk perubahan prompt disarankan `run --repeat 2 --compare` (tercatat di `CLAUDE.md`).
- Ditambah di luar draf awal, tetap di area skrip: retry otomatis untuk error Gemini sementara (`--retries`, `--retry-wait`), laporan tetap disimpan walau ada video gagal, `raw_clips` di laporan run (di-ignore git) agar `score` bisa menilai ulang.
- `check_labels`: tidak ada catatan untuk ketiga video (semua rentang dalam durasi, tidak tumpang tindih). Klip di zona terlarang yang tertangkap memang sah: B memilih intro 0-20 s; C 54% di low-context dan 52% di outro.
- `baseline.json` hanya angka (tanpa kutipan, judul, atau transkrip). Laporan run di `tests/golden/data/runs/` memuat kutipan dan tetap lokal.
- Batasan: metrik ini mengukur kerapian/kejujuran output, belum kualitas pilihan momen. `ref_recall` menunggu K3 Tahap 2 (Shorts resmi + pilihan pemilik) sebelum #1/#2. Sampel 3 video.
- Perbaikan temuan reviewer (/tutup pertama, PASS dengan catatan): `--model auto` (default) mengunci satu model flash yang benar-benar menjawab; model yang dipakai backend dicatat per video dari event SSE langkah 4 dan disimpan di laporan serta `baseline.json` (`models_used`); video yang kena fallback model diulang; `--compare` exit 3 bila model berbeda dari baseline; baseline ditolak bila model campuran; nama laporan unik; `score --save-baseline` dicatat di `CLAUDE.md` dan codemap.
- Kuota: `gemini-2.5-flash` 404 untuk key pemilik, kuota harian `gemini-3.8-flash` habis karena uji hari ini. Bila besok `auto` memilih 3.8, `--compare` exit 3 terhadap baseline 3.7: buat ulang baseline dengan prompt lama dulu (langkah tertulis di `CLAUDE.md`).
- Perlu dicoba pemilik: jalankan `golden_fixtures.py run --compare` sekali (memakai kuota Gemini) dan pastikan hasilnya bisa dibaca.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
