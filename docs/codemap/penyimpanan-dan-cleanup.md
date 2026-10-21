---
fitur: penyimpanan file dan auto-cleanup
file_utama: [backend/services/system_service.py, backend/main.py, backend/routers/system.py, backend/video_engine.py]
---
# Penyimpanan dan cleanup

File kerja (cache) dibersihkan otomatis. **Hasil render disimpan permanen** di `EXPORTS_DIR` (default `~/CheatClip`, di luar proyek, bisa diganti lewat env `CHEAT_CLIP_EXPORTS_DIR`) dan tidak pernah disentuh cleanup (task #16). Daemon cleanup berjalan 15 detik setelah backend menyala, lalu tiap 30 menit.

## Folder

| Folder | Isi | Dibersihkan? |
| --- | --- | --- |
| `backend/temp_clips/` | segmen mentah, `.ass`, PNG judul, frame, **ZIP batch** (cache, dibuat ulang saat diunduh) | Ya (TTL 1 jam + kuota) |
| `backend/temp_clips/uploads/` | upload user, unduhan Drive, BGM, SFX, watermark | Ya |
| `backend/temp_clips/yt_cache/` | cache stream HD YouTube 1080p per video (#28, [[unduhan-raw]]), ±250-450 MB per video. mtime disegarkan tiap dipakai | Ya (TTL 1 jam sejak terakhir dipakai + kuota) |
| `backend/temp/` | file sementara lain | Ya |
| `EXPORTS_DIR` (default `~/CheatClip`) | MP4 hasil render, unduhan raw | **Tidak** (permanen, tanpa kuota) |
| `EXPORTS_DIR/kits/` | Posting kit per klip (#22): `video.mp4` hardlink ke MP4 render, SRT, `metadata.json`, caption per platform. Lihat [[render-server]] | **Tidak** (permanen) |
| `EXPORTS_DIR/data/` | `clip_choices.json` pilihan Pakai/Lewati pemilik (#35, [[pilihan-klip]]) | **Tidak** (permanen) |
| `backend/exports/` | fallback `EXPORTS_DIR` bila folder default gagal dibuat | Tidak |
| `backend/fonts/` | font bawaan + font upload | Tidak (dilindungi) |
| `cookies.txt` (backend atau root) | cookies lama | Tidak (dilindungi) |

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/main.py` | `background_storage_cleanup_worker` | L52-71 | Tunggu 15 s, lalu loop tiap `CLEANUP_INTERVAL_SECONDS` (1800) |
| `backend/services/system_service.py` | `auto_cleanup_expired_files` | L149-272 | Pass 1 TTL (`TEMP_MAX_AGE_SECONDS`, 3600), pass 2 kuota (`TEMP_STORAGE_QUOTA_GB`, 5 GB → turun ke 80%), hapus folder kosong |
| `backend/services/system_service.py` | daftar folder target | L165 | `TEMP_DIR`, `backend/temp`, `UPLOADS_DIR` (tanpa `EXPORTS_DIR`) |
| `backend/services/system_service.py` | pengaman `is_permanent_output` | L166-173 | Lewati file di dalam `EXPORTS_DIR` walau folder itu diarahkan ke dalam folder cache |
| `backend/services/system_service.py` | `is_protected_system_file` | L117-138 | Pengecualian: nama cookies dan isi `FONTS_DIR` |
| `backend/services/system_service.py` | `clear_temp_files` | L44-114 | Hapus temp manual (`POST /api/clear-temp`) |
| `backend/services/system_service.py` | `cleanup_expired_temp_files` | L141-146 | Pembungkus TTL dalam jam |
| `backend/services/system_service.py` | `get_temp_storage_summary` | L27-41 | Ukuran storage untuk UI |
| `backend/routers/system.py` | `clear_temp_folder` | L192-203 | `POST /api/clear-temp` (ditolak di mode server) |
| `backend/routers/system.py` | `api_trigger_auto_cleanup` | L213-222 | `POST /api/auto-cleanup` manual |
| `backend/video_engine.py` | konstanta folder | L21-26 | Definisi path. `EXPORTS_DIR` dari env `CHEAT_CLIP_EXPORTS_DIR`, default `~/CheatClip` (L23) |
| `backend/video_engine.py` | pembuatan folder | L152-162 | `mkdir` saat impor. Gagal membuat `EXPORTS_DIR` → fallback `backend/exports` + log peringatan |
| `src/App.tsx` | `executeGlobalClearTemp` | L688-709 | Tombol Clear Temp di header |

## Input / output
- Input: variabel `.env` `CHEAT_CLIP_EXPORTS_DIR`, `TEMP_MAX_AGE_SECONDS`, `TEMP_STORAGE_QUOTA_GB`, `CLEANUP_INTERVAL_SECONDS`.
- Output: file terhapus, ringkasan `{ttl_deleted_files, quota_deleted_files, remaining_storage_mb, ...}` di log.

## Risiko
- Folder permanen tidak punya batas ukuran. Pemilik membersihkannya sendiri.
- Windows Defender Controlled Folder Access memblokir python.exe/ffmpeg.exe menulis ke `~/Videos`, karena itu default-nya `~/CheatClip`. Kalau `CHEAT_CLIP_EXPORTS_DIR` diarahkan ke folder terlindungi, backend jatuh ke `backend/exports`.
- Menjalankan backend saja (tanpa membuka UI) memicu cleanup 15 detik kemudian, tetapi hanya untuk folder cache.
- `scripts/smoke_test.py` cek 5 menguji bahwa cleanup tidak menyentuh `EXPORTS_DIR` (TTL dan kuota).
- Kuota 5 GB dihitung gabungan folder cache (tanpa `EXPORTS_DIR`). Render besar bisa ikut menghapus upload yang masih dipakai.
- Upload yang sudah terhapus membuat analisis ulang/render dari riwayat gagal ([[unduhan-raw]], [[sumber-video]]).

## Terkait
[[index]] · [[arsitektur-backend]] · [[render-server]] · [[unduhan-raw]] · [[sistem-update]]
