---
name: review
description: Review penuh satu task di sesi baru, hanya berdasarkan kontrak, git diff commit task, dan test yang dijalankan sendiri. Menulis verdict PASS atau FIX_REQUIRED.
argument-hint: <ID task>
disable-model-invocation: true
---

# /review $ARGUMENTS

Kamu adalah reviewer independen untuk task **$ARGUMENTS**. Jalankan skill ini di sesi Claude Code yang baru. Jangan memakai pengetahuan dari percakapan implementasi; bukti hanya dari kontrak, diff, dan perintah yang kamu jalankan sendiri.

## 1. Kumpulkan bahan
1. Baca `CLAUDE.md`, baris task `$ARGUMENTS` di `TASKS.md`, dan `docs/tasks/CHEAT-$ARGUMENTS.md` (Area, Di luar scope, Kriteria selesai, Cara menguji, Laporan implementer).
2. Temukan commit task: `git log --oneline --grep="^$ARGUMENTS:"`.
   Kalau kontrak tidak ada, baris task tidak ada di `TASKS.md`, atau tidak ada commit berawalan `$ARGUMENTS:`, **berhenti** dan laporkan apa yang tidak ditemukan. Jangan membuat kontrak, baris Log, atau commit pengganti.
3. Lihat perubahannya: `git show --stat <commit>` dan `git show <commit>` untuk setiap commit itu. Abaikan commit yang hanya mengubah `TASKS.md`.

## 2. Periksa
- **Lingkup**: setiap file yang berubah ada di "Area yang boleh disentuh" (plus kontrak, `TASKS.md`, `docs/codemap/`). File di luar area = temuan.
- **Kriteria selesai**: untuk tiap kriteria, tentukan terpenuhi atau tidak berdasarkan diff dan test. Jangan percaya centang di laporan implementer tanpa bukti.
- **Test**: jalankan sendiri langkah "Cara menguji", `npm run build` bila `src/` berubah, smoke test dari `CLAUDE.md` bila sudah ada, dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- **Codemap**: catatan yang menyebut file yang diubah sudah diperbarui, dan cek codemap lulus.
- **Kualitas**: bug yang jelas, penanganan error yang hilang, rahasia yang ter-commit, perubahan yang tidak perlu (format ulang, refactor di luar kontrak).
- Jangan mengubah kode. Kalau menemukan masalah, catat saja.

## 3. Tulis verdict
Isi bagian **Review (sesi baru)** di kontrak:
```
VERDICT: PASS | FIX_REQUIRED
ALASAN:
- <kriteria/temuan 1 + bukti (file:baris, output perintah)>
- ...
```
- `PASS` hanya bila semua kriteria yang bisa dibuktikan terpenuhi, tidak ada perubahan di luar lingkup, dan test lulus.
- Kriteria yang memang hanya bisa dibuktikan pemilik (mis. dicoba manual) disebut sebagai "perlu dicek pemilik", tidak otomatis membuat FIX_REQUIRED.

Lalu di `TASKS.md`:
- `PASS`: status tetap `REVIEW` (DONE ditetapkan pemilik), tambah baris Log `| YYYY-MM-DD | $ARGUMENTS | REVIEW | Review sesi baru: PASS |`.
- `FIX_REQUIRED`: status baris task dan baton → `FIX_REQUIRED`, tambah baris Log dengan ringkasan temuan.

Simpan, baca ulang `TASKS.md`, lalu commit hanya kontrak + `TASKS.md` dengan pesan `$ARGUMENTS: review <PASS|FIX_REQUIRED>` dan push.

## 4. Laporkan
Verdict, daftar temuan dengan bukti, dan apa yang perlu dicoba pemilik.
