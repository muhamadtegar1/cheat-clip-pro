---
fitur: penyimpanan file dan auto-cleanup
file_utama: [backend/services/system_service.py, backend/main.py, backend/routers/system.py, backend/video_engine.py]
---
# Penyimpanan dan cleanup

Semua file kerja dan **hasil render** disimpan di folder yang sama-sama dibersihkan otomatis. Daemon cleanup berjalan 15 detik setelah backend menyala, lalu tiap 30 menit.

## Folder

| Folder | Isi | Dibersihkan? |
| --- | --- | --- |
| `backend/temp_clips/` | segmen mentah, `.ass`, PNG judul, frame | Ya (TTL 1 jam + kuota) |
| `backend/temp_clips/uploads/` | upload user, unduhan Drive, BGM, SFX, watermark | Ya |
| `backend/temp/` | file sementara lain | Ya |
| `backend/exports/` | **MP4 hasil render, ZIP batch, unduhan raw** | **Ya** |
| `backend/fonts/` | font bawaan + font upload | Tidak (dilindungi) |
| `cookies.txt` (backend atau root) | cookies lama | Tidak (dilindungi) |

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/main.py` | `background_storage_cleanup_worker` | L51-69 | Tunggu 15 s, lalu loop tiap `CLEANUP_INTERVAL_SECONDS` (1800) |
| `backend/services/system_service.py` | `auto_cleanup_expired_files` | L149-262 | Pass 1 TTL (`TEMP_MAX_AGE_SECONDS`, 3600), pass 2 kuota (`TEMP_STORAGE_QUOTA_GB`, 5 GB → turun ke 80%), hapus folder kosong |
| `backend/services/system_service.py` | daftar folder target | L165 | `TEMP_DIR`, `backend/temp`, `UPLOADS_DIR`, `EXPORTS_DIR` |
| `backend/services/system_service.py` | `is_protected_system_file` | L117-138 | Pengecualian: nama cookies dan isi `FONTS_DIR` |
| `backend/services/system_service.py` | `clear_temp_files` | L44-114 | Hapus temp manual (`POST /api/clear-temp`) |
| `backend/services/system_service.py` | `cleanup_expired_temp_files` | L141-146 | Pembungkus TTL dalam jam |
| `backend/services/system_service.py` | `get_temp_storage_summary` | L27-41 | Ukuran storage untuk UI |
| `backend/routers/system.py` | `clear_temp_folder` | L64-75 | `POST /api/clear-temp` (ditolak di mode server) |
| `backend/routers/system.py` | `api_trigger_auto_cleanup` | L85-94 | `POST /api/auto-cleanup` manual |
| `backend/video_engine.py` | konstanta folder | L21-26 | Definisi path |
| `backend/video_engine.py` | pembuatan folder | L152-157 | `mkdir` saat impor |
| `src/App.tsx` | `executeGlobalClearTemp` | L653-674 | Tombol Clear Temp di header |

## Input / output
- Input: variabel `.env` `TEMP_MAX_AGE_SECONDS`, `TEMP_STORAGE_QUOTA_GB`, `CLEANUP_INTERVAL_SECONDS`.
- Output: file terhapus, ringkasan `{ttl_deleted_files, quota_deleted_files, remaining_storage_mb, ...}` di log.

## Risiko
- **Hasil render di `backend/exports` hilang setelah 1 jam.** Menjalankan backend saja (tanpa membuka UI) sudah memicu cleanup 15 detik kemudian. Unduh hasil segera atau pindahkan ke luar folder proyek. Target task #16: pisahkan output permanen dari cache.
- Kuota 5 GB dihitung gabungan semua folder target. Render besar bisa ikut menghapus upload yang masih dipakai.
- Upload yang sudah terhapus membuat analisis ulang/render dari riwayat gagal ([[unduhan-raw]], [[sumber-video]]).

## Terkait
[[index]] · [[arsitektur-backend]] · [[render-server]] · [[unduhan-raw]] · [[sistem-update]]
