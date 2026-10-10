---
fitur: subtitle, judul, font, watermark, audio tambahan
file_utama: [backend/video_engine.py, backend/services/render_service.py, backend/routers/media.py]
---
# Subtitle dan judul

Bagian dari render server. Subtitle karaoke dibuat dari transkripsi Whisper per kata pada audio klip yang sudah dipotong, lalu ditulis sebagai file ASS dan dibakar oleh FFmpeg (filter libass). Judul dengan emoji dirender ke PNG transparan karena libass tidak bisa menampilkan emoji berwarna.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/services/render_service.py` | langkah subtitle/judul per klip | L74-172 | Overlay judul emoji, transkripsi kata, panggil `generate_ass_file` |
| `backend/services/render_service.py` | subtitle mode merged | L373-461 | Kata per segmen digeser waktunya lalu digabung |
| `backend/video_engine.py` | `transcribe_clip_words` | L1140-1225 | Whisper per kata (0.0 = awal klip), fallback sebar transkrip |
| `backend/video_engine.py` | `generate_ass_file` | L1687-2059 | File ASS: gaya caption, posisi, karaoke, judul teks |
| `backend/video_engine.py` | `format_ass_timestamp` | L1228-1236 | Format waktu ASS |
| `backend/video_engine.py` | `escape_ass_text` | L1680-1684 | Escape teks untuk ASS |
| `backend/video_engine.py` | `clean_caption_text` | L1118-1137 | Bersihkan teks caption |
| `backend/video_engine.py` | `apply_text_case` | L1239-1248 | uppercase / lowercase / title case |
| `backend/video_engine.py` | `wrap_title_smart` | L1251-1296 | Pecah judul jadi beberapa baris |
| `backend/video_engine.py` | `render_title_overlay_png` | L1479-1677 | PNG judul seukuran kanvas, mendukung emoji berwarna |
| `backend/video_engine.py` | `render_text_watermark_png` | L1409-1476 | Watermark teks via Pillow (hindari error Fontconfig di Windows) |
| `backend/video_engine.py` | `has_emoji` | L1314-1318 | Penentu jalur PNG vs ASS untuk judul |
| `backend/video_engine.py` | `get_font` | L1344-1360 | Muat font dari `backend/fonts` |
| `backend/video_engine.py` | `get_emoji_font` | L1363-1382 | Font emoji (`seguiemj.ttf` atau `EMOJI_FONT_PATH`) |
| `backend/video_engine.py` | `get_ffmpeg_safe_font_path` | L1385-1406 | Path font yang aman untuk filter FFmpeg |
| `backend/routers/media.py` | `upload_font` | L441-488 | `POST /api/upload-font` |
| `backend/routers/media.py` | `list_available_fonts` | L492-546 | `GET /api/fonts` |
| `backend/routers/media.py` | `upload_bgm` | L260-286 | `POST /api/upload-bgm` (musik latar) |
| `backend/routers/media.py` | `upload_hook_sfx` | L300-326 | `POST /api/upload-sfx` (efek suara hook) |
| `backend/routers/media.py` | `upload_watermark` | L330-356 | `POST /api/upload-watermark` |

## Input / output
- Input: file segmen mentah, `clip.start_time/end_time`, `transcript` (fallback), opsi di `RenderSettingsModel` (`caption_style`, `caption_font`, `font_size(_px)`, `text_case`, `subtitle_y_percent`, `title_*`, `watermark_*`, `bgm_*`, `hook_sfx_*`).
- Output: file `.ass` dan `.png` di `backend/temp_clips/`, dipakai `render_clip_to_mp4` di [[render-server]].

## Risiko
- Ukuran font, posisi, dan wrap dihitung untuk kanvas 1080×1920 (lihat [[render-server]]).
- Teks subtitle diambil langsung dari Whisper. Belum ada koreksi manual sebelum render (target task #11: `ClipStudioSection.tsx`, `schemas/render.py`, `generate_ass_file`).
- Whisper memakai model global yang sama dengan [[transkrip]]. Render yang paralel dengan analisis bisa berebut RAM.
- Font kustom yang di-upload disimpan di `backend/fonts` dan dilindungi dari cleanup ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[transkrip]] · [[clip-studio]]
