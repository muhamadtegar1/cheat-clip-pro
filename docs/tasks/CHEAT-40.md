# CHEAT-40: Perbaikan kecil sisa review #39 dan #36b
Status: REVIEW

## Riwayat
- 2026-10-20: dibuat dari catatan review #39 dan #36b yang tercatat di baton ("perbaiki sekalian bila menyentuh area itu"). Pemilik meminta dikerjakan sekarang sebagai satu task kecil.

## Tujuan
Empat kekurangan kecil yang diketahui ditutup tanpa mengubah perilaku lain: bahasa audio tidak membuat app gagal saat `localStorage` diblokir, fallback Whisper YouTube dengan bahasa terpilih teruji di smoke test, render tidak memakai suntingan subtitle yang pratinjaunya gagal, dan kata lebih dari 60 karakter ditolak langsung di input sunting.

## Desain
1. **`localStorage` bahasa audio (#39)**: `src/utils/subtitlePreview.ts` mendapat `readStoredAudioLanguage()` dan `storeAudioLanguage(value)`, masing-masing dibungkus try/catch di tingkat modul (bukan di badan komponen, agar React Compiler tetap menganalisis `App`). Gagal baca = `auto`, gagal simpan = diabaikan (state tetap berubah). `src/App.tsx` memakai kedua helper itu.
2. **Fallback Whisper YouTube (#39)**: cek smoke baru (bukan mengubah cek #39 yang ada). Analisis URL YouTube dengan `fetch_video_metadata`, `fetch_transcript` (melempar), `download_youtube_audio_file`, `transcribe_local_video_file` dipalsukan di `analyze_mod`, Gemini palsu `rate_limit` agar alur berhenti setelah transkrip. Harap bahasa ke Whisper `[None, "en"]` untuk request tanpa bahasa dan `audio_language: "en"`.
3. **Suntingan dipakai walau pratinjau gagal (#36b catatan 2)**: `requestSubtitlePreview` tidak lagi menulis `editedWords` saat status `loading`; `editedWords` baru (atau dihapus untuk `edited: null`) hanya ditulis saat backend menjawab sukses. Gagal = `editedWords` tetap versi terakhir yang pratinjaunya berhasil, sama dengan yang tampil. Render (`handleLaunch`) tidak berubah.
4. **Batas 60 karakter per kata (#36b catatan 3)**: konstanta `SUBTITLE_WORD_MAX_CHARS = 60` (sama dengan `render_service.SUBTITLE_WORD_MAX_CHARS`) dan helper `findTooLongWord(text)` di `subtitlePreview.ts`. Ketik ulang baris (blur/Enter) dan ketikan tertunda saat pecah/gabung: kata > 60 karakter = suntingan baris itu tidak diterapkan, input dikembalikan ke teks lama, pesan galat tampil (string baru di `id.ts` dan `en.ts`). Pesan hilang saat suntingan berikutnya berhasil diterapkan.

## Area yang boleh disentuh
- `src/utils/subtitlePreview.ts`: helper baru di dekat `parseAudioLanguage` (L14-24) dan dekat `retypeLine` (L128-168).
- `src/App.tsx`: state `audioLanguage` (L123-128) saja.
- `src/components/ClipStudioSection.tsx`: `requestSubtitlePreview` (L568-601), aksi sunting (L617-660), input baris sunting dan pesan galatnya (sekitar L4543-4600).
- `src/locales/id.ts`, `src/locales/en.ts`: satu string galat kata terlalu panjang.
- `scripts/smoke_test.py`: satu cek baru #40 dan pemanggilannya; cek lama tidak diubah.
- `docs/codemap/clip-studio.md`, `frontend-app.md`, catatan lain yang rujukan barisnya bergeser. `CLAUDE.md` (deskripsi smoke test), `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- `localStorage` lain di `App.tsx` (model, durasi, jumlah klip, riwayat, dll.).
- Backend (`analyze.py`, `video_engine.py`, `render_service.py`, `subtitle_preview_service.py`), termasuk `normalize_audio_language` di luar try di `transcribe_clip_words`.
- Batas waktu kata `durasi + 60` (#36b catatan 1).
- Catatan kecil review #28 (`import threading`, kuota cleanup).
- Perilaku render, `handleLaunch`, tampilan pratinjau lain.

## Keputusan yang boleh diambil AI sendiri
- Nama helper dan nama kunci string locale, teks pesan galat.
- Letak pesan galat di panel sunting.
- Nama video ID palsu dan detail pemalsuan di smoke test.

## Kriteria selesai (ya/tidak)
- [x] `localStorage.getItem`/`setItem` yang melempar tidak membuat `App` gagal: bahasa jatuh ke Otomatis, ganti bahasa tetap mengubah state (dibuktikan di browser dengan `localStorage` dipaksa melempar, atau dari kode bila tidak bisa).
- [x] Smoke test: fallback Whisper YouTube meneruskan bahasa (`[None, "en"]`), tanpa jaringan.
- [x] Pratinjau suntingan yang gagal (mis. backend mati atau 422) tidak mengubah `editedWords`; render memakai kata yang sama dengan pratinjau terakhir yang tampil.
- [x] Kata > 60 karakter di input sunting ditolak di UI dengan pesan (id dan en), tanpa memanggil backend; kata ≤ 60 tetap diterima.
- [x] `npm run build` lulus, lint tidak menambah masalah di file yang disentuh, smoke test lulus, `check_codemap.py` lulus.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`, `npm run build`, `npm run lint`, `venv\Scripts\python.exe scripts\check_codemap.py`.
- Browser bawaan (`npm run dev`): buka hasil analisis (key `mock`), Clip Studio, buat pratinjau subtitle, sunting baris dengan kata 61 karakter (ditolak, pesan tampil), sunting baris biasa lalu matikan backend sebelum pratinjau selesai (atau paksa galat) dan pastikan `editedWords` tidak berubah. Paksa `localStorage` melempar lalu muat ulang.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `src/utils/subtitlePreview.ts`: `readStoredAudioLanguage`, `storeAudioLanguage` (L19-34, try/catch di tingkat modul), `SUBTITLE_WORD_MAX_CHARS = 60` dan `findTooLongWord` (L146-150).
- `src/App.tsx`: state `audioLanguage` (L124-128) memakai kedua helper; import disesuaikan. Jumlah baris tetap.
- `src/components/ClipStudioSection.tsx`: import 2 helper; `requestSubtitlePreview` (L570-604) tidak lagi menulis `editedWords` saat `loading`, `editedUpdate` ditulis di `.then` (sukses) saja; `rejectTooLongWord` + state `subtitleEditError` (L624-630), `applySubtitleLines` menghapus pesan, `subtitleLinesWithPending` mengembalikan `null` bila ketikan ditolak (pecah/gabung batal); `onBlur` input baris: kata > 60 = input kembali ke teks lama tanpa memanggil backend; pesan galat `role="alert"` di panel sunting.
- `src/locales/id.ts`, `en.ts`: `subtitlePreviewWordTooLong(n, max)`.
- `scripts/smoke_test.py`: `run_yt_whisper_language_check` (cek 12) dan pemanggilannya; cek lama tidak diubah.
- `CLAUDE.md` (deskripsi smoke), `docs/codemap/clip-studio.md`, `frontend-app.md`, `face-tracking.md` (rentang bergeser), `TASKS.md`, kontrak ini.
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: `22/22 cek lulus. SMOKE TEST LULUS`, termasuk `[PASS] fallback Whisper YouTube meneruskan bahasa (#40): tanpa bahasa = None, audio_language 'en' = 'en' di fallback Whisper`.
- `npm run build`: lulus (`built in 1.06s`, hanya peringatan ukuran chunk yang sudah ada).
- Lint (eslint JSON, sebelum lewat `git stash` vs sesudah): `App.tsx` 27 = 27, `ClipStudioSection.tsx` 32 = 32, aturan sama; `subtitlePreview.ts`, `id.ts`, `en.ts` 0.
- `venv\Scripts\python.exe scripts\check_codemap.py`: `SEMUA CEK LULUS` (284 simbol).
- Browser bawaan (`dev-backend` + `dev-frontend`): helper diuji dengan `Storage.prototype.getItem/setItem` dipaksa melempar `SecurityError`: baca = `auto`, simpan tidak melempar; storage normal: `id` terbaca, `en` tersimpan. `findTooLongWord`: 61 karakter = ditemukan, 60 = `null`.
- Uji UI Clip Studio (video sintetis 40 s di `uploads`, hasil analisis `mock` dimasukkan ke riwayat lalu Load Analysis): pratinjau klip 1 jalan (Whisper `small`). Sunting baris dengan kata 61 karakter + Enter = pesan "A word has 61 characters, max 60 per word..." tampil, input kembali ke "Miung", log backend tidak ada `POST /api/preview-subtitles` baru. Kata 60 karakter = diterima, pesan hilang, status "Edited". Lalu `fetch` ke `/api/preview-subtitles` dibuat gagal (simulasi backend mati) dan baris diketik ulang "kata gagal": galat pratinjau tampil, overlay tetap teks lama; render 1 klip (request `/api/render-batch` dicegat) mengirim `subtitle_words` = `["halo", "aaa…(60)"]`, yaitu pratinjau terakhir yang berhasil, bukan "kata gagal". Sebelum #40 render akan mengirim "kata gagal".
- File uji (video, riwayat `localStorage`) dihapus setelah uji.
CODEMAP_DIPERBARUI: ya. `clip-studio.md` (catatan #40 di state pratinjau subtitle dan `subtitlePreview.ts`, semua rentang `ClipStudioSection.tsx`/`subtitlePreview.ts` yang bergeser), `frontend-app.md` (state bahasa audio), `face-tracking.md` (`fetchFace` bergeser). Rentang digeser otomatis dari hunk `git diff`, lalu `check_codemap.py` lulus.
CATATAN:
- Kriteria storage diblokir dibuktikan pada helper, bukan pada seluruh `App`: `localStorage` lain di `App.tsx` (model, durasi, jumlah klip, riwayat) masih tanpa try/catch, jadi storage yang benar-benar diblokir tetap bisa menjatuhkan `App` lewat baris lain. Sesuai kontrak (di luar scope).
- Ditemukan (sudah ada sebelum #40, tidak diubah): setelah pratinjau suntingan gagal, input baris tetap menampilkan teks yang diketik (input tidak terkontrol, kunci baris tidak berubah) walau overlay dan render memakai teks lama. Pesan galat tampil, dan "Regenerate"/suntingan berikutnya menyamakan lagi. Kandidat perbaikan kecil bila menyentuh area ini.
- Tidak ada perubahan backend; batas 60 di UI disalin dari `render_service.SUBTITLE_WORD_MAX_CHARS` (dicatat di komentar dan codemap).

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
