# CHEAT-9: Sumber sampai 2160p + bitrate AMF lebih tinggi
Status: REVIEW

## Tujuan
Batas format yt-dlp dinaikkan ke 2160p dan encoder AMD AMF memakai bitrate lebih tinggi, sehingga klip 1080×1920 dari sumber resolusi tinggi lebih tajam tanpa mengubah fallback 720p/480p.

## Area yang boleh disentuh
- `backend/video_engine.py`:
  - `ENCODER_CONFIGS` L292-297: hanya entri `"amf"` L294 (sekarang `-quality speed -rc cbr -b:v 6M`). Entri `nvenc`, `qsv`, `cpu` tidak diubah.
  - `download_clip_segment` metode 1 L806-850: string format L811 `height<=1080` → `height<=2160`.
  - `download_clip_segment` metode 2 L851-911: string format L863 `height<=1080` → `height<=2160`.
  - `download_full_raw_video` L1019-1120: string format L1060 `height<=1080` → `height<=2160` (tombol unduh video asli).
  - Pesan log terkait di area yang sama (mis. "Downloading HD section") boleh disesuaikan.
- `docs/codemap/render-server.md` dan `docs/codemap/unduhan-raw.md` (baris, risiko, catatan task #9). Catatan lain hanya bila baris bergeser.

## Di luar scope (jangan dikerjakan)
- Fallback metode 3 (720p, L912-954, format L924) dan metode 4 (480p, L955-1016, format L967). Tidak berubah sama sekali.
- Format `extract_clip_frame` L3286 (`18/best[height<=720]/best`) untuk frame pratinjau.
- Ukuran kanvas 1080×1920 dan literal di `build_ffmpeg_filtergraph` (task #10).
- Encoder `nvenc`, `qsv`, `cpu`, logika `detect_hardware_support`/`resolve_encoder`/`check_encoder_support`.
- Trim lokal di `backend/services/download_service.py` L140-155 (ikut memakai `ACTIVE_ENCODER_ARGS`, jadi otomatis ikut bitrate AMF baru, tapi kodenya tidak diubah).
- Face tracking (`detect_speaker_face_box`), sampling frame, decoder hardware (`vp9_amf`/`av1_amf`).
- Opsi UI baru untuk memilih kualitas sumber atau bitrate.
- `get_yt_dlp_base_cmd` (`player_client`) dan strategi unduhan YouTube HD: dipindah ke task #28 (lihat CATATAN pemilik di bawah).
- `player_client` di `backend/services/youtube_service.py` L238, L486, L587.
- Preferensi SDR vs HDR di string format (video HDR ikut terunduh HDR10 seperti sebelumnya, warna bisa pudar saat dirender SDR). Kandidat task terpisah.

## Keputusan yang boleh diambil AI sendiri
- Nilai parameter AMF dalam batas: `-b:v` 10M-16M, boleh menambah `-maxrate`/`-bufsize`, boleh mengganti `-rc` (`cbr`, `vbr_peak`, `qvbr`) dan `-quality` (`speed`/`balanced`). Pilihan akhir berdasarkan pengukuran: waktu render 1 klip AMF dari sumber 1080p tidak lebih dari 1,5× versi lama, dan argumen lolos `check_encoder_support` di komputer ini (AMD Radeon iGPU, K2).
- Bila video 4K YouTube hanya tersedia sebagai AV1 dan decode AV1 di CPU membuat render jauh lebih lambat (> 2× dibanding sumber 1080p untuk klip yang sama), boleh mengutamakan VP9 di string format (mis. `bestvideo[height<=2160][vcodec^=vp9]+bestaudio/...` sebelum alternatif lain). Catat hasil ukurnya di laporan.
- Video uji 4K publik yang dipakai untuk pengujian.

## Kriteria selesai (ya/tidak)
- [x] Metode 1, metode 2, dan `download_full_raw_video` memakai batas `height<=2160` (diff). Dengan `player_client` saat ini, format yang dipilih yt-dlp untuk video YouTube uji tidak berubah (`--print format_id` sebelum/sesudah), jadi unduhan YouTube tidak menjadi lebih buruk.
- [x] Segmen dari file lokal 4K (sumber upload, video sintetis 3840×2160) lewat `download_clip_segment` tetap 2160 dan render menghasilkan 1080×1920 (`ffprobe`), MP4 valid (`is_valid_mp4`).
- [ ] Segmen YouTube 2160p dari sumber 4K: tidak bisa dicapai di task ini (format HD 403 lewat ffmpeg), dipindah ke #28. Bukan syarat REVIEW #9.
- [x] Encoder AMF: bitrate rata-rata output untuk klip uji yang sama lebih tinggi dari versi lama (`ffprobe` `bit_rate`, angka lama dan baru dicatat), dan waktu render tidak lebih dari 1,5× versi lama.
- [x] Format fallback 720p (L924) dan 480p (L967) tidak berubah (`git diff`).
- [x] Hanya entri `amf` di `ENCODER_CONFIGS` yang berubah.
- [x] Smoke test lulus 7/7 dengan dan tanpa `--gpu`, `check_codemap.py` lulus.
- [ ] Klip hasil render terlihat lebih tajam dibanding versi lama (perlu dicek pemilik secara visual, lihat CATATAN soal PSNR).

## Cara menguji
- Video uji lokal sintetis (FFmpeg `testsrc2` + noise, 30 detik) 1920×1080 dan 3840×2160. Render dengan `hardware_accel` `amf` memakai argumen AMF lama dan baru, catat waktu render dan `bit_rate` output.
- `yt-dlp --print format_id` untuk video YouTube uji dengan string format lama dan baru (argumen dasar app), harus sama.
- Ulangi setelah perubahan dengan klip yang sama, bandingkan.
- `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,bit_rate -of csv=p=0 <file>` untuk segmen dan output.
- `venv\Scripts\python.exe scripts\smoke_test.py` dan `venv\Scripts\python.exe scripts\smoke_test.py --gpu`.
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- `git diff backend/video_engine.py`: hanya L294, L811, L863, L1060 (plus pesan log bila ada).
- File uji di `EXPORTS_DIR` dan `backend/temp_clips` yang dibuat saat pengujian dihapus setelahnya.

## Catatan pemilik (perubahan kontrak saat implementasi)
- Uji versi lama: video YouTube 4K uji (`aqz-KE-bpKQ`) menghasilkan segmen **640×360** (format 18). Dengan `player_client=android,ios,web_embedded,mweb,web` hanya format 18 yang tersedia.
- Menambah `default` di depan `player_client` memunculkan format HD (klien `android_vr`), tetapi ffmpeg mendapat **403 Forbidden** saat mengambil URL itu (format mewajibkan request per potongan `http_chunk_size` 10 MB; downloader native yt-dlp berhasil, `--downloader ffmpeg` gagal). Metode 1-4 semuanya lewat ffmpeg, jadi unduhan gagal berantai sampai >20 menit. Perubahan `player_client` dibatalkan.
- Pemilik memilih: #9 sebatas batas format 2160p + bitrate AMF; unduhan HD YouTube menjadi task #28.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `backend/video_engine.py` (L294 entri `amf`; L811, L863, L1060 `height<=1080` → `height<=2160`; docstring L696 dan L1026), `docs/codemap/render-server.md`, `docs/codemap/unduhan-raw.md`, kontrak, `TASKS.md` (status #9, baris baru #28)
HASIL_TEST:
- Format YouTube (`aqz-KE-bpKQ`, argumen dasar app tanpa cookies): string lama `18 640x360`, string baru `18 640x360`. Tidak berubah.
- Segmen lokal lewat `download_clip_segment`: 1920×1080 → h264 1920x1080 (4,8 s); 3840×2160 → h264 3840x2160 (15,7 s).
- Render AMF klip 20 detik (sumber sintetis `testsrc2` + noise, face tracking aktif), angka dari `ffprobe`:
  - sumber 1080p, AMF lama (`speed`/`cbr` 6M): 8,4 s, 6,00 Mbps, 1080x1920
  - sumber 1080p, AMF baru (`balanced`/`vbr_peak` 12M/16M/24M): 7,5 s, 12,01 Mbps, 1080x1920, `is_valid_mp4` True
  - sumber 4K, AMF lama: 17,3 s, 6,06 Mbps
  - sumber 4K, AMF baru: 17,4 s, 11,97 Mbps, 1080x1920, `is_valid_mp4` True
  - varian `speed`/`vbr_peak` 12M: 7,7 s / 18,0 s, bitrate sama.
- `check_encoder_support('h264_amf')`: True.
- `venv\Scripts\python.exe scripts\smoke_test.py`: 7/7 PASS, exit 0 (render ke `D:\CheatClip`). `--gpu`: 7/7 PASS, render memakai `h264_amf`, 6 s.
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS (200 simbol).
- `git diff -U0 backend/video_engine.py`: hunk hanya di L294, L696, L811, L863, L1026, L1060. L924/L967 tidak berubah.
CODEMAP_DIPERBARUI: ya. `render-server.md` (argumen AMF baru di `ENCODER_CONFIGS`, dipakai juga metode 2 dan trim lokal), `unduhan-raw.md` (label metode 1, baris batas 2160p dan fallback dikoreksi, risiko baru "YouTube praktis hanya 360p" untuk #28). Tidak ada baris yang bergeser.
CATATAN:
- Keputusan sendiri: AMF `-quality balanced -rc vbr_peak -b:v 12M -maxrate 16M -bufsize 24M` (dalam batas kontrak). Waktu render sama dengan varian `speed`, jadi dipilih `balanced`.
- Preferensi VP9 tidak dipakai: tidak relevan selama YouTube hanya memberi format 18 (#28).
- Video uji 20 detik, bukan 30 detik seperti di Cara menguji: disk C: sempat penuh saat membuat video uji 30 detik (sisa ±3 GB). Video uji kecil dibuat ulang dan dihapus setelah uji.
- Ukur kualitas objektif tidak meyakinkan: PSNR AMF vs referensi ±30 dB konstan di bitrate apa pun (bahkan `cqp` QP 18), sedangkan libx264 50 dB. Ada selisih sistematis dari encoder AMF yang tidak bergantung bitrate (bukan pergeseran frame, sudah dicek). Penyebabnya belum diketahui. Ketajaman perlu dicek pemilik secara visual.
- Ukuran file AMF dua kali lipat (±1,5 MB per detik klip).
- Di luar task: `EXPORTS_DIR` dipindah ke `D:\CheatClip` lewat `CHEAT_CLIP_EXPORTS_DIR` di `backend/.env` (di-ignore git, tidak di-commit), 2 klip lama dipindah dari `~/CheatClip`.
- Unduhan HD YouTube (format 403 lewat ffmpeg, app selama ini 360p) dipindah ke task #28.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
