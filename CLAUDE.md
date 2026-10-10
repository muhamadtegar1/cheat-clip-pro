# CLAUDE.md: Cheat Clip PRO (fork kustom)

Auto-clipper: video panjang (YouTube, Google Drive, upload) → Gemini memilih momen viral → render klip vertikal dengan subtitle karaoke, face tracking, judul, musik. Frontend React 19 + Vite, backend FastAPI + yt-dlp + FFmpeg + Whisper.

Repo ini fork dari `galihjuansaputra/cheat-clip-pro` (MIT).
- Remote: `origin` = `muhamadtegar1/cheat-clip-pro` (fork), `upstream` = repo asli (hanya tarik manual).
- Branch kerja: `custom`. Jangan commit ke `master`.

## Alur task (skill di `.claude/skills/`)
| Perintah | Siapa | Isi |
| --- | --- | --- |
| `/mulai <ID>` | pemilik | Baca baton + codemap, tulis draf kontrak, **berhenti** menunggu persetujuan, lalu implementasi |
| `/tutup` | pemilik | Cek lingkup, build/smoke test/cek codemap, laporan, status REVIEW, commit + push, subagent `reviewer` |
| `/review <ID>` | pemilik, di sesi baru | Review independen dari kontrak + diff commit `<ID>:` + test sendiri, tulis verdict |
| `/done <ID>` | pemilik | Tandai DONE, perbarui baton dan log, commit + push |

Blok Baton dicetak otomatis di awal sesi oleh hook `SessionStart` (`.claude/settings.json` → `scripts/baton.js`). Semua skill memakai `disable-model-invocation: true`, jadi hanya bisa dipanggil pemilik. Pesan commit task selalu diawali `<ID>:` karena reviewer mencari commit dengan pola itu.

## Sebelum mengerjakan apa pun
1. Baca blok **Baton** di `TASKS.md` (juga tampil di awal sesi): fase aktif, task aktif, langkah berikut, blocker.
2. Kerjakan **satu task** saja. Kontraknya ada di `docs/tasks/CHEAT-<ID>.md` (template: `docs/tasks/_TEMPLATE.md`). Kalau kontrak belum ada, tulis drafnya dulu.
3. Buka `docs/codemap/index.md` dan catatan fitur yang relevan untuk menemukan file + rentang baris. Jangan grep panjang kalau codemap sudah menjawab.
4. Sentuh **hanya** file/area yang disebut di kontrak. Tidak ada refactor, format ulang, atau perubahan dependensi di luar kontrak.

## Menjalankan
```bash
npm install
python -m venv venv
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm run dev
```
- `npm run dev` menjalankan frontend (`http://localhost:5173`) dan backend (`http://localhost:8000`, docs di `/docs`) bersamaan. Backend dijalankan `scripts/start-backend.js` dengan `uvicorn backend.main:app --port 8000 --reload`.
- Backend saja: `venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000`.
- Build frontend: `npm run build` (wajib lulus sebelum commit yang menyentuh `src/`). Lint: `npm run lint`.
- Prasyarat sistem: FFmpeg dan yt-dlp di PATH (`winget install Gyan.FFmpeg yt-dlp.yt-dlp`).
- Isi API key Gemini dengan `mock` untuk menguji alur analisis tanpa memanggil Gemini.

## Smoke test
**Belum ada** (task 17 di `TASKS.md`, menunggu golden fixtures K3). Sampai task itu selesai, minimal:
1. `npm run build` lulus.
2. `venv\Scripts\python.exe scripts\check_codemap.py` lulus (link codemap valid, rentang baris cocok dengan kode).
3. Untuk perubahan backend: impor modul atau uji endpoint terisolasi (FastAPI `TestClient` pada router terkait) agar tidak memicu auto-cleanup.
4. Uji manual analisis dengan API key `mock`.

Setelah task 17 selesai, ganti bagian ini dengan satu perintah smoke test.

## Aturan kerja
- Status task: `TODO` → `IN_PROGRESS` → `REVIEW`. **`DONE` hanya ditetapkan pemilik proyek.** AI berhenti di `REVIEW`.
- Satu kontrak = satu fitur kecil = satu commit kode, plus commit terpisah untuk `TASKS.md`.
- Stage file satu per satu (`git add <file>`). **Jangan `git add .`**, dan jangan commit `package-lock.json` kecuali task memang mengubah dependensi.
- Jalankan `git status` sebelum commit. Hanya file dalam scope kontrak yang boleh ikut.
- Setiap perubahan kode wajib memperbarui catatan `docs/codemap/` yang terdampak (rentang baris, fungsi, risiko), lalu `scripts/check_codemap.py` harus lulus.
- Perubahan prompt AI wajib lulus golden fixtures (setelah task 17).
- Review dilakukan di sesi Claude Code baru, hanya dari kontrak + `git diff` + hasil test. Task berisiko tinggi (#7, #12, #16) wajib `/review` di sesi yang benar-benar baru.
- Setelah menyimpan `TASKS.md`, baca ulang untuk memastikan tidak tertimpa proses lain.
- Jangan sentuh `backend/exports`, `backend/temp_clips`, `venv`, `node_modules`.

## Jebakan yang diketahui
1. **Auto-cleanup menghapus hasil render.** 15 detik setelah backend menyala, lalu tiap 30 menit, semua file berumur > 1 jam di `backend/temp_clips`, `backend/temp`, `uploads`, dan **`backend/exports`** dihapus (plus kuota 5 GB). Menyalakan backend saja sudah memicunya. Detail: `docs/codemap/penyimpanan-dan-cleanup.md`. Target task #16.
2. **Kanvas 1080×1920 ditulis langsung.** ±80 literal `1080`/`1920` di `backend/video_engine.py` (filtergraph, ASS, overlay judul). Rasio lain ditempatkan di dalam kanvas vertikal; hanya `16:9_landscape` yang 1920×1080. Pratinjau Clip Studio meniru angka yang sama. Detail: `docs/codemap/render-server.md`. Target task #10.
3. **Self-update `git pull` dimatikan.** Flag `SELF_UPDATE_DISABLED` di `backend/routers/system.py` dan `src/App.tsx`. Jangan aktifkan lagi; update dari upstream dilakukan manual (`git fetch upstream`, merge ke `custom`). Detail: `docs/codemap/sistem-update.md`.
4. **`uvicorn --reload` aktif.** Menyimpan file `.py` saat render/analisis berjalan me-restart backend. Semua state job (render, unduhan) ada di memori dan hilang.
5. **`analyze_video` adalah satu generator ±1250 baris** (`backend/routers/analyze.py` L224-1477). Ubah per potongan sesuai codemap `analisis-ai.md`.
6. **Mengimpor `backend.config` punya efek samping**: membuat folder, mencari FFmpeg, menguji encoder GPU.
7. **Komponen mati**: `src/components/ClipStudioModal.tsx` dan `BatchRenderProgressModal.tsx` tidak dipakai. UI aktif ada di `ClipStudioSection.tsx`.
8. **Data sensitif di `localStorage`**: Gemini API key (`cheat_clip_gemini_api_key`) dan cookies YouTube. Target task #7.
9. **Teks UI dua bahasa**: setiap string baru harus masuk `src/locales/id.ts` dan `src/locales/en.ts`.
10. **Menjalankan `claude -p "/skill ..."` dari Git Bash** membuat `/skill` diubah menjadi path Windows. Pakai `MSYS_NO_PATHCONV=1` atau PowerShell.
11. **Line ending campuran** (CRLF/LF). Peringatan `LF will be replaced by CRLF` dari git normal. Pertahankan line ending file yang diedit.

## Peta
- Tugas dan status: `TASKS.md`
- Kontrak: `docs/tasks/`
- Codemap: `docs/codemap/index.md` (folder `docs/` bisa dibuka sebagai vault Obsidian)
