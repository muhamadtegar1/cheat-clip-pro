---
fitur: transkrip
file_utama: [backend/services/youtube_service.py, backend/video_engine.py, backend/utils/text.py, backend/routers/analyze.py, scripts/whisper_bench.py]
---
# Transkrip

Langkah 3 dari `POST /api/analyze`. Menghasilkan `transcript_lines` berformat `[{"text", "start", "duration"}]`. Urutan sumber: subtitle manual dari user → rantai 7 tier (YouTube) → Whisper lokal sebagai fallback terakhir.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | transkrip upload (Whisper) | L450-545 | Subtitle manual atau `transcribe_local_video_file` (#39: `language=request.audio_language`, L500) |
| `backend/routers/analyze.py` | transkrip YouTube | L637-856 | Subtitle manual → `fetch_transcript` → fallback Whisper |
| `backend/routers/analyze.py` | fallback Whisper YouTube | L743-856 | Unduh audio lalu transkripsi lokal; bila heatmap kosong, heatmap energi audio dari audio itu (`heatmap_source = "audio"`, #32). #39: `language=request.audio_language` (L806) |
| `backend/routers/analyze.py` | potong rentang + skor engagement | L857-906 | `range_start`/`range_end`, gabung dengan heatmap |
| `backend/services/youtube_service.py` | `fetch_transcript` | L607-801 | Orkestrator 7 tier (Supadata, proxy, langsung) |
| `backend/services/youtube_service.py` | `fetch_transcript_supadata` | L294-363 | Tier 1, API Supadata dengan rotasi key |
| `backend/services/youtube_service.py` | `get_supadata_usage_data` | L422-472 | Kuota Supadata (`GET /api/supadata-usage`) |
| `backend/services/youtube_service.py` | `fetch_transcript_cli` | L121-163 | Tier 3/6, CLI youtube-transcript-api di subprocess |
| `backend/services/youtube_service.py` | `fetch_transcript_ytdlp` | L475-541 | Tier 4/7, caption via yt-dlp |
| `backend/services/youtube_service.py` | `prioritize_transcripts` | L86-118 | Urutkan trek: bahasa asli video dulu, manual sebelum otomatis |
| `backend/services/youtube_service.py` | `normalize_transcript` | L35-83 | Seragamkan format semua tier |
| `backend/services/youtube_service.py` | `download_youtube_audio_file` | L544-604 | Audio untuk fallback Whisper |
| `backend/video_engine.py` | `transcribe_local_video_file` | L688-747 | Whisper untuk transkrip penuh. #39: `language` dipilih = dikirim ke Whisper tanpa `initial_prompt`; None = Otomatis (argumen sama dengan sebelum #39, `initial_prompt` "Bahasa Indonesia atau English") |
| `backend/video_engine.py` | `resolve_whisper_model_name` | L259-268 | #38: nama model dari env `CHEAT_CLIP_WHISPER_MODEL` (bisa di `backend/.env`); kosong = `WHISPER_DEFAULT_MODEL` (`small`, pilihan pemilik #38), nama di luar `WHISPER_KNOWN_MODELS` = peringatan + `base`. Dibaca saat model pertama dimuat, jadi ganti env butuh restart backend |
| `backend/video_engine.py` | `get_whisper_model` | L285-296 | Muat model Whisper secara lazy (nama dari `resolve_whisper_model_name`, dicatat di log); satu instance global untuk transkrip analisis dan subtitle klip |
| `backend/video_engine.py` | `normalize_audio_language` | L275-282 | #39: kode bahasa dari `WHISPER_AUDIO_LANGUAGES` (L272: en, id, ms, es, pt, fr, de, ar, hi, ja, ko) atau None (kosong/`auto`); kode lain = ValueError. Dipakai kedua fungsi transkripsi dan validator schema |
| `backend/video_engine.py` | `release_whisper_model` | L299-310 | Lepas model dari RAM (tidak dipanggil di mana pun) |
| `scripts/whisper_bench.py` | `main` | L141-222 | #38: ukur model Whisper pada potongan audio lokal; tiap model di proses anak, tabel + JSON di `tests/whisper_bench/` (di-ignore git) |
| `scripts/whisper_bench.py` | `worker` | L109-129 | Proses anak: muat model, `transcribe` dengan opsi sama seperti `transcribe_clip_words`, RAM puncak lewat `peak_memory_mb` |
| `scripts/whisper_bench.py` | `load_reference` | L87-100 | Acuan `.txt` atau JSON transkrip; JSON dirapatkan ke baris utuh di dalam rentang |
| `scripts/whisper_bench.py` | `word_error_rate` | L74-84 | WER kata (setelah `normalize_words`), juga dipakai untuk kestabilan run 1 vs run 2 |
| `backend/utils/text.py` | `parse_manual_subtitles` | L28-114 | Parser SRT/TXT dari user |
| `backend/utils/text.py` | `detect_transcript_language` | L245-359 | Deteksi bahasa untuk aturan zero-translation di [[analisis-ai]] |
| `backend/utils/text.py` | `parse_time_str` | L4-26 | Parse timestamp |

## Input / output
- Input: `video_id`, `request.subtitles` (opsional), `request.proxy`, `request.cookies`, `SUPADATA_API_KEY(S)` dan `WEBSHARE_*` dari `.env`.
- Output: `transcript_lines` lalu `enriched_transcript` (`start`, `end`, `text`, `engagement`) yang dipakai prompt di [[analisis-ai]] dan dikirim ke frontend sebagai `AnalyzeResponse.transcript`.

## Risiko
- Tanpa Supadata/proxy, YouTube sering memblokir (bot check). Tier langsung bisa gagal di IP rumahan. Lihat [[cookies-dan-proxy]].
- Fallback Whisper memakan CPU/RAM besar dan lambat untuk video panjang. Model berbagi instance global dengan transkripsi kata per kata di [[subtitle-dan-judul]].
- Model Whisper (#38) dipilih lewat `CHEAT_CLIP_WHISPER_MODEL`. Model lebih besar memperlambat fallback Whisper analisis dan subtitle klip sekaligus (satu model global). Model `.en` merusak video non-Inggris: default wajib multibahasa sampai ada pilihan bahasa (#39). Data ukur di laptop pemilik: kontrak `docs/tasks/CHEAT-38.md`.
- Bahasa audio (#39) hanya berlaku di jalur Whisper (upload/Drive, YouTube tanpa caption); YouTube dengan caption tidak berubah. Bahasa yang dipilih dipaksakan ke Whisper, jadi salah pilih = Whisper menerjemahkan kasar ke bahasa itu (uji 2026-10-20: audio Inggris dengan `id` menjadi terjemahan Indonesia yang kacau), bukan transkrip ucapan. Deteksi bahasa untuk prompt Gemini tetap dari teks transkrip ([[analisis-ai]]).
- Kutipan (`key_quotes`) dari AI tidak dicek ke transkrip ini (target task #12).

## Terkait
[[index]] · [[sumber-video]] · [[analisis-ai]] · [[subtitle-dan-judul]] · [[cookies-dan-proxy]]
