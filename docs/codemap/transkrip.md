---
fitur: transkrip
file_utama: [backend/services/youtube_service.py, backend/video_engine.py, backend/utils/text.py, backend/routers/analyze.py]
---
# Transkrip

Langkah 3 dari `POST /api/analyze`. Menghasilkan `transcript_lines` berformat `[{"text", "start", "duration"}]`. Urutan sumber: subtitle manual dari user → rantai 7 tier (YouTube) → Whisper lokal sebagai fallback terakhir.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | transkrip upload (Whisper) | L373-468 | Subtitle manual atau `transcribe_local_video_file` |
| `backend/routers/analyze.py` | transkrip YouTube | L559-777 | Subtitle manual → `fetch_transcript` → fallback Whisper |
| `backend/routers/analyze.py` | fallback Whisper YouTube | L665-777 | Unduh audio lalu transkripsi lokal |
| `backend/routers/analyze.py` | potong rentang + skor engagement | L778-827 | `range_start`/`range_end`, gabung dengan heatmap |
| `backend/services/youtube_service.py` | `fetch_transcript` | L607-801 | Orkestrator 7 tier (Supadata, proxy, langsung) |
| `backend/services/youtube_service.py` | `fetch_transcript_supadata` | L294-363 | Tier 1, API Supadata dengan rotasi key |
| `backend/services/youtube_service.py` | `get_supadata_usage_data` | L422-472 | Kuota Supadata (`GET /api/supadata-usage`) |
| `backend/services/youtube_service.py` | `fetch_transcript_cli` | L121-163 | Tier 3/6, CLI youtube-transcript-api di subprocess |
| `backend/services/youtube_service.py` | `fetch_transcript_ytdlp` | L475-541 | Tier 4/7, caption via yt-dlp |
| `backend/services/youtube_service.py` | `prioritize_transcripts` | L86-118 | Urutkan trek: bahasa asli video dulu, manual sebelum otomatis |
| `backend/services/youtube_service.py` | `normalize_transcript` | L35-83 | Seragamkan format semua tier |
| `backend/services/youtube_service.py` | `download_youtube_audio_file` | L544-604 | Audio untuk fallback Whisper |
| `backend/video_engine.py` | `transcribe_local_video_file` | L638-685 | Whisper untuk transkrip penuh |
| `backend/video_engine.py` | `get_whisper_model` | L251-261 | Muat model Whisper `base` secara lazy |
| `backend/video_engine.py` | `release_whisper_model` | L264-275 | Lepas model dari RAM |
| `backend/utils/text.py` | `parse_manual_subtitles` | L28-114 | Parser SRT/TXT dari user |
| `backend/utils/text.py` | `detect_transcript_language` | L245-359 | Deteksi bahasa untuk aturan zero-translation di [[analisis-ai]] |
| `backend/utils/text.py` | `parse_time_str` | L4-26 | Parse timestamp |

## Input / output
- Input: `video_id`, `request.subtitles` (opsional), `request.proxy`, `request.cookies`, `SUPADATA_API_KEY(S)` dan `WEBSHARE_*` dari `.env`.
- Output: `transcript_lines` lalu `enriched_transcript` (`start`, `end`, `text`, `engagement`) yang dipakai prompt di [[analisis-ai]] dan dikirim ke frontend sebagai `AnalyzeResponse.transcript`.

## Risiko
- Tanpa Supadata/proxy, YouTube sering memblokir (bot check). Tier langsung bisa gagal di IP rumahan. Lihat [[cookies-dan-proxy]].
- Fallback Whisper memakan CPU/RAM besar dan lambat untuk video panjang. Model berbagi instance global dengan transkripsi kata per kata di [[subtitle-dan-judul]].
- Kutipan (`key_quotes`) dari AI tidak dicek ke transkrip ini (target task #12).

## Terkait
[[index]] · [[sumber-video]] · [[analisis-ai]] · [[subtitle-dan-judul]] · [[cookies-dan-proxy]]
