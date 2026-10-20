---
fitur: self-update, restart, akses admin
file_utama: [backend/routers/system.py, scripts/start-backend.js, backend/services/system_service.py, backend/restart_runner.py, src/components/AppUpdateModal.tsx, update.bat]
---
# Sistem update

Aplikasi asli punya self-update: `git pull origin <branch>` lalu `npm install`/`pip install` dan restart. **Di fork ini fitur itu dimatikan (P1)** agar kustomisasi tidak tertimpa. Update dilakukan manual: `git fetch upstream`, merge `upstream/master` ke `custom`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/system.py` | `SELF_UPDATE_DISABLED` | L31 | Flag utama. `True` = update/restart ditolak |
| `backend/routers/system.py` | `SELF_UPDATE_DISABLED_MESSAGE` | L32-35 | Pesan 403 |
| `backend/routers/system.py` | `api_perform_update` | L295-378 | `POST /api/system/update`. Langsung 403 bila flag aktif; kode git pull asli tetap ada di bawahnya |
| `backend/routers/system.py` | `api_restart_app` | L382-396 | `POST /api/system/restart`. 403 bila flag aktif |
| `backend/routers/system.py` | `api_check_update` | L232-291 | `GET /api/system/check-update`. Bila flag aktif: `update_available: false` tanpa `git fetch` |
| `backend/routers/system.py` | `api_system_version` | L226-228 | `GET /api/system/version` (commit, branch, `allow_update`) |
| `backend/routers/system.py` | `verify_admin_access` | L60-82 | Dengan `ADMIN_API_KEY`: `X-API-Key` / Bearer wajib cocok (401). Tanpa key: hanya klien loopback dan `Origin` localhost/127.0.0.1 (403) |
| `backend/routers/system.py` | `_is_loopback_client` | L52-57 | Cek `request.client.host` loopback |
| `backend/routers/system.py` | `require_admin_key` | L85-95 | Untuk update/restart: selalu butuh `ADMIN_API_KEY` (403 bila tidak diset, 401 bila salah) |
| `backend/routers/system.py` | `GEMINI_KEY_ENV_PATH` | L102 | `backend/.env`, bukan `.env` root (Vite me-restart + reload halaman bila `.env` root berubah) |
| `backend/routers/system.py` | `_gemini_key_status` | L126-133 | `configured`, `source` (`file`/`env`), `hint` 4 karakter terakhir, `is_mock`. Tidak pernah key utuh |
| `backend/routers/system.py` | `get_gemini_key_status` | L137-139 | `GET /api/settings/gemini-key` |
| `backend/routers/system.py` | `save_gemini_key` | L143-167 | `PUT /api/settings/gemini-key`: validasi format, tulis baris `GEMINI_API_KEY` (baris lain dan CRLF/LF utuh), set `os.environ` |
| `backend/routers/system.py` | `delete_gemini_key` | L171-182 | `DELETE /api/settings/gemini-key` |
| `backend/services/system_service.py` | `is_update_allowed` | L327-334 | `False` di Docker/server kecuali `ALLOW_SERVER_UPDATE` |
| `backend/services/system_service.py` | `is_server_environment` | L309-324 | Deteksi Docker/cloud/`SERVER_MODE` |
| `backend/services/system_service.py` | `get_current_git_info` | L337-368 | Info git lokal (hanya baca) |
| `backend/services/system_service.py` | `run_git_command` | L291-306 | Jalankan git dengan timeout |
| `backend/services/system_service.py` | `trigger_detached_restart` | L371-384 | Jalankan `restart_runner.py` terpisah |
| `backend/restart_runner.py` | `main` | L85-123 | Bebaskan port lalu nyalakan ulang app |
| `src/App.tsx` | `SELF_UPDATE_DISABLED` | L30 | Flag frontend: sembunyikan tombol Update |
| `src/App.tsx` | tombol Update di header | L2451-2474 | Tampil hanya bila `allowAppUpdates && !SELF_UPDATE_DISABLED` |
| `src/components/AppUpdateModal.tsx` | `AppUpdateModal` | L25-648 | Modal update/restart (masih ada, tidak bisa dibuka dari UI) |
| `update.bat` | seluruh file | L1-20 | Hanya mencetak petunjuk update manual, tidak menjalankan git/npm/pip |
| `scripts/start-backend.js` | argumen uvicorn | L244-256 | `--host 127.0.0.1`: backend tidak terbuka ke LAN |

## Input / output
- Input: request ke endpoint system, header `X-API-Key` / `Authorization: Bearer`, header `Origin`, alamat klien, variabel `SERVER_MODE`, `ALLOW_SERVER_UPDATE`, `ADMIN_API_KEY`, `GEMINI_API_KEY`.
- Output: 403 untuk update/restart (tanpa `ADMIN_API_KEY`, atau flag aktif); info versi untuk UI; status Gemini key dan baris `GEMINI_API_KEY` di `backend/.env`.

## Risiko
- **Jangan set `SELF_UPDATE_DISABLED = False`** kecuali pemilik proyek meminta. Bila aktif lagi, update menjalankan `git pull origin <branch>`, yaitu fork sendiri. Itu tidak menarik dari repo asli, tetapi tetap bisa men-stash/menimpa perubahan lokal.
- `allowAppUpdates` di frontend juga mengatur tombol Clear Temp. Jangan matikan `allow_update` secara global untuk menyembunyikan tombol Update.
- Tanpa `ADMIN_API_KEY`, endpoint admin (clear temp, cleanup, settings key) hanya dari komputer sendiri. Bila `ADMIN_API_KEY` diisi, frontend tidak mengirim key itu, jadi tombol Clear Temp dan pengaturan Gemini key di UI ikut ditolak (401).
- Backend di belakang reverse proxy di mesin yang sama melihat klien sebagai loopback. Untuk deployment server, isi `ADMIN_API_KEY`.
- Gemini key yang disimpan UI ada di `backend/.env` (di-ignore git). Karena `backend/.env` dimuat lebih dulu, nilainya menang atas `.env` root.
- `scripts/smoke_test.py` cek 6 menguji guard dan endpoint key dengan `GEMINI_KEY_ENV_PATH` dialihkan ke folder sementara.

## Terkait
[[index]] · [[arsitektur-backend]] · [[penyimpanan-dan-cleanup]] · [[frontend-app]]
