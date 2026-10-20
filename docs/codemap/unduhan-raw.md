---
fitur: unduhan segmen dan video asli
file_utama: [backend/video_engine.py, backend/services/download_service.py, backend/routers/downloads.py]
---
# Unduhan raw

Dua kebutuhan: (1) segmen klip mentah untuk render ([[render-server]], [[render-browser]]), dan (2) tombol unduh video/segmen asli tanpa crop di UI. Semua lewat yt-dlp untuk YouTube, atau potong langsung dengan FFmpeg untuk file lokal (upload/Drive).

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/video_engine.py` | `download_clip_segment` | L744-1072 | Potong satu segmen, 4 metode fallback |
| `backend/video_engine.py` | potong file lokal | L763-834 | Sumber upload/Drive: cari file, potong dengan FFmpeg |
| `backend/video_engine.py` | metode 1: `--download-sections` sampai 2160p | L862-906 | Format di L867 |
| `backend/video_engine.py` | metode 2: URL stream + FFmpeg | L907-967 | Format di L919 |
| `backend/video_engine.py` | metode 3: 720p | L968-1010 | Format di L980 |
| `backend/video_engine.py` | metode 4: 480p | L1011-1072 | Format di L1023 |
| `backend/video_engine.py` | `download_full_raw_video` | L1075-1176 | Video utuh, format di L1116 |
| `backend/video_engine.py` | `get_yt_dlp_base_cmd` | L427-469 | Argumen dasar yt-dlp (proxy, cookies, header) |
| `backend/video_engine.py` | `format_section_time` | L407-416 | Format waktu untuk `--download-sections` |
| `backend/services/download_service.py` | `run_raw_download_job` | L28-85 | Job background unduh video utuh |
| `backend/services/download_service.py` | `run_raw_clip_download_job` | L88-234 | Job background unduh segmen |
| `backend/routers/downloads.py` | `handle_download_raw_video` | L23-60 | `POST /api/download-raw-video` |
| `backend/routers/downloads.py` | `get_raw_download_status` | L64-68 | `GET /api/download-raw-status/{job_id}` |
| `backend/routers/downloads.py` | `handle_download_raw_clip` | L72-111 | `POST /api/download-raw-clip` |
| `backend/routers/downloads.py` | `get_raw_clip_download_status` | L115-119 | `GET /api/download-raw-clip-status/{job_id}` |
| `src/App.tsx` | `handleDownloadRawVideo` | L1782-1880 | Tombol unduh video asli |
| `src/App.tsx` | `handleDownloadRawClip` | L1898-1985 | Tombol unduh segmen asli |

## Input / output
- Input: URL YouTube atau `/api/video/{id}`, `start_time`, `end_time`, `cookies_content` (dari `localStorage` browser).
- Output: MP4 di `backend/temp_clips/` (segmen render) atau `EXPORTS_DIR` (unduhan raw, permanen, default `~/CheatClip`), status job di dict memori `raw_download_jobs` / `raw_clip_download_jobs`.

## Risiko
- Batas kualitas `height<=2160` di L867, L919, L1116 (task #9). Fallback 720p/480p (L980, L1023) jangan diubah.
- **YouTube praktis hanya 360p** (ditemukan di task #9, target task #28): dengan `player_client=android,ios,web_embedded,mweb,web` di `get_yt_dlp_base_cmd` hanya format 18 yang tersedia. Menambah `default` memunculkan format HD klien `android_vr`, tetapi ffmpeg (dipakai `--download-sections` dan metode 2) mendapat 403 karena format itu wajib diambil per potongan 10 MB (`http_chunk_size`); downloader native yt-dlp berhasil. Akibatnya semua metode gagal berantai dan unduhan bisa > 20 menit. Sumber upload/Drive tidak terdampak (dipotong lokal di resolusi aslinya).
- Timeout dinamis (300 s + 5 s per detik klip, maks 20 menit). Unduhan lama menahan antrean render karena semaphore di [[render-server]].
- Cookies dicoba dulu, lalu mode tamu bila ditolak. Lihat [[cookies-dan-proxy]].
- Sumber `upload_`/`gdrive_` tidak pernah dikirim ke YouTube. Kalau file lokalnya sudah dihapus cleanup, render gagal ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sumber-video]]
