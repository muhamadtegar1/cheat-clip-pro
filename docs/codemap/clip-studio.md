---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L316-5278 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L224 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L260-292 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L305-314 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1599-1669 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1714-1791 | Susun objek `RenderSettings` dan panggil `onStartRender`. #39: `audioLanguage` (L1759); kata pratinjau diambil dengan kunci bahasa (L1720). #36b: klip dengan pratinjau subtitle membawa `subtitle_words` (`editedWords ?? whisperWords`, L1721) |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1672-1712 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1366-1426 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1436-1482 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L770-856 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `startTracking` | L858-900 | Interval 150 ms: `currentTime`, berhenti/ulang di akhir klip. #41: interval dan `onStateChange` YouTube membaca `previewBoundsRef` (L705-708: awal, akhir, Loop terbaru), bukan closure saat dibuat, agar rentang hasil trimmer dan tombol Loop langsung berlaku |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L463-473 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L508-538 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L1091-1116 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L1172-1196 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1233-1262 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L88-116 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1874-2012 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L2097-2506 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2507-3090 | Gaya, font, posisi subtitle, pilihan bahasa audio (#39, L2995-3019, state milik `App`), kamus koreksi kata (#11, L3021-3086, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L298-303 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L295 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L348-353 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L3091-3712 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3713-4030 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L4031-4124 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L4125-5158 | Kolom kanan, pratinjau 9:16. Overlay subtitle L4359-4455: event asli #36a (L4396-4409) atau contoh gaya; kartu "Subtitle asli (pratinjau)" L4580-4709 (tombol, status, daftar potongan yang bisa diklik untuk seek; #36b: tombol Sunting/Selesai, input per baris dengan pecah/gabung/hapus, peringatan > 22 karakter, tombol kembalikan ke hasil Whisper) |
| `src/components/ClipStudioSection.tsx` | state pratinjau subtitle | L581-700 | #36a: `subtitlePreviews` per kunci `start_end_bahasa` (`subtitlePreviewKey`, bahasa #39 ikut kunci; klip yang di-trim = kunci baru), `requestSubtitlePreview(clip, force)` (`force` saat hasil sudah ada = tombol "Buat ulang" menjalankan Whisper lagi; `.then/.catch`, bukan try/catch, agar React Compiler tetap menganalisis komponen), hitung ulang otomatis saat kamus #11/`text_case` berubah (`subtitleSignature`), `activeSubtitleEventIndex` dari `currentTime - clipStart`. Tipe `SubtitlePreviewEntry` L52-61. #36b (L634-698): `requestSubtitlePreview(clip, {force, words, edited})` (`words` diisi = backend tanpa Whisper; hitung ulang kamus/`text_case` juga mengirim kata yang ada), `whisperWords`/`whisperSource`/`editedWords` per klip, `subtitleEditMode`, `subtitleLines` dari `linesFromPreview`, aksi ketik ulang/pecah (posisi kursor di `subtitleCursorRef`)/gabung/hapus/kembalikan, `generateSubtitlePreview` (konfirmasi bila ada suntingan). #40: `editedWords` baru ditulis saat pratinjau sukses (`editedUpdate`), jadi pratinjau gagal tidak mengubah kata yang dipakai render; `rejectTooLongWord` + `subtitleEditError` menolak kata > 60 karakter di input sunting (blur/Enter: input kembali ke teks lama; pecah/gabung dengan ketikan tertunda dibatalkan), pesan `subtitlePreviewWordTooLong` di panel sunting |
| `src/utils/subtitlePreview.ts` | `fetchSubtitlePreview` | L74-103 | #36a: `POST /api/preview-subtitles`; #39: `audio_language` (L89, tidak dikirim bila `auto`), helper `AUDIO_LANGUAGE_OPTIONS`, `parseAudioLanguage`, `audioLanguageParam`, `subtitlePreviewKey` (L14-40); juga `SUBTITLE_HIGHLIGHT_COLORS` (L59, sama dengan `highlight_color` di `generate_ass_file`), `findActiveSubtitleEvent` (L106), `groupSubtitleChunks` (L114). #36b: fungsi murni sunting `linesFromPreview` (L155), `linesToWords` (L168), `retypeLine` (L177: jumlah kata sama = waktu dipertahankan, beda = rentang baris dibagi rata), `wordsBeforeCursor` (L193), `splitLine` (L197), `mergeLines` (L207), `SUBTITLE_LINE_MAX_CHARS` (L144). #40: `readStoredAudioLanguage`/`storeAudioLanguage` (L20-34, `localStorage` dibungkus try/catch di tingkat modul), `SUBTITLE_WORD_MAX_CHARS` (L147, sama dengan `render_service.SUBTITLE_WORD_MAX_CHARS`), `findTooLongWord` (L149) |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L5159-5221 | Tombol render, progres inline |
| `src/components/ClipStudioSection.tsx` | folder posting kit | L4945-4950 | #22: baris `postingKitSaved(batchProgress.kit_dir)` di bawah tombol ZIP, tampil bila backend mengisi `kit_dir` |
| `src/components/ClipTrimmerModal.tsx` | `ClipTrimmerModal` | L51-1642 | Atur ulang start/end klip dengan konteks ±120 s |
| `src/components/ClipTrimmerModal.tsx` | `handlePointerDown` | L429-535 | Drag handle start/end/playhead |
| `src/components/ClipTrimmerModal.tsx` | `getAdjustedClip` | L563-572 | Klip hasil trim (dikirim ke `handleApplyAdjustedClipToResults`) |
| `src/components/ClipTrimmerModal.tsx` | `nudgeStart`/`nudgeEnd` | L538-549 | Geser awal/akhir (jarak minimal 3 s); tombol ±1 (#41), ±5, ±15, ±30 di L1295-1381 |
| `src/components/ClipTrimmerModal.tsx` | tombol Terapkan | L1571-1595 | #41: prop opsional `onApply` (L17) = terapkan rentang ke hasil tanpa unduh raw; tombol unduh raw tetap memanggil `onDownload` |
| `src/components/ClipStudioSection.tsx` | judul kustom ikut rentang baru | L354-367 | #41: `customClipTitles` dipindah dari kunci lama ke baru saat prop `clipRangeChange` berubah (pola sesuaikan state saat render, tanpa efek) |
| `src/components/ClipStudioSection.tsx` | tombol Sesuaikan durasi | L4092-4117 | #41: per klip di daftar klip terpilih, memanggil prop `onAdjustClip` (membuka trimmer milik `App`) |
| `src/components/HeatmapTimeline.tsx` | `HeatmapTimeline` | L13-318 | Grafik retensi SVG, klik untuk seek |

## Input / output
- Input: `result.clips`, `markedClips`, `videoId`, `batchProgress`, `transcript` (#36a, fallback pratinjau subtitle), `audioLanguage` + `onAudioLanguageChange` (#39, satu state dengan form analisis), `onAdjustClip` + `clipRangeChange` (#41) (props dari `App`).
- Output: objek `RenderSettings` (lihat `src/types.ts`) yang dipetakan ke `RenderSettingsModel` di [[render-server]].

## Risiko
- Pratinjau di browser meniru logika render server (posisi, wrap judul, ukuran font). Mengubah satu sisi tanpa sisi lain membuat pratinjau tidak sama dengan hasil ([[subtitle-dan-judul]]).
- Pratinjau subtitle asli (#36a) hanya meniru teks, potongan, waktu, dan warna sorot ASS; ukuran/outline libass tidak ditiru piksel per piksel. Hasil dan suntingan (#36b) disimpan di state komponen, hilang saat halaman dimuat ulang. Kata yang dibuang kamus/pembersih tidak masuk baris mana pun, jadi ikut terbuang saat baris disunting. Lihat [[subtitle-dan-judul]].
- Pratinjau memakai skala `320/1080` atau `320/1920` (asumsi kanvas tetap, lihat [[render-server]]).
- Pilihan encoder `browser_wasm` mengalihkan ke [[render-browser]] dengan fitur jauh lebih sedikit.
- `ClipStudioModal.tsx` adalah versi lama yang tidak dipakai. Edit `ClipStudioSection.tsx`.
- State per klip memakai kunci rentang `start_end` (tanda render, judul kustom, pratinjau subtitle, unduhan raw, pilihan Pakai/Lewati di backend). Trimmer #41 hanya memindahkan tanda render dan judul kustom; pratinjau/suntingan subtitle dan pilihan Pakai/Lewati tidak disalin ke rentang baru (subtitle harus dibuat ulang karena waktunya berubah). Rentang hasil trim tidak disimpan ke cache riwayat analisis: setelah muat ulang/riwayat, kembali ke rentang AI. Kolom judul di trimmer menampilkan `title_suggestion`, bukan judul kustom Clip Studio (judul kustom tetap menang saat render).

## Terkait
[[index]] · [[frontend-app]] · [[render-server]] · [[render-browser]] · [[subtitle-dan-judul]] · [[face-tracking]]
