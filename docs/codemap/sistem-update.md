---
fitur: self-update, restart, akses admin
file_utama: [backend/routers/system.py, backend/services/system_service.py, backend/restart_runner.py, src/components/AppUpdateModal.tsx, update.bat]
---
# Sistem update

Aplikasi asli punya self-update: `git pull origin <branch>` lalu `npm install`/`pip install` dan restart. **Di fork ini fitur itu dimatikan (P1)** agar kustomisasi tidak tertimpa. Update dilakukan manual: `git fetch upstream`, merge `upstream/master` ke `custom`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/system.py` | `SELF_UPDATE_DISABLED` | L28 | Flag utama. `True` = update/restart ditolak |
| `backend/routers/system.py` | `SELF_UPDATE_DISABLED_MESSAGE` | L29-32 | Pesan 403 |
| `backend/routers/system.py` | `api_perform_update` | L167-250 | `POST /api/system/update`. Langsung 403 bila flag aktif; kode git pull asli tetap ada di bawahnya |
| `backend/routers/system.py` | `api_restart_app` | L254-268 | `POST /api/system/restart`. 403 bila flag aktif |
| `backend/routers/system.py` | `api_check_update` | L104-163 | `GET /api/system/check-update`. Bila flag aktif: `update_available: false` tanpa `git fetch` |
| `backend/routers/system.py` | `api_system_version` | L98-100 | `GET /api/system/version` (commit, branch, `allow_update`) |
| `backend/routers/system.py` | `verify_admin_access` | L35-54 | Cek `X-API-Key` / Bearer bila `ADMIN_API_KEY` diset. Tanpa key = akses terbuka |
| `backend/services/system_service.py` | `is_update_allowed` | L327-334 | `False` di Docker/server kecuali `ALLOW_SERVER_UPDATE` |
| `backend/services/system_service.py` | `is_server_environment` | L309-324 | Deteksi Docker/cloud/`SERVER_MODE` |
| `backend/services/system_service.py` | `get_current_git_info` | L337-368 | Info git lokal (hanya baca) |
| `backend/services/system_service.py` | `run_git_command` | L291-306 | Jalankan git dengan timeout |
| `backend/services/system_service.py` | `trigger_detached_restart` | L371-384 | Jalankan `restart_runner.py` terpisah |
| `backend/restart_runner.py` | `main` | L85-123 | Bebaskan port lalu nyalakan ulang app |
| `src/App.tsx` | `SELF_UPDATE_DISABLED` | L25 | Flag frontend: sembunyikan tombol Update |
| `src/App.tsx` | tombol Update di header | L2342-2365 | Tampil hanya bila `allowAppUpdates && !SELF_UPDATE_DISABLED` |
| `src/components/AppUpdateModal.tsx` | `AppUpdateModal` | L25-648 | Modal update/restart (masih ada, tidak bisa dibuka dari UI) |
| `update.bat` | seluruh file | L1-20 | Hanya mencetak petunjuk update manual, tidak menjalankan git/npm/pip |

## Input / output
- Input: request ke endpoint system, header `X-API-Key` (opsional), variabel `SERVER_MODE`, `ALLOW_SERVER_UPDATE`, `ADMIN_API_KEY`.
- Output: 403 untuk update/restart selama flag aktif; info versi untuk UI.

## Risiko
- **Jangan set `SELF_UPDATE_DISABLED = False`** kecuali pemilik proyek meminta. Bila aktif lagi, update menjalankan `git pull origin <branch>`, yaitu fork sendiri. Itu tidak menarik dari repo asli, tetapi tetap bisa men-stash/menimpa perubahan lokal.
- `allowAppUpdates` di frontend juga mengatur tombol Clear Temp. Jangan matikan `allow_update` secara global untuk menyembunyikan tombol Update.
- Tanpa `ADMIN_API_KEY`, endpoint admin (clear temp, cleanup) terbuka untuk siapa pun yang bisa mengakses port 8000 (target task #7).

## Terkait
[[index]] · [[arsitektur-backend]] · [[penyimpanan-dan-cleanup]] · [[frontend-app]]
