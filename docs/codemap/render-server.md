---
fitur: render server (FFmpeg)
file_utama: [backend/routers/render.py, backend/services/render_service.py, backend/video_engine.py, backend/schemas/render.py]
---
# Render server

Batch render klip menjadi MP4 vertikal. Router membuat `batch_id`, service menjalankan job di background (satu job aktif sekaligus), progres dibaca frontend lewat SSE. Hasil ditulis ke `EXPORTS_DIR` (default `~/CheatClip`, permanen). ZIP batch ditulis ke `TEMP_DIR` sebagai cache.

Alur per klip: unduh segmen ([[unduhan-raw]]) → transkripsi kata + file `.ass` + overlay judul ([[subtitle-dan-judul]]) → deteksi wajah ([[face-tracking]]) → filtergraph FFmpeg → encode → validasi MP4 → ZIP batch.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/render.py` | `start_batch_render` | L37-98 | `POST /api/render-batch`, buat status awal, jadwalkan background task |
| `backend/routers/render.py` | `retry_batch_rendering` | L102-146 | `POST /api/render-batch/{id}/retry` |
| `backend/routers/render.py` | `get_render_progress` | L150-185 | `GET /api/render-progress/{id}` (SSE) |
| `backend/routers/render.py` | `download_rendered_file` | L189-202 | `GET /api/download-rendered/{file}` |
| `backend/routers/render.py` | `download_batch_zip` | L206-233 | `GET /api/download-batch-zip/{id}` |
| `backend/routers/render.py` | `get_hardware_acceleration_status` | L237-278 | `GET /api/hardware-accel` |
| `backend/services/render_service.py` | state job di memori | L23-26 | `RENDER_BATCHES`, `BATCH_REQUESTS`, `_RENDER_SEMAPHORE = Semaphore(1)` |
| `backend/services/render_service.py` | `process_batch_rendering` | L535-587 | Normalisasi URL sumber, mode `separate` atau `merged` |
| `backend/services/render_service.py` | `render_single_batch_clip` | L29-242 | Satu klip: unduh (L54), subtitle/judul (L74), render (L173) |
| `backend/services/render_service.py` | `render_merged_batch_clips` | L297-532 | Gabung beberapa segmen jadi satu video highlight |
| `backend/services/render_service.py` | `update_batch_summary_and_zip` | L245-294 | ZIP hasil (di `TEMP_DIR`, L258) + status akhir batch |
| `backend/services/render_service.py` | `process_batch_retry` | L590-643 | Render ulang klip yang gagal |
| `backend/schemas/render.py` | `RenderSettingsModel` | L4-54 | Semua opsi render dari Clip Studio |
| `backend/schemas/render.py` | `RenderBatchRequest` | L56-62 | `video_url`, `video_id`, `clips`, `settings`, `transcript`, `cookies` |
| `backend/video_engine.py` | `render_clip_to_mp4` | L2868-3203 | Susun perintah FFmpeg: video, judul, subtitle, watermark, BGM, SFX hook |
| `backend/video_engine.py` | `build_ffmpeg_filtergraph` | L2534-2849 | Layout, crop, background blur, preset streamer, rasio aspek |
| `backend/video_engine.py` | `check_has_audio` | L2852-2865 | Cek trek audio sumber |
| `backend/video_engine.py` | `is_valid_mp4` | L437-493 | Validasi output dengan ffprobe/decode |
| `backend/video_engine.py` | `ENCODER_CONFIGS` | L292-297 | Argumen nvenc/amf/qsv/cpu. AMF di L294: `-quality balanced -rc vbr_peak -b:v 12M -maxrate 16M -bufsize 24M` (task #9, sebelumnya `speed`/`cbr` 6M). Ikut dipakai metode 2 unduhan dan trim lokal lewat `ACTIVE_ENCODER_ARGS` |
| `backend/video_engine.py` | `detect_hardware_support` | L302-328 | Deteksi GPU, hasil di-cache |
| `backend/video_engine.py` | `get_preferred_video_encoder` | L331-346 | Pilih encoder saat modul diimpor |
| `backend/video_engine.py` | `resolve_encoder` | L349-365 | Encoder sesuai pilihan `hardware_accel` user |
| `backend/video_engine.py` | `check_encoder_support` | L278-289 | Uji encoder dengan kanvas 1080x1920 |
| `backend/video_engine.py` | `extract_clip_frame` | L3206-3342 | Frame pratinjau (`GET /api/clip-frame`) |

## Input / output
- Input: `RenderBatchRequest` dari `handleStartBatchRender` di [[frontend-app]] (pengaturan dari [[clip-studio]]).
- Output: `EXPORTS_DIR/clip_{n}_{batch_id}.mp4`, ZIP batch `TEMP_DIR/cheat_clip_pro_{batch_id}.zip`, event SSE `{clips: [{status, progress_percent, download_url, error_message}], overall_status, zip_url}`.

## Risiko
- **Kanvas 1080×1920 ditulis langsung**: ±80 literal `1080`/`1920` di `video_engine.py`, terutama di `build_ffmpeg_filtergraph` (L2534-2849), `generate_ass_file`, dan `render_title_overlay_png`. Rasio 1:1, 4:3, 16:9 ditempatkan **di dalam** kanvas vertikal. Hanya `16:9_landscape` yang memakai kanvas 1920×1080. Target task #10.
- **Hasil dihapus otomatis** setelah 1 jam oleh cleanup. Lihat [[penyimpanan-dan-cleanup]] (target task #16).
- State job hanya di memori. Restart backend (termasuk `--reload` karena file `.py` disimpan) menghilangkan progres (target task #8).
- `_RENDER_SEMAPHORE` membuat batch berikutnya menunggu batch sebelumnya selesai.
- Deteksi encoder menjalankan FFmpeg saat impor modul, jadi startup backend lebih lambat dan log `Hardware acceleration auto-select` muncul di setiap impor.

## Terkait
[[index]] · [[subtitle-dan-judul]] · [[face-tracking]] · [[unduhan-raw]] · [[clip-studio]] · [[render-browser]] · [[penyimpanan-dan-cleanup]]
