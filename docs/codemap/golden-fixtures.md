---
fitur: golden fixtures analisis AI
file_utama: [scripts/golden_fixtures.py, tests/golden/labels.json, tests/golden/baseline.json]
---
# Golden fixtures

Alat ukur untuk perubahan prompt AI (task 17b). Tiga video K3 (podcast EN, edukasi EN, gaming ID) dianalisis ulang dari transkrip tersimpan, lalu hasilnya dinilai dengan metrik objektif dan dibandingkan dengan baseline. Wajib dijalankan untuk setiap perubahan prompt di [[analisis-ai]] (task #1, #2, #12).

Alur: `fetch` (sekali) → `run` (Gemini flash) → nilai → laporan di `tests/golden/data/runs/` → `--compare` dengan `tests/golden/baseline.json`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `scripts/golden_fixtures.py` | `cmd_fetch` | L279-307 | Ambil metadata, heatmap ([[sumber-video]]) dan transkrip ([[transkrip]]) lewat fungsi backend yang sama dengan app |
| `scripts/golden_fixtures.py` | `cmd_run` | L348-447 | `POST /api/analyze` lewat `TestClient`, transkrip sebagai `subtitles`, `fetch_video_metadata` diganti data tersimpan, `fetch_transcript`/unduh audio diblokir. Retry untuk error Gemini sementara |
| `scripts/golden_fixtures.py` | `cmd_score` | L523-551 | Nilai ulang `raw_clips` dari laporan run tanpa Gemini |
| `scripts/golden_fixtures.py` | `cmd_selftest` | L556-613 | 16 kasus buatan untuk semua metrik dan `compare` |
| `scripts/golden_fixtures.py` | `score_video` | L167-229 | Semua metrik satu video: grounded/misplaced/fabricated, valid_time, duplicates, avoid_hits, heat_lift, ref_recall |
| `scripts/golden_fixtures.py` | `classify_quote` | L144-154 | Kutipan `grounded` (sekitar klip ±5 s), `misplaced` (ada di video, bukan di klip), `fabricated` |
| `scripts/golden_fixtures.py` | `quote_fragments` | L112-116 | Kutipan bersambung "..." dipecah per potongan (≥ 3 kata) |
| `scripts/golden_fixtures.py` | `text_contains` | L119-136 | Cocok persis atau fuzzy (`QUOTE_MATCH` 0,85) dengan jendela kata |
| `scripts/golden_fixtures.py` | `compare` | L251-274 | Rate turun > `WORSE_RATE` (5 poin) atau hitungan naik > `COUNT_NOISE` (1) = LEBIH BURUK |
| `scripts/golden_fixtures.py` | `finish` | L477-518 | Total, laporan run, simpan baseline (hanya angka), `--compare` |
| `scripts/golden_fixtures.py` | `check_labels` | L319-332 | Cek kewajaran label (dalam durasi, tidak tumpang tindih), hanya dicatat |
| `scripts/golden_fixtures.py` | `lines_to_srt` | L99-107 | Transkrip tersimpan → SRT untuk `parse_manual_subtitles` |

## Input / output
- Input: `tests/golden/labels.json` (di-commit: ID video, rentang "jangan dipilih", `references` kosong sampai Tahap 2), `tests/golden/data/<video_id>/metadata.json` + `transcript.json` (di-ignore git), `GEMINI_API_KEY` dari `backend/.env`.
- Output: laporan `tests/golden/data/runs/<waktu>.json` (memuat klip mentah, di-ignore git), `tests/golden/baseline.json` (di-commit, hanya angka), exit 0 / 1 (gagal) / 2 (ada metrik lebih buruk).

## Risiko
- Transkrip milik channel lain: jangan pernah commit `tests/golden/data/`. Hilang bila folder dihapus; `fetch --force` mengambil ulang, tetapi caption otomatis YouTube bisa sedikit berbeda dan baseline perlu dibuat ulang.
- Hasil Gemini bervariasi dengan prompt sama: karangan/salah tempat 0-1 antar run, klip di zona terlarang 1. Untuk perubahan prompt pakai `run --repeat 2 --compare`.
- Bergantung pada nama `fetch_video_metadata`, `fetch_transcript`, `download_youtube_audio_file` yang diimpor di `backend/routers/analyze.py` (dipatch di modul itu). Mengganti nama atau cara impor memutus skrip ini.
- Memakai kuota Gemini: ±3 analisis per run, Video A (52 menit) paling besar. Gemini yang sibuk (503) diulang otomatis 2 kali.
- `ref_recall` masih "n/a" sampai label Tahap 2 (Shorts resmi) diisi sebelum task #1/#2.

## Terkait
[[index]] · [[analisis-ai]] · [[transkrip]] · [[sumber-video]]
