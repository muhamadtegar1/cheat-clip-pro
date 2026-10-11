# CHEAT-P3b: Otomasi alur Claude Code
Status: DONE

## Tujuan
Sesi Claude Code baru otomatis tahu baton, dan satu task bisa dijalankan dengan alur `/mulai <ID>` → setujui kontrak → `/tutup` → `/done <ID>`.

## Area yang boleh disentuh
- `.claude/skills/mulai/SKILL.md`, `.claude/skills/tutup/SKILL.md`, `.claude/skills/review/SKILL.md`, `.claude/skills/done/SKILL.md` (baru)
- `.claude/agents/reviewer.md` (baru)
- `.claude/settings.json` (baru, hanya hook `SessionStart`)
- `scripts/baton.js` (baru)
- `scripts/check_codemap.py` + `scripts/codemap_ts_index.cjs` (baru, usulan dari P3 yang disetujui pemilik)
- `CLAUDE.md`: bagian alur kerja dan smoke test (sebut skill + skrip cek codemap)
- `docs/tasks/CHEAT-P3b.md`, `TASKS.md`

## Di luar scope (jangan dikerjakan)
- Kode aplikasi (`src/`, `backend/`), dependensi, `package.json`
- Smoke test aplikasi (task 17)
- `docs/.obsidian/` (konfigurasi pribadi pemilik)
- Pengaturan permission atau hook lain selain `SessionStart`

## Keputusan yang boleh diambil AI sendiri
- Isi dan susunan instruksi di tiap skill, selama mengikuti aturan kerja di `TASKS.md`
- Format keluaran `scripts/baton.js`
- Cara reviewer menemukan diff (konvensi pesan commit `<ID>: ...`)

## Kriteria selesai (ya/tidak)
- [x] 4 skill ada, masing-masing dengan `disable-model-invocation: true`
- [x] `/mulai` menulis draf kontrak bila belum ada lalu BERHENTI menunggu persetujuan
- [x] `/tutup` menjalankan cek (build, smoke test bila ada, cek codemap), mengisi laporan, status REVIEW, commit, lalu memanggil subagent reviewer
- [x] `.claude/agents/reviewer.md` hanya punya tools Read, Grep, Glob, Bash (tanpa Edit/Write)
- [x] `scripts/baton.js` mencetak blok Baton; hook `SessionStart` (matcher startup, clear, compact) terpasang di `.claude/settings.json`
- [x] Sesi baru tanpa prompt pembuka sudah tahu baton (diuji dengan sesi `claude -p` terpisah)
- [x] `scripts/check_codemap.py` lulus pada codemap saat ini
- [ ] Alur penuh `/mulai` → `/tutup` → `/done` terbukti pada satu task nyata (dibuktikan pada task berikutnya oleh pemilik)

## Cara menguji
- `node scripts/baton.js` mencetak baton dari `TASKS.md`
- Validasi JSON `.claude/settings.json`
- `claude -p "..."` di sesi baru: tanyakan task aktif tanpa menyebut TASKS.md
- `venv\Scripts\python.exe scripts\check_codemap.py` keluar dengan kode 0

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `.claude/skills/{mulai,tutup,review,done}/SKILL.md`, `.claude/agents/reviewer.md`, `.claude/settings.json`, `scripts/baton.js`, `scripts/check_codemap.py`, `scripts/codemap_ts_index.cjs` (semua baru); `CLAUDE.md` (tabel alur task, langkah cek codemap, jebakan no. 10); `docs/tasks/CHEAT-P3b.md`; `TASKS.md`
HASIL_TEST:
- `node scripts/baton.js`: mencetak blok Baton, exit 0. Pipe-test `echo '{}' | node scripts/baton.js`: exit 0.
- `.claude/settings.json`: JSON valid, matcher `startup|clear|compact`, command `node scripts/baton.js`.
- Sesi baru `claude -p` (tanpa tool, tanpa menyebut TASKS.md) menjawab task_aktif P3b, status P3b IN_PROGRESS, dan blocker K3, serta menyebut sumbernya hook SessionStart.
- Sesi baru `claude -p "/review ZZTEST"` (Bash/Edit/Write diblokir): skill ter-expand (mencari `CHEAT-ZZTEST.md` dan commit `^ZZTEST:`), tidak ada file berubah. Dari tes ini ditambahkan guard "task tidak ditemukan" di `/review`, `/tutup`, `/done`.
- Sesi baru `claude -p`: subagent `reviewer` terdaftar dengan tools `Read, Grep, Glob, Bash`.
- `venv\Scripts\python.exe scripts\check_codemap.py`: 15 catatan, 190 simbol terverifikasi, SEMUA CEK LULUS (juga lulus saat dijalankan dari subfolder `backend/`).
- Tidak ada kode aplikasi yang berubah, jadi `npm run build` tidak relevan. ESLint hanya mencakup `*.ts/tsx`, jadi skrip baru tidak memengaruhi `npm run lint`.
CODEMAP_DIPERBARUI: tidak (tidak ada kode aplikasi yang berubah; skrip tooling tidak dipetakan di codemap fitur)
CATATAN: Kriteria terakhir (alur penuh `/mulai` → `/tutup` → `/done` pada task nyata) belum bisa dibuktikan di sesi ini karena skill proyek baru dimuat di sesi berikutnya; buktinya adalah task pertama yang dikerjakan dengan skill ini. Pemanggilan headless dari Git Bash butuh `MSYS_NO_PATHCONV=1` (dicatat di CLAUDE.md). Skill `/done` memakai nilai baton `task_aktif: —` agar sama dengan format TASKS.md. `docs/.obsidian/` sengaja tidak di-commit; pertimbangkan menambahkannya ke `.gitignore` di task terpisah.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
