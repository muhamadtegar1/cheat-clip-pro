# CHEAT-11: Kamus koreksi subtitle sebelum render
Status: DONE
Risiko: rendah-sedang (mengubah teks subtitle di `generate_ass_file` yang dipakai semua render server; tanpa perubahan prompt AI)

## Tujuan
Pemilik bisa mengisi daftar koreksi kata subtitle ("salah → benar") di Clip Studio, dan setiap kata Whisper yang cocok tampil sebagai kata yang benar di video hasil render (mode separate dan merged).

## Kondisi sekarang (diverifikasi di kode)
- Kata subtitle dibuat saat render, bukan saat analisis: `render_service.py` memanggil `transcribe_clip_words` (Whisper per kata pada audio klip yang sudah dipotong, fallback ke transkrip) lalu `generate_ass_file` (mode separate L136-171, mode merged L433-460). Jadi teks Whisper belum ada sebelum render, dan pemilik tidak bisa menyunting kata per klip sebelum tombol render.
- `generate_ass_file` (`backend/video_engine.py` L1701-2073), langkah A subtitle (L1969-1981): tiap kata dibersihkan `clean_caption_text`, diberi kapitalisasi `apply_text_case`, lalu di-escape `escape_ass_text`.
- `RenderSettingsModel` (`backend/schemas/render.py` L4-53) belum punya field koreksi. Frontend memetakan `RenderSettings` (camelCase, `src/types.ts` L138-195) ke snake_case di `src/App.tsx` (body `POST /api/render-batch`, ±L471-530).
- Preferensi Clip Studio tersimpan di `localStorage` (`STUDIO_PREFS_KEY` L176, `DEFAULT_STUDIO_PREFS` L211-242, simpan L1384-1453, reset L1455-1494), `handleLaunch` L1496-1567, JSX kontrol subtitle L2283-2773.
- Render browser (`clientRenderer.ts`, encoder `browser_wasm`) tidak membuat subtitle Whisper, jadi tidak terdampak.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Kamus koreksi global**, bukan sunting per klip: daftar pasangan `{from, to}` yang berlaku untuk semua klip dalam render, disimpan di preferensi studio (`localStorage`) supaya kata yang sering salah (nama orang, nama channel, istilah, slang) cukup diisi sekali. Alasan: teks Whisper baru ada saat render, sedangkan sunting per klip butuh endpoint pratranskripsi baru (Whisper berat, berebut RAM dengan analisis), jauh di luar ukuran task kecil.
2. **Aturan cocok**: `from` satu kata, dicocokkan dengan kata Whisper yang sudah dibersihkan, tanpa membedakan huruf besar/kecil dan mengabaikan tanda baca di ujung (`.`, `,`, `?`). Tanda baca ujung kata asli dipertahankan. `to` boleh lebih dari satu kata (ditampilkan sebagai satu potongan dengan waktu kata asli) atau kosong (kata dihapus dari subtitle). Kapitalisasi akhir tetap mengikuti pengaturan `text_case` (mis. mode uppercase tetap huruf besar).
3. **Backend**: field baru `subtitle_replacements: Optional[List[{from, to}]]` di `RenderSettingsModel` (maks 100 pasangan, `from` 1-40 karakter tanpa spasi, `to` 0-60 karakter), parameter baru `word_replacements` di `generate_ass_file` yang diterapkan di langkah A sebelum `apply_text_case`, diteruskan dari kedua pemanggil di `render_service.py`. Tanpa field ini perilaku sama persis dengan sekarang.
4. **UI**: di grup kontrol subtitle Clip Studio, bagian "Koreksi kata subtitle" dengan baris `salah → benar` (tambah/hapus baris), jumlah koreksi aktif, dan petunjuk singkat. Baris dengan `from` kosong diabaikan saat render.
5. Tidak menyentuh analisis, transkrip, atau prompt.

## Area yang boleh disentuh
- `backend/schemas/render.py`: field `subtitle_replacements` + model kecil pasangan (±L4-53).
- `backend/video_engine.py`: parameter `word_replacements` di `generate_ass_file` (signature L1701-1724, langkah A L1969-1981) + helper kecil untuk menerapkan kamus (letak di dekat `clean_caption_text` L1132-1151 atau tepat sebelum `generate_ass_file`).
- `backend/services/render_service.py`: meneruskan `word_replacements=settings.subtitle_replacements` pada dua panggilan `generate_ass_file` (L148-171, L437-460).
- `src/types.ts`: tipe pasangan koreksi + field `subtitleReplacements` di `RenderSettings` (L138-195).
- `src/App.tsx`: satu field `subtitle_replacements` di body `POST /api/render-batch` (±L471-530).
- `src/components/ClipStudioSection.tsx`: state + preferensi (`StudioPreferences`, `DEFAULT_STUDIO_PREFS` L211-242, simpan L1384-1453, reset L1455-1494), `handleLaunch` L1496-1567, JSX di grup subtitle L2283-2773.
- `src/locales/id.ts`, `src/locales/en.ts`: string baru.
- `scripts/smoke_test.py`: satu cek baru (`generate_ass_file` dengan kamus: kata diganti, huruf besar/kecil, tanda baca ujung, `to` kosong menghapus kata, tanpa kamus hasil identik dengan sebelumnya). `CLAUDE.md`: kalimat deskripsi smoke test (#11).
- `docs/codemap/`: `subtitle-dan-judul.md`, `clip-studio.md`, `render-server.md` (bila rentang bergeser), `frontend-app.md` (bila rentang `App.tsx`/`types.ts` bergeser); `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Sunting teks subtitle per klip atau per kata dengan pratinjau transkrip Whisper sebelum render (butuh endpoint pratranskripsi; bisa jadi task lanjutan).
- Pencocokan frasa multi-kata di sisi `from`, regex, atau koreksi otomatis dengan AI.
- Mengubah Whisper, `transcribe_clip_words`, transkrip analisis, prompt AI, gaya/posisi/ukuran subtitle, judul, render browser (`clientRenderer.ts`), `ClipStudioModal.tsx`.
- Menyimpan kamus di backend/file permanen (cukup preferensi studio di `localStorage`).

## Keputusan yang boleh diambil AI sendiri
- Tata letak, teks, dan ikon kontrol kamus selama ringkas dan konsisten dengan grup subtitle.
- Nama helper, nama kunci locale, batas jumlah/panjang selama sesuai urutan besaran di Desain no. 3.
- Apakah baris kosong dibuang saat disimpan atau hanya saat render.
- Bila `to` berisi karakter yang dibuang `clean_caption_text` (mis. `-`), boleh dibersihkan dengan aturan yang sama demi konsistensi, asal dicatat.

## Kriteria selesai (ya/tidak)
- [x] Clip Studio punya kontrol kamus koreksi di grup subtitle (id dan en); isinya tersimpan di preferensi studio dan tetap ada setelah halaman dimuat ulang; reset ke default mengosongkannya.
- [x] Kamus terkirim ke backend lewat `subtitle_replacements` dan diterapkan di render server mode separate dan merged.
- [x] Kata yang dikoreksi muncul benar di file `.ass` dan video hasil render: cocok tanpa membedakan huruf besar/kecil, tanda baca ujung dipertahankan, `to` kosong menghapus kata, kapitalisasi mengikuti `text_case`.
- [x] Tanpa kamus (atau kamus kosong), file `.ass` yang dihasilkan identik dengan sebelum task.
- [x] Input tidak valid (`from` kosong/berspasi, terlalu panjang, terlalu banyak pasangan) ditolak 422 atau diabaikan dengan aman, render tidak gagal karenanya.
- [x] Semua string baru di `id.ts` dan `en.ts`; `npm run build` lulus; lint tanpa error baru; smoke test (dengan cek baru) dan `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `npm run build`, `npm run lint` (bandingkan jumlah masalah `ClipStudioSection.tsx` dan `App.tsx` dengan sebelum task).
- `venv\Scripts\python.exe scripts\smoke_test.py` (cek baru #11, termasuk render 1 klip yang sudah ada dengan kamus) dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- Uji browser dengan `npm run dev`: isi kamus, muat ulang (kamus tetap ada), reset (kamus kosong), cek payload `POST /api/render-batch` berisi `subtitle_replacements`, cek teks id dan en.
- Pemilik: render 1-2 klip nyata dengan kata yang sering salah ditangkap Whisper (mis. nama orang/channel), pastikan subtitle di video hasil sudah benar, di mode separate dan merged.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/schemas/render.py`: model `SubtitleReplacement` (L5-8, `from` lewat alias, 1-40 karakter tanpa spasi; `to` 0-60) dan `RenderSettingsModel.subtitle_replacements` (L38, maks 100).
- `backend/video_engine.py`: `build_word_replacement_map` (L1704-1720), `apply_word_replacement` (L1723-1734), parameter `word_replacements` di `generate_ass_file` (L1737-2113), diterapkan di langkah A subtitle (L2008-2012) sebelum `apply_text_case`.
- `backend/services/render_service.py`: `word_replacements=settings.subtitle_replacements` di dua panggilan `generate_ass_file` (separate L171, merged L461).
- `src/types.ts`: `SubtitleReplacement`, `RenderSettings.subtitleReplacements`.
- `src/App.tsx` (+1): `subtitle_replacements` di body `POST /api/render-batch` (L498), hanya bila kamus tidak kosong.
- `src/components/ClipStudioSection.tsx`: `SUBTITLE_REPLACEMENT_LIMITS` + `sanitizeSubtitleReplacements` (L248-256), state `subtitleReplacements`/`activeSubtitleReplacements` (L296-301), preferensi studio (tipe, default, simpan, reset), `handleLaunch`, JSX kamus di grup subtitle (L2795-2860, hanya saat subtitle aktif).
- `src/locales/id.ts`, `src/locales/en.ts`: 8 kunci baru di `studio`.
- `scripts/smoke_test.py`: `run_subtitle_fix_check` (cek 16). `CLAUDE.md`: deskripsi smoke test.
HASIL_TEST:
- `npm run build`: lulus (hanya peringatan ukuran chunk lama).
- Lint: 5 file frontend yang diubah total 59 masalah, sama dengan sebelum task (dibandingkan dengan `git stash`); tidak ada masalah baru.
- Smoke test: 16/16 lulus, exit 0, termasuk "[PASS] koreksi subtitle (#11): tanpa kamus/kamus kosong identik, ganti kata + tanda baca ujung, hapus kata, uppercase, 5 input tidak valid ditolak".
- `check_codemap.py`: SEMUA CEK LULUS (17 catatan, 259 simbol).
- Uji render ujung ke ujung (skrip di scratchpad, `TestClient` + `/api/render-batch`, `EXPORTS_DIR` dialihkan ke folder sementara lalu dihapus; transkrip berisi "yutub" dan "eh", kamus `yutub -> YouTube`, `EH -> ""`): mode separate dan merged `completed`; file `.ass` dari kedua mode berisi "YouTube" dan tanpa "eh"; frame video hasil render menampilkan "datang di YouTube"; kamus `dua kata` di request ditolak 422.
- Uji browser (Vite, data riwayat contoh disuntikkan lalu dihapus): kontrol muncul di grup subtitle, baris `dua kata` bertanda merah, badge "1 aktif"; payload `POST /api/render-batch` (fetch dicegat) hanya berisi `[{"from":"yutub","to":"YouTube"}]`; muat ulang: baris pulih dari preferensi; "Reset ke Default": kamus kosong; teks en "Subtitle word fixes", "Wrong word", "+ Add fix" benar. Lebar halaman 1200 px pada jendela 1024 px sudah ada sebelum task (diukur dengan blok baru disembunyikan).
CODEMAP_DIPERBARUI: ya. `subtitle-dan-judul.md` (helper baru, `SubtitleReplacement`, risiko #11 diganti dengan perilaku kamus), `clip-studio.md` (`sanitizeSubtitleReplacements`, state kamus, JSX subtitle), `render-server.md` (`RenderSettingsModel`), `frontend-app.md` (payload render, tipe); rentang yang bergeser di `face-tracking.md`, `penyimpanan-dan-cleanup.md`, `pilihan-klip.md`, `sistem-update.md`, `sumber-video.md`, `unduhan-raw.md` (dipetakan ulang dengan difflib HEAD -> kerja).
CATATAN:
- Keputusan sendiri: kamus global (bukan per klip) sesuai Desain no. 1; baris tidak valid diabaikan saat dikirim (sanitasi frontend) dan juga ditolak 422 di backend bila tetap terkirim; pengganti ikut dibersihkan `clean_caption_text` (mis. `-` hilang) agar konsisten dengan kata Whisper; tanda baca ujung pengganti dibuang lalu diganti tanda baca kata asli; batas 100 pasangan, 40/60 karakter.
- Kata yang dihapus ikut membuang tanda baca ujungnya, sehingga pemotongan potongan subtitle (yang memisah di akhir kalimat) bisa sedikit bergeser.
- `from` hanya satu kata; frasa multi-kata dan sunting per klip belum didukung (di luar scope, kandidat task lanjutan).
- Render browser (`browser_wasm`) tidak membuat subtitle Whisper, jadi tidak memakai kamus.
- Perlu dicek pemilik: render 1-2 klip nyata dengan kata yang sering salah ditangkap Whisper (nama orang/channel), mode separate dan merged, lalu pastikan subtitle di video hasil sudah benar.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: commit `9454cf0` hanya menyentuh `backend/schemas/render.py`, `backend/video_engine.py`, `backend/services/render_service.py`, `src/types.ts`, `src/App.tsx` (+1 baris), `src/components/ClipStudioSection.tsx`, `src/locales/id.ts`, `src/locales/en.ts`, `scripts/smoke_test.py`, `CLAUDE.md` (kalimat smoke test), `docs/codemap/*`, kontrak ini. Semuanya ada di "Area yang boleh disentuh"; tidak ada refactor/format ulang, tidak ada rahasia.
- Kontrol kamus di grup subtitle (id/en): JSX `ClipStudioSection.tsx` L2795-2860 di dalam blok subtitle aktif, 8 kunci baru di `id.ts` dan `en.ts`; `subtitleReplacements` masuk `StudioPreferences`, `DEFAULT_STUDIO_PREFS` (`[]`), simpan ke `localStorage`, dimuat dari preferensi saat init, dan `handleResetToDefaults` mengembalikannya ke `[]`. Terpenuhi dari diff; tampilan dan muat ulang di browser perlu dicek pemilik.
- Terkirim dan diterapkan di kedua mode: `App.tsx` L498 mengirim `subtitle_replacements` (hanya bila tidak kosong), `render_service.py` meneruskan `word_replacements=settings.subtitle_replacements` di mode separate (L171) dan merged (L461). Retry batch memakai `BATCH_REQUESTS` yang sama, jadi kamus ikut.
- Aturan cocok: `apply_word_replacement` dipanggil di langkah A setelah `clean_caption_text` dan sebelum `apply_text_case`/`escape_ass_text` (`video_engine.py` L2008-2016). Probe sendiri: `yutub`/`YUTUB?`/`yutub...` -> `YouTube`/`YouTube?`/`YouTube...`, `eh,` -> dihapus, `ehh` tidak berubah, `from` `...` diabaikan, pengganti `You-Tube` dibersihkan jadi `YouTube`. Smoke cek 16 juga membuktikan uppercase (`YOUTUBE,`).
- Tanpa kamus identik: `apply_word_replacement` langsung mengembalikan teks bila map kosong; smoke membandingkan isi `.ass` tanpa kamus, kamus `[]`, dan kamus tanpa kecocokan, ketiganya identik.
- Input tidak valid: `SubtitleReplacement` (`from` 1-40 karakter `^\S+$`, `to` <= 60) dan `max_length=100` menolak 5/5 kasus di smoke (422 di request); frontend `sanitizeSubtitleReplacements` juga membuang baris kosong/berspasi sebelum dikirim.
- Test yang saya jalankan: `smoke_test.py` 16/16 lulus ("SMOKE TEST LULUS"), `check_codemap.py` "SEMUA CEK LULUS" (17 catatan, 259 simbol), `npm run build` lulus, ESLint pada 5 file frontend yang diubah total 59 masalah (sama dengan angka sebelum task di laporan implementer) dan tidak ada satu pun di baris yang ditambahkan task ini.
- Codemap: `subtitle-dan-judul.md`, `clip-studio.md`, `render-server.md`, `frontend-app.md` memuat simbol/rentang baru; cek codemap lulus.
- Catatan kecil (tidak memblokir): (1) cek smoke #11 menguji `generate_ass_file` + `RenderSettingsModel`, bukan render penuh lewat `/api/render-batch` dengan kamus; jalur render hanya meneruskan satu argumen dan uji ujung ke ujung dilaporkan implementer, belum saya ulangi. (2) Bila `localStorage` berisi item kamus rusak (mis. `from` bukan string, hanya lewat edit manual), `pair.from.trim()` di JSX bisa melempar error; `getSavedStudioPreferences` hanya memeriksa `Array.isArray`.
- Perlu dicek pemilik: render 1-2 klip nyata dengan kata yang sering salah ditangkap Whisper, mode separate dan merged, pastikan subtitle di video hasil benar; isi kamus, muat ulang, dan reset di Clip Studio.
