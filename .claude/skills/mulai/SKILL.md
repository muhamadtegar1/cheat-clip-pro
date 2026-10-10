---
name: mulai
description: Mulai satu task dari TASKS.md. Baca baton dan kontrak, tulis draf kontrak bila belum ada, lalu berhenti menunggu persetujuan pemilik sebelum implementasi.
argument-hint: <ID task, mis. 17 atau P3b>
disable-model-invocation: true
---

# /mulai $ARGUMENTS

Task yang diminta: **$ARGUMENTS**. Kalau kosong, pakai `langkah_berikut` dari baton dan sebutkan ID yang dipilih.

## Tahap 1: Persiapan (tanpa mengubah kode)
1. Baca `CLAUDE.md` dan blok **Baton** + baris task `$ARGUMENTS` di `TASKS.md`.
2. Cek aturan kerja no. 6: kalau task berasal dari fase setelah `fase_aktif`, atau ada task lain berstatus `IN_PROGRESS`/`REVIEW`, sebutkan dan tanyakan apakah tetap lanjut.
3. Cek blocker di baton dan tabel **Keputusan terbuka**. Kalau task bergantung pada keputusan yang belum dijawab (mis. K3 untuk task 17), berhenti dan minta jawabannya.
4. Jalankan `git status`. Kalau ada perubahan lokal yang tidak terkait, berhenti dan tanyakan.
5. Buka `docs/codemap/index.md` dan catatan fitur yang relevan. Ambil file, fungsi, dan rentang baris dari sana. Verifikasi rentangnya dengan membaca kodenya.

## Tahap 2: Kontrak
- Kalau `docs/tasks/CHEAT-$ARGUMENTS.md` **sudah ada**: baca, ringkas isinya ke pemilik, lalu lanjut ke Tahap 3 hanya bila statusnya sudah disetujui (`IN_PROGRESS`) atau pemilik bilang lanjut.
- Kalau **belum ada**: salin `docs/tasks/_TEMPLATE.md` menjadi `docs/tasks/CHEAT-$ARGUMENTS.md`, hapus komentar `<!-- -->` dan blok prompt review di bawah garis `---`, lalu isi:
  - Judul: `# CHEAT-$ARGUMENTS: <judul singkat>`, `Status: TODO`
  - Tujuan (satu kalimat), Area yang boleh disentuh (file + fungsi + rentang baris dari codemap), Di luar scope, Keputusan yang boleh diambil AI, Kriteria selesai (ya/tidak, diambil dari kolom "Selesai jika" di TASKS.md lalu dipertajam), Cara menguji.
  - Biarkan bagian Laporan implementer dan Review kosong.

Lalu **BERHENTI**. Tampilkan ringkasan kontrak (tujuan, area, kriteria, cara uji, risiko dari codemap) dan tanyakan: "Setujui kontrak ini?" Jangan menyentuh kode sebelum pemilik menjawab setuju.

## Tahap 3: Setelah disetujui
1. Ubah `Status:` kontrak menjadi `IN_PROGRESS`.
2. Di `TASKS.md`: status baris task → `IN_PROGRESS`, baton `task_aktif: $ARGUMENTS`, `status: $ARGUMENTS IN_PROGRESS`. Simpan, lalu baca ulang untuk memastikan tidak tertimpa.
3. Implementasi. Sentuh **hanya** area di kontrak. Kalau ternyata perlu file lain, berhenti dan minta kontrak diperbarui.
4. Selama bekerja: stage file satu per satu, jangan `git add .`, jangan commit `package-lock.json` kecuali kontrak mengizinkan.
5. Setelah implementasi selesai, beri tahu pemilik bahwa langkah berikutnya adalah `/tutup`. Jangan commit sebelum `/tutup`.
