# CHEAT-P3: CLAUDE.md + codemap per fitur
Status: DONE

## Tujuan
Sesi Claude Code baru bisa langsung tahu cara menjalankan app, aturan kerja, jebakan yang diketahui, dan lokasi file + rentang baris tiap fitur tanpa grep panjang.

## Area yang boleh disentuh
- `CLAUDE.md` (baru, root)
- `docs/codemap/*.md` (baru, ±12 catatan fitur + 1 indeks)
- `docs/tasks/CHEAT-P3.md` (kontrak ini)
- `TASKS.md` (status, baton, log)

## Di luar scope (jangan dikerjakan)
- Mengubah kode aplikasi apa pun (`src/`, `backend/`, `scripts/`)
- Skill, subagent, hook, `.claude/` (itu P3b)
- Smoke test / golden fixtures (itu task 17). CLAUDE.md cukup menyebut bahwa smoke test belum ada.
- Konfigurasi Obsidian (`.obsidian/`)

## Keputusan yang boleh diambil AI sendiri
- Pembagian fitur ke catatan codemap dan nama file catatan
- Format catatan (frontmatter, urutan bagian), selama konsisten
- Menyebut jebakan tambahan yang ditemukan saat membaca kode

## Kriteria selesai (ya/tidak)
- [x] `CLAUDE.md` berisi: cara menjalankan app, status smoke test, aturan kerja (baca TASKS.md + kontrak, sentuh hanya area yang diizinkan), jebakan yang diketahui (auto-cleanup `exports`, 1080×1920 hardcoded, self-update `git pull`)
- [x] `docs/codemap/` berisi ±12 catatan fitur, masing-masing dengan file + fungsi kunci + rentang baris, input/output, risiko, dan link `[[...]]`
- [x] Setiap link `[[...]]` menunjuk ke catatan yang ada (tidak ada link patah, tidak ada catatan yatim)
- [x] Rentang baris yang disebut cocok dengan kode di commit saat ini (dicek dengan skrip)
- [x] Tidak ada perubahan di luar area yang diizinkan

## Cara menguji
- Skrip cek: semua `[[link]]` resolve, semua catatan punya minimal satu link masuk
- Skrip cek: setiap `nama_fungsi` + `Lx–Ly` di codemap benar-benar ada di file tersebut pada baris itu
- `git status` hanya menunjukkan file di area yang diizinkan

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `CLAUDE.md` (baru), `docs/codemap/` (baru: `index.md` + 14 catatan fitur), `docs/tasks/CHEAT-P3.md`, `TASKS.md`
HASIL_TEST: Skrip cek (di luar repo, scratchpad sesi) lulus: 15 catatan, 0 link patah, 0 catatan yatim, semua catatan ditautkan dari `index`. 190 baris tabel dengan simbol dicocokkan persis (awal dan akhir) dengan AST Python dan TypeScript compiler API. 64 baris label (potongan di dalam fungsi besar) dicek batasnya dan baris awal/akhirnya diperiksa manual. Tidak ada kode aplikasi yang diubah, jadi `npm run build` tidak dijalankan ulang.
CODEMAP_DIPERBARUI: ya (dibuat dari nol, diverifikasi pada commit kode `4b32420`)
CATATAN: 14 catatan (sedikit di atas ±12) karena render server, render browser, subtitle, dan face tracking dipisah agar task #9, #10, #11 masing-masing menunjuk satu catatan. Temuan baru yang dicatat sebagai jebakan: `uvicorn --reload` + state job di memori, efek samping impor `backend.config`, komponen mati `ClipStudioModal.tsx` dan `BatchRenderProgressModal.tsx`, upload hanya mengirim audio ke server, render browser mengabaikan judul/subtitle. Skrip cek codemap belum disimpan di repo (di luar area kontrak); layak dijadikan bagian P3b atau task 17.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
