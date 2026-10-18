---
fitur: sumber video
file_utama: [backend/routers/analyze.py, backend/routers/media.py, backend/services/gdrive_service.py, backend/services/youtube_service.py, src/utils/audioExtractor.ts]
---
# Sumber video (YouTube, Google Drive, upload)

Langkah 1 dan 2 dari `POST /api/analyze`: menentukan jenis sumber dari `request.url`, mengambil metadata (judul, channel, durasi), dan heatmap retensi.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | cabang Google Drive | L307-346 | Unduh file Drive dengan progres lewat antrean SSE |
| `backend/routers/analyze.py` | deteksi upload | L347-354 | `upload_*`, `/api/video/...`, `file://`, atau path yang ada di disk |
| `backend/routers/analyze.py` | cabang upload lokal | L356-545 | Probe metadata, transkrip via subtitle manual atau Whisper |
| `backend/routers/analyze.py` | heatmap akustik (upload) | L407-449 | Heatmap dari energi audio karena tidak ada data retensi; `heatmap_source = "audio"` (#32) agar prompt menyebutnya energi audio, bukan minat penonton |
| `backend/routers/analyze.py` | cabang YouTube: metadata | L546-608 | `extract_video_id`, `fetch_video_metadata`, mock fallback; `heatmap_source = "viewer"` (#32) |
| `backend/routers/analyze.py` | cabang YouTube: heatmap | L609-636 | Langkah 2, kurva retensi dari metadata |
| `backend/services/youtube_service.py` | `fetch_video_metadata` | L218-274 | yt-dlp JSON: judul, channel, durasi, heatmap |
| `backend/services/youtube_service.py` | `get_youtube_oembed_title` | L166-215 | Fallback judul via oEmbed |
| `backend/services/gdrive_service.py` | `is_google_drive_url` | L14-19 | Deteksi link Drive |
| `backend/services/gdrive_service.py` | `extract_google_drive_file_id` | L22-44 | Ambil ID file |
| `backend/services/gdrive_service.py` | `download_google_drive_video` | L47-203 | Unduh ke `temp_clips/uploads` |
| `backend/routers/media.py` | `upload_video` | L78-130 | `POST /api/upload-video`, simpan + metadata |
| `backend/routers/media.py` | `_save_uploaded_file_chunked` | L44-74 | Tulis upload per chunk |
| `backend/routers/media.py` | `_find_video_file_on_disk` | L133-182 | Cari file video berdasarkan ID/nama |
| `backend/routers/media.py` | `get_video_file` | L186-256 | `GET /api/video/{file_name}`, streaming dengan Range |
| `backend/routers/media.py` | `_is_safe_path` | L34-41 | Cegah path traversal |
| `backend/video_engine.py` | `get_video_file_metadata` | L496-570 | ffprobe: durasi, resolusi, audio |
| `backend/video_engine.py` | `compute_audio_energy_heatmap` | L576-644 | Heatmap pengganti dari energi audio (RMS per 1% durasi). Mengembalikan `[]` bila tanpa trek audio, file rusak, gagal/timeout (batas `max(30, durasi/10)` s, maks 900), senyap, atau volume rata (`AUDIO_FLAT_SPREAD` 15%, derau AAC nada konstan 6-8%); tidak pernah membuat data buatan (#33) |
| `backend/utils/heatmap.py` | `get_average_heatmap_value` | L3-31 | Skor engagement per baris transkrip |
| `backend/utils/text.py` | `extract_video_id` | L116-134 | ID YouTube dari URL |
| `backend/utils/text.py` | `is_safe_remote_url` | L414-452 | Validasi URL remote (anti SSRF) |
| `src/utils/audioExtractor.ts` | `extractAudioFromVideoClient` | L104-136 | Ekstrak audio di browser sebelum upload |
| `src/App.tsx` | upload di `handleAnalyze` | L1419-1472 | Mengirim audio WAV + resolusi ke `/api/upload-video` |

## Input / output
- Input: `AnalyzeRequest.url` (URL YouTube, URL Drive, atau nama file upload), `cookies`, `proxy`.
- Output (variabel lokal di `analyze_video`): `video_id`, `title`, `channel`, `duration`, `heatmap`, `source_type`, `video_url`, `transcript_lines`. Diteruskan ke [[transkrip]] dan [[analisis-ai]].

## Risiko
- Untuk sumber upload, browser hanya mengirim **audio** (WAV) ke server. Video aslinya tetap di browser sebagai object URL. Cek jalur render untuk sumber upload sebelum mengubah alur ini ([[render-browser]], [[render-server]]).
- `video_id` sumber non-YouTube berawalan `upload_` atau `gdrive_`. Banyak kode bercabang berdasarkan awalan ini (mis. `render_service.process_batch_rendering`).
- Kualitas sumber YouTube dibatasi 1080p di [[unduhan-raw]] (target task #9).

## Terkait
[[index]] · [[transkrip]] · [[analisis-ai]] · [[cookies-dan-proxy]] · [[frontend-app]]
