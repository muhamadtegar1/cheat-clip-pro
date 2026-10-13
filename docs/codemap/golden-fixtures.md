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
| `scripts/golden_fixtures.py` | `cmd_fetch` | L283-311 | Ambil metadata, heatmap ([[sumber-video]]) dan transkrip ([[transkrip]]) lewat fungsi backend yang sama dengan app |
| `scripts/golden_fixtures.py` | `cmd_run` | L393-510 | `POST /api/analyze` lewat `TestClient`, transkrip sebagai `subtitles`, `fetch_video_metadata` diganti data tersimpan, `fetch_transcript`/unduh audio diblokir. Retry untuk error Gemini sementara dan bila backend fallback ke model lain |
| `scripts/golden_fixtures.py` | `resolve_model` | L352-369 | `auto`: model flash pertama (urutan `get_flash_models_for_key`) yang menjawab permintaan kecil; model 404/429 dilewati |
| `scripts/golden_fixtures.py` | `model_used` | L372-377 | Model yang benar-benar menjawab, dari event SSE langkah 4 "Clip Verification & Alignment" (`successful_model`) |
| `scripts/golden_fixtures.py` | `model_mismatch` | L380-382 | Video yang modelnya berbeda dari `models_used` baseline |
| `scripts/golden_fixtures.py` | `unique_path` | L385-390 | Nama laporan run tidak saling menimpa |
| `scripts/golden_fixtures.py` | `cmd_score` | L611-640 | Nilai ulang `raw_clips` dari laporan run tanpa Gemini |
| `scripts/golden_fixtures.py` | `cmd_selftest` | L645-709 | 18 kasus buatan untuk semua metrik, `compare`, dan deteksi model |
| `scripts/golden_fixtures.py` | `score_video` | L171-233 | Semua metrik satu video: grounded/misplaced/fabricated, valid_time, duplicates, avoid_hits, heat_lift, ref_recall |
| `scripts/golden_fixtures.py` | `classify_quote` | L148-158 | Kutipan `grounded` (sekitar klip ±5 s), `misplaced` (ada di video, bukan di klip), `fabricated` |
| `scripts/golden_fixtures.py` | `quote_fragments` | L116-120 | Kutipan bersambung "..." dipecah per potongan (≥ 3 kata) |
| `scripts/golden_fixtures.py` | `text_contains` | L123-140 | Cocok persis atau fuzzy (`QUOTE_MATCH` 0,85) dengan jendela kata |
| `scripts/golden_fixtures.py` | `compare` | L255-278 | Rate turun > `WORSE_RATE` (5 poin) atau hitungan naik > `COUNT_NOISE` (1) = LEBIH BURUK |
| `scripts/golden_fixtures.py` | `finish` | L560-606 | Total, laporan run, simpan baseline (hanya angka + `models_used`, ditolak bila model campuran), `--compare` |
| `scripts/golden_fixtures.py` | `print_compare` | L535-557 | Tabel selisih. Exit 2 = ada metrik lebih buruk, exit 3 = model berbeda dari baseline (tidak setara) |
| `scripts/golden_fixtures.py` | `check_labels` | L323-336 | Cek kewajaran label (dalam durasi, tidak tumpang tindih), hanya dicatat |
| `scripts/golden_fixtures.py` | `lines_to_srt` | L103-111 | Transkrip tersimpan → SRT untuk `parse_manual_subtitles` |

## Input / output
- Input: `tests/golden/labels.json` (di-commit: ID video, rentang "jangan dipilih", `references` kosong sampai Tahap 2), `tests/golden/data/<video_id>/metadata.json` + `transcript.json` (di-ignore git), `GEMINI_API_KEY` dari `backend/.env`.
- Output: laporan `tests/golden/data/runs/<waktu>.json` (memuat klip mentah dan `models_used`, di-ignore git), `tests/golden/baseline.json` (di-commit, hanya angka + model per video), exit 0 / 1 (gagal) / 2 (ada metrik lebih buruk) / 3 (model berbeda dari baseline).

## Risiko
- Transkrip milik channel lain: jangan pernah commit `tests/golden/data/`. Hilang bila folder dihapus; `fetch --force` mengambil ulang, tetapi caption otomatis YouTube bisa sedikit berbeda dan baseline perlu dibuat ulang.
- Hasil Gemini bervariasi dengan prompt sama: karangan/salah tempat 0-1 antar run, klip di zona terlarang 1. Untuk perubahan prompt pakai `run --repeat 2 --compare`.
- Bergantung pada nama `fetch_video_metadata`, `fetch_transcript`, `download_youtube_audio_file` yang diimpor di `backend/routers/analyze.py` (dipatch di modul itu). Mengganti nama atau cara impor memutus skrip ini.
- Memakai kuota Gemini: ±3 analisis per run plus satu permintaan kecil per model saat `auto`, Video A (52 menit) paling besar. Gemini yang sibuk (503) atau fallback ke model lain diulang otomatis 2 kali. Kuota harian per model (free tier) bisa habis: pada 2026-10-13 `gemini-2.5-flash` 404 untuk key pemilik dan `gemini-3.8-flash` 429 setelah beberapa run, jadi `auto` memilih `gemini-3.7-flash`.
- Backend memilih model sendiri bila model yang diminta gagal (fallback di [[analisis-ai]]). Karena itu model dicatat per video dan `--compare` exit 3 bila berbeda dari baseline. Saat model yang tersedia berganti (mis. kuota), buat ulang baseline dari prompt lama dulu sebelum mengukur perubahan prompt.
- `score <laporan> --save-baseline` menimpa baseline dari laporan yang dinilai ulang. Pakai hanya bila penilai (bukan prompt) diubah.
- `ref_recall` masih "n/a" sampai label Tahap 2 (Shorts resmi) diisi sebelum task #1/#2.

## Terkait
[[index]] · [[analisis-ai]] · [[transkrip]] · [[sumber-video]]
