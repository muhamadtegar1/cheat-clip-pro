# CHEAT-36b: Sunting subtitle per klip dan render memakai kata pratinjau
Status: REVIEW
Risiko: sedang (render tidak lagi menjalankan Whisper untuk klip yang punya kata pratinjau; `build_subtitle_events` mendapat mode potongan manual tanpa mengubah hasil lama; tanpa perubahan prompt AI)

## Tujuan
Kata subtitle yang terlihat (dan disunting) di pratinjau Clip Studio dibakar persis sama ke video hasil render, mode separate dan merged, tanpa Whisper dijalankan lagi.

## Latar belakang
Uji pemilik 2026-10-19 (`clip_1_batch_1792356132_4a8d32.mp4`, 24,6 s): sekitar separuh baris berbeda antara pratinjau #36a dan render, karena keduanya mengunduh segmen dan menjalankan Whisper `base` sendiri-sendiri. Pemotongan (`build_subtitle_events`) sudah identik; yang berbeda adalah kata dan waktu dari Whisper.

## Kondisi sekarang (diverifikasi di kode)
- Render separate: `render_single_batch_clip` memanggil `transcribe_clip_words` (`backend/services/render_service.py` L153-162), lalu `generate_ass_file`.
- Render merged: `render_merged_batch_clips` memanggil `transcribe_clip_words` per segmen lalu menggeser waktunya (L392-416).
- `RenderBatchRequest.clips` adalah `List[Dict]` mentah (`backend/schemas/render.py` L64-70) dan disimpan di `BATCH_REQUESTS`, jadi `process_batch_retry` memakai dict klip yang sama.
- Frontend: `handleLaunch` (`src/components/ClipStudioSection.tsx` L1570-1582) sudah menyisipkan judul kustom per klip berdasarkan kunci `start_end`, lalu `App.tsx` meneruskan `clips` apa adanya ke `/api/render-batch`.
- Pratinjau #36a menyimpan hasil per kunci `start_end` (state `subtitlePreviews`, L532-564) berisi `words` mentah dan `events`; kartu pratinjau ada di L4379-4434.
- `build_subtitle_events` (`backend/video_engine.py` L1737-1842) memotong otomatis di langkah B (L1766-1785): maks 3 kata, 22 karakter, jeda >= 0.38 s, akhir kalimat.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Render memakai kata pratinjau**: setiap klip yang punya hasil pratinjau `ready` dikirim dengan field `subtitle_words` (`[{word, start, end, group?}]`, waktu relatif awal klip) lewat `handleLaunch`. Backend: bila `subtitle_words` ada (termasuk list kosong = tanpa subtitle), Whisper dilewati dan kata itu yang dipakai. Klip tanpa pratinjau tetap Whisper seperti sekarang. Berlaku juga untuk klip yang belum disunting, sehingga perbedaan seperti uji 2026-10-19 hilang.
2. **Validasi di backend** (helper baru di `render_service.py`): list maks 3000 kata, `word` string maks 60 karakter, `start`/`end` angka berhingga dengan `0 <= start <= end <= durasi klip + 1`, `group` bilangan bulat opsional. Bila tidak valid, klip gagal dengan pesan jelas (tidak diam-diam kembali ke Whisper).
3. **Potongan manual**: `build_subtitle_events` menerima kata dengan `group`. Bila **semua** kata punya `group`, langkah B memotong per `group` berurutan (tanpa aturan otomatis); langkah A, C, D tetap. Tanpa `group`, hasilnya identik dengan sekarang (hash acuan smoke #36a tetap sama). Event mendapat field tambahan `indices` (indeks kata masukan dalam potongan) agar UI bisa memetakan baris ke kata.
4. **Pratinjau dari kata suntingan**: `PreviewSubtitlesRequest` mendapat field opsional `words`. Bila diisi, endpoint tidak mengunduh atau menjalankan Whisper, hanya `build_subtitle_events` (`source: "edited"`), sehingga pratinjau suntingan memakai logika potongan yang sama dengan render.
5. **UI sunting di kartu pratinjau**: tombol "Sunting" mengubah daftar baris menjadi input teks per baris dengan aksi:
   - ketik ulang: kata baru dipecah per spasi; bila jumlah kata sama, waktu tiap kata dipertahankan; bila berbeda, rentang baris (awal kata pertama s.d. akhir kata terakhir) dibagi rata;
   - hapus baris: kata-katanya dibuang;
   - pecah baris: dipecah di batas kata (posisi kursor, atau tengah bila kursor di ujung);
   - gabung dengan baris berikutnya.
   Setelah sunting pertama, semua kata mendapat `group` sesuai baris. Ada tombol "Kembalikan ke hasil Whisper" dan penanda "disunting". Baris > 22 karakter diberi peringatan (render memakai `\q2`, teks tidak dibungkus dan bisa terpotong di tepi). "Buat ulang" pada klip yang sudah disunting meminta konfirmasi karena suntingan akan hilang.
6. Kamus #11 dan `text_case` tetap diterapkan di atas kata suntingan, saat pratinjau dan render, lewat `build_subtitle_events`.

## Area yang boleh disentuh
- `backend/video_engine.py`: `build_subtitle_events` (L1737-1842): dukungan `group` di langkah B dan field `indices` di event. `generate_ass_file` tidak diubah.
- `backend/services/render_service.py`: helper validasi `subtitle_words` (baru); pemakaian di `render_single_batch_clip` (L153-162) dan `render_merged_batch_clips` (L392-416). Alur render lain tidak diubah.
- `backend/schemas/render.py`: field `words` di `PreviewSubtitlesRequest` (L73-83).
- `backend/services/subtitle_preview_service.py`: `preview_subtitles` (L84-99) melewati `_load_words` bila `words` diisi.
- `src/types.ts`: `subtitle_words?` di `ViralClip`, `source: 'edited'`, `indices` di `SubtitlePreviewEvent`, tipe kata subtitle.
- `src/utils/subtitlePreview.ts`: kirim `words`; fungsi murni sunting (baris dari event, ketik ulang, hapus, pecah, gabung, ke daftar kata ber-`group`).
- `src/components/ClipStudioSection.tsx`: state suntingan per kunci klip, UI sunting di kartu pratinjau (L4379-4434), `handleLaunch` (L1570-1582) menyisipkan `subtitle_words`.
- `src/locales/id.ts`, `src/locales/en.ts`: string baru.
- `scripts/smoke_test.py`: cek baru #36b; `CLAUDE.md`: kalimat deskripsi smoke test.
- `docs/codemap/`: `subtitle-dan-judul.md`, `render-server.md`, `clip-studio.md`, `frontend-app.md` (tipe), rentang yang bergeser; `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- `src/App.tsx` (tidak perlu: `clips` sudah diteruskan apa adanya).
- Mengganti model Whisper atau mengunci bahasa (kandidat task terpisah).
- Render browser (`browser_wasm`/client), judul, prompt AI, `ClipStudioModal.tsx`.
- Menyimpan suntingan permanen (`localStorage`/file); suntingan hilang saat halaman dimuat ulang.
- Menyunting waktu kata secara manual (geser awal/akhir) dan menyeret kata antar baris.
- Mengubah `clean_caption_text` (mis. tanda hubung pada "laki-laki" tetap dibuang seperti sekarang).
- Memakai ulang file segmen pratinjau saat render (render tetap mengunduh segmen untuk video).

## Keputusan yang boleh diambil AI sendiri
- Tata letak, ikon, dan teks tombol sunting selama ringkas; cara memilih titik pecah.
- Batas validasi yang lebih ketat bila beralasan, nama helper dan field turunan.
- Debounce pratinjau setelah sunting.
- Penanda di UI/log bahwa klip dirender dari kata pratinjau.

## Kriteria selesai (ya/tidak)
- [x] Klip yang punya hasil pratinjau (disunting atau tidak) dirender tanpa memanggil `transcribe_clip_words`, dan baris `Dialogue` di `.ass` sama dengan event pratinjau untuk kata, kamus, dan `text_case` yang sama; mode separate dan merged (merged: kata tiap segmen digeser seperti sekarang).
- [x] Klip tanpa hasil pratinjau tetap memakai Whisper seperti sekarang; retry batch memakai kata yang sama dengan render awal.
- [x] `subtitle_words: []` menghasilkan video tanpa subtitle (bukan Whisper); `subtitle_words` tidak valid membuat klip gagal dengan pesan jelas.
- [x] Di kartu pratinjau, baris bisa diketik ulang, dihapus, dipecah, dan digabung; waktu kata dipertahankan sesuai aturan di Desain; pratinjau overlay dan daftar baris langsung mengikuti suntingan; ada tombol kembalikan ke hasil Whisper.
- [x] Tanpa `group`, `build_subtitle_events` dan `generate_ass_file` menghasilkan keluaran identik dengan sebelum task (hash acuan smoke #36a tetap sama, dan dibandingkan dengan kode `HEAD` sebelum task); dengan `group`, potongan mengikuti `group`.
- [x] Semua string baru di `id.ts` dan `en.ts`; `npm run build` lulus; lint tanpa masalah baru; smoke test (dengan cek baru) dan `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `npm run build`, `npm run lint` (bandingkan jumlah masalah file yang diubah dengan sebelum task).
- `venv\Scripts\python.exe scripts\smoke_test.py` dengan cek baru: `build_subtitle_events` dengan `group`; render separate dengan `subtitle_words` (Whisper dipalsukan agar gagal bila dipanggil) dan `Dialogue` sama dengan event pratinjau; `[]` tanpa subtitle; masukan tidak valid gagal; merged 2 segmen dengan kata digeser benar.
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Bandingkan `generate_ass_file` versi `HEAD` dan versi baru untuk masukan acak tanpa `group`: harus identik.
- Uji browser dengan `npm run dev` dan video upload berisi ucapan: buat subtitle, sunting (ketik ulang, hapus, pecah, gabung), render, lalu periksa frame video hasil bahwa teksnya sama dengan pratinjau.
- Pemilik: ulangi uji 2026-10-19 (klip yang sama): buat subtitle, render tanpa sunting, bandingkan; lalu sunting beberapa baris, render lagi, bandingkan.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/video_engine.py`: `build_subtitle_events` (L1737-1854): `manual_groups` (L1758) bila semua kata punya `group` int, langkah B memotong per group (L1777-1783); event mendapat `indices` (L1852). `generate_ass_file` tidak diubah.
- `backend/services/render_service.py`: `clip_subtitle_words` (L57-93, validasi), `_with_groups` (L96-118, group otomatis per segmen untuk merged); `render_single_batch_clip` memvalidasi sebelum unduh (L151) dan memakai kata pratinjau tanpa Whisper (L233-237); `render_merged_batch_clips` memvalidasi semua segmen di awal (L424), segmen dengan kata pratinjau tanpa Whisper (L495), group digeser per segmen bila ada segmen bergroup (L488, L506).
- `backend/schemas/render.py`: field `words` di `PreviewSubtitlesRequest` (maks 3000).
- `backend/services/subtitle_preview_service.py`: `preview_subtitles` dengan `words` = tanpa unduh/Whisper, divalidasi `clip_subtitle_words` (ValueError -> 422), `source: "edited"`.
- `src/types.ts`: `SubtitleWord`, `ViralClip.subtitle_words`, `SubtitlePreviewEvent.indices`, `source: 'edited'`.
- `src/utils/subtitlePreview.ts`: `words` di request; `SubtitleLine`, `SUBTITLE_LINE_MAX_CHARS`, `subtitleLineText`, `linesFromPreview`, `linesToWords`, `retypeLine`, `wordsBeforeCursor`, `splitLine`, `mergeLines`.
- `src/components/ClipStudioSection.tsx`: `SubtitlePreviewEntry` (`whisperWords`, `whisperSource`, `editedWords`), `requestSubtitlePreview(clip, {force, words, edited})`, hitung ulang kamus/`text_case` mengirim kata yang ada, state dan aksi sunting (L601-654), kartu dengan mode sunting (L4474-4594), `handleLaunch` menyisipkan `subtitle_words` (L1674).
- `src/locales/id.ts`, `src/locales/en.ts`: 11 kunci baru di `studio`.
- `scripts/smoke_test.py`: `run_subtitle_edit_check` (cek 18). `CLAUDE.md`: deskripsi smoke test.
- `src/App.tsx` tidak diubah (sesuai kontrak).
HASIL_TEST:
- `npm run build`: lulus (`built in 744ms`, hanya peringatan ukuran chunk lama).
- Lint: `ClipStudioSection.tsx` 32 masalah, daftar aturan + pesan identik dengan `HEAD` (dibandingkan lewat stdin, `diff` kosong); `subtitlePreview.ts`, `types.ts`, locale: 0.
- Smoke test: 18/18 lulus, exit 0, termasuk `[PASS] subtitle suntingan dipakai render (#36b): pratinjau suntingan (group, 422), separate/retry tanpa Whisper dan Dialogue = pratinjau, tanpa pratinjau tetap Whisper, [] tanpa subtitle, tidak valid gagal jelas, merged per segmen`. Hash acuan #36a tetap sama. Baris log `ERROR ... smoke36b: encode dilewati` disengaja (cek memalsukan `render_clip_to_mp4` agar berhenti setelah `.ass` dibuat).
- `.ass` identik tanpa `group`: `generate_ass_file` versi `HEAD` vs baru pada 500 masukan acak (7 gaya, 3 rasio, 4 `text_case`, judul, kamus, kata kosong/tag/backslash, urutan acak): `diff= 0`.
- `check_codemap.py`: SEMUA CEK LULUS (17 catatan, 269 simbol).
- Uji browser (backend + frontend lewat preview, sumber `D:\CheatClip\clip_1_batch_1792356132_4a8d32.mp4` hanya dibaca, entri riwayat disuntikkan ke `localStorage` lalu dihapus): "Buat subtitle" -> 58 kata Whisper, 25 baris. Ketik ulang 3 -> 4 kata (waktu dibagi rata), pecah di kursor ("kadang kadang" / "pengganti"), gabung (peringatan 26 karakter tampil), hapus baris: semua berhasil, status "Disunting", overlay menampilkan baris suntingan dengan kata aktif kuning. Batal pada konfirmasi "Buat ulang" tidak mengubah apa pun; "Kembalikan" memulihkan 25 baris Whisper. Log backend: Whisper hanya sekali sepanjang uji. Permintaan `/api/render-batch` dicegat di browser (tidak ada render ke `EXPORTS_DIR`): klip membawa 58 `subtitle_words` dalam 24 group, `text_case` dan gaya sesuai. Teks en dicek. `.claude/launch.json` dikembalikan, tanpa file `preview_*` tertinggal.
CODEMAP_DIPERBARUI: ya. `subtitle-dan-judul.md` (`build_subtitle_events` group/indices, `preview_subtitles` words, baris baru `clip_subtitle_words` dan `_with_groups`, langkah render separate/merged, risiko diperbarui), `render-server.md` (`render_single_batch_clip`), `clip-studio.md` (`handleLaunch`, state sunting, kartu, util sunting, risiko), `frontend-app.md` (tipe); rentang bergeser di `face-tracking.md`, `clip-studio.md`, `render-server.md` (dipetakan ulang dengan difflib dari `HEAD`).
CATATAN:
- Keputusan sendiri: batas waktu kata saat validasi `durasi + 60` s, bukan `durasi + 1` seperti di Desain, karena kata fallback transkrip analisis bisa melewati akhir klip (baris disebar rata) dan dengan `+1` render untuk pratinjau sah akan gagal. Tetap menolak waktu negatif, `start > end`, NaN/inf, dan nilai tidak wajar.
- Keputusan sendiri: merged dengan sebagian segmen bergroup memotong semua segmen per segmen (`_with_groups`), jadi potongan yang dulu bisa menyambung melewati batas segmen tidak terjadi bila ada segmen yang disunting. Tanpa segmen bergroup, perilaku merged sama dengan sebelumnya.
- Keputusan sendiri: hitung ulang otomatis karena kamus/`text_case` kini mengirim kata yang sudah ada (bukan mengandalkan cache backend), sehingga restart backend tidak memicu Whisper baru yang hasilnya berbeda. "Kembalikan" mengirim kata Whisper yang tersimpan di frontend, bukan Whisper ulang.
- Keputusan sendiri: aksi pecah/gabung/hapus memakai `onMouseDown preventDefault` agar ketikan yang belum disimpan ikut diterapkan; input dan tombol dikunci selama permintaan berjalan (hindari balapan). Status saat disunting hanya "Disunting. Render memakai teks ini persis."
- Risiko: kata yang dibuang kamus/pembersih tidak masuk baris mana pun, jadi ikut terbuang saat baris disunting (bila kamus diubah lagi, kata itu tidak kembali). Suntingan hanya di state komponen, hilang saat halaman dimuat ulang. `clean_caption_text` tetap membuang tanda hubung ("laki-laki" -> "lakilaki"). Baris dari Whisper bisa sudah > 22 karakter (peringatan juga muncul untuk baris itu).
- Uji browser menunjukkan Whisper `base` memberi transkripsi ketiga yang berbeda lagi pada audio yang sama, mendukung alasan task ini; peningkatan model Whisper tetap kandidat task terpisah.
- Saat `/mulai`, #32 masih berstatus REVIEW (aturan no. 6); tidak disebut sebelum mulai, dicatat di sini.
- Perlu dicek pemilik: ulangi uji 2026-10-19 pada video nyata (YouTube dan upload): buat subtitle, render tanpa sunting, bandingkan teks video dengan pratinjau (harus sama persis); lalu sunting beberapa baris (ketik ulang, pecah, gabung, hapus), render lagi, bandingkan; coba juga mode merged dengan satu segmen disunting.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
