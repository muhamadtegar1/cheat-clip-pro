---
fitur: unduhan segmen dan video asli
file_utama: [backend/video_engine.py, backend/services/download_service.py, backend/routers/downloads.py]
---
# Unduhan raw

Dua kebutuhan: (1) segmen klip mentah untuk render ([[render-server]], [[render-browser]]), dan (2) tombol unduh video/segmen asli tanpa crop di UI. Semua lewat yt-dlp untuk YouTube, atau potong langsung dengan FFmpeg untuk file lokal (upload/Drive).

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/video_engine.py` | `download_clip_segment` | L952-1289 | Potong satu segmen, 4 metode fallback |
| `backend/video_engine.py` | potong file lokal | L971-1042 | Sumber upload/Drive: cari file, potong dengan FFmpeg. #28: juga memotong segmen dari cache HD YouTube |
| `backend/video_engine.py` | pemanggilan cache HD (#28) | L1052-1059 | Setelah guard upload/Drive: `get_youtube_hd_cache`, lalu panggil ulang `download_clip_segment` dengan path cache (jalur potong lokal). Gagal = lanjut ke metode 1 |
| `backend/video_engine.py` | metode 1: `--download-sections` sampai 2160p | L1079-1123 | Format di L1084 |
| `backend/video_engine.py` | metode 2: URL stream + FFmpeg | L1124-1184 | Format di L1136 |
| `backend/video_engine.py` | metode 3: 720p | L1185-1227 | Format di L1197 |
| `backend/video_engine.py` | metode 4: 480p | L1228-1289 | Format di L1240 |
| `backend/video_engine.py` | `download_full_raw_video` | L1292-1393 | Video utuh, format di L1333 |
| `backend/video_engine.py` | `get_yt_dlp_base_cmd` | L427-475 | Argumen dasar yt-dlp (proxy, cookies, header). #28: `solve_js_challenges=False` (default) = `--no-js-runtimes` (yt-dlp-ejs mati, YouTube hanya format 18 seperti sebelum #28); `True` = `--js-runtimes deno/node`, hanya dipakai `get_youtube_hd_cache` |
| `backend/video_engine.py` | konstanta cache HD (#28) | L755-770 | `YT_HD_CACHE_SUBDIR` (`yt_cache`), 1080p maks / 720p min, `YT_HD_CACHE_FORMAT` (H.264 > VP9 > lain), batas 2 GB, 2 kali ekstraksi, lock per video |
| `backend/video_engine.py` | `yt_hd_cache_enabled` | L773-775 | Saklar `CHEAT_CLIP_YT_HD_CACHE` (`0`/`false`/`off`/`no` = mati), dibaca saat dipanggil |
| `backend/video_engine.py` | `yt_hd_cache_max_bytes` | L778-785 | Batas perkiraan ukuran `CHEAT_CLIP_YT_HD_CACHE_MAX_GB` (default 2) |
| `backend/video_engine.py` | `extract_youtube_video_id` | L788-796 | ID 11 karakter dari URL watch/youtu.be/shorts/embed/live atau ID polos |
| `backend/video_engine.py` | `yt_hd_cache_path` | L799-800 | `TEMP_DIR/yt_cache/<id>_1080p.mp4` |
| `backend/video_engine.py` | `_yt_hd_cache_extract` | L832-860 | `yt-dlp -J -f YT_HD_CACHE_FORMAT`: tolak bila tinggi < 720, hitung perkiraan ukuran, simpan info JSON |
| `backend/video_engine.py` | `_yt_hd_cache_download` | L863-875 | Unduh native dari `--load-info-json` (tanpa ekstraksi ulang), `--no-mtime` |
| `backend/video_engine.py` | `get_youtube_hd_cache` | L886-949 | Inti #28: saklar, lock per video, pakai ulang (segarkan mtime), cookies lalu tamu, coba ulang ekstraksi, batas ukuran, validasi `ffprobe` tinggi >= 720, rename atomik. Gagal = `None` |
| `backend/video_engine.py` | `format_section_time` | L407-416 | Format waktu untuk `--download-sections` |
| `backend/services/download_service.py` | `run_raw_download_job` | L28-85 | Job background unduh video utuh |
| `backend/services/download_service.py` | `run_raw_clip_download_job` | L88-234 | Job background unduh segmen |
| `backend/routers/downloads.py` | `handle_download_raw_video` | L23-60 | `POST /api/download-raw-video` |
| `backend/routers/downloads.py` | `get_raw_download_status` | L64-68 | `GET /api/download-raw-status/{job_id}` |
| `backend/routers/downloads.py` | `handle_download_raw_clip` | L72-111 | `POST /api/download-raw-clip` |
| `backend/routers/downloads.py` | `get_raw_clip_download_status` | L115-119 | `GET /api/download-raw-clip-status/{job_id}` |
| `src/App.tsx` | `handleDownloadRawVideo` | L1792-1890 | Tombol unduh video asli |
| `src/App.tsx` | `handleDownloadRawClip` | L1933-2020 | Tombol unduh segmen asli |

## Input / output
- Input: URL YouTube atau `/api/video/{id}`, `start_time`, `end_time`, `cookies_content` (dari `localStorage` browser).
- Output: MP4 di `backend/temp_clips/` (segmen render) atau `EXPORTS_DIR` (unduhan raw, permanen, default `~/CheatClip`), status job di dict memori `raw_download_jobs` / `raw_clip_download_jobs`.

## Risiko
- Batas kualitas `height<=2160` di L1084, L1136, L1333 (task #9). Fallback 720p/480p (L1197, L1240) jangan diubah.
- **Cache HD YouTube (#28)**: tanpa paket `yt-dlp-ejs` (plus Node/Deno di PATH) YouTube hanya memberi format 18 (360p); dengan paket itu format sampai 2160p tersedia, tetapi tidak di setiap ekstraksi (sesekali hanya 360p, ada HTTP 429), jadi `get_youtube_hd_cache` mencoba ekstraksi 2 kali per mode cookies lalu kembali ke metode 1-4. Unduhan pertama 1080p menahan render klip pertama (video 10,5 menit ±75 s, 52 menit ±2 menit menurut perkiraan ukuran); klip berikutnya dari video sama hanya memotong lokal. Cache harus tetap di subfolder: pencarian sumber lokal di `download_clip_segment` memindai file langsung di `TEMP_DIR` dengan pencocokan nama longgar. YouTube bisa berubah lagi: perbarui manual `pip install -U yt-dlp yt-dlp-ejs` di venv. 1440p/2160p dan `download_full_raw_video` belum memakai cache (#28b). **Jangan** menyalakan `solve_js_challenges` untuk metode 1-4, `download_full_raw_video`, atau `extract_clip_frame`: dengan format HD terbuka, metode 1-2 (ffmpeg ke URL remote) macet sampai timeout berlapis dan unduh video asli bisa memilih 2160p utuh (ditemukan saat uji #28).
- **Sebelum #28 (metode 1-4 masih begini)**: dengan `player_client=android,ios,web_embedded,mweb,web` di `get_yt_dlp_base_cmd` tanpa `yt-dlp-ejs` hanya format 18 yang tersedia. Menambah `default` memunculkan format HD klien `android_vr`, tetapi ffmpeg (dipakai `--download-sections` dan metode 2) mendapat 403 karena format itu wajib diambil per potongan 10 MB (`http_chunk_size`); downloader native yt-dlp berhasil. Akibatnya semua metode gagal berantai dan unduhan bisa > 20 menit. Sumber upload/Drive tidak terdampak (dipotong lokal di resolusi aslinya).
- Timeout dinamis (300 s + 5 s per detik klip, maks 20 menit). Unduhan lama menahan antrean render karena semaphore di [[render-server]].
- Cookies dicoba dulu, lalu mode tamu bila ditolak. Lihat [[cookies-dan-proxy]]. Catatan: di metode 1-4 badan loop `for use_cookies in attempts` hanya mengisi `base_cmd`, jadi metode lama praktis berjalan sekali dengan `base_cmd` percobaan terakhir (mode tamu bila ada cookies). Helper cache #28 mengikuti urutan cookies lalu tamu dengan benar.
- Sumber `upload_`/`gdrive_` tidak pernah dikirim ke YouTube. Kalau file lokalnya sudah dihapus cleanup, render gagal ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sumber-video]]
