---
fitur: unduhan segmen dan video asli
file_utama: [backend/video_engine.py, backend/services/download_service.py, backend/routers/downloads.py]
---
# Unduhan raw

Dua kebutuhan: (1) segmen klip mentah untuk render ([[render-server]], [[render-browser]]), dan (2) tombol unduh video/segmen asli tanpa crop di UI. Semua lewat yt-dlp untuk YouTube, atau potong langsung dengan FFmpeg untuk file lokal (upload/Drive).

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/video_engine.py` | `download_clip_segment` | L688-1016 | Potong satu segmen, 4 metode fallback |
| `backend/video_engine.py` | potong file lokal | L707-778 | Sumber upload/Drive: cari file, potong dengan FFmpeg |
| `backend/video_engine.py` | metode 1: `--download-sections` 1080p | L806-850 | Format di L811 |
| `backend/video_engine.py` | metode 2: URL stream + FFmpeg | L851-911 | Format di L863 |
| `backend/video_engine.py` | metode 3: 720p | L912-954 | Format di L924 |
| `backend/video_engine.py` | metode 4: 480p | L955-1016 | Format di L967 |
| `backend/video_engine.py` | `download_full_raw_video` | L1019-1120 | Video utuh, format di L1060 |
| `backend/video_engine.py` | `get_yt_dlp_base_cmd` | L392-434 | Argumen dasar yt-dlp (proxy, cookies, header) |
| `backend/video_engine.py` | `format_section_time` | L372-381 | Format waktu untuk `--download-sections` |
| `backend/services/download_service.py` | `run_raw_download_job` | L28-85 | Job background unduh video utuh |
| `backend/services/download_service.py` | `run_raw_clip_download_job` | L88-234 | Job background unduh segmen |
| `backend/routers/downloads.py` | `handle_download_raw_video` | L23-60 | `POST /api/download-raw-video` |
| `backend/routers/downloads.py` | `get_raw_download_status` | L64-68 | `GET /api/download-raw-status/{job_id}` |
| `backend/routers/downloads.py` | `handle_download_raw_clip` | L72-111 | `POST /api/download-raw-clip` |
| `backend/routers/downloads.py` | `get_raw_clip_download_status` | L115-119 | `GET /api/download-raw-clip-status/{job_id}` |
| `src/App.tsx` | `handleDownloadRawVideo` | L1765-1863 | Tombol unduh video asli |
| `src/App.tsx` | `handleDownloadRawClip` | L1881-1968 | Tombol unduh segmen asli |

## Input / output
- Input: URL YouTube atau `/api/video/{id}`, `start_time`, `end_time`, `cookies_content` (dari `localStorage` browser).
- Output: MP4 di `backend/temp_clips/` (segmen render) atau `EXPORTS_DIR` (unduhan raw, permanen, default `~/CheatClip`), status job di dict memori `raw_download_jobs` / `raw_clip_download_jobs`.

## Risiko
- Batas kualitas `height<=1080` di L806, L858, L1055 (target task #9: naik ke 2160p). Fallback 720p/480p (L919, L962) jangan diubah.
- Timeout dinamis (300 s + 5 s per detik klip, maks 20 menit). Unduhan lama menahan antrean render karena semaphore di [[render-server]].
- Cookies dicoba dulu, lalu mode tamu bila ditolak. Lihat [[cookies-dan-proxy]].
- Sumber `upload_`/`gdrive_` tidak pernah dikirim ke YouTube. Kalau file lokalnya sudah dihapus cleanup, render gagal ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sumber-video]]
