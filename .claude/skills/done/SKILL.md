---
name: done
description: Tandai task DONE setelah pemilik proyek mencoba hasilnya. Perbarui kontrak, TASKS.md (status, baton, log), commit, push.
argument-hint: <ID task>
disable-model-invocation: true
---

# /done $ARGUMENTS

Pemilik proyek menetapkan task **$ARGUMENTS** sebagai DONE. Skill ini hanya dipanggil oleh pemilik; jangan menjalankannya atas inisiatif sendiri.

1. Pastikan baris task `$ARGUMENTS` ada di `TASKS.md` dan berstatus `REVIEW`. Kalau barisnya tidak ditemukan, berhenti dan laporkan. Kalau statusnya lain (`IN_PROGRESS`, `FIX_REQUIRED`, dll.), sebutkan dan tanyakan apakah tetap lanjut.
2. `git status`. Kalau ada perubahan lain selain yang akan diubah skill ini, berhenti dan tanyakan.
3. Kontrak `docs/tasks/CHEAT-$ARGUMENTS.md`: ubah `Status:` menjadi `DONE` (bila file ada).
4. `TASKS.md`:
   - Status baris task → `DONE` (pertahankan lebar kolom bila memungkinkan).
   - Baton: `task_aktif: —`, `status: $ARGUMENTS DONE`. Perbarui `langkah_berikut` ke task berikutnya di fase aktif yang belum DONE (hormati aturan no. 6 dan blocker), dan `blocker` sesuai kondisi terkini.
   - Bila semua task di fase aktif sudah DONE, ubah `fase_aktif` ke fase berikutnya.
   - Tambah baris Log: `| YYYY-MM-DD | $ARGUMENTS | DONE | Ditetapkan DONE oleh pemilik proyek |`.
   - Simpan, lalu baca ulang untuk memastikan perubahan tidak tertimpa.
5. Stage hanya kontrak + `TASKS.md` (satu per satu), commit `$ARGUMENTS: tandai DONE`, lalu `git push`.
6. Laporkan: commit, isi baton baru, dan apa task berikutnya (sebut blocker bila ada).
