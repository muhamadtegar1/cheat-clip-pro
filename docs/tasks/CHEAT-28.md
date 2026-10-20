# CHEAT-28: Unduhan HD YouTube lewat cache stream (versi kecil, 1080p)
Status: REVIEW

## Riwayat
- 2026-10-11: ditunda pemilik (SKIPPED). Kualitas dianggap cukup, draf lama dinilai riskan. Saran saat itu: versi kecil (cache 1080p, batas ukuran, saklar `.env`, timeout ketat, `yt-dlp-ejs` hanya bersama metode cache).
- 2026-10-20: dibuka kembali atas keputusan pemilik sebelum produksi untuk campaign (sumber 360p dipotong vertikal = area ±202x360 diperbesar 5,3x). Kontrak ditulis ulang sebagai #28a (versi kecil). Pilihan 1440p/2160p dan tombol unduh video asli menjadi #28b, nanti dan hanya bila perlu.
- 2026-10-20 (implementasi): uji nyata menemukan regresi. Setelah `yt-dlp-ejs` terpasang di venv, semua pemanggil `get_yt_dlp_base_cmd` ikut memecahkan tantangan JS, sehingga metode lama (saklar mati atau cache gagal) memilih format HD lewat ffmpeg ke URL remote dan macet sampai timeout (sebelumnya 360p dalam ±17 s); `download_full_raw_video` dan `extract_clip_frame` juga berubah perilaku. Dibuktikan: `--no-js-runtimes` dengan `yt-dlp-ejs` terpasang = hanya format 18 dalam 7-8 s, sama dengan sebelum task. Pemilik menyetujui perluasan kontrak: `get_yt_dlp_base_cmd` mendapat parameter `solve_js_challenges` (default mati = `--no-js-runtimes`), hanya cache HD yang menyalakannya. Pemanggil lewat pustaka Python (`youtube_service`, `gdrive_service`) tidak terdampak (default pustaka hanya Deno, tidak terpasang).

## Tujuan
Segmen klip dari video YouTube (render, pratinjau subtitle, unduh segmen) bersumber 1080p lewat cache stream yang diunduh sekali per video lalu dipotong lokal, dengan metode lama (sampai 360p) tetap sebagai cadangan dan saklar `.env` untuk mematikannya.

## Temuan riset ulang 2026-10-20 (tanpa mengubah kode, `yt-dlp-ejs` dipasang di folder scratchpad, bukan venv)
- yt-dlp 2026.08.19, Node v22.17.0 di PATH, Deno tidak ada. `get_yt_dlp_base_cmd` (L427-469) sudah mengirim `--js-runtimes node`, jadi yang kurang hanya paket `yt-dlp-ejs` (0.8.0).
- Tanpa `yt-dlp-ejs`: hanya format 18 (360p). Dengan `yt-dlp-ejs` dan daftar `player_client` yang sama: format sampai 2160p tersedia (video uji `aqz-KE-bpKQ` 10,5 menit dan K3 `hbZbPHjE8NE` 52 menit).
- **Tidak selalu**: dari ±9 ekstraksi, 1-2 kali hanya muncul format 18 (tantangan JS tidak dipecahkan pada permintaan itu, ada peringatan HTTP 429 di halaman). Jadi metode baru wajib memeriksa tinggi format, mencoba ulang terbatas, lalu turun ke metode lama.
- Unduhan native (bukan ffmpeg) 1080p H.264 60fps + audio untuk video 10,5 menit: 275 MB dalam 73 s (rata-rata 4,4 MiB/s, potongan ±10 MB). Ukuran 1080p H.264 video K3 52 menit: ±376 MB video + ±48 MB audio.
- Potong lokal 30 s dari cache dengan perintah jalur file lokal yang sudah ada (x264 `veryfast` CRF 18, L813-823): 15,6 s, hasil 1920x1080, durasi 30,02 s.
- Metode 1 sekarang (`--download-sections`) dengan `yt-dlp-ejs` tetap memilih format 18 pada uji ini; riset 2026-10-11 juga membuktikan ffmpeg ke URL remote HD tidak andal (400/403). Karena itu pendekatannya unduh native utuh, bukan memperbaiki metode 1.
- Tanpa batasan codec, yt-dlp memilih AV1 (`399`). Decode AV1 di iGPU AMD/CPU berisiko lambat, jadi H.264 diutamakan, lalu VP9.
- Pencarian file lokal di `download_clip_segment` (L786-807) memindai file langsung di `TEMP_DIR` dengan pencocokan nama longgar (`clean_lower in f.name`). Cache **tidak boleh** diletakkan langsung di `TEMP_DIR`, karena file yang sedang diunduh bisa salah dianggap sumber lokal.
- Disk: D: sisa ±103 GB (`TEMP_DIR` di D:), C: ±32 GB.

## Desain
1. `backend/requirements.txt`: tambah `yt-dlp-ejs` (paket resmi proyek yt-dlp). Dipasang ke venv lewat `pip install -r backend/requirements.txt`.
2. `backend/video_engine.py`, di dekat `download_clip_segment`:
   - Saklar `CHEAT_CLIP_YT_HD_CACHE` (env, bisa di `backend/.env`): kosong/`1` = aktif, `0` = mati (perilaku persis seperti sebelum task). Dibaca saat dipanggil, bukan saat impor.
   - Helper cache: kunci = ID video YouTube + tinggi (1080), file di subfolder `TEMP_DIR/yt_cache/` (bukan langsung di `TEMP_DIR`), ditulis ke nama sementara lalu di-rename setelah valid, kunci (lock) per video agar beberapa klip dari video yang sama tidak mengunduh bersamaan; pemakai berikutnya menunggu lalu memakai file yang sama.
   - Unduhan: downloader native yt-dlp (tanpa `--download-sections`), format 1080p dengan batas bawah 720 (H.264 > VP9 > lainnya, audio m4a diutamakan), `--merge-output-format mp4`, timeout ketat. Hasil diperiksa `ffprobe`: tinggi < 720 atau MP4 tidak valid = gagal. Bila format HD tidak tersedia pada ekstraksi pertama, coba ulang sekali; tetap gagal = langsung ke metode lama.
   - Batas: perkiraan ukuran dari metadata format (`filesize`/`filesize_approx`) di atas batas (default 2 GB) atau tidak diketahui untuk video sangat panjang = lewati cache, pakai metode lama.
   - Pemotongan: memakai perintah potong lokal yang sudah ada (L810-833), tanpa mengubah perintah itu.
   - Penyisipan di `download_clip_segment`: setelah guard upload/Drive (L835-837) dan sebelum metode 1 (L862). Metode 1-4 dan string format 720p/480p tidak diubah.
   - `get_yt_dlp_base_cmd(..., solve_js_challenges=False)`: default mengirim `--no-js-runtimes` (pemecah tantangan JS mati, efeknya sama dengan sebelum task: hanya format 18); `True` mengirim `--js-runtimes deno/node` seperti sekarang. Hanya helper cache HD yang memanggil dengan `True`.
3. `scripts/smoke_test.py`: cek offline baru (tanpa jaringan, subprocess yt-dlp dipalsukan): kunci/nama cache, saklar `0` = metode lama dipanggil tanpa helper cache, HD tidak tersedia/tinggi < 720/gagal = jatuh ke metode lama, cache dipakai ulang tanpa unduh kedua, cache di subfolder dan tidak terdeteksi sebagai sumber lokal.
4. `CLAUDE.md`: prasyarat Node di PATH untuk `yt-dlp-ejs`, saklar `CHEAT_CLIP_YT_HD_CACHE`, catatan bahwa YouTube bisa berubah dan `yt-dlp`/`yt-dlp-ejs` diperbarui manual (`pip install -U yt-dlp yt-dlp-ejs` di venv), deskripsi smoke test.

## Area yang boleh disentuh
- `backend/requirements.txt`: satu baris `yt-dlp-ejs`.
- `backend/video_engine.py`: helper cache baru tepat sebelum `download_clip_segment` (sekitar L743), dan di `download_clip_segment` (L744-1072) hanya penyisipan pemanggilan cache antara guard L835-837 dan metode 1 (L862), plus log. `get_yt_dlp_base_cmd` (L427-469): hanya parameter `solve_js_challenges` dan pilihan argumen runtime JS (perluasan disetujui pemilik 2026-10-20); daftar `player_client`, cookies, dan argumen lain tidak diubah.
- `scripts/smoke_test.py`: cek baru #28; cek lama tidak diubah logikanya.
- `docs/codemap/unduhan-raw.md`, `render-server.md`, `penyimpanan-dan-cleanup.md` (subfolder cache), `arsitektur-backend.md` (dependensi), catatan lain yang rujukan barisnya bergeser. `CLAUDE.md` (lihat Desain no. 4), `TASKS.md`, kontrak ini.
- Venv: hanya `pip install -r backend/requirements.txt` (menambah `yt-dlp-ejs`).

## Di luar scope (jangan dikerjakan)
- 1440p/2160p, pilihan resolusi di UI atau env (#28b).
- `download_full_raw_video` (tombol unduh video asli, L1075-1176) dan `extract_clip_frame` (#28b bila perlu).
- Daftar `player_client`, PO Token provider, cookies, proxy, `backend/services/youtube_service.py`.
- Metode 1-4 lama, perintah potong lokal, encoder, filtergraph, kanvas, face tracking.
- `render_service.py`, `download_service.py`, `subtitle_preview_service.py` (memanggil `download_clip_segment` dengan signature yang sama).
- Frontend, analisis (jalur caption YouTube tidak mengunduh video), fallback Whisper YouTube (unduh audio).
- Kebijakan auto-cleanup (TTL 1 jam, kuota 5 GB) dan `backend/services/system_service.py`.

## Keputusan yang boleh diambil AI sendiri
- Nama helper, nama file cache, nama env selain `CHEAT_CLIP_YT_HD_CACHE`, nilai timeout, batas ukuran (default 2 GB, boleh disesuaikan dengan alasan dari pengukuran), string format persis (selama 1080p maks, 720p min, H.264 diutamakan).
- Mekanisme lock (mis. `threading.Lock` per ID video), cara menunggu unduhan yang sedang berjalan.
- Menyegarkan waktu file cache saat dipakai ulang (agar tidak dihapus TTL di tengah sesi) atau tidak.
- Cara memalsukan subprocess di smoke test.
- Urutan cookies/tamu untuk metode cache: mengikuti urutan `attempts` yang sudah ada.

## Kriteria selesai (ya/tidak)
- [x] `backend/requirements.txt` memuat `yt-dlp-ejs`, dan `pip install -r backend/requirements.txt` di venv tidak error.
- [x] Segmen 30 s dari video uji `aqz-KE-bpKQ` (menit 5) lewat `download_clip_segment` tingginya 1080 (`ffprobe`), MP4 valid (`is_valid_mp4`), codec sumber cache H.264.
- [x] Andal: 3 kali berturut-turut dengan cache dihapus di antaranya, semuanya 1080 (bila YouTube sesekali hanya memberi 360p, percobaan ulang menutupinya; kalau tetap 360p, log menyebut alasannya dan hasilnya tetap valid lewat metode lama).
- [x] Waktu wajar: unduhan pertama video uji (10,5 menit) ≤ 3 menit; segmen kedua dari video yang sama (posisi lain, mis. menit 9) memakai cache tanpa unduh ulang (terlihat di log) dan selesai ≤ 30 s dengan durasi benar (±0,5 s).
- [x] Dua segmen dari video yang sama diminta bersamaan hanya memicu satu unduhan cache.
- [x] Saklar `CHEAT_CLIP_YT_HD_CACHE=0`: helper cache tidak dipanggil, perilaku sama dengan sebelum task (smoke test).
- [x] Pemanggil lain `get_yt_dlp_base_cmd` (metode 1-4, `download_full_raw_video`, `extract_clip_frame`) mendapat `--no-js-runtimes` dan tidak ada `--js-runtimes`; uji nyata saklar `0` = segmen 360p lewat metode 1 dalam waktu wajar (bukan macet).
- [x] Gagal (HD tidak tersedia, tinggi < 720, ID video salah, ukuran di atas batas): jatuh ke metode lama, string format 720p/480p tidak berubah (`git diff`).
- [x] File cache ada di `TEMP_DIR/yt_cache/` (bukan `EXPORTS_DIR`, bukan langsung di `TEMP_DIR`), tidak terdeteksi sebagai sumber lokal, dan ikut auto-cleanup.
- [x] Render 1 klip dari segmen YouTube HD menghasilkan 1080x1920 valid (AMF), dan potongan frame dibandingkan dengan render dari sumber 360p (gambar disimpan sementara untuk dilihat pemilik).
- [x] Smoke test lulus (cek lama + cek #28, offline), `check_codemap.py` lulus.
- [ ] Klip dari YouTube di UI terlihat HD (perlu dicek pemilik). Implementer sudah menguji alur UI (pratinjau + render memakai cache 1080p, lihat HASIL_TEST); penilaian visual akhir tetap oleh pemilik.

## Cara menguji
- Skrip uji di scratchpad yang memanggil `download_clip_segment` dan `render_clip_to_mp4` langsung, mencatat waktu, `ffprobe` (codec, tinggi, durasi), dan baris log metode yang dipakai. Ulangi 3 kali dengan cache dihapus, lalu 1 kali tanpa menghapus cache (posisi lain), lalu 2 permintaan bersamaan.
- Paksa gagal: ID video salah, batas ukuran diperkecil lewat env, `CHEAT_CLIP_YT_HD_CACHE=0`.
- `venv\Scripts\python.exe scripts\smoke_test.py` dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- Pemilik: `npm run dev`, analisis satu video YouTube, pratinjau dan render satu klip, lihat ketajamannya; log backend menyebut cache HD.
- File uji besar dan cache dihapus setelah pengujian (cache di `TEMP_DIR/yt_cache/` juga dibersihkan auto-cleanup).

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/requirements.txt`: `yt-dlp-ejs>=0.8.0` (L13), terpasang di venv lewat `pip install -r backend/requirements.txt` (0.8.0).
- `backend/video_engine.py`:
  - `get_yt_dlp_base_cmd` (L427-475): parameter `solve_js_challenges=False`; default `--no-js-runtimes`, `True` = `--js-runtimes deno/node` seperti sebelumnya (perluasan kontrak disetujui pemilik). Satu baris lama berubah (`if shutil.which("deno")` menjadi `elif`).
  - Blok baru L750-951 sebelum `download_clip_segment`: konstanta `YT_HD_CACHE_*` (subfolder `yt_cache`, 1080p maks, 720p min, format H.264 > VP9 > lain, 2 kali ekstraksi), `yt_hd_cache_enabled` (saklar `CHEAT_CLIP_YT_HD_CACHE`), `yt_hd_cache_max_bytes` (`CHEAT_CLIP_YT_HD_CACHE_MAX_GB`, default 2), `extract_youtube_video_id`, `yt_hd_cache_path`, lock per video, `_probe_video_stream`, `_yt_hd_cache_valid`, `_yt_hd_cache_extract` (`-J -f`, tolak tinggi < 720, perkiraan ukuran, info JSON), `_yt_hd_cache_download` (`--load-info-json`, tanpa ekstraksi ulang, `--no-mtime`), `get_youtube_hd_cache` (cookies lalu tamu, coba ulang, batas ukuran, validasi `ffprobe`, rename atomik, mtime disegarkan saat dipakai ulang; gagal apa pun = `None`).
  - `download_clip_segment` L1052-1059: setelah sanitasi `clean_url`, `get_youtube_hd_cache` lalu panggil ulang `download_clip_segment` dengan path cache (jalur potong lokal yang sudah ada, perintahnya tidak diubah); potong gagal = lanjut metode 1. Metode 1-4 dan string format tidak berubah (`git diff -U0`: hanya hunk di `get_yt_dlp_base_cmd`, blok baru, dan sisipan ini).
- `scripts/smoke_test.py`: `run_yt_hd_cache_check` (cek 11) dan pemanggilannya di `main`; cek lama tidak diubah.
- `CLAUDE.md` (prasyarat Node/Deno, saklar dan pembaruan manual, deskripsi smoke), `docs/codemap/` (lihat di bawah), `TASKS.md`, kontrak ini.
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: `21/21 cek lulus. SMOKE TEST LULUS`, termasuk `[PASS] cache HD YouTube (#28)` (runtime JS hanya untuk cache, saklar 0, coba ulang, batas ukuran, < 720p ditolak, 2 permintaan = 1 unduhan, potong lokal dari cache tanpa metode lama, cache tidak terdeteksi sebagai sumber lokal).
- `venv\Scripts\python.exe scripts\check_codemap.py`: `SEMUA CEK LULUS` (284 simbol).
- Uji nyata (skrip scratchpad memanggil `download_clip_segment`/`render_clip_to_mp4` langsung, video `aqz-KE-bpKQ`, menit 5, 30 s):
  - Unduhan pertama dengan cache dihapus, 3 kali: semuanya 1920x1080 H.264, durasi 30,02 s, sumber cache H.264 format `299+258`; total 71,4 / 65,7 / 75,8 s (unduhan 275 MB 41-50 s). Setelah perubahan `solve_js_challenges` diulang sekali: 67,1 s, 1080p.
  - Pakai ulang (menit 9, tanpa hapus cache): 18,5 s, log `Memakai cache ... (tanpa unduh ulang)`, 1080p, durasi 30,02 s.
  - Dua segmen bersamaan (menit 1:40 dan 3:20): 1 unduhan + 1 pakai ulang, keduanya 1080p 20,02 s, total 65,2 s.
  - Gagal: ID salah = `None` dalam 12,8 s (log `This video is unavailable`); batas 0,01 GB = `None` (`perkiraan ukuran 275 MB di atas batas 10 MB`); saklar `0` = `None` tanpa memanggil ekstraksi.
  - Saklar `0` lewat `download_clip_segment`: metode 1, 640x360, 20,0 s. Sebelum perbaikan `--no-js-runtimes` uji ini macet > 5 menit di ffmpeg ke URL remote HD (regresi, lihat Riwayat).
  - Render AMF 9:16 tanpa face tracking: dari segmen HD 1080x1920 valid 10,4 s; dari segmen 360p 1080x1920 valid 5,0 s. Potongan tengah frame berdampingan di `tests/hd28/banding_360_vs_hd.png` (kiri 360p, kanan HD), video di `tests/hd28/render_*.mp4` (folder lokal, dikecualikan lewat `.git/info/exclude`).
- Uji UI oleh implementer (browser bawaan, `npm run dev-backend` + `dev-frontend`, tanpa kuota Gemini): video K3 B `094y1Z2wpJg` (22 menit) dianalisis lewat `/api/analyze` dengan key `mock` per request, hasilnya dimasukkan ke riwayat `localStorage` browser bawaan lalu dibuka lewat Load Analysis. Pratinjau subtitle klip 1 (0:11-0:22): log `[YT HD cache] Mengunduh 094y1Z2wpJg format 137+140 1080p avc1.640028 ±121 MB (mode tamu)`, `siap dalam 18s`, lalu `Slicing local/gdrive video: ...yt_cache\094y1Z2wpJg_1080p.mp4`; Whisper 21 kata Inggris akurat. Render 1 klip dari UI (AMF): log `Memakai cache ... (tanpa unduh ulang)`, `memakai 21 kata dari pratinjau`, UI `1 of 1 completed`; hasil `D:\CheatClip\clip_1_batch_1792479468_b9f0d2.mp4` 1080x1920 H.264 ±11,9 Mbps, 11,03 s, frame tajam dan subtitle karaoke ter-render (`tests/hd28/ui_render_frame.png`, `ui_render_sub.png`). Kriteria "terlihat HD di UI" tetap untuk dicek pemilik.
- Riset `--no-js-runtimes` dengan `yt-dlp-ejs` terpasang: 2 kali `-F`, hanya format 18, 7-8 s.
CODEMAP_DIPERBARUI: ya. `unduhan-raw.md` (baris baru konstanta, fungsi cache, pemanggilan cache, `get_yt_dlp_base_cmd`, risiko cache HD + larangan menyalakan pemecah JS untuk metode lama + catatan loop cookies), `penyimpanan-dan-cleanup.md` (folder `yt_cache`), `arsitektur-backend.md` (dependensi), rentang bergeser di `face-tracking.md`, `render-server.md`, `subtitle-dan-judul.md`, `sumber-video.md`, `transkrip.md`. Dirapikan juga rujukan lama yang sudah usang sebelum task: "pemanggilan saat render" di `face-tracking.md` (sekarang L3282, `detect_speaker_face_box(`).
CATATAN:
- Keputusan sendiri: batas ukuran 2 GB (video K3 52 menit ±424 MB), lebih dari 3 jam tanpa info ukuran = lewati; timeout unduhan 2 s per MB (300-1800 s); ekstraksi timeout 90 s; mtime cache disegarkan saat dipakai ulang (TTL 1 jam dihitung dari pemakaian terakhir); `--no-mtime` agar file baru tidak langsung dianggap tua oleh auto-cleanup.
- Ditemukan, di luar scope dan tidak diubah: di `download_clip_segment` badan loop `for use_cookies in attempts` hanya mengisi `base_cmd`, jadi metode 1-4 praktis berjalan sekali dengan `base_cmd` percobaan terakhir (mode tamu bila ada cookies). Dicatat di codemap `unduhan-raw.md`. Helper cache memakai urutan cookies lalu tamu dengan benar.
- Ditemukan, di luar scope: segmen metode 1 lama (`--force-keyframes-at-cuts`) mulai beberapa frame berbeda dari segmen potong lokal pada detik yang sama (terlihat di gambar pembanding).
- Klip pertama dari video YouTube baru sekarang menunggu unduhan cache (±45-120 s tergantung panjang video) sebelum dipotong; klip berikutnya dari video yang sama cepat. Analisis jalur caption YouTube tidak mengunduh video, jadi tidak terdampak.
- `download_full_raw_video` dan `extract_clip_frame` tetap 360p (tetap `--no-js-runtimes`), sesuai scope (#28b).
- YouTube bisa berubah lagi; bila klip kembali 360p, log `[YT HD cache] ... kembali ke metode lama: <alasan>` menjelaskan sebabnya. Pembaruan manual tercatat di `CLAUDE.md`.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
