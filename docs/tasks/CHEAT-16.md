# CHEAT-16: Pisahkan output permanen dari cache
Status: REVIEW

## Tujuan
Hasil render (MP4) dan unduhan raw disimpan di folder permanen di luar proyek (default `~/CheatClip`), dan auto-cleanup hanya menghapus folder cache (`temp_clips`, `temp_clips/uploads`, `backend/temp`), tidak pernah folder permanen.

## Area yang boleh disentuh
- `backend/video_engine.py`: konstanta folder L21-26 (`EXPORTS_DIR` dibaca dari env `CHEAT_CLIP_EXPORTS_DIR`, default `~/CheatClip`), pembuatan folder L152-157 (`mkdir` tetap, sekarang untuk path baru).
- `backend/services/system_service.py`: `auto_cleanup_expired_files` L149-262, daftar folder target L165 (hapus `EXPORTS_DIR` dari TTL, kuota, dan pembersihan folder kosong). Docstring diperbarui.
- `backend/services/render_service.py`: `update_batch_summary_and_zip` L245-294, lokasi ZIP batch (L258) pindah ke `TEMP_DIR`.
- `backend/routers/render.py`: `download_batch_zip` L205-232, baca/buat ZIP di `TEMP_DIR`.
- `backend/main.py`: docstring `background_storage_cleanup_worker` L51-69 (teks saja, tanpa perubahan logika).
- `scripts/smoke_test.py`: tambah cek 5 (cleanup) dan sesuaikan pembersihan ZIP di `TEMP_DIR`.
- `CLAUDE.md`: jebakan no. 1 diperbarui.
- `docs/codemap/`: `penyimpanan-dan-cleanup.md`, `render-server.md`, `arsitektur-backend.md`, `unduhan-raw.md`, `index.md`.

## Di luar scope (jangan dikerjakan)
- Memindahkan isi `backend/exports` yang sudah ada (saat ini kosong) atau menghapus folder itu.
- UI pengaturan folder output, tombol "buka folder", atau penyimpanan pilihan folder di frontend (`src/`).
- Mengubah nilai TTL (1 jam), kuota (5 GB), atau interval cleanup untuk folder cache.
- Mengubah `clear_temp_files` (sudah hanya menyentuh `TEMP_DIR` dan `backend/temp`).
- Mengubah pencarian sumber lokal yang ikut memindai `EXPORTS_DIR` (`download_clip_segment`, `_find_video_file_on_disk`, `download_service`, `extract_clip_frame`). Perilakunya tetap, hanya path foldernya berubah.
- Pembersihan otomatis folder permanen (kuota/TTL untuk output). Folder permanen dikelola pemilik secara manual.

## Keputusan yang boleh diambil AI sendiri
- Nama env var (`CHEAT_CLIP_EXPORTS_DIR`) dan cara membacanya (`expanduser`, path relatif dianggap relatif terhadap root repo).
- Kalau folder default tidak bisa dibuat (izin, drive tidak ada), fallback ke `backend/exports` dengan log peringatan, agar backend tetap menyala.
- ZIP batch dianggap cache (duplikat dari MP4) dan disimpan di `TEMP_DIR`, sehingga tetap dibersihkan setelah 1 jam. Endpoint `download_batch_zip` sudah bisa membuat ulang ZIP bila hilang.
- Cara cek 5 smoke test mengisolasi cleanup: `TEMP_DIR`, `UPLOADS_DIR`, `EXPORTS_DIR`, dan `_base_dir` diganti sementara ke folder sementara, sehingga file asli pemilik tidak tersentuh.

- Default diubah dari `~/Videos/CheatClip` ke `~/CheatClip` atas keputusan pemilik: Windows Defender Controlled Folder Access memblokir python.exe/ffmpeg.exe menulis ke `Videos`.

## Kriteria selesai (ya/tidak)
- [x] Tanpa env var, `EXPORTS_DIR` = `~/CheatClip` (di luar folder proyek) dan folder dibuat saat startup.
- [x] Dengan `CHEAT_CLIP_EXPORTS_DIR` di `.env`, `EXPORTS_DIR` mengikuti nilai itu.
- [x] Render batch menulis MP4 ke folder permanen, dan `GET /api/download-rendered/{file}` tetap mengirim file itu.
- [x] ZIP batch ditulis ke `TEMP_DIR`, dan `GET /api/download-batch-zip/{id}` tetap berfungsi (termasuk membuat ulang bila ZIP hilang).
- [x] `auto_cleanup_expired_files` tidak menghapus file di `EXPORTS_DIR`, baik lewat TTL maupun kuota: file MP4 berumur > 1 jam di folder permanen tetap ada setelah cleanup berjalan.
- [x] File berumur > 1 jam di `TEMP_DIR`/`UPLOADS_DIR` tetap dihapus seperti sebelumnya (perilaku cache tidak berubah).
- [x] Ukuran folder permanen tidak dihitung ke kuota 5 GB.
- [x] Smoke test punya cek 5 untuk dua poin di atas, dan `venv\Scripts\python.exe scripts\smoke_test.py` lulus 6/6.
- [x] Tidak ada perubahan di `src/`. Codemap terdampak diperbarui dan `check_codemap.py` lulus.
- [x] `git diff` hanya berisi file di "Area yang boleh disentuh".

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`: 6/6 PASS. Cek 4 (render) memastikan MP4 ada di `EXPORTS_DIR` baru, cek 5 menjalankan `auto_cleanup_expired_files` di folder terisolasi dengan file MP4 lama di exports (harus tetap ada) dan file lama di temp/uploads (harus terhapus).
- Uji negatif sementara (tidak di-commit): kembalikan `EXPORTS_DIR` ke daftar target cleanup, pastikan cek 5 FAIL.
- Impor `backend.config` dengan dan tanpa `CHEAT_CLIP_EXPORTS_DIR` (lewat env proses), cetak `EXPORTS_DIR`.
- `TestClient` pada router render: `download_batch_zip` untuk batch yang ZIP-nya dihapus membuat ulang ZIP di `TEMP_DIR`.
- `venv\Scripts\python.exe scripts\check_codemap.py` lulus.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `backend/video_engine.py` (L23 `EXPORTS_DIR` dari env, default `~/CheatClip`; L152-162 mkdir + fallback), `backend/services/system_service.py` (`auto_cleanup_expired_files`: `EXPORTS_DIR` keluar dari target, pengaman `is_permanent_output`), `backend/services/render_service.py` (ZIP ke `TEMP_DIR`), `backend/routers/render.py` (impor `TEMP_DIR`, `download_batch_zip` di `TEMP_DIR`), `backend/main.py` (docstring), `scripts/smoke_test.py` (cek 5), `CLAUDE.md`, 11 catatan `docs/codemap/`, kontrak, `TASKS.md`
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: 6/6 PASS, exit 0. Render: `1080x1920, 10.03s, di C:\Users\TEGAR_ADYAKSA\CheatClip`. Cek 5: "cache lama terhapus, exports utuh, kuota hanya cache".
- Uji negatif (sementara, sudah dikembalikan): `EXPORTS_DIR` dimasukkan lagi ke `target_dirs` dan pengaman dimatikan → `[FAIL] auto-cleanup tidak menyentuh exports: TTL menghapus MP4 di exports; kuota menghapus MP4 di exports; ...`, 5/6, exit 1.
- Env: tanpa env → `C:\Users\TEGAR_ADYAKSA\CheatClip`. `CHEAT_CLIP_EXPORTS_DIR=<temp>\cc_env_out` → path itu, folder dibuat. `CHEAT_CLIP_EXPORTS_DIR=~/Videos/CheatClip` → peringatan + fallback `backend\exports`.
- TestClient router render: `update_batch_summary_and_zip` menulis ZIP di `TEMP_DIR` (tidak di exports). ZIP dihapus lalu `GET /api/download-batch-zip/{id}` → 200 dan ZIP dibuat ulang di `TEMP_DIR`. `GET /api/download-rendered/{file}` → 200. Batch tidak dikenal → 404.
- Pengaman: `EXPORTS_DIR` diarahkan ke `temp_clips/my_outputs`, file berumur 2 jam di dalamnya tetap ada, file lama di temp terhapus.
- `~/CheatClip`, `backend/exports`, `backend/temp_clips/uploads` kosong setelah semua uji.
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS.
- `npm run build`: tidak dijalankan, `src/` tidak berubah.
CODEMAP_DIPERBARUI: ya. Isi: `penyimpanan-dan-cleanup.md`, `render-server.md`, `arsitektur-backend.md`, `unduhan-raw.md`, `index.md`. Hanya geser rentang baris (video_engine +5 setelah L153, system_service +10 setelah L165, render.py +1, main.py +1): `cookies-dan-proxy.md`, `face-tracking.md`, `sistem-update.md`, `subtitle-dan-judul.md`, `sumber-video.md`, `transkrip.md`.
CATATAN:
- Default diubah dari `~/Videos/CheatClip` ke `~/CheatClip` atas keputusan pemilik setelah ditemukan Windows Defender Controlled Folder Access memblokir python.exe menulis ke `~/Videos` (event Defender 1123).
- Ditambahkan pengaman `is_permanent_output` (di luar rencana awal, masih di dalam fungsi yang diizinkan): file di dalam `EXPORTS_DIR` dilewati walau folder itu diarahkan ke dalam folder cache.
- Pesan log fallback berbahasa Inggris mengikuti gaya log di `video_engine.py`.
- Folder permanen tidak punya batas ukuran (sengaja, di luar scope). Pencarian sumber lokal yang memindai `EXPORTS_DIR` tidak diubah.
- Line ending `video_engine.py` sempat berubah ke LF oleh `sed -i`, sudah dikembalikan ke CRLF.
- Task berisiko tinggi: wajib `/review 16` di sesi baru.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
