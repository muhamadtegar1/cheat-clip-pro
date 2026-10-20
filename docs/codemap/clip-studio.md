---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L312-5224 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L220 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L256-288 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L301-310 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1571-1641 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1686-1763 | Susun objek `RenderSettings` dan panggil `onStartRender`. #39: `audioLanguage` (L1731); kata pratinjau diambil dengan kunci bahasa (L1692). #36b: klip dengan pratinjau subtitle membawa `subtitle_words` (`editedWords ?? whisperWords`, L1693) |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1644-1684 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1338-1398 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1408-1454 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L745-830 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L444-454 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L489-519 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L1063-1088 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L1144-1168 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1205-1234 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L84-112 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1846-1984 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L2069-2478 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2479-3062 | Gaya, font, posisi subtitle, pilihan bahasa audio (#39, L2967-2991, state milik `App`), kamus koreksi kata (#11, L2993-3058, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L294-299 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L291 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L342-347 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L3063-3684 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3685-4002 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L4003-4070 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L4071-5104 | Kolom kanan, pratinjau 9:16. Overlay subtitle L4305-4401: event asli #36a (L4342-4355) atau contoh gaya; kartu "Subtitle asli (pratinjau)" L4526-4655 (tombol, status, daftar potongan yang bisa diklik untuk seek; #36b: tombol Sunting/Selesai, input per baris dengan pecah/gabung/hapus, peringatan > 22 karakter, tombol kembalikan ke hasil Whisper) |
| `src/components/ClipStudioSection.tsx` | state pratinjau subtitle | L562-681 | #36a: `subtitlePreviews` per kunci `start_end_bahasa` (`subtitlePreviewKey`, bahasa #39 ikut kunci; klip yang di-trim = kunci baru), `requestSubtitlePreview(clip, force)` (`force` saat hasil sudah ada = tombol "Buat ulang" menjalankan Whisper lagi; `.then/.catch`, bukan try/catch, agar React Compiler tetap menganalisis komponen), hitung ulang otomatis saat kamus #11/`text_case` berubah (`subtitleSignature`), `activeSubtitleEventIndex` dari `currentTime - clipStart`. Tipe `SubtitlePreviewEntry` L52-61. #36b (L615-679): `requestSubtitlePreview(clip, {force, words, edited})` (`words` diisi = backend tanpa Whisper; hitung ulang kamus/`text_case` juga mengirim kata yang ada), `whisperWords`/`whisperSource`/`editedWords` per klip, `subtitleEditMode`, `subtitleLines` dari `linesFromPreview`, aksi ketik ulang/pecah (posisi kursor di `subtitleCursorRef`)/gabung/hapus/kembalikan, `generateSubtitlePreview` (konfirmasi bila ada suntingan). #40: `editedWords` baru ditulis saat pratinjau sukses (`editedUpdate`), jadi pratinjau gagal tidak mengubah kata yang dipakai render; `rejectTooLongWord` + `subtitleEditError` menolak kata > 60 karakter di input sunting (blur/Enter: input kembali ke teks lama; pecah/gabung dengan ketikan tertunda dibatalkan), pesan `subtitlePreviewWordTooLong` di panel sunting |
| `src/utils/subtitlePreview.ts` | `fetchSubtitlePreview` | L74-103 | #36a: `POST /api/preview-subtitles`; #39: `audio_language` (L89, tidak dikirim bila `auto`), helper `AUDIO_LANGUAGE_OPTIONS`, `parseAudioLanguage`, `audioLanguageParam`, `subtitlePreviewKey` (L14-40); juga `SUBTITLE_HIGHLIGHT_COLORS` (L59, sama dengan `highlight_color` di `generate_ass_file`), `findActiveSubtitleEvent` (L106), `groupSubtitleChunks` (L114). #36b: fungsi murni sunting `linesFromPreview` (L155), `linesToWords` (L168), `retypeLine` (L177: jumlah kata sama = waktu dipertahankan, beda = rentang baris dibagi rata), `wordsBeforeCursor` (L193), `splitLine` (L197), `mergeLines` (L207), `SUBTITLE_LINE_MAX_CHARS` (L144). #40: `readStoredAudioLanguage`/`storeAudioLanguage` (L20-34, `localStorage` dibungkus try/catch di tingkat modul), `SUBTITLE_WORD_MAX_CHARS` (L147, sama dengan `render_service.SUBTITLE_WORD_MAX_CHARS`), `findTooLongWord` (L149) |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L5105-5167 | Tombol render, progres inline |
| `src/components/ClipStudioSection.tsx` | folder posting kit | L4891-4896 | #22: baris `postingKitSaved(batchProgress.kit_dir)` di bawah tombol ZIP, tampil bila backend mengisi `kit_dir` |
| `src/components/ClipTrimmerModal.tsx` | `ClipTrimmerModal` | L49-1601 | Atur ulang start/end klip dengan konteks ±120 s |
| `src/components/ClipTrimmerModal.tsx` | `handlePointerDown` | L426-532 | Drag handle start/end/playhead |
| `src/components/ClipTrimmerModal.tsx` | `getAdjustedClip` | L560-569 | Klip hasil trim (dikirim ke `handleApplyAdjustedClipToResults`) |
| `src/components/HeatmapTimeline.tsx` | `HeatmapTimeline` | L13-318 | Grafik retensi SVG, klik untuk seek |

## Input / output
- Input: `result.clips`, `markedClips`, `videoId`, `batchProgress`, `transcript` (#36a, fallback pratinjau subtitle), `audioLanguage` + `onAudioLanguageChange` (#39, satu state dengan form analisis) (props dari `App`).
- Output: objek `RenderSettings` (lihat `src/types.ts`) yang dipetakan ke `RenderSettingsModel` di [[render-server]].

## Risiko
- Pratinjau di browser meniru logika render server (posisi, wrap judul, ukuran font). Mengubah satu sisi tanpa sisi lain membuat pratinjau tidak sama dengan hasil ([[subtitle-dan-judul]]).
- Pratinjau subtitle asli (#36a) hanya meniru teks, potongan, waktu, dan warna sorot ASS; ukuran/outline libass tidak ditiru piksel per piksel. Hasil dan suntingan (#36b) disimpan di state komponen, hilang saat halaman dimuat ulang. Kata yang dibuang kamus/pembersih tidak masuk baris mana pun, jadi ikut terbuang saat baris disunting. Lihat [[subtitle-dan-judul]].
- Pratinjau memakai skala `320/1080` atau `320/1920` (asumsi kanvas tetap, lihat [[render-server]]).
- Pilihan encoder `browser_wasm` mengalihkan ke [[render-browser]] dengan fitur jauh lebih sedikit.
- `ClipStudioModal.tsx` adalah versi lama yang tidak dipakai. Edit `ClipStudioSection.tsx`.

## Terkait
[[index]] · [[frontend-app]] · [[render-server]] · [[render-browser]] · [[subtitle-dan-judul]] · [[face-tracking]]
