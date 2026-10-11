# CHEAT-28: Unduhan HD YouTube (yt-dlp-ejs + stream cache)
Status: SKIPPED

## Alasan ditunda
Ditunda oleh pemilik proyek (2026-10-11): kualitas render saat ini dianggap cukup, task tidak mendesak, dan draf kontrak di bawah dinilai riskan (perubahan besar di `download_clip_segment`, uji bergantung pada YouTube yang tidak stabil). `yt-dlp-ejs` yang dipasang saat riset sudah dicopot lagi dari venv, jadi app kembali memakai format 18 (360p) yang stabil. Bila dilanjutkan, mulai dari versi kecil: cache native hanya 1080p, video ≤ 30 menit, saklar `.env`, timeout ketat, dan `yt-dlp-ejs` hanya aktif bersama metode cache.

## Tujuan
Segmen klip dari video YouTube terunduh minimal 1080p (bukan 360p seperti sekarang) dalam waktu wajar dan andal, dengan fallback 720p/480p tetap ada.

## Temuan riset (sebelum kontrak, tanpa mengubah kode)
- Tanpa pemecah JS challenge (`yt-dlp-ejs` tidak terpasang), daftar `player_client=android,ios,web_embedded,mweb,web` hanya memberi format 18 (360p). Klien `default` memberi HD lewat `android_vr`, tetapi format itu hanya menyajikan ±10 MB pertama lalu 403, bahkan untuk downloader native yt-dlp.
- Setelah `pip install yt-dlp-ejs` (0.8.0) di venv, daftar klien yang **sama** memberi format 2160p (`401+258`, klien `WEB_EMBEDDED_PLAYER`). Uji `curl` dengan header `Range`: potongan di awal, tengah, dan 10 MB semuanya 206, ±3-4 MB/s.
- ffmpeg ke URL remote (dipakai `--download-sections` metode 1 dan URL stream metode 2) tidak andal: tanpa `-request_size` macet sampai timeout; dengan `-request_size 10485760` audio berhasil, tetapi demuxer MP4 membaca dekat akhir file dan YouTube membalas 400 ("partial file"). yt-dlp tetap keluar `rc=0` dengan file 262 byte.
- Backend memakai `yt-dlp.exe` dari venv (`scripts/start-backend.js` menaruh `venv\Scripts` di depan `PATH`), versi 2026.8.19.

## Area yang boleh disentuh
- `backend/requirements.txt`: tambah `yt-dlp-ejs` (paket resmi proyek yt-dlp). Paket sudah terpasang di venv saat riset atas persetujuan pemilik.
- `backend/video_engine.py`:
  - `download_clip_segment` L688-1016: tambah metode baru sebelum metode 1 (atau mengganti urutan) untuk sumber YouTube: unduh stream video + audio dengan **downloader native yt-dlp** (tanpa `--download-sections`) ke cache `TEMP_DIR`, lalu potong lokal dengan FFmpeg. Metode 1-4 lama tetap ada sebagai fallback, string format 720p/480p (L924, L967) tidak diubah.
  - Fungsi helper baru di dekat `download_clip_segment` untuk cache stream per video (kunci: ID video + batas tinggi), termasuk kunci/lock agar beberapa klip dari video yang sama tidak mengunduh bersamaan.
  - `get_yt_dlp_base_cmd` L392-434: hanya bila perlu untuk metode baru (mis. argumen `--js-runtimes`). Daftar `player_client` tidak diubah kecuali uji membuktikan perlu, dan alasannya dicatat.
- `scripts/smoke_test.py`: tidak wajib. Boleh menambah cek offline untuk logika cache (tanpa jaringan), bukan unduhan YouTube.
- `docs/codemap/unduhan-raw.md`, `docs/codemap/render-server.md`, `docs/codemap/penyimpanan-dan-cleanup.md` (cache baru di `TEMP_DIR`), `docs/codemap/arsitektur-backend.md` (dependensi), `CLAUDE.md` bagian "Menjalankan" bila prasyarat berubah.

## Di luar scope (jangan dikerjakan)
- `download_full_raw_video` (tombol unduh video asli) dan `extract_clip_frame`: task terpisah bila perlu.
- `player_client` di `backend/services/youtube_service.py` (metadata/transkrip).
- PO Token provider (`bgutil-ytdlp-pot-provider`), cookies akun, proxy.
- Encoder, filtergraph, ukuran kanvas, preferensi SDR/HDR.
- `backend/services/render_service.py` dan `download_service.py` (memanggil `download_clip_segment` dengan signature yang sama, jadi tidak perlu diubah).
- Frontend.

## Keputusan yang boleh diambil AI sendiri
- Batas tinggi stream cache: 1080 atau 2160. Pakai 2160 hanya bila ukuran/waktu unduh wajar (lihat kriteria); kalau tidak, cache 1080 dan biarkan 2160 untuk task lain. Catat angka ukurnya.
- Batas durasi video untuk metode cache (mis. hanya bila durasi video ≤ N menit atau perkiraan ukuran ≤ X GB, sisanya langsung ke fallback lama). Nilai N/X berdasarkan pengukuran dan sisa disk.
- Nama file dan lokasi cache di `TEMP_DIR` (dibersihkan auto-cleanup 1 jam, kuota 5 GB). Potong lokal: `-c copy` bila aman, atau encode ulang dengan `ACTIVE_ENCODER_ARGS` seperti jalur file lokal.
- Mengutamakan codec tertentu (mis. VP9/AVC di atas AV1) bila decode AV1 terbukti memperlambat render > 2×.
- Mengapa metode cache gagal (403, format tidak tersedia, timeout) → langsung lanjut ke metode lama tanpa mengubah perilakunya.

## Kriteria selesai (ya/tidak)
- [ ] `backend/requirements.txt` memuat `yt-dlp-ejs`, dan `pip install -r backend/requirements.txt` di venv tidak error.
- [ ] Segmen 30 detik dari video YouTube 4K uji (`aqz-KE-bpKQ`, menit 5) lewat `download_clip_segment` tingginya ≥ 1080 (`ffprobe`), MP4 valid (`is_valid_mp4`).
- [ ] Andal: 3 kali percobaan berturut-turut (cache dihapus di antaranya) semuanya ≥ 1080.
- [ ] Waktu wajar: unduhan pertama untuk video uji (10,5 menit) selesai ≤ 3 menit; klip kedua dari video yang sama memakai cache (tanpa unduh ulang, terlihat di log) dan selesai ≤ 30 detik.
- [ ] Segmen kedua di posisi berbeda (mis. menit 9) dari cache yang sama juga benar durasinya (±0,5 detik).
- [ ] Bila metode cache dipaksa gagal (mis. URL video tidak valid), fallback metode lama tetap jalan dan string format 720p/480p tidak berubah (`git diff`).
- [ ] Render 1 klip dari segmen YouTube HD menghasilkan 1080×1920 valid (render AMF).
- [ ] File cache berada di `TEMP_DIR` (bukan `EXPORTS_DIR`) dan ikut kebijakan auto-cleanup.
- [ ] Smoke test 7/7 (offline) dan `check_codemap.py` lulus.
- [ ] Klip dari YouTube di UI terlihat HD (perlu dicek pemilik).

## Cara menguji
- Skrip uji di scratchpad yang memanggil `download_clip_segment` dan `render_clip_to_mp4` langsung, mencatat waktu, `ffprobe` (codec, tinggi, durasi), dan baris log metode yang dipakai.
- Ulangi 3 kali dengan cache dihapus, lalu 1 kali tanpa menghapus cache (posisi lain).
- Paksa gagal metode cache (URL video tidak ada / ID salah) untuk memastikan fallback.
- `venv\Scripts\python.exe scripts\smoke_test.py` dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- File uji besar ditulis di drive D: (`TEMP_DIR` ada di D:), bukan C: (sisa ±8 GB). Semua file uji dan cache dihapus setelahnya.

## Laporan implementer
STATUS:
FILE_DIUBAH:
HASIL_TEST:
CODEMAP_DIPERBARUI: ya/tidak (sebutkan catatan)
CATATAN:

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
