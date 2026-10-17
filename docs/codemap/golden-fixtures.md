---
fitur: golden fixtures analisis AI
file_utama: [scripts/golden_fixtures.py, tests/golden/labels.json, tests/golden/baseline.json]
---
# Golden fixtures

Alat ukur untuk perubahan prompt AI (task 17b). Tiga video K3 (podcast EN, edukasi EN, gaming ID) dianalisis ulang dari transkrip tersimpan, lalu hasilnya dinilai dengan metrik objektif dan dibandingkan dengan baseline. Wajib dijalankan untuk setiap perubahan prompt di [[analisis-ai]] (task #1, #2, #12).

Alur: `fetch` (sekali) → `run` (`--model auto`: satu model flash yang menjawab, dikunci untuk semua video) → nilai → laporan di `tests/golden/data/runs/` → `--compare` dengan `tests/golden/baseline.json`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `scripts/golden_fixtures.py` | `cmd_fetch` | L290-318 | Ambil metadata, heatmap ([[sumber-video]]) dan transkrip ([[transkrip]]) lewat fungsi backend yang sama dengan app |
| `scripts/golden_fixtures.py` | `cmd_run` | L416-553 | `POST /api/analyze` lewat `TestClient`, transkrip sebagai `subtitles`, `fetch_video_metadata` diganti data tersimpan, `fetch_transcript`/unduh audio diblokir. `--no-heatmap` (#31): heatmap kosong dikirim ke backend, dicek lewat `heatmap_sent`; run gagal bila backend tetap menerima heatmap. Retry untuk error Gemini sementara dan bila backend fallback ke model lain. Kuota habis di semua model (`EXHAUSTED_RE`): berhenti tanpa retry, video sisanya dilewati |
| `scripts/golden_fixtures.py` | `resolve_model` | L359-377 | `auto`: model flash pertama (urutan `get_flash_models_for_key`) yang menjawab permintaan kecil; model 404/429 dilewati |
| `scripts/golden_fixtures.py` | `model_used` | L380-385 | Model yang benar-benar menjawab, dari event SSE langkah 4 "Clip Verification & Alignment" (`successful_model`) |
| `scripts/golden_fixtures.py` | `model_mismatch` | L388-390 | Video yang modelnya berbeda dari `models_used` baseline |
| `scripts/golden_fixtures.py` | `heatmap_sent` | L393-400 | Dari event SSE langkah 2: `Retention Decoded` = backend menerima heatmap, `Dialogue Fallback` = tidak |
| `scripts/golden_fixtures.py` | `baseline_path` | L403-405 | Mode `none` (`--no-heatmap`) memakai `tests/golden/baseline-noheatmap.json`, mode biasa `tests/golden/baseline.json` |
| `scripts/golden_fixtures.py` | `unique_path` | L408-413 | Nama laporan run tidak saling menimpa |
| `scripts/golden_fixtures.py` | `cmd_score` | L663-692 | Nilai ulang `raw_clips` dari laporan run tanpa Gemini, mengikuti mode heatmap laporan |
| `scripts/golden_fixtures.py` | `cmd_selftest` | L697-773 | 21 kasus buatan untuk semua metrik, `compare`, deteksi model, kuota habis, baseline per mode heatmap, dan `heatmap_sent` |
| `scripts/golden_fixtures.py` | `score_video` | L178-240 | Semua metrik satu video: grounded/misplaced/fabricated, valid_time, duplicates, avoid_hits, heat_lift, ref_recall |
| `scripts/golden_fixtures.py` | `classify_quote` | L155-165 | Kutipan `grounded` (sekitar klip ±5 s), `misplaced` (ada di video, bukan di klip), `fabricated` |
| `scripts/golden_fixtures.py` | `quote_fragments` | L123-127 | Kutipan bersambung "..." dipecah per potongan (≥ 3 kata) |
| `scripts/golden_fixtures.py` | `text_contains` | L130-147 | Cocok persis atau fuzzy (`QUOTE_MATCH` 0,85) dengan jendela kata |
| `scripts/golden_fixtures.py` | `compare` | L262-285 | Rate turun > `WORSE_RATE` (5 poin) atau hitungan naik > `COUNT_NOISE` (1) = LEBIH BURUK |
| `scripts/golden_fixtures.py` | `finish` | L608-658 | Total, laporan run (akhiran `-noheatmap` untuk mode tanpa heatmap), simpan baseline ke file sesuai mode (hanya angka + `models_used`, ditolak bila model campuran), `--compare` |
| `scripts/golden_fixtures.py` | `print_compare` | L578-605 | Tabel selisih terhadap baseline mode yang sama. Exit 2 = ada metrik lebih buruk, exit 3 = model atau mode heatmap berbeda dari baseline (tidak setara) |
| `scripts/golden_fixtures.py` | `check_labels` | L330-343 | Cek kewajaran label (dalam durasi, tidak tumpang tindih), hanya dicatat |
| `scripts/golden_fixtures.py` | `lines_to_srt` | L110-118 | Transkrip tersimpan → SRT untuk `parse_manual_subtitles` |

## Input / output
- Input: `tests/golden/labels.json` (di-commit: ID video, rentang "jangan dipilih", `references` Tahap 2: 4 momen per video yang dinilai layak pemilik, dengan `source` gemini/heatmap/short, `verified`, `kind`, `note`; skrip hanya membaca `start`/`end`), `tests/golden/data/<video_id>/metadata.json` + `transcript.json` (di-ignore git), `GEMINI_API_KEY` dari `backend/.env`.
- Output: laporan `tests/golden/data/runs/<waktu>.json` (memuat klip mentah dan `models_used`, di-ignore git), `tests/golden/baseline.json` (di-commit, hanya angka + model per video), `tests/golden/baseline-noheatmap.json` (sama, untuk `--no-heatmap`, mencatat `heatmap: "none"`), exit 0 / 1 (gagal) / 2 (ada metrik lebih buruk) / 3 (model berbeda dari baseline).

## Risiko
- Transkrip milik channel lain: jangan pernah commit `tests/golden/data/`. Hilang bila folder dihapus; `fetch --force` mengambil ulang, tetapi caption otomatis YouTube bisa sedikit berbeda dan baseline perlu dibuat ulang.
- Hasil Gemini bervariasi dengan prompt sama: karangan/salah tempat 0-1 antar run, klip di zona terlarang 1. Untuk perubahan prompt pakai `run --repeat 2 --compare`.
- Bergantung pada nama `fetch_video_metadata`, `fetch_transcript`, `download_youtube_audio_file` yang diimpor di `backend/routers/analyze.py` (dipatch di modul itu). Mengganti nama atau cara impor memutus skrip ini.
- Memakai kuota Gemini: ±3 analisis per run plus satu permintaan kecil per model saat `auto`, Video A (52 menit) paling besar. Gemini yang sibuk (503) atau fallback ke model lain diulang otomatis 2 kali. Kuota harian per model (free tier) bisa habis: pada 2026-10-13 `gemini-2.5-flash` 404 untuk key pemilik dan `gemini-3.8-flash` 429 setelah beberapa run, jadi `auto` memilih `gemini-3.7-flash`.
- Backend memilih model sendiri bila model yang diminta gagal (fallback di [[analisis-ai]]). Karena itu model dicatat per video dan `--compare` exit 3 bila berbeda dari baseline. Saat model yang tersedia berganti (mis. kuota), buat ulang baseline dari prompt lama dulu sebelum mengukur perubahan prompt.
- `score <laporan> --save-baseline` menimpa baseline dari laporan yang dinilai ulang. Pakai hanya bila penilai (bukan prompt) diubah.
- `ref_recall` aktif sejak K3 Tahap 2 (2026-10-17): baseline 70,85% (run 20261013-150232 dinilai ulang dengan `score --save-baseline`, klip dan model sama). Momen yang terlewat: A masa kecil (heatmap), B analogi saham, C kuyang sekali tembak (keduanya pilihan Gemini), C happy ending di satu ulangan. `per_video` di baseline hanya ulangan terakhir; `total` rata-rata semua ulangan.
- `--no-heatmap` mengukur persis jalur YouTube tanpa heatmap. Untuk upload/Drive hanya pendekatan: app di sana memakai heatmap energi audio (`compute_audio_energy_heatmap`), yang tidak bisa disimulasikan karena unduh audio diblokir di skrip ini. Perubahan prompt (#1, #2, #32) sebaiknya diukur di kedua mode: `run --repeat 2 --compare` dan `run --no-heatmap --repeat 2 --compare`.
- Referensi bukan ground truth objektif: 12 momen, 6 dari kandidat Gemini dan 6 dari puncak heatmap, semuanya dinilai pemilik. Batas dirapikan ke kalimat utuh dari transkrip, bukan dari Gemini (Gemini sering mulai/selesai 2-14 s meleset dan salah menulis angka).

## Terkait
[[index]] · [[analisis-ai]] · [[transkrip]] · [[sumber-video]]
