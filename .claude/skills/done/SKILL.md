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
5. Di branch task (worktree), stage hanya kontrak + `TASKS.md` (satu per satu), lalu commit `$ARGUMENTS: tandai DONE`. Belum push.
6. **Merge ke `custom`**. `<utama>` = checkout utama (baris pertama `git worktree list`), `<branch>` = branch task (`git rev-parse --abbrev-ref HEAD`).
   1. `git -C <utama> status --short --branch`: harus di `custom` dan tanpa perubahan pada file yang dilacak (file untracked boleh). Kalau tidak, berhenti dan laporkan.
   2. Beri tahu pemilik: merge mengubah file di checkout utama, jadi app produksi yang sedang jalan akan reload (backend `--reload` restart dan job render/unduhan yang berjalan hilang). Sarankan menunggu render selesai.
   3. `git -C <utama> merge --no-ff <branch> -m "$ARGUMENTS: merge ke custom"`.
   4. Konflik `TASKS.md`: pertahankan semua baris Log dari kedua sisi (urut tanggal) dan baris task versi terbaru (status paling maju, mis. `DONE`); blok Baton ambil dari branch task. Selesaikan di `<utama>`, `git -C <utama> add TASKS.md`, lalu `git -C <utama> commit --no-edit`.
   5. Konflik file lain: **berhenti**, jangan selesaikan sendiri. Laporkan daftar file (`git -C <utama> diff --name-only --diff-filter=U`) dan biarkan pemilik memutuskan (`git -C <utama> merge --abort` untuk batal).
   6. Setelah merge berhasil: `git -C <utama> push origin custom`, lalu `git push -u origin HEAD` (branch task). Kalau push meminta login, beri tahu pemilik dan tunggu.
   7. Worktree dan branch task **tidak** dihapus otomatis. Bila pemilik nanti minta dihapus: lepas junction dulu (`cmd /c rmdir node_modules` dan `cmd /c rmdir venv` di worktree) sebelum `git worktree remove`, agar isi `node_modules`/`venv` utama tidak ikut terhapus.
7. Laporkan: commit DONE, commit merge di `custom`, isi baton baru, dan apa task berikutnya (sebut blocker bila ada).
