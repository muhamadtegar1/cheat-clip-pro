---
fitur: subtitle, judul, font, watermark, audio tambahan
file_utama: [backend/video_engine.py, backend/services/render_service.py, backend/routers/media.py]
---
# Subtitle dan judul

Bagian dari render server. Subtitle karaoke dibuat dari transkripsi Whisper per kata pada audio klip yang sudah dipotong, lalu ditulis sebagai file ASS dan dibakar oleh FFmpeg (filter libass). Judul dengan emoji dirender ke PNG transparan karena libass tidak bisa menampilkan emoji berwarna.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/services/render_service.py` | langkah subtitle/judul per klip | L92-191 | Overlay judul emoji, transkripsi kata, panggil `generate_ass_file` |
| `backend/services/render_service.py` | subtitle mode merged | L392-481 | Kata per segmen digeser waktunya lalu digabung |
| `backend/video_engine.py` | `transcribe_clip_words` | L1154-1239 | Whisper per kata (0.0 = awal klip), fallback sebar transkrip |
| `backend/video_engine.py` | `generate_ass_file` | L1845-2139 | File ASS: gaya caption, posisi, karaoke, judul teks. Baris `Dialogue` subtitle ditulis dari `build_subtitle_events` (L2115-2132, #36a); `word_replacements` (#11) diteruskan ke sana |
| `backend/video_engine.py` | `build_subtitle_events` | L1737-1842 | #36a: langkah A-D subtitle (bersihkan kata, kamus #11 L1754, `text_case`, potongan 1-3 kata maks 22 karakter, putus di jeda >= 0.38 s / akhir kalimat, irisan waktu kata aktif). Satu sumber untuk render dan pratinjau Clip Studio; teks belum di-escape ASS |
| `backend/services/subtitle_preview_service.py` | `preview_subtitles` | L84-99 | #36a: `POST /api/preview-subtitles`: kata mentah dari `_load_words` lalu `build_subtitle_events` per permintaan (kamus/`text_case` tanpa Whisper ulang) |
| `backend/services/subtitle_preview_service.py` | `_load_words` | L47-81 | #36a: cache memori per (video_id, rentang) maks `PREVIEW_CACHE_MAX` (L20); bila kosong: di bawah `_RENDER_SEMAPHORE`, `resolve_source_url`, `download_clip_segment` ke `TEMP_DIR/preview_*_raw.mp4` (dihapus di `finally`), `_transcribe_segment` |
| `backend/services/subtitle_preview_service.py` | `_transcribe_segment` | L36-44 | #36a: Whisper dulu (`source=whisper`), lalu fallback transkrip analisis dengan path kosong (`transcript`), selain itu `none` |
| `backend/video_engine.py` | `build_word_replacement_map` | L1704-1720 | #11: kamus koreksi `{from, to}` -> `{kunci: pengganti}`; kunci dibersihkan seperti kata Whisper, huruf kecil, tanpa tanda baca ujung |
| `backend/video_engine.py` | `apply_word_replacement` | L1723-1734 | #11: ganti satu kata bila cocok, tanda baca ujung (`.,?`) dipertahankan, pengganti kosong = kata dihapus |
| `backend/schemas/render.py` | `SubtitleReplacement` | L5-8 | #11: pasangan `from` (alias, 1-40 karakter tanpa spasi) dan `to` (0-60); `RenderSettingsModel.subtitle_replacements` maks 100 (L38) |
| `backend/video_engine.py` | `format_ass_timestamp` | L1242-1250 | Format waktu ASS |
| `backend/video_engine.py` | `escape_ass_text` | L1694-1698 | Escape teks untuk ASS |
| `backend/video_engine.py` | `clean_caption_text` | L1132-1151 | Bersihkan teks caption |
| `backend/video_engine.py` | `apply_text_case` | L1253-1262 | uppercase / lowercase / title case |
| `backend/video_engine.py` | `wrap_title_smart` | L1265-1310 | Pecah judul jadi beberapa baris |
| `backend/video_engine.py` | `render_title_overlay_png` | L1493-1691 | PNG judul seukuran kanvas, mendukung emoji berwarna |
| `backend/video_engine.py` | `render_text_watermark_png` | L1423-1490 | Watermark teks via Pillow (hindari error Fontconfig di Windows) |
| `backend/video_engine.py` | `has_emoji` | L1328-1332 | Penentu jalur PNG vs ASS untuk judul |
| `backend/video_engine.py` | `get_font` | L1358-1374 | Muat font dari `backend/fonts` |
| `backend/video_engine.py` | `get_emoji_font` | L1377-1396 | Font emoji (`seguiemj.ttf` atau `EMOJI_FONT_PATH`) |
| `backend/video_engine.py` | `get_ffmpeg_safe_font_path` | L1399-1420 | Path font yang aman untuk filter FFmpeg |
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
- Teks subtitle diambil langsung dari Whisper saat render, jadi belum bisa disunting per klip sebelum render. Koreksi yang ada (#11) berupa kamus global "salah -> benar" dari Clip Studio (`subtitle_replacements`), diteruskan `render_service.py` ke kedua panggilan `generate_ass_file` (mode separate L189, merged L479). Kata pengganti tetap mengikuti `text_case`; kata yang dihapus ikut membuang tanda baca ujungnya (bisa menggeser pemotongan potongan subtitle). `from` hanya satu kata, frasa multi-kata belum didukung.
- Pratinjau subtitle asli (#36a) menjalankan Whisper dan mengunduh segmen klip sendiri; render belum memakai ulang hasilnya, jadi Whisper berjalan dua kali (pratinjau + render). Hasilnya bisa sedikit berbeda bila model Whisper tidak deterministik. Pratinjau memakai `_RENDER_SEMAPHORE`, jadi menunggu bila render berjalan. Cache kata hanya di memori dan hilang saat backend restart (`--reload`).
- Whisper memakai model global yang sama dengan [[transkrip]]. Render yang paralel dengan analisis bisa berebut RAM.
- Font kustom yang di-upload disimpan di `backend/fonts` dan dilindungi dari cleanup ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[transkrip]] · [[clip-studio]]
