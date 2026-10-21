# CHEAT-41: Sesuaikan durasi klip sebelum render
Status: REVIEW

## Riwayat
- 2026-10-21: draf dibuat. Permintaan pemilik: klip kadang mulai di tempat yang salah dan berakhir menggantung; pemilik ingin menambah/mengurangi durasi klip secara manual sebelum render. Izin aturan no. 6 (Fase 3) dari pemilik, tercatat di Log.

## Tujuan
Pemilik bisa membuka trimmer dari tombol "Sesuaikan durasi" di kartu klip dan di Clip Studio, menggeser awal/akhir klip (termasuk ±1 detik dan klik kalimat transkrip), menekan "Terapkan" tanpa mengunduh klip mentah, lalu merender klip dengan rentang baru tanpa klip hilang dari pilihan render.

## Temuan saat menyusun kontrak (kode sekarang)
- `ClipTrimmerModal` sudah punya drag handle, input waktu, preset ±15/30/60/120 s, tombol geser ±5/15/30 s (`nudgeStart`/`nudgeEnd` L535-546, tombol L1284-1370), navigasi transkrip "Jadikan Mulai/Selesai", dan `getAdjustedClip` (L560-569). Satu-satunya aksi adalah `onDownload` (L571-582, tombol L1592) yang di `App.tsx` (L4967-4980) menerapkan rentang baru (`handleApplyAdjustedClipToResults` L1890-1904) lalu mengunduh raw.
- Bug yang akan muncul bila rentang diterapkan: tanda klip untuk render (`markedClips`, L250, kunci `start_end`, disimpan di `localStorage` `marked_clips_<video_id>` L896-923) dimuat ulang dari `localStorage` setiap `result` berubah (L873-888). Klip yang di-trim mendapat kunci baru, jadi hilang dari daftar klip terpilih Clip Studio. Judul kustom per klip di Clip Studio (`customClipTitles` L348, kunci `start_end`) juga hilang.
- Pratinjau/suntingan subtitle (#36a/#36b) memakai kunci `start_end_bahasa`, jadi rentang baru otomatis tanpa pratinjau dan render memakai Whisper untuk rentang baru (benar, kata lama tidak cocok waktunya). Pakai/Lewati (#35) memakai kunci rentang di backend, jadi rentang baru = record baru (perilaku yang sudah didokumentasikan di `pilihan-klip.md`). Render, posting kit, dan backend memakai `start_time`/`end_time` dari klip yang dikirim, jadi tidak perlu diubah.

## Area yang boleh disentuh
- `src/components/ClipTrimmerModal.tsx`:
  - props (L5-16): aksi baru `onApply` (terapkan tanpa unduh); `onDownload` tetap.
  - `nudgeStart`/`nudgeEnd` dan baris tombol geser (L535-546, L1284-1370): tambah −1 / +1 detik.
  - footer (±L1525-1600): tombol "Terapkan" sebagai aksi utama di samping tombol unduh raw.
  - judul/subjudul modal (L611-617) bila teksnya diganti agar tidak hanya tentang unduhan.
- `src/App.tsx`:
  - `handleApplyAdjustedClipToResults` (L1890-1904): pindahkan tanda `markedClips` (state + `localStorage`) dari kunci lama ke kunci baru, dan cegah tabrakan dengan klip lain yang rentangnya sama persis.
  - kartu klip (sekitar tombol unduh raw L4800-4860): tombol "Sesuaikan durasi".
  - render `ClipTrimmerModal` (L4966-4980): sambungkan `onApply`.
  - props `ClipStudioSection` (sekitar L4925-4960): callback untuk membuka trimmer dari Clip Studio.
- `src/components/ClipStudioSection.tsx`:
  - props (L63-80, L312-330): callback baru opsional untuk membuka trimmer.
  - daftar klip terpilih (L4003-4070): tombol "Sesuaikan durasi" per klip.
  - `customClipTitles` (L348): pindahkan judul kustom ke kunci rentang baru saat klip disesuaikan.
- `src/locales/id.ts`, `src/locales/en.ts`: blok `trimmer`, `results`, `studio` untuk string baru.
- `docs/codemap/clip-studio.md`, `frontend-app.md`, `index.md` bila perlu, `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Backend (render, posting kit, pilihan klip) dan `scripts/smoke_test.py`: tidak perlu berubah.
- Menyimpan rentang hasil trim ke cache riwayat analisis (`localStorage` hasil analisis). Setelah halaman dimuat ulang atau hasil dimuat dari riwayat, rentang kembali ke pilihan AI.
- Menyalin pilihan Pakai/Lewati atau pratinjau/suntingan subtitle dari rentang lama ke rentang baru.
- Trim di dalam pratinjau Clip Studio (timeline baru), mode merged per segmen, batas ±2 menit trimmer.
- Memperbaiki tampilan waktu di daftar klip terpilih yang bisa menulis "x:60" (bug lama, L4058-4060).
- Merombak tampilan trimmer di luar tombol yang disebut.

## Keputusan yang boleh diambil AI sendiri
- Nama prop/fungsi, teks UI, ikon, letak tombol di kartu dan daftar Clip Studio.
- Apakah modal tertutup setelah "Terapkan" atau menampilkan konfirmasi singkat.
- Cara memberi tahu `ClipStudioSection` tentang perubahan rentang (mis. callback dengan rentang lama dan baru).
- Perilaku bila rentang baru sama persis dengan klip lain (tolak dengan pesan, atau geser sedikit), selama tidak ada klip yang hilang atau tertimpa diam-diam.

## Kriteria selesai (ya/tidak)
- [x] Kartu klip dan daftar klip terpilih Clip Studio punya tombol "Sesuaikan durasi" yang membuka trimmer untuk klip itu.
- [x] Trimmer punya tombol "Terapkan" yang menerapkan rentang dan judul baru ke hasil analisis tanpa memanggil unduhan raw; tombol unduh raw tetap bekerja seperti sebelumnya.
- [x] Trimmer punya tombol −1 dan +1 detik untuk awal dan akhir (selain tombol ±5/15/30 yang sudah ada).
- [x] Klip yang sudah ditandai untuk render tetap tertanda dan tetap ada di daftar klip terpilih Clip Studio setelah rentangnya diubah, termasuk setelah tanda dibaca ulang dari `localStorage`; judul kustom Clip Studio untuk klip itu ikut pindah.
- [x] Render `separate` 1 klip setelah "Terapkan" menghasilkan MP4 dengan rentang baru (`metadata.json` kit: `start_time`/`end_time` sama dengan rentang baru; durasi MP4 sesuai), dan pratinjau subtitle tidak memakai kata dari rentang lama.
- [x] String baru ada di `id.ts` dan `en.ts`.
- [x] `npm run build` lulus, lint tidak menambah masalah di file yang disentuh, smoke test lulus, `check_codemap.py` lulus.

## Cara menguji
- `npm run build`, `npm run lint` (bandingkan jumlah error/warning file yang disentuh sebelum dan sesudah), `venv\Scripts\python.exe scripts\smoke_test.py`, `venv\Scripts\python.exe scripts\check_codemap.py`.
- Browser bawaan (`npm run dev`): video sintetis atau hasil dari riwayat dengan key `mock`; tandai 1 klip, buka "Sesuaikan durasi" dari kartu, geser awal +1 s dan akhir −1 s, Terapkan; pastikan tidak ada request unduh raw, klip tetap tertanda dan muncul di Clip Studio dengan rentang baru; ulangi dari tombol di Clip Studio; render 1 klip dan cek `metadata.json` kit serta durasi MP4 (`ffprobe`). Cek id dan en.
- Perlu dicek pemilik: alur memperbaiki awal yang salah dan akhir yang menggantung terasa nyaman pada video campaign nyata.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `src/components/ClipTrimmerModal.tsx`: prop opsional `onApply` (L17, L61); tombol −1/+1 s untuk awal dan akhir di baris tombol geser (memakai `nudgeStart`/`nudgeEnd` yang sudah ada); tombol "✔ Terapkan (awal - akhir)" di footer sebelum tombol unduh raw (L1571-1595). Tombol unduh raw tidak diubah.
- `src/App.tsx`: state `clipRangeChange` (L90-91); `handleApplyAdjustedClipToResults` (L1893-1931) mengembalikan boolean, menolak rentang yang sama persis dengan klip lain (toast), memindahkan tanda `markedClips` ke kunci baru dan menulis `localStorage` sebelum `setResult` (efek sinkronisasi membaca ulang `localStorage` saat `result` berubah), mengisi `clipRangeChange`, memperbarui `activeClip`; tombol "Sesuaikan Durasi" di kartu klip (L4826-4839); `onApply` di `ClipTrimmerModal` (L5024-5033: terapkan, toast, tutup); props `onAdjustClip`/`clipRangeChange` ke `ClipStudioSection`.
- `src/components/ClipStudioSection.tsx`: props `onAdjustClip`, `clipRangeChange`; pemindahan `customClipTitles` ke kunci baru (L354-367, pola sesuaikan state saat render, tanpa efek); tombol "Sesuaikan durasi" per klip di daftar klip terpilih (L4083-4108).
- `src/locales/id.ts`, `en.ts`: `results.adjustDuration*` (4 string), `trimmer.modalTitle`/`modalSubtitle` diganti, `trimmer.applyBtn`/`applyTooltip`, `studio.adjustDuration`.
- Codemap, `TASKS.md`, kontrak ini. Backend tidak berubah.
HASIL_TEST:
- `npm run build`: lulus (`built in 972ms`, hanya peringatan ukuran chunk lama).
- Lint (eslint, `git show HEAD:<file>` lewat stdin vs sesudah, error/warning): `App.tsx` 23/4 = 23/4, `ClipStudioSection.tsx` 30/2 = 30/2, `ClipTrimmerModal.tsx` 17/1 = 17/1, `id.ts`/`en.ts` 0/0.
- `venv\Scripts\python.exe scripts\smoke_test.py`: `23/23 cek lulus. SMOKE TEST LULUS`.
- `venv\Scripts\python.exe scripts\check_codemap.py`: `SEMUA CEK LULUS` (294 simbol).
- Browser bawaan (backend + frontend): video sintetis 60 s diunggah lewat `/api/upload-video`, hasil analisis `mock` dimasukkan ke riwayat `localStorage`, Load Analysis. Klip 1 (11-22 s) ditandai dan diberi judul kustom di Clip Studio; tombol "Adjust duration" di Clip Studio membuka trimmer, +1 s awal, −1 s akhir, Apply: modal tertutup, toast, klip 12-21 s tetap tertanda (`marked_clips_*` = `{"12_21":true}`), judul kustom tetap, tidak ada request unduh raw di daftar network. Dari tombol kartu klip 2 (22-32): rentang 12-21 ditolak (toast duplikat, modal tetap terbuka, tidak ada klip berubah); 23-31 diterapkan. Render 1 klip: `metadata.json` kit `start_time` 12.0, `end_time` 21.0, `duration` 9.0, judul kustom; `ffprobe` MP4 9.03 s. Teks id dicek (tombol, judul modal, Terapkan). File uji (MP4, kit, upload, `localStorage`) dihapus.
CODEMAP_DIPERBARUI: ya. `clip-studio.md` (baris `nudgeStart`/`nudgeEnd`, tombol Terapkan, pemindahan judul kustom, tombol Sesuaikan durasi, input props, risiko kunci rentang), `frontend-app.md` (`handleApplyAdjustedClipToResults`, `toggleMarkedClip`, tombol kartu, `onApply`/props Clip Studio). Rentang baris yang bergeser di `App.tsx`/`ClipStudioSection.tsx`/`ClipTrimmerModal.tsx` digeser dari hunk `git diff` di semua catatan (`face-tracking`, `penyimpanan-dan-cleanup`, `pilihan-klip`, `render-browser`, `sistem-update`, `sumber-video`, `unduhan-raw`).
CATATAN:
- Keputusan sendiri: modal tertutup setelah Terapkan dengan toast; rentang yang sama persis dengan klip lain ditolak (bukan digeser otomatis). Tombol unduh raw tetap menerapkan rentang lalu mengunduh seperti sebelumnya (kini ikut memindahkan tanda; bila bentrok, rentang tidak diterapkan tetapi unduhan tetap jalan, sama seperti perilaku lama yang tidak memeriksa bentrok).
- Kolom judul di trimmer menampilkan `title_suggestion`, bukan judul kustom Clip Studio; judul kustom tetap menang saat render.
- Sesuai kontrak: rentang hasil trim tidak disimpan ke cache riwayat; pilihan Pakai/Lewati dan pratinjau/suntingan subtitle tidak disalin ke rentang baru.
- Console menampilkan peringatan React `src=""` kosong saat uji; tidak ditelusuri apakah sudah ada sebelum task ini.
- Saat uji, folder `D:\CheatClip\kits` dan MP4 lama di `D:\CheatClip` sudah tidak berisi kit Casita/MP4 sebelumnya (sebelum render uji); hanya file uji sendiri yang dihapus.
- Perlu dicek pemilik: alur memperbaiki awal yang salah dan akhir yang menggantung pada video campaign nyata.
- Perbaikan setelah review subagent (FIX_REQUIRED, 2026-10-21): "Unduh raw" lalu "Terapkan" di modal yang sama memakai `trimmerClip` basi (rentang lama), sehingga Terapkan ditolak dengan pesan duplikat keliru atau melapor sukses tanpa mengubah klip. Sekarang `App.tsx` menyimpan versi klip yang sudah diterapkan di `trimmerAppliedRef` (dikosongkan oleh `openTrimmer` saat modal dibuka) dan `handleApplyAdjustedClipToResults` mengembalikan `false` bila klip asal tidak ada di `result`. Uji browser ulang: 11-22 → +1 awal → Unduh (12-22 diterapkan, file raw terunduh) → −1 akhir → Terapkan = 12-21, toast sukses, tanda `{"12_21":true}`; buka lagi → +1 awal → Unduh → Terapkan tanpa ubah = 13-21, tanpa toast duplikat. Build lulus, lint `App.tsx` 23/4 sama, `check_codemap.py` lulus. File uji (raw MP4 di `D:\CheatClip` dan `Downloads`, upload, `localStorage`) dihapus.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
