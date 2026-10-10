---
name: tutup
description: Tutup task aktif. Jalankan cek, perbarui codemap, isi laporan implementer, set status REVIEW, commit + push, lalu panggil subagent reviewer.
argument-hint: (opsional) ID task; default task_aktif di baton
disable-model-invocation: true
---

# /tutup $ARGUMENTS

Task: **$ARGUMENTS**. Kalau kosong, pakai `task_aktif` dari baton di `TASKS.md`. Kalau baton tidak menunjuk task berstatus `IN_PROGRESS`, berhenti dan tanyakan.

Kontrak: `docs/tasks/CHEAT-<ID>.md`. Baca dulu, terutama Area, Kriteria selesai, dan Cara menguji. Kalau kontrak tidak ada, berhenti: task harus dimulai dengan `/mulai <ID>`.

## 1. Cek lingkup
- `git status` dan `git diff --stat`. Semua file yang berubah harus ada di "Area yang boleh disentuh" (plus `TASKS.md`, kontrak, dan `docs/codemap/`).
- Kalau ada file di luar area (termasuk `package-lock.json` yang berubah karena `npm install`), kembalikan bila itu efek samping, atau berhenti dan laporkan bila memang dibutuhkan.

## 2. Jalankan cek
Catat perintah dan hasil (lulus/gagal + potongan output penting) untuk laporan:
1. Bila `src/` berubah: `npm run build`.
2. **Smoke test**: jalankan perintah smoke test di bagian "Smoke test" pada `CLAUDE.md`. Kalau bagian itu masih bertulisan "Belum ada", lewati dengan peringatan jelas di laporan ("smoke test belum tersedia, task 17"), jangan dianggap gagal.
3. Langkah di "Cara menguji" pada kontrak.
4. Bila task mengubah prompt AI: golden fixtures (setelah task 17 tersedia).

Kalau ada yang gagal, berhenti di sini. Laporkan ke pemilik dan jangan set REVIEW.

## 3. Perbarui codemap
- Untuk setiap file kode yang berubah, cari catatan di `docs/codemap/` yang menyebutnya (`grep -l <path> docs/codemap/*.md`). Perbarui rentang baris, fungsi baru/terhapus, input/output, dan risiko.
- Jalankan `venv\Scripts\python.exe scripts\check_codemap.py`. Harus keluar dengan `SEMUA CEK LULUS`. Perbaiki codemap sampai lulus.

## 4. Laporan dan status
1. Isi bagian **Laporan implementer** di kontrak: `STATUS: REVIEW`, `FILE_DIUBAH`, `HASIL_TEST` (dari langkah 2), `CODEMAP_DIPERBARUI` (sebutkan catatan), `CATATAN` (keputusan yang diambil sendiri, risiko, hal yang perlu dicek pemilik). Centang kriteria yang terpenuhi; yang belum, jelaskan.
2. Ubah `Status:` kontrak menjadi `REVIEW`.
3. Di `TASKS.md`: status baris task → `REVIEW`, baton `status: <ID> REVIEW`, perbarui `langkah_berikut` dan `blocker` bila perlu, tambah satu baris **Log** (`| YYYY-MM-DD | <ID> | REVIEW | ringkasan |`). Pertahankan format tabel. Simpan lalu baca ulang; kalau tertimpa, laporkan.
4. Jangan pernah menulis `DONE`. Itu hak pemilik lewat `/done`.

## 5. Commit dan push
1. `git status`, lalu stage file kode + kontrak + codemap satu per satu (jangan `git add .`). Commit: `<ID>: <judul singkat dari kontrak>`.
2. Stage `TASKS.md` saja. Commit: `<ID>: TASKS.md status REVIEW`.
3. `git push` ke `origin custom`. Kalau push meminta login, beri tahu pemilik dan tunggu.

## 6. Review oleh subagent
Panggil subagent `reviewer` (Agent tool, `subagent_type: "reviewer"`) dengan prompt: "Review task <ID>. Kontrak: docs/tasks/CHEAT-<ID>.md. Commit task: yang pesannya diawali `<ID>:`." Subagent hanya bisa membaca dan menjalankan perintah, tidak bisa mengedit.

Setelah subagent selesai:
- Tampilkan verdict dan alasannya ke pemilik apa adanya.
- Jangan mengisi bagian "Review (sesi baru)" di kontrak; bagian itu milik `/review` di sesi baru.
- Kalau verdict `FIX_REQUIRED`, tanyakan apakah temuannya diperbaiki sekarang.

## 7. Ringkasan untuk pemilik
Perintah yang dijalankan, file yang diubah, hasil tiap kriteria selesai, verdict subagent, dan apa yang perlu dicoba pemilik sebelum `/done <ID>`. Untuk task berisiko tinggi (#7, #12, #16), ingatkan bahwa `/review <ID>` wajib dijalankan di sesi baru.
