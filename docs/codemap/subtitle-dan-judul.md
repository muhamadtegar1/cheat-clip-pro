---
fitur: subtitle, judul, font, watermark, audio tambahan
file_utama: [backend/video_engine.py, backend/services/render_service.py, backend/routers/media.py]
---
# Subtitle dan judul

Bagian dari render server. Subtitle karaoke dibuat dari transkripsi Whisper per kata pada audio klip yang sudah dipotong, lalu ditulis sebagai file ASS dan dibakar oleh FFmpeg (filter libass). Judul dengan emoji dirender ke PNG transparan karena libass tidak bisa menampilkan emoji berwarna.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/services/render_service.py` | langkah subtitle/judul per klip | L170-274 | Overlay judul emoji, transkripsi kata, panggil `generate_ass_file`. #36b: `subtitle_words` dari pratinjau divalidasi sebelum unduh (L151) dan dipakai tanpa Whisper (L233-237) |
| `backend/services/render_service.py` | subtitle mode merged | L484-587 | Kata per segmen digeser waktunya lalu digabung. #36b: segmen dengan `subtitle_words` (divalidasi di awal, L425) tanpa Whisper (L496); bila ada segmen bergroup, semua segmen dipotong per group lewat `_with_groups` dan nomornya digeser per segmen (L489, L508) |
| `backend/video_engine.py` | `transcribe_clip_words` | L1201-1291 | Whisper per kata (0.0 = awal klip), fallback sebar transkrip. #39: `language` (None = Otomatis, argumen `transcribe` sama dengan sebelum #39; kode dipilih = `language=<kode>`) |
| `backend/video_engine.py` | `generate_ass_file` | L1909-2203 | File ASS: gaya caption, posisi, karaoke, judul teks. Baris `Dialogue` subtitle ditulis dari `build_subtitle_events` (L2179-2196, #36a); `word_replacements` (#11) diteruskan ke sana |
| `backend/video_engine.py` | `build_subtitle_events` | L1789-1906 | #36a: langkah A-D subtitle (bersihkan kata, kamus #11 L1809, `text_case`, potongan 1-3 kata maks 22 karakter, putus di jeda >= 0.38 s / akhir kalimat, irisan waktu kata aktif). Satu sumber untuk render dan pratinjau Clip Studio; teks belum di-escape ASS. #36b: bila semua kata punya `group` (L1810), langkah B memotong per group tanpa aturan otomatis (L1829); event berisi `indices` (indeks kata masukan, L1904) |
| `backend/services/subtitle_preview_service.py` | `preview_subtitles` | L87-107 | #36a: `POST /api/preview-subtitles`: kata mentah dari `_load_words` lalu `build_subtitle_events` per permintaan (kamus/`text_case` tanpa Whisper ulang). #36b: `words` diisi (L91) = tanpa unduh/Whisper, divalidasi `clip_subtitle_words` (ValueError -> 422), `source=edited` |
| `backend/services/render_service.py` | `clip_subtitle_words` | L57-93 | #36b: validasi `clip["subtitle_words"]` (None = Whisper, `[]` = tanpa subtitle, maks 3000 kata, `word` <= 60 karakter, `0 <= start <= end <= durasi + 60`, `group` int untuk semua kata atau tidak sama sekali); tidak valid = ValueError, klip gagal jelas |
| `backend/services/render_service.py` | `_with_groups` | L96-118 | #36b (merged): kata tanpa group diberi group dari pemotongan otomatisnya sendiri; group dinomori ulang 0..n-1 |
| `backend/services/subtitle_preview_service.py` | `_load_words` | L50-84 | #36a: cache memori per (video_id, rentang, bahasa audio #39) maks `PREVIEW_CACHE_MAX`, dilewati dan ditimpa bila `force` (tombol "Buat ulang") (L21); bila kosong: di bawah `_RENDER_SEMAPHORE`, `resolve_source_url`, `download_clip_segment` ke `TEMP_DIR/preview_*_raw.mp4` (dihapus di `finally`), `_transcribe_segment` |
| `backend/services/subtitle_preview_service.py` | `_transcribe_segment` | L38-47 | #36a: Whisper dulu (`source=whisper`), lalu fallback transkrip analisis dengan path kosong (`transcript`), selain itu `none`. #39: `audio_language` diteruskan sebagai `language` |
| `backend/services/subtitle_preview_service.py` | `_cache_key` | L26-28 | #39: kunci cache `(video_id, start, end, bahasa)`, bahasa None = `auto`; ganti bahasa = Whisper jalan lagi |
| `backend/video_engine.py` | `build_word_replacement_map` | L1756-1772 | #11: kamus koreksi `{from, to}` -> `{kunci: pengganti}`; kunci dibersihkan seperti kata Whisper, huruf kecil, tanpa tanda baca ujung |
| `backend/video_engine.py` | `apply_word_replacement` | L1775-1786 | #11: ganti satu kata bila cocok, tanda baca ujung (`.,?`) dipertahankan, pengganti kosong = kata dihapus |
| `backend/schemas/render.py` | `SubtitleReplacement` | L17-20 | #11: pasangan `from` (alias, 1-40 karakter tanpa spasi) dan `to` (0-60); `RenderSettingsModel.subtitle_replacements` maks 100 (L50) |
| `backend/video_engine.py` | `format_ass_timestamp` | L1294-1302 | Format waktu ASS |
| `backend/video_engine.py` | `escape_ass_text` | L1746-1750 | Escape teks untuk ASS |
| `backend/video_engine.py` | `clean_caption_text` | L1179-1198 | Bersihkan teks caption |
| `backend/video_engine.py` | `apply_text_case` | L1305-1314 | uppercase / lowercase / title case |
| `backend/video_engine.py` | `wrap_title_smart` | L1317-1362 | Pecah judul jadi beberapa baris |
| `backend/video_engine.py` | `render_title_overlay_png` | L1545-1743 | PNG judul seukuran kanvas, mendukung emoji berwarna |
| `backend/video_engine.py` | `render_text_watermark_png` | L1475-1542 | Watermark teks via Pillow (hindari error Fontconfig di Windows) |
| `backend/video_engine.py` | `has_emoji` | L1380-1384 | Penentu jalur PNG vs ASS untuk judul |
| `backend/video_engine.py` | `get_font` | L1410-1426 | Muat font dari `backend/fonts` |
| `backend/video_engine.py` | `get_emoji_font` | L1429-1448 | Font emoji (`seguiemj.ttf` atau `EMOJI_FONT_PATH`) |
| `backend/video_engine.py` | `get_ffmpeg_safe_font_path` | L1451-1472 | Path font yang aman untuk filter FFmpeg |
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
- Klip yang punya hasil pratinjau (#36b) dirender dari kata pratinjau atau suntingan (`subtitle_words`) tanpa Whisper; klip tanpa pratinjau tetap Whisper saat render. Koreksi global (#11) berupa kamus global "salah -> benar" dari Clip Studio (`subtitle_replacements`), diteruskan `render_service.py` ke kedua panggilan `generate_ass_file` (mode separate L272, merged L585). Kata pengganti tetap mengikuti `text_case`; kata yang dihapus ikut membuang tanda baca ujungnya (bisa menggeser pemotongan potongan subtitle). `from` hanya satu kata, frasa multi-kata belum didukung.
- Pratinjau subtitle asli (#36a) menjalankan Whisper pada segmen klip sendiri. Whisper `base` tidak stabil untuk bahasa Indonesia (uji 2026-10-19: sekitar separuh baris berbeda antara dua kali jalan), jadi sejak #36b render memakai kata pratinjau, bukan Whisper ulang; render tetap mengunduh segmen sendiri untuk videonya. Klip tanpa pratinjau masih bisa berbeda dari pratinjau yang dibuat belakangan. Pada mode merged, bila satu segmen disunting, segmen lain dipotong per segmen (potongan lintas batas segmen tidak lagi terjadi). Pratinjau memakai `_RENDER_SEMAPHORE`, jadi menunggu bila render berjalan. Cache kata hanya di memori dan hilang saat backend restart (`--reload`).
- Whisper memakai model global yang sama dengan [[transkrip]], dipilih lewat `CHEAT_CLIP_WHISPER_MODEL` (#38). Bahasa audio (#39, `audio_language` di settings render dan permintaan pratinjau) dipaksakan ke Whisper bila dipilih; bahasa yang salah pilih membuat Whisper menerjemahkan kasar ke bahasa itu, jadi subtitle tidak lagi sesuai ucapan. Pratinjau Clip Studio dikunci per bahasa, jadi kata pratinjau bahasa lain tidak dipakai render. Render yang paralel dengan analisis bisa berebut RAM; model lebih besar memperpanjang waktu pratinjau subtitle (#36a) dan render.
- Font kustom yang di-upload disimpan di `backend/fonts` dan dilindungi dari cleanup ([[penyimpanan-dan-cleanup]]).

## Terkait
[[index]] · [[render-server]] · [[transkrip]] · [[clip-studio]]
