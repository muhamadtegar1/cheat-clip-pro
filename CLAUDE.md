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
```bash
venv\Scripts\python.exe scripts\smoke_test.py
```
Butuh ±20 detik, tanpa jaringan dan tanpa backend yang menyala. Membuat video sintetis dengan FFmpeg, lalu menguji `POST /api/analyze` (key `mock`, skenario `RATE_LIMIT` dan `MALFORMED_JSON` lewat klien Gemini palsu) dan render 1 klip 1080×1920 lewat `POST /api/render-batch`, serta memastikan auto-cleanup tidak menyentuh `EXPORTS_DIR` dan guardrail output (#12, `backend/utils/clip_guardrails.py`) bekerja pada kasus buatan, termasuk klip fallback heatmap dengan dan tanpa rentang khusus (#29) dan tanpa tumpang tindih pada video sintetis kedua 120 s (#30). Exit code 0 = lulus. Skrip tidak mengimpor `backend.main`, jadi auto-cleanup tidak terpicu, dan file buatannya dihapus di akhir (`--keep` untuk menyimpan, `--gpu` untuk encoder `auto`).

Selain smoke test, `npm run build` (bila menyentuh `src/`) dan `venv\Scripts\python.exe scripts\check_codemap.py` tetap wajib lulus.

## Golden fixtures (perubahan prompt AI)
```bash
venv\Scripts\python.exe scripts\golden_fixtures.py fetch
venv\Scripts\python.exe scripts\golden_fixtures.py run --repeat 2 --compare
```
`fetch` cukup sekali (transkrip, metadata, heatmap 3 video K3 ke `tests/golden/data/`, di-ignore git karena transkrip milik channel lain; jangan pernah di-commit). `run` memanggil Gemini flash dengan key dari `backend/.env` (±3 analisis per ulangan, memakai kuota pemilik) tanpa memanggil YouTube, lalu menilai kutipan (grounded/salah tempat/karangan), timestamp, duplikat, klip di zona "jangan dipilih", dan heatmap. Exit 2 bila ada metrik lebih buruk dari `tests/golden/baseline.json`, exit 3 bila model Gemini yang dipakai berbeda dari baseline (perbandingan tidak setara: buat ulang baseline dari prompt lama dengan model yang sekarang tersedia, lalu ukur lagi). Model dipilih otomatis (`--model auto`) dan dicatat per video. Perbarui baseline hanya bila perubahan prompt diterima: `run --save-baseline`; `score <laporan> --save-baseline` hanya bila penilainya yang diubah. `run --mock` dan `selftest` tanpa Gemini. Detail: `docs/codemap/golden-fixtures.md`.

## Aturan kerja
- Status task: `TODO` → `IN_PROGRESS` → `REVIEW`. **`DONE` hanya ditetapkan pemilik proyek.** AI berhenti di `REVIEW`.
- Satu kontrak = satu fitur kecil = satu commit kode, plus commit terpisah untuk `TASKS.md`.
- Stage file satu per satu (`git add <file>`). **Jangan `git add .`**, dan jangan commit `package-lock.json` kecuali task memang mengubah dependensi.
- Jalankan `git status` sebelum commit. Hanya file dalam scope kontrak yang boleh ikut.
- Setiap perubahan kode wajib memperbarui catatan `docs/codemap/` yang terdampak (rentang baris, fungsi, risiko), lalu `scripts/check_codemap.py` harus lulus.
- Perubahan prompt AI (teks prompt, deskripsi field `ViralClipGemini`/`VideoAnalysis`, pasca-proses klip) wajib lulus golden fixtures: `golden_fixtures.py run --repeat 2 --compare` exit 0, hasilnya dicatat di laporan implementer.
- Review dilakukan di sesi Claude Code baru, hanya dari kontrak + `git diff` + hasil test. Task berisiko tinggi (#7, #12, #16) wajib `/review` di sesi yang benar-benar baru.
- Setelah menyimpan `TASKS.md`, baca ulang untuk memastikan tidak tertimpa proses lain.
- Jangan sentuh `backend/exports`, `EXPORTS_DIR` (`~/CheatClip`), `backend/temp_clips`, `venv`, `node_modules`.

## Jebakan yang diketahui
1. **Auto-cleanup hanya untuk cache.** 15 detik setelah backend menyala, lalu tiap 30 menit, file berumur > 1 jam di `backend/temp_clips` (termasuk `uploads` dan ZIP batch) dan `backend/temp` dihapus (plus kuota 5 GB). Hasil render dan unduhan raw disimpan permanen di `EXPORTS_DIR` (default `~/CheatClip`, env `CHEAT_CLIP_EXPORTS_DIR`) dan tidak pernah dibersihkan. Jangan arahkan output ke `~/Videos`: Windows Defender Controlled Folder Access memblokirnya. Detail: `docs/codemap/penyimpanan-dan-cleanup.md`.
2. **Kanvas 1080×1920 ditulis langsung.** ±80 literal `1080`/`1920` di `backend/video_engine.py` (filtergraph, ASS, overlay judul). Rasio lain ditempatkan di dalam kanvas vertikal; hanya `16:9_landscape` yang 1920×1080. Pratinjau Clip Studio meniru angka yang sama. Detail: `docs/codemap/render-server.md`. Target task #10.
3. **Self-update `git pull` dimatikan.** Flag `SELF_UPDATE_DISABLED` di `backend/routers/system.py` dan `src/App.tsx`. Jangan aktifkan lagi; update dari upstream dilakukan manual (`git fetch upstream`, merge ke `custom`). Detail: `docs/codemap/sistem-update.md`.
4. **`uvicorn --reload` aktif.** Menyimpan file `.py` saat render/analisis berjalan me-restart backend. Semua state job (render, unduhan) ada di memori dan hilang.
5. **`analyze_video` adalah satu generator ±1300 baris** (`backend/routers/analyze.py` L225-1541). Ubah per potongan sesuai codemap `analisis-ai.md`.
6. **Mengimpor `backend.config` punya efek samping**: membuat folder, mencari FFmpeg, menguji encoder GPU.
7. **Komponen mati**: `src/components/ClipStudioModal.tsx` dan `BatchRenderProgressModal.tsx` tidak dipakai. UI aktif ada di `ClipStudioSection.tsx`.
8. **Gemini key di backend, admin hanya lokal.** Key disimpan UI ke `backend/.env` lewat `/api/settings/gemini-key` dan tidak pernah dikirim balik utuh ke browser (task #7). Jangan menambah `api_key` lagi ke request frontend. Backend hanya mendengarkan `127.0.0.1`. Tanpa `ADMIN_API_KEY`, endpoint admin hanya menerima klien loopback dengan `Origin` localhost. Update/restart selalu butuh `ADMIN_API_KEY`. Cookies YouTube masih di `localStorage`. Detail: `docs/codemap/sistem-update.md`.
9. **Teks UI dua bahasa**: setiap string baru harus masuk `src/locales/id.ts` dan `src/locales/en.ts`.
10. **Menjalankan `claude -p "/skill ..."` dari Git Bash** membuat `/skill` diubah menjadi path Windows. Pakai `MSYS_NO_PATHCONV=1` atau PowerShell.
11. **Line ending campuran** (CRLF/LF). Peringatan `LF will be replaced by CRLF` dari git normal. Pertahankan line ending file yang diedit.

## Peta
- Tugas dan status: `TASKS.md`
- Kontrak: `docs/tasks/`
- Codemap: `docs/codemap/index.md` (folder `docs/` bisa dibuka sebagai vault Obsidian)
