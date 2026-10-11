# CHEAT-17a: Smoke test satu perintah
Status: DONE

## Tujuan
Satu perintah (`venv\Scripts\python.exe scripts\smoke_test.py`) memverifikasi alur inti, yaitu analisis mode mock, skenario error Gemini, dan render 1 klip dari video sintetis. Semuanya lulus pada kode saat ini tanpa YouTube, tanpa Gemini sungguhan, dan tanpa memicu auto-cleanup.

## Area yang boleh disentuh
- `scripts/smoke_test.py` (baru): seluruh logika smoke test.
- `CLAUDE.md`: bagian "Smoke test" diganti dengan satu perintah (sesuai instruksi di bagian itu).
- `docs/codemap/analisis-ai.md`: baris risiko "Smoke test (task 17a) akan bergantung padanya" diperbarui.
- `docs/codemap/index.md`: satu baris rujukan ke smoke test (opsional).
- Kode yang **dipanggil** (dibaca saja, tidak diubah):
  - `backend/routers/analyze.py` `analyze_video` L224-1477: cek key mock L228-233, deteksi upload L281-288, cabang upload L290-467 (subtitle manual L374-397 agar Whisper dilewati), mock short-circuit L827-892, panggilan Gemini + retry L1076-1299, rekonstruksi klip L1385-1426.
  - `backend/routers/render.py` `start_batch_render` L36-97.
  - `backend/services/render_service.py` `process_batch_rendering` L535-587, `render_single_batch_clip` L29-242, `update_batch_summary_and_zip` L245-294.
  - `backend/video_engine.py` `download_clip_segment` (cabang file lokal), `render_clip_to_mp4` L2856-3191, `is_valid_mp4` L432-488.

## Di luar scope (jangan dikerjakan)
- Mengubah kode aplikasi di `backend/` atau `src/`. Kriteria task adalah "lulus pada kode asli".
- Golden fixtures dan perbandingan kualitas analisis (task 17b).
- Test frontend/UI, render di browser (FFmpeg WASM), face tracking, Whisper, unduhan YouTube/Drive.
- Menambah dependensi (`requirements.txt`, `package.json`) atau framework test (pytest).
- CI/GitHub Actions.

## Keputusan yang boleh diambil AI sendiri
- **Skenario `RATE_LIMIT` dan `MALFORMED_JSON` disimulasikan di skrip uji, bukan di backend.** Skrip mengganti `genai.Client` dan `get_flash_models_for_key` di modul `backend.routers.analyze` dengan klien palsu (monkeypatch). Klien palsu melempar error `429 RESOURCE_EXHAUSTED` atau mengembalikan teks JSON terpotong. Dengan cara ini jalur asli diuji, yaitu fallback model, pesan error 429, `parse_lenient_json_analysis`, dan rekonstruksi klip, tanpa mengubah `analyze.py`. *Berbeda dari teks TASKS.md ("Mock ditambah skenario"), disetujui pemilik saat kontrak disetujui.*
- Durasi, resolusi, dan isi video sintetis (mis. 40 s, 1280×720, `testsrc2` + nada sine) dan isi SRT manual.
- Pengaturan render minimal agar cepat dan deterministik: `caption_style: "none"` (tanpa Whisper), `enable_face_tracking: false`, `hardware_accel: "cpu"`. Judul overlay tetap aktif. Flag `--gpu` opsional untuk memakai `auto`.
- Lokasi file kerja: folder sementara sistem (`tempfile`), dihapus di akhir. Output render milik test (`clip_*_{batch_id}.mp4`, ZIP batch, segmen `{batch_id}_*` di `temp_clips`) dihapus setelah diverifikasi. Flag `--keep` untuk menyimpannya.
- Format output: satu baris `PASS`/`FAIL` per cek, ringkasan di akhir, exit code 0 bila semua lulus, 1 bila ada yang gagal.

## Kriteria selesai (ya/tidak)
- [x] `venv\Scripts\python.exe scripts\smoke_test.py` berjalan dari root repo dan keluar dengan kode 0 pada kode saat ini.
- [x] Skrip **tidak** mengimpor `backend.main` (lifespan tidak berjalan, jadi auto-cleanup tidak terpicu) dan tidak membutuhkan backend yang sedang menyala.
- [x] Video sintetis dibuat dengan FFmpeg di folder sementara, tanpa jaringan. (Lalu disalin sementara ke `backend/temp_clips/uploads/upload_smoke_*.mp4` karena render hanya menemukan sumber lokal di sana. Dihapus di akhir.)
- [x] Cek 1 (analyze mock): `POST /api/analyze` dengan key `mock` + path video sintetis + SRT manual menghasilkan event `done` dengan ≥ 1 klip, dan `start_time < end_time` di setiap klip.
- [x] Cek 2 (`RATE_LIMIT`): klien Gemini palsu yang selalu melempar error 429 menghasilkan event error `status: 429`, tanpa `done`.
- [x] Cek 3 (`MALFORMED_JSON`): klien palsu yang mengembalikan JSON terpotong/rusak tetap menghasilkan `done` dengan ≥ 1 klip lewat `parse_lenient_json_analysis`.
- [x] Cek 4 (render): satu klip (±10 s) dari video sintetis dirender lewat `POST /api/render-batch`. Status akhir batch `completed`, file MP4 ada, `is_valid_mp4` benar, dan ffprobe melaporkan 1080×1920 dengan durasi ±1 s dari durasi klip.
- [x] File yang dibuat test dibersihkan, dan tidak ada file lain di `backend/exports` atau `backend/temp_clips` yang tersentuh.
- [x] Bila FFmpeg tidak ada di PATH, skrip gagal dengan pesan jelas (bukan traceback).
- [x] Bagian "Smoke test" di `CLAUDE.md` berisi satu perintah ini. Codemap terdampak diperbarui dan `scripts/check_codemap.py` lulus.
- [x] `git diff` hanya berisi file di "Area yang boleh disentuh".

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py` → semua cek PASS, exit 0.
- Uji negatif sementara (tidak di-commit): ubah satu ekspektasi di skrip (mis. resolusi 1080×1080), pastikan cek terkait FAIL dan exit 1, lalu kembalikan.
- `git status` sebelum dan sesudah test: tidak ada file baru di `backend/exports` atau `backend/temp_clips`.
- `venv\Scripts\python.exe scripts\check_codemap.py` lulus.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `scripts/smoke_test.py` (baru), `CLAUDE.md` (bagian Smoke test), `docs/codemap/analisis-ai.md` (risiko), `docs/tasks/CHEAT-17a.md`, `TASKS.md`
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: 5/5 PASS, exit 0, ±22 s (video sintetis; analyze mock 3 klip; RATE_LIMIT status 429 setelah 4 model dicoba; MALFORMED_JSON 1 klip dari JSON rusak; render 1080x1920 10.03 s).
- Uji negatif (salinan sementara dengan ekspektasi 1080x1080, sudah dihapus): `[FAIL] render 1 klip: resolusi 1080x1920`, 4/5, exit 1.
- FFmpeg hilang (simulasi `shutil.which` -> None): `[FAIL] FFmpeg/ffprobe tidak ditemukan di PATH...`, exit 1, tanpa traceback.
- Isi `backend/temp_clips/uploads` dan `backend/exports` sebelum dan sesudah test sama (tidak ada sisa file `upload_smoke_*` atau `*batch_*` milik test).
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS.
- `npm run build`: tidak dijalankan, `src/` tidak berubah.
CODEMAP_DIPERBARUI: ya (`analisis-ai.md`, risiko: smoke test me-monkeypatch `genai` dan `get_flash_models_for_key`). `index.md` tidak diubah (opsional di kontrak).
CATATAN:
- Tidak ada perubahan di `backend/` atau `src/`.
- Video sintetis harus ada di `UPLOADS_DIR` karena `process_batch_rendering` mengubah `video_id` tanpa awalan `upload_`/`gdrive_` menjadi URL YouTube, dan `download_clip_segment` hanya mencari sumber lokal di `UPLOADS_DIR`/`TEMP_DIR`/`EXPORTS_DIR`.
- Mengimpor `backend.config` membuat folder `backend/temp_clips/uploads` bila belum ada (perilaku bawaan backend, bukan file test).
- Analisis non-mock mencoba 4 model fallback sebelum melaporkan 429. Klien palsu membuat ini instan.
- Starlette menampilkan `DeprecationWarning` soal `httpx` pada `TestClient`. Tidak memengaruhi hasil.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
