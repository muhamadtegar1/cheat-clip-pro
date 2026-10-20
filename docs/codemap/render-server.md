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
| `backend/services/render_service.py` | state job di memori | L26-29 | `RENDER_BATCHES`, `BATCH_REQUESTS`, `_RENDER_SEMAPHORE = Semaphore(1)` |
| `backend/services/render_service.py` | `process_batch_rendering` | L698-740 | Normalisasi URL sumber (`resolve_source_url`), mode `separate` atau `merged` |
| `backend/services/render_service.py` | `resolve_source_url` | L32-47 | #36a: normalisasi URL sumber (upload/gdrive -> `/api/video/<id>`, selain itu URL watch YouTube), dipakai render dan pratinjau subtitle. `process_batch_retry` masih punya salinan sendiri |
| `backend/services/render_service.py` | `render_single_batch_clip` | L122-373 | Satu klip: unduh (L150), subtitle/judul (L174), render (L281). #36b: `subtitle_words` (pratinjau Clip Studio) menggantikan Whisper, divalidasi `clip_subtitle_words` (L58-94). Lihat [[subtitle-dan-judul]]. #22: kata yang dipakai (`words_used` L147, diisi L279 bila subtitle aktif) dan blok posting kit setelah MP4 valid (L331-352): `write_clip_kit`, galat = `kit_error`, klip tetap `completed`; `kit_dir` per klip dan batch |
| `backend/services/render_service.py` | `render_merged_batch_clips` | L436-695 | Gabung beberapa segmen jadi satu video highlight |
| `backend/services/render_service.py` | `update_batch_summary_and_zip` | L376-433 | ZIP hasil (di `TEMP_DIR`, L389) + status akhir batch |
| `backend/services/render_service.py` | `process_batch_retry` | L743-798 | Render ulang klip yang gagal |
| `backend/schemas/render.py` | `RenderSettingsModel` | L22-76 | Semua opsi render dari Clip Studio, termasuk `subtitle_replacements` (#11, model `SubtitleReplacement` L17-20) dan `audio_language` (#39, L52) yang diteruskan ke `transcribe_clip_words` (separate L253, merged L515; retry memakai settings batch). Lihat [[subtitle-dan-judul]] |
| `backend/schemas/render.py` | `PreviewSubtitlesRequest` | L96-110 | #36a: `video_url`, `video_id`, rentang, `transcript`, `cookies`, `subtitle_replacements`, `text_case`, `force` (lewati cache, tombol "Buat ulang") |
| `backend/schemas/render.py` | `_check_audio_language` | L5-10 | #39: validator tipe `AudioLanguage` (L14) untuk `AnalyzeRequest`, `RenderSettingsModel`, `PreviewSubtitlesRequest`; impor lambat `normalize_audio_language` (efek samping impor `video_engine`), kode di luar daftar = 422, `auto` = None |
| `backend/schemas/render.py` | `RenderBatchRequest` | L86-93 | `video_url`, `video_id`, `clips`, `settings`, `transcript`, `cookies`, `kit_meta` (#22) |
| `backend/schemas/render.py` | `KitMeta` | L79-84 | #22: judul video, channel, model, `prompt_version`, `custom_prompt` untuk metadata posting kit (semua opsional) |
| `backend/services/posting_kit.py` | `PLATFORM_RULES` | L23-28 | #22: batas karakter dan jumlah hashtag per platform (TikTok, Reels, Shorts, X). Nilai awal konservatif, cek pemilik terhadap aturan platform terbaru |
| `backend/services/posting_kit.py` | `kit_batch_dir` | L41-46 | `EXPORTS_DIR/kits/<YYYY-MM-DD>_<batch_id>` (tanggal dari epoch di `batch_id`); folder klip `NN_<judul aman>` (`clip_kit_dirname` L49-50, `safe_name` L34-38) |
| `backend/services/posting_kit.py` | `build_srt` | L61-80 | SRT dari kata render lewat `build_subtitle_events` (`text_case="original"`, kamus #11), event per kata digabung per potongan = baris karaoke video |
| `backend/services/posting_kit.py` | `build_platform_captions` | L131-149 | Caption per platform dari `caption_suggestion` + `hashtag_suggestion` (hashtag huruf kecil, unik) + kredit `credit_line` (L119-128, URL hanya http, channel placeholder `Local Upload`/`Google Drive` di `PLACEHOLDER_CHANNELS` L107 tidak dipakai); badan dipotong di batas kata, kredit dan hashtag dipertahankan; Shorts baris 1 judul. Tanpa caption = judul |
| `backend/services/posting_kit.py` | `public_source_url` | L110-116 | URL sumber untuk kredit dan `metadata.json`: hanya http dan bukan ID `upload_`/`gdrive_` (frontend mengirim URL watch YouTube buatan untuk upload yang dimuat dari riwayat, ditemukan saat uji browser) |
| `backend/services/posting_kit.py` | `build_metadata` | L168-228 | Isi `metadata.json` (`schema_version` 1): sumber, klip, skor, analisis (model, `prompt_version`, `custom_prompt`), render ringkas, daftar file |
| `backend/services/posting_kit.py` | `write_clip_kit` | L231-274 | Tulis/timpa folder kit: `video.mp4` hardlink ke MP4 render (gagal = salin, `_link_or_copy` L152-160), `subtitles.srt` (dihapus bila retry tanpa subtitle), 4 caption, `metadata.json` |
| `backend/video_engine.py` | `render_clip_to_mp4` | L3217-3552 | Susun perintah FFmpeg: video, judul, subtitle, watermark, BGM, SFX hook |
| `backend/video_engine.py` | `build_ffmpeg_filtergraph` | L2883-3198 | Layout, crop, background blur, preset streamer, rasio aspek |
| `backend/video_engine.py` | `check_has_audio` | L3201-3214 | Cek trek audio sumber |
| `backend/video_engine.py` | `is_valid_mp4` | L478-534 | Validasi output dengan ffprobe/decode |
| `backend/video_engine.py` | `ENCODER_CONFIGS` | L327-332 | Argumen nvenc/amf/qsv/cpu. AMF di L329: `-quality balanced -rc vbr_peak -b:v 12M -maxrate 16M -bufsize 24M` (task #9, sebelumnya `speed`/`cbr` 6M). Ikut dipakai metode 2 unduhan dan trim lokal lewat `ACTIVE_ENCODER_ARGS` |
| `backend/video_engine.py` | `detect_hardware_support` | L337-363 | Deteksi GPU, hasil di-cache |
| `backend/video_engine.py` | `get_preferred_video_encoder` | L366-381 | Pilih encoder saat modul diimpor |
| `backend/video_engine.py` | `resolve_encoder` | L384-400 | Encoder sesuai pilihan `hardware_accel` user |
| `backend/video_engine.py` | `check_encoder_support` | L313-324 | Uji encoder dengan kanvas 1080x1920 |
| `backend/video_engine.py` | `extract_clip_frame` | L3555-3691 | Frame pratinjau (`GET /api/clip-frame`) |

## Input / output
- Input: `RenderBatchRequest` dari `handleStartBatchRender` di [[frontend-app]] (pengaturan dari [[clip-studio]]).
- Output: `EXPORTS_DIR/clip_{n}_{batch_id}.mp4`, posting kit `EXPORTS_DIR/kits/<tanggal>_<batch_id>/<NN>_<judul>/` (#22, hanya mode `separate`), ZIP batch `TEMP_DIR/cheat_clip_pro_{batch_id}.zip` (MP4 + `kits/<NN>_<judul>/` tanpa `video.mp4`, L405-412), event SSE `{clips: [{status, progress_percent, download_url, error_message, kit_dir, kit_error}], overall_status, zip_url, kit_dir}`.

## Risiko
- **Kanvas 1080×1920 ditulis langsung**: ±80 literal `1080`/`1920` di `video_engine.py`, terutama di `build_ffmpeg_filtergraph` (L2883-3198), `generate_ass_file`, dan `render_title_overlay_png`. Rasio 1:1, 4:3, 16:9 ditempatkan **di dalam** kanvas vertikal. Hanya `16:9_landscape` yang memakai kanvas 1920×1080. Target task #10.
- **Hasil dihapus otomatis** setelah 1 jam oleh cleanup. Lihat [[penyimpanan-dan-cleanup]] (target task #16).
- State job hanya di memori. Restart backend (termasuk `--reload` karena file `.py` disimpan) menghilangkan progres (target task #8).
- `_RENDER_SEMAPHORE` membuat batch berikutnya menunggu batch sebelumnya selesai.
- Deteksi encoder menjalankan FFmpeg saat impor modul, jadi startup backend lebih lambat dan log `Hardware acceleration auto-select` muncul di setiap impor.

## Terkait
[[index]] · [[subtitle-dan-judul]] · [[face-tracking]] · [[unduhan-raw]] · [[clip-studio]] · [[render-browser]] · [[penyimpanan-dan-cleanup]]
