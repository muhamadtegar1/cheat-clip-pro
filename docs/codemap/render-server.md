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
| `backend/routers/render.py` | `start_batch_render` | L39-100 | `POST /api/render-batch`, buat status awal, jadwalkan background task |
| `backend/routers/render.py` | `retry_batch_rendering` | L104-148 | `POST /api/render-batch/{id}/retry` |
| `backend/routers/render.py` | `get_render_progress` | L152-187 | `GET /api/render-progress/{id}` (SSE) |
| `backend/routers/render.py` | `download_rendered_file` | L191-204 | `GET /api/download-rendered/{file}` |
| `backend/routers/render.py` | `download_batch_zip` | L208-235 | `GET /api/download-batch-zip/{id}` |
| `backend/routers/render.py` | `get_hardware_acceleration_status` | L239-280 | `GET /api/hardware-accel` |
| `backend/routers/render.py` | `preview_clip_subtitles` | L285-292 | #36a: `POST /api/preview-subtitles` (422 rentang tidak valid, 500 dengan detail). Lihat [[subtitle-dan-judul]] |
| `backend/services/render_service.py` | state job di memori | L25-28 | `RENDER_BATCHES`, `BATCH_REQUESTS`, `_RENDER_SEMAPHORE = Semaphore(1)` |
| `backend/services/render_service.py` | `process_batch_rendering` | L659-699 | Normalisasi URL sumber (`resolve_source_url`), mode `separate` atau `merged` |
| `backend/services/render_service.py` | `resolve_source_url` | L31-46 | #36a: normalisasi URL sumber (upload/gdrive -> `/api/video/<id>`, selain itu URL watch YouTube), dipakai render dan pratinjau subtitle. `process_batch_retry` masih punya salinan sendiri |
| `backend/services/render_service.py` | `render_single_batch_clip` | L121-343 | Satu klip: unduh (L146), subtitle/judul (L170), render (L274). #36b: `subtitle_words` (pratinjau Clip Studio) menggantikan Whisper, divalidasi `clip_subtitle_words` (L57-93). Lihat [[subtitle-dan-judul]] |
| `backend/services/render_service.py` | `render_merged_batch_clips` | L398-656 | Gabung beberapa segmen jadi satu video highlight |
| `backend/services/render_service.py` | `update_batch_summary_and_zip` | L346-395 | ZIP hasil (di `TEMP_DIR`, L359) + status akhir batch |
| `backend/services/render_service.py` | `process_batch_retry` | L702-755 | Render ulang klip yang gagal |
| `backend/schemas/render.py` | `RenderSettingsModel` | L10-62 | Semua opsi render dari Clip Studio, termasuk `subtitle_replacements` (#11, model `SubtitleReplacement` L5-8). Lihat [[subtitle-dan-judul]] |
| `backend/schemas/render.py` | `PreviewSubtitlesRequest` | L73-85 | #36a: `video_url`, `video_id`, rentang, `transcript`, `cookies`, `subtitle_replacements`, `text_case`, `force` (lewati cache, tombol "Buat ulang") |
| `backend/schemas/render.py` | `RenderBatchRequest` | L64-70 | `video_url`, `video_id`, `clips`, `settings`, `transcript`, `cookies` |
| `backend/video_engine.py` | `render_clip_to_mp4` | L2969-3304 | Susun perintah FFmpeg: video, judul, subtitle, watermark, BGM, SFX hook |
| `backend/video_engine.py` | `build_ffmpeg_filtergraph` | L2635-2950 | Layout, crop, background blur, preset streamer, rasio aspek |
| `backend/video_engine.py` | `check_has_audio` | L2953-2966 | Cek trek audio sumber |
| `backend/video_engine.py` | `is_valid_mp4` | L458-514 | Validasi output dengan ffprobe/decode |
| `backend/video_engine.py` | `ENCODER_CONFIGS` | L313-318 | Argumen nvenc/amf/qsv/cpu. AMF di L294: `-quality balanced -rc vbr_peak -b:v 12M -maxrate 16M -bufsize 24M` (task #9, sebelumnya `speed`/`cbr` 6M). Ikut dipakai metode 2 unduhan dan trim lokal lewat `ACTIVE_ENCODER_ARGS` |
| `backend/video_engine.py` | `detect_hardware_support` | L323-349 | Deteksi GPU, hasil di-cache |
| `backend/video_engine.py` | `get_preferred_video_encoder` | L352-367 | Pilih encoder saat modul diimpor |
| `backend/video_engine.py` | `resolve_encoder` | L370-386 | Encoder sesuai pilihan `hardware_accel` user |
| `backend/video_engine.py` | `check_encoder_support` | L299-310 | Uji encoder dengan kanvas 1080x1920 |
| `backend/video_engine.py` | `extract_clip_frame` | L3307-3443 | Frame pratinjau (`GET /api/clip-frame`) |

## Input / output
- Input: `RenderBatchRequest` dari `handleStartBatchRender` di [[frontend-app]] (pengaturan dari [[clip-studio]]).
- Output: `EXPORTS_DIR/clip_{n}_{batch_id}.mp4`, ZIP batch `TEMP_DIR/cheat_clip_pro_{batch_id}.zip`, event SSE `{clips: [{status, progress_percent, download_url, error_message}], overall_status, zip_url}`.

## Risiko
- **Kanvas 1080×1920 ditulis langsung**: ±80 literal `1080`/`1920` di `video_engine.py`, terutama di `build_ffmpeg_filtergraph` (L2588-2903), `generate_ass_file`, dan `render_title_overlay_png`. Rasio 1:1, 4:3, 16:9 ditempatkan **di dalam** kanvas vertikal. Hanya `16:9_landscape` yang memakai kanvas 1920×1080. Target task #10.
- **Hasil dihapus otomatis** setelah 1 jam oleh cleanup. Lihat [[penyimpanan-dan-cleanup]] (target task #16).
- State job hanya di memori. Restart backend (termasuk `--reload` karena file `.py` disimpan) menghilangkan progres (target task #8).
- `_RENDER_SEMAPHORE` membuat batch berikutnya menunggu batch sebelumnya selesai.
- Deteksi encoder menjalankan FFmpeg saat impor modul, jadi startup backend lebih lambat dan log `Hardware acceleration auto-select` muncul di setiap impor.

## Terkait
[[index]] · [[subtitle-dan-judul]] · [[face-tracking]] · [[unduhan-raw]] · [[clip-studio]] · [[render-browser]] · [[penyimpanan-dan-cleanup]]
