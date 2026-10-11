# CHEAT-7: Amankan API key + endpoint admin
Status: REVIEW

## Tujuan
Gemini API key tidak lagi disimpan di `localStorage` browser melainkan di `backend/.env` (dikelola backend, tidak pernah dikirim balik ke browser), dan endpoint admin hanya bisa dipakai dari komputer sendiri, dengan update/restart selalu butuh key admin.

## Area yang boleh disentuh
- `backend/routers/system.py`:
  - `verify_admin_access` L35-54: tanpa `ADMIN_API_KEY`, hanya terima klien loopback (`127.0.0.1`, `::1`) dan tolak header `Origin` yang bukan localhost/127.0.0.1. Dengan `ADMIN_API_KEY`, perilaku lama (key wajib cocok).
  - Dependency baru `require_admin_key` untuk `api_perform_update` L166-250 dan `api_restart_app` L253-268: selalu 401/403 bila `ADMIN_API_KEY` tidak diset atau tidak cocok.
  - Endpoint baru di file yang sama: `GET /api/settings/gemini-key` (status: `configured`, `source` `env`/`file`, `hint` 4 karakter terakhir, tidak pernah key utuh), `PUT /api/settings/gemini-key` (simpan ke `backend/.env` + `os.environ`), `DELETE /api/settings/gemini-key`. Ketiganya memakai `verify_admin_access`.
- `backend/routers/analyze.py`: tidak ada perubahan logika. `request.api_key` tetap diterima (dipakai smoke test `mock`), fallback `GEMINI_API_KEY` L228 sudah ada.
- `src/App.tsx`:
  - State API key L51-52: hapus baca `localStorage`, ganti dengan status key dari `GET /api/settings/gemini-key`.
  - Migrasi sekali jalan: bila `cheat_clip_gemini_api_key` masih ada di `localStorage`, kirim ke `PUT /api/settings/gemini-key`, lalu hapus dari `localStorage` bila berhasil.
  - `fetchModels` L738-774: panggil `/api/models` tanpa `api_key` di query string (backend memakai key tersimpan).
  - Cek wajib key di `handleAnalyze` L1289-1293 dan body `api_key` L1486: pakai status key backend, tidak mengirim `api_key`.
  - Kartu API key L2783-2836: input untuk menyimpan key baru (tombol Simpan, input dikosongkan setelah tersimpan), tampilan "tersimpan (…abcd)", tombol Hapus.
  - Tombol "Ganti API Key" L3630-3660: tetap fokus ke input `gemini-key-input`.
- `src/locales/id.ts` dan `src/locales/en.ts`: string baru untuk status key, simpan, hapus, error. Ubah `apiKeyErrorHint` (tidak lagi "tersimpan lokal di browser").
- `scripts/start-backend.js` L249-250: `--host 0.0.0.0` → `127.0.0.1` (backend tidak terbuka ke jaringan LAN).
- `scripts/smoke_test.py`: cek 6 untuk endpoint key dan guard admin (path `.env` dialihkan ke folder sementara, tidak menyentuh `.env` asli).
- `CLAUDE.md`: jebakan no. 8 diperbarui.
- `docs/codemap/`: `sistem-update.md`, `frontend-app.md`, `arsitektur-backend.md`, `analisis-ai.md` (bila baris bergeser), `index.md` bila perlu.

## Di luar scope (jangan dikerjakan)
- Cookies YouTube di `localStorage` (jebakan no. 8 bagian kedua). Task terpisah.
- Enkripsi key di disk atau Windows Credential Manager. Pola `.env` di `.gitignore` sudah mencakup `backend/.env`.
- Mengubah `SELF_UPDATE_DISABLED` atau isi logika update/restart.
- Mengubah CORS di `backend/main.py`, auth untuk endpoint non-admin (`/api/analyze`, render, dll).
- `src/components/AppUpdateModal.tsx` dan `ClipStudioModal.tsx` (komponen mati). `ClipStudioSection.tsx` tidak perlu diubah karena `POST /api/clear-temp` dari browser lokal tetap lolos guard.
- Mengubah `AnalyzeRequest.api_key` di `backend/schemas/analyze.py`.

## Keputusan yang boleh diambil AI sendiri
- Menulis `.env` dengan `dotenv.set_key`/`unset_key` atau penulisan manual, asal baris lain di `.env` tetap utuh. Path `.env` disimpan di variabel modul agar bisa dialihkan di test.
- Kode status untuk penolakan (401 vs 403) dan teks pesan error.
- Validasi minimal key (tidak kosong, tanpa spasi/baris baru, panjang wajar). `mock` tetap diterima agar mode mock bisa dipakai dari UI.
- Bila `GEMINI_API_KEY` berasal dari environment sistem (bukan `.env`), `source: "env"` dan UI tetap mengizinkan menimpanya untuk sesi berjalan.
- Lokasi file diubah saat implementasi dari `.env` root ke `backend/.env`: Vite me-restart server dan me-reload halaman setiap `.env` root berubah (terbukti di uji browser). `backend/.env` sudah dimuat `config.py` lebih dulu dan tidak dipantau Vite maupun `uvicorn --reload`.
- Tata letak dan gaya kartu API key, selama mengikuti gaya kartu yang ada.

## Kriteria selesai (ya/tidak)
- [x] Setelah memakai app (simpan key, analisis), `localStorage` tidak berisi `cheat_clip_gemini_api_key` maupun nilai key.
- [x] Key lama di `localStorage` dipindah otomatis ke backend lalu dihapus dari browser.
- [x] `GET /api/settings/gemini-key` tidak pernah mengembalikan key utuh. Key tidak muncul di query string request mana pun (`/api/models`).
- [x] Key yang disimpan lewat UI tetap ada setelah backend restart (tertulis di `backend/.env`), dan baris lain di `.env` tidak berubah.
- [x] Analisis dari UI berjalan dengan key tersimpan tanpa mengirim `api_key` di body.
- [x] `POST /api/system/update` dan `/api/system/restart` menolak request tanpa key admin (termasuk saat `ADMIN_API_KEY` tidak diset).
- [ ] Tanpa `ADMIN_API_KEY`: endpoint admin lain (`clear-temp`, `cleanup-expired-temp`, `auto-cleanup`, settings key) menolak klien non-loopback dan request dengan `Origin` asing, tetapi tombol Clear Temp di UI lokal tetap berfungsi. (Penolakan terbukti di cek 6. Clear Temp dari UI perlu dicek pemilik, lihat CATATAN.)
- [x] Backend dari `npm run dev` hanya mendengarkan `127.0.0.1:8000`.
- [x] String UI baru ada di `id.ts` dan `en.ts`.
- [x] Smoke test lulus 7/7 (termasuk cek 6 baru), `npm run build` dan `npm run lint` lulus (tidak ada error baru), `check_codemap.py` lulus.
- [x] `git diff` hanya berisi file di "Area yang boleh disentuh".

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`: 7/7 PASS. Cek 6 memakai `TestClient` dengan host klien dan header `Origin` diatur: loopback tanpa Origin lolos, Origin `https://evil.example` ditolak, klien non-loopback ditolak, update/restart ditolak tanpa key admin dan diterima dengan key yang cocok (sampai 403 dari `SELF_UPDATE_DISABLED`), PUT/GET/DELETE key memakai `.env` sementara dan GET tidak memuat key utuh.
- `npm run build` dan `npm run lint`.
- Browser (pane bawaan): buka app, isi `localStorage` dengan key palsu lama, muat ulang, pastikan pindah ke backend dan hilang dari `localStorage`. Simpan key `mock`, jalankan analisis video sintetis/upload, cek request di tab network tidak membawa key.
- `curl` dari alamat LAN komputer ke `:8000` gagal tersambung setelah perubahan host.
- `venv\Scripts\python.exe scripts\check_codemap.py` lulus.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `backend/routers/system.py` (guard `verify_admin_access` L60-82, `require_admin_key` L85-95 untuk update/restart, endpoint `GET/PUT/DELETE /api/settings/gemini-key` L137-182, `GEMINI_KEY_ENV_PATH` = `backend/.env`), `src/App.tsx` (state key L51-56, `saveGeminiKey`/`handleSaveApiKey`/`handleDeleteApiKey` L740-791, migrasi L793-810, `fetchModels` tanpa key di query, `handleAnalyze` tanpa `api_key`, kartu API key L2863-2949), `src/locales/id.ts`, `src/locales/en.ts` (9 string baru, `apiKeyErrorHint` diubah), `scripts/start-backend.js` (`--host 127.0.0.1`), `scripts/smoke_test.py` (cek 6), `CLAUDE.md` (jebakan 8), 7 catatan `docs/codemap/`, kontrak, `TASKS.md`
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: 7/7 PASS, exit 0. Cek 6: "LAN/Origin asing ditolak, update/restart butuh key admin, key di .env tanpa bocor". Percobaan pertama cek 6 menemukan bug (CRLF `.env` berubah jadi LF), sudah diperbaiki.
- `npm run build`: lulus. `npm run lint`: 97 masalah (88 error, 9 warning), sama persis dengan sebelum perubahan (diuji dengan `git stash`), tidak ada yang baru.
- Browser pane: `localStorage` diisi key palsu lama, buka ulang app → `PUT` ke backend, status "Key stored in backend …LEGA", `localStorage` kosong. Simpan `mock` lewat input + Enter → input kosong, status "…mock", pesan tersimpan, tanpa reload halaman. Request `/api/analyze` dari UI ditangkap: body `{"url":...,"duration":"30s","model":"gemini-2.5-flash","target_clip_count":"auto"}` tanpa `api_key`. Tombol Hapus → `DELETE`, lalu `/api/analyze` tanpa key → "Gemini API Key is required".
- `curl` `/api/analyze` tanpa `api_key` dengan key tersimpan: lolos cek key (lanjut ke error sumber 404). Key `…PERS` disimpan lalu proses Python baru mengimpor `backend.config` → `GEMINI_API_KEY` berakhiran `PERS` (persist).
- `curl http://192.168.1.3:8000/api/health` → gagal tersambung (exit 7). `127.0.0.1:8000` → 200. `netstat`: `127.0.0.1:8000 LISTENING`.
- `venv\Scripts\python.exe scripts\check_codemap.py`: SEMUA CEK LULUS (200 simbol).
- File uji (`backend/.env`, `.env` root kosong, `.claude/launch.json`) dihapus setelah uji.
CODEMAP_DIPERBARUI: ya. Isi: `sistem-update.md` (guard, `require_admin_key`, endpoint key, start-backend, risiko), `frontend-app.md` (fungsi key baru, migrasi, key `localStorage`, risiko, geser baris), `arsitektur-backend.md` (host, endpoint, env). Hanya geser baris: `penyimpanan-dan-cleanup.md`, `render-browser.md`, `sumber-video.md`, `unduhan-raw.md`.
CATATAN:
- Penyimpangan dari draf: key disimpan di `backend/.env`, bukan `.env` root, karena Vite me-restart server dan me-reload halaman setiap `.env` root berubah (terlihat di log `.env changed, restarting server...`). `backend/.env` dimuat `config.py` lebih dulu, di-ignore git, dan tidak memicu reload. Kontrak sudah disesuaikan.
- Key `mock` diterima agar mode mock bisa dipakai dari UI. `hint` = 4 karakter terakhir hanya bila key >= 12 karakter.
- Migrasi memakai retry (`resilientFetch`, 4 kali) karena saat `npm run dev` baru menyala backend belum siap. Bila gagal, key lama tetap di `localStorage` dan dicoba lagi pada pembukaan berikutnya.
- Tombol Hapus hanya tampil bila key berasal dari `backend/.env` (`source: file`). Key dari `.env` root atau environment sistem ditampilkan sebagai "dari .env root atau environment sistem".
- Bila pemilik mengisi `ADMIN_API_KEY`, frontend tidak mengirim key itu, jadi Clear Temp dan pengaturan Gemini key di UI ikut ditolak (401). Sama dengan perilaku lama untuk Clear Temp.
- Kriteria Clear Temp: guard yang sama sudah lolos dari browser (PUT/DELETE key dengan `Origin: http://localhost:5173` lewat proxy Vite → 200), tetapi tombol Clear Temp tidak diklik karena menghapus cache sungguhan. Perlu dicek pemilik.
- Gemini key asli pemilik belum dipindah: di browser biasa, key lama akan pindah otomatis saat app dibuka. Bila tidak, tempel ulang key lalu klik Simpan.
- Cookies YouTube masih di `localStorage` (di luar scope).
- Task berisiko tinggi: wajib `/review 7` di sesi baru.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: `git show --stat c25a9ea` hanya berisi file di Area (`backend/routers/system.py`, `src/App.tsx`, `src/locales/id.ts`/`en.ts`, `scripts/start-backend.js`, `scripts/smoke_test.py`, `CLAUDE.md`, 7 catatan `docs/codemap/`, kontrak). `backend/routers/analyze.py`, `backend/schemas/analyze.py`, `backend/main.py`, komponen mati tidak disentuh. `9662a71` hanya `TASKS.md`.
- Key tidak di `localStorage`: `src/App.tsx` L52 state awal kosong, `cheat_clip_gemini_api_key` hanya dibaca lalu dihapus di migrasi L793-810 (`removeItem` setelah PUT sukses). `grep` di `src/` tidak menemukan `setItem` key atau `api_key` lain.
- Key tidak bocor: `_gemini_key_status` (`system.py` L126-133) hanya mengembalikan `hint` 4 karakter (bila key >= 12). `fetchModels` memanggil `/api/models` tanpa query; backend jatuh ke `os.environ["GEMINI_API_KEY"]` (`ai_service.py` L83). Body `/api/analyze` tidak lagi memuat `api_key` (diff L1558), backend fallback ke env (`analyze.py` L228).
- Persist + baris lain utuh: PUT/DELETE menulis `backend/.env` dengan newline asli dipertahankan (`_read_env_lines`/`_write_env_lines`). Cek 6 membandingkan byte `.env` CRLF sebelum/sesudah PUT dan DELETE. `backend/.env` di-ignore git (`git check-ignore`: `.gitignore:6`), dan dimuat `config.py` L46.
- Update/restart: `require_admin_key` dipakai di `system.py` L295 dan L382. Cek 6: tanpa `ADMIN_API_KEY` 403, key salah 401, key benar sampai 403 `SELF_UPDATE_DISABLED`.
- Guard admin tanpa key: `clear-temp`, `cleanup-expired-temp`, `auto-cleanup`, dan 3 endpoint key memakai `verify_admin_access` (L137, L143, L171, L192, L207, L216). Cek 6: klien LAN 403, `Origin: https://evil.example` 403, loopback + `Origin: http://localhost:5173` 200. Vite proxy (`vite.config.ts`) meneruskan ke `127.0.0.1:8000` dan Vite default hanya `localhost`, jadi permintaan dari UI lokal lolos guard. Klik tombol Clear Temp di UI: perlu dicek pemilik.
- Host: `scripts/start-backend.js` L250 `127.0.0.1`, tidak ada `0.0.0.0` lain di `scripts/`/`package.json`. Uji `curl` dari IP LAN: perlu dicek pemilik (dicatat lulus oleh implementer).
- String UI: 9 kunci baru + `apiKeyErrorHint` ada di `id.ts` dan `en.ts`. Tombol "Ganti API Key" tetap fokus ke `gemini-key-input` (`App.tsx` L3750).
- Test (dijalankan reviewer): `smoke_test.py` 7/7 lulus, exit 0 (cek 6 PASS). `npm run build` lulus (hanya peringatan ukuran chunk). `check_codemap.py` SEMUA CEK LULUS (200 simbol). `eslint src/App.tsx`: 27 masalah, sama persis dengan versi `c25a9ea^`, tidak ada masalah baru.
- Codemap: `sistem-update.md`, `frontend-app.md`, `arsitektur-backend.md` diperbarui dengan simbol dan baris baru; cek codemap lulus. Tidak ada rahasia ter-commit (hanya key palsu smoke test).
- Catatan non-blok: (1) key lama di `localStorage` dengan format tidak valid (mis. berisi spasi) ditolak 400 dan tidak dihapus, jadi tetap tertinggal di browser; (2) DELETE hanya menghapus dari `backend/.env`, key di `.env` root akan aktif lagi setelah restart; (3) karena key kini disimpan backend, endpoint non-admin seperti `/api/analyze` bisa memakai key itu tanpa auth, hanya dibatasi CORS (di luar scope, kandidat task lanjutan).
