# CHEAT-36a: Pratinjau subtitle asli (Whisper) di Clip Studio sebelum render
Status: REVIEW
Risiko: sedang (endpoint baru yang menjalankan Whisper dan mengunduh segmen; `generate_ass_file` dipecah tanpa mengubah hasil `.ass`; tanpa perubahan prompt AI)

## Tujuan
Pemilik bisa menekan "Buat subtitle" untuk klip yang sedang dipratinjau di Clip Studio, lalu melihat subtitle karaoke asli (kata, pemotongan, dan waktu yang sama persis dengan yang akan dibakar saat render) berjalan di pratinjau, sehingga kata yang salah terlihat sebelum render.

## Kondisi sekarang (diverifikasi di kode)
- Pratinjau Clip Studio hanya menampilkan contoh gaya ("VIRAL POP", "UNREAL HACK", dst.) di overlay subtitle (`src/components/ClipStudioSection.tsx` L4107-4188). Teks asli belum ada sebelum render.
- Saat render, `render_single_batch_clip` (`backend/services/render_service.py` L29-243) mengunduh segmen dengan `download_clip_segment` (L54-70; `backend/video_engine.py` L697), lalu `transcribe_clip_words` (`video_engine.py` L1154-1239: Whisper `base` per kata pada segmen, waktu relatif 0.0 = awal klip, fallback ke transkrip analisis), lalu `generate_ass_file` (L1737-2113). Di dalamnya, langkah A-D subtitle (L2005-2106) membersihkan kata, menerapkan kamus #11 dan `text_case`, mengelompokkan 1-3 kata (maks 22 karakter, putus di jeda >= 0.38 s atau akhir kalimat), lalu membagi waktu kata aktif. Logika ini yang menentukan apa yang terlihat di video.
- URL sumber dinormalisasi di `process_batch_rendering` (`render_service.py` L537-560: upload/gdrive -> `/api/video/<id>`, YouTube -> URL watch). Render memakai `_RENDER_SEMAPHORE = asyncio.Semaphore(1)` (L26).
- Pratinjau melacak `currentTime` (waktu sumber absolut) untuk YouTube iframe dan video langsung (L477, L660-700); klip yang dipratinjau adalah `currentPreviewClip`, `clipStart` (L513-514). Komponen belum menerima transkrip analisis (props L25-39, dipasang di `src/App.tsx` ±L4887-4907); cookies YouTube ada di `getStoredCookies` (`src/utils/cookieUtils.ts`).

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Satu sumber kebenaran untuk pemotongan subtitle**: langkah A-D di `generate_ass_file` dipindah ke fungsi murni `build_subtitle_events(words, text_case, word_replacements)` di `video_engine.py` yang mengembalikan daftar event `{start, end, words: [teks], active: indeks}` (teks belum di-escape ASS). `generate_ass_file` memakainya dan hanya menulis baris `Dialogue` seperti sekarang. Hasil `.ass` wajib identik byte-per-byte dengan sebelum task.
2. **Endpoint `POST /api/preview-subtitles`** (di `backend/routers/render.py`, model request di `backend/schemas/render.py`, logika di layanan baru `backend/services/subtitle_preview_service.py`): input `video_url`, `video_id`, `start_time`, `end_time`, `transcript` (fallback), `cookies`, `subtitle_replacements`, `text_case`. Proses: normalisasi URL (helper yang sama dengan render), `download_clip_segment` ke `TEMP_DIR` (file dihapus setelah selesai), `transcribe_clip_words`, lalu `build_subtitle_events`. Keluaran: `events` (waktu relatif awal klip), `words` mentah (untuk #36b), `source` (`whisper` / `transcript` / `none`), durasi proses.
3. **Cache + antrean**: kata mentah disimpan di memori per (video_id, start, end) (maks ±50 entri), jadi mengubah kamus/`text_case` hanya menghitung ulang event tanpa Whisper. Proses Whisper memakai `_RENDER_SEMAPHORE` yang sama dengan render, sehingga pratinjau dan render tidak menjalankan Whisper/FFmpeg bersamaan (berebut RAM). Konsekuensi: saat render berjalan, tombol pratinjau menunggu.
4. **UI Clip Studio**: tombol "Buat subtitle" + status (memproses / sumber / gagal) di kolom pratinjau. Bila event tersedia untuk klip yang dipratinjau, overlay subtitle menampilkan event aktif pada `currentTime - clipStart` (kata aktif diberi warna sorot gaya terpilih, teks lain putih, font/ukuran/posisi seperti overlay sekarang); bila belum, tetap contoh gaya seperti sekarang. Di bawah pratinjau ada teks subtitle lengkap per potongan (baca saja), potongan yang sedang tampil disorot. Saat kamus #11 atau `text_case` berubah, event dihitung ulang otomatis (memanggil endpoint lagi, kena cache). Hasil disimpan di state per kunci klip (`start_end`), jadi klip yang di-trim otomatis berstatus "belum dibuat" (kunci baru). Tidak disimpan ke `localStorage`.
5. `App.tsx` hanya meneruskan `transcript={result.transcript}` ke `ClipStudioSection`.

## Area yang boleh disentuh
- `backend/video_engine.py`: fungsi baru `build_subtitle_events`, `generate_ass_file` langkah A-D (L2005-2106) diganti pemanggilan fungsi itu.
- `backend/services/subtitle_preview_service.py` (baru): unduh segmen, Whisper, cache, `build_subtitle_events`.
- `backend/services/render_service.py`: helper normalisasi URL sumber diekstrak dari `process_batch_rendering` (L537-560) supaya dipakai bersama; `_RENDER_SEMAPHORE` (L26) dipakai bersama. Alur render lain tidak diubah.
- `backend/schemas/render.py`: model request/response pratinjau.
- `backend/routers/render.py`: route `POST /api/preview-subtitles`.
- `src/types.ts`: tipe event/response pratinjau.
- `src/utils/subtitlePreview.ts` (baru): panggilan API, cari event aktif pada waktu tertentu.
- `src/components/ClipStudioSection.tsx`: prop `transcript`, state + tombol + status, overlay subtitle (L4107-4188), daftar teks per potongan di kolom pratinjau (L3873-4754), hitung ulang saat kamus/`text_case` berubah.
- `src/App.tsx`: satu prop `transcript` di `<ClipStudioSection>` (±L4887-4907).
- `src/locales/id.ts`, `src/locales/en.ts`: string baru.
- `scripts/smoke_test.py`: cek baru (`.ass` identik untuk beberapa masukan kata vs keluaran `build_subtitle_events`; endpoint pratinjau pada video sintetis dengan Whisper dipalsukan/transkrip fallback: event sama dengan baris `Dialogue` render, kamus diterapkan, cache kena pada panggilan kedua, file segmen tidak tertinggal). `CLAUDE.md`: kalimat deskripsi smoke test (#36a).
- `docs/codemap/`: `subtitle-dan-judul.md`, `clip-studio.md`, `render-server.md`, `arsitektur-backend.md` (endpoint baru), `frontend-app.md` (prop), rentang yang bergeser; `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Menyunting kata/potongan dan memakai kata hasil suntingan saat render (task #36b).
- Memakai ulang segmen atau kata pratinjau saat render (render tetap mengunduh dan menjalankan Whisper sendiri seperti sekarang).
- Meniru ASS secara piksel (outline, ukuran persis libass) di pratinjau; cukup teks, pemotongan, waktu, warna sorot, dan font/posisi seperti overlay sekarang.
- Mode merged (pratinjau per klip saja), render browser (`browser_wasm`), judul, prompt AI, Whisper/model lain, `ClipStudioModal.tsx`.
- Menyimpan hasil pratinjau permanen (`localStorage`/file).

## Keputusan yang boleh diambil AI sendiri
- Letak dan teks tombol/status/daftar teks di kolom pratinjau, selama ringkas.
- Nama fungsi, kunci locale, batas cache, struktur respons tambahan yang murni turunan.
- Cara menentukan `source` (mis. dari ketersediaan model Whisper dan hasil kosong).
- Debounce hitung ulang saat kamus/`text_case` berubah.
- Bila `build_subtitle_events` butuh parameter tambahan agar `.ass` identik, boleh, asal hasil tetap identik dan dicatat.

## Kriteria selesai (ya/tidak)
- [x] Tombol "Buat subtitle" di kolom pratinjau Clip Studio (id dan en) memanggil `POST /api/preview-subtitles` untuk klip yang dipratinjau dan menampilkan status memproses, sumber (Whisper/transkrip), atau pesan gagal tanpa merusak pratinjau.
- [x] Setelah selesai, overlay pratinjau menampilkan subtitle asli yang berjalan sesuai waktu pemutar (potongan dan kata aktif sama dengan baris `Dialogue` yang akan ditulis `generate_ass_file` untuk kata yang sama), dengan gaya/font/posisi terpilih; daftar teks per potongan tampil dan potongan aktif disorot.
- [x] Kamus #11 dan `text_case` diterapkan; mengubahnya memperbarui pratinjau tanpa menjalankan Whisper lagi (cache).
- [x] Klip yang di-trim (rentang berubah) tidak memakai subtitle lama; klip tanpa hasil tetap menampilkan contoh gaya seperti sekarang.
- [x] `generate_ass_file` menghasilkan `.ass` identik byte-per-byte dengan sebelum task untuk masukan yang sama (dibuktikan di smoke test dan dibandingkan dengan kode `HEAD` sebelum task).
- [x] Pratinjau dan render tidak menjalankan Whisper bersamaan; file segmen pratinjau dihapus setelah dipakai.
- [x] Semua string baru di `id.ts` dan `en.ts`; `npm run build` lulus; lint tanpa masalah baru; smoke test (dengan cek baru) dan `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `npm run build`, `npm run lint` (bandingkan jumlah masalah file yang diubah dengan sebelum task).
- `venv\Scripts\python.exe scripts\smoke_test.py` (cek baru #36a) dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- Bandingkan `.ass` dari `generate_ass_file` versi `HEAD` dan versi baru untuk beberapa set kata (gaya, `text_case`, kamus, jeda, tanda baca berbeda): harus identik.
- Uji browser dengan `npm run dev` (backend + frontend) dan video upload sintetis berisi suara atau data riwayat: tekan "Buat subtitle", pastikan subtitle berjalan di pratinjau, ubah kamus dan `text_case` (pratinjau berubah cepat tanpa Whisper ulang), trim klip (status kembali "belum dibuat"), cek teks id dan en, matikan backend (pesan gagal, pratinjau tidak rusak).
- Pemilik: pada video nyata (YouTube dan upload), buat subtitle di pratinjau, lalu render klip yang sama dan bandingkan teksnya dengan video hasil.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/video_engine.py`: fungsi baru `build_subtitle_events` (L1737-1842, langkah A-D yang dipindah dari `generate_ass_file`, teks belum di-escape); `generate_ass_file` (L1845-2139) kini menulis baris `Dialogue` dari event itu (L2115-2132, escape ASS per kata di sini).
- `backend/services/subtitle_preview_service.py` (baru): `_transcribe_segment` (Whisper lalu fallback transkrip, mencatat `source`), `_load_words` (cache memori maks 50, `_RENDER_SEMAPHORE`, `resolve_source_url`, `download_clip_segment` ke `TEMP_DIR/preview_*_raw.mp4` yang dihapus di `finally`), `preview_subtitles`.
- `backend/services/render_service.py`: helper `resolve_source_url` (L29-44) diekstrak dari `process_batch_rendering` (pemakaian L565); alur render lain tidak diubah.
- `backend/schemas/render.py`: `PreviewSubtitlesRequest` (L73-81).
- `backend/routers/render.py`: `POST /api/preview-subtitles` (`preview_clip_subtitles` L285-292; 422 rentang tidak valid, 500 dengan detail error).
- `src/types.ts`: `SubtitlePreviewEvent`, `SubtitlePreviewResponse`.
- `src/utils/subtitlePreview.ts` (baru): `fetchSubtitlePreview`, `findActiveSubtitleEvent`, `groupSubtitleChunks`, `subtitlePreviewSignature`, `SUBTITLE_HIGHLIGHT_COLORS`.
- `src/components/ClipStudioSection.tsx`: prop `transcript`, tipe `SubtitlePreviewEntry`, state + `requestSubtitlePreview` + hitung ulang otomatis (L532-564), overlay subtitle asli (L4194-4207), kartu "Subtitle asli (pratinjau)" (L4378-4433).
- `src/App.tsx` (+1): `transcript={result.transcript}` ke `ClipStudioSection`.
- `src/locales/id.ts`, `src/locales/en.ts`: 9 kunci baru di `studio`.
- `scripts/smoke_test.py`: `run_subtitle_preview_check` (cek 17). `CLAUDE.md`: deskripsi smoke test.
HASIL_TEST:
- `npm run build`: lulus (hanya peringatan ukuran chunk lama).
- Lint: 6 file frontend total 59 masalah, isi aturan identik dengan sebelum task (dibandingkan dengan `git stash`, `diff` kosong); `src/utils/subtitlePreview.ts` bersih. Catatan: versi awal memakai `try/catch` di `useCallback` async sehingga React Compiler berhenti menganalisis komponen dan hitungan lint turun palsu (59 -> 55); diganti `.then/.catch` hingga identik lagi.
- `.ass` identik: `generate_ass_file` versi `HEAD` vs baru pada 400 masukan acak (gaya, `text_case`, rasio, judul, kamus, jeda, tanda baca, kata kosong/tag/backslash, urutan acak): 0 perbedaan. Smoke menyimpan hash baris `Dialogue` dari kode sebelum task sebagai acuan.
- Smoke test: 17/17 lulus, exit 0, termasuk "[PASS] pratinjau subtitle (#36a): event = baris Dialogue di 3 gaya, hash acuan sama, endpoint whisper/cache/text_case/fallback transkrip/422, segmen dihapus".
- `check_codemap.py`: SEMUA CEK LULUS (17 catatan, 267 simbol).
- Uji endpoint (TestClient, video sintetis senyap): Whisper sungguhan tidak menemukan ucapan, sumber jatuh ke transkrip, kamus terpakai, panggilan kedua `cached` 0 s, rentang kosong 422, tanpa file `preview_*` tertinggal.
- Uji browser (`npm run dev`, video upload sementara berisi ucapan TTS Windows 18 s, data riwayat disuntikkan lalu dihapus): "Buat subtitle" -> 12 baris dari Whisper dalam ±8 s; klik baris "MY YOUTUBE CHANNEL" melompat ke sana dan overlay menampilkan teks itu dengan kata aktif "MY" kuning; kamus `youtube -> YT` dan huruf kecil diperbarui lewat cache (0 s, tanpa Whisper); klip dengan rentang lain berstatus "belum dibuat" dan menampilkan contoh gaya; video yang tidak ada menampilkan pesan gagal tanpa merusak pratinjau; teks en benar. Video uji, data uji, dan `.claude/launch.json` dikembalikan.
CODEMAP_DIPERBARUI: ya. `subtitle-dan-judul.md` (`build_subtitle_events`, `generate_ass_file`, 3 fungsi layanan pratinjau, risiko Whisper ganda), `render-server.md` (route, `PreviewSubtitlesRequest`, `resolve_source_url`), `clip-studio.md` (state, overlay, kartu, util, input `transcript`, risiko), `arsitektur-backend.md` (endpoint), `frontend-app.md` (tipe, prop); rentang bergeser di `face-tracking.md` (dipetakan ulang dengan difflib).
CATATAN:
- Keputusan sendiri: kartu pratinjau di bawah kontrol pemutar (hanya saat subtitle aktif); daftar potongan bisa diklik untuk seek; event dihitung ulang otomatis 400 ms setelah kamus/`text_case` berubah; `source` ditentukan dengan memanggil Whisper dulu lalu fallback transkrip (path kosong) sehingga sumber tercatat jujur; `resolve_source_url` diekstrak untuk dipakai bersama (`process_batch_retry` tetap memakai salinan lamanya, tidak diubah); detail error backend tanpa prefiks ganda.
- Risiko: render belum memakai ulang segmen/kata pratinjau, jadi Whisper berjalan dua kali dan hasil bisa sedikit berbeda bila Whisper tidak deterministik (#36b akan memakai kata pratinjau). Pratinjau menunggu bila render berjalan (`_RENDER_SEMAPHORE`). Cache kata hanya di memori; hasil di UI hilang saat muat ulang. Pratinjau tidak meniru outline/ukuran libass piksel per piksel.
- Saat uji, `uvicorn --reload` tidak selesai memuat ulang setelah `render.py` disimpan (proses lama tetap melayani) sampai server dinyalakan ulang; jebakan lama #4, bukan karena task ini.
- Perlu dicek pemilik: di video nyata (YouTube dan upload), "Buat subtitle" lalu render klip yang sama dan bandingkan teks pratinjau dengan video hasil; coba trim klip lewat trimmer dan pastikan subtitle lama tidak dipakai.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
