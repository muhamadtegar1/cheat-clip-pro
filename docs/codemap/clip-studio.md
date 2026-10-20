---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L310-5194 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L218 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L254-286 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L299-308 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1557-1627 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1672-1749 | Susun objek `RenderSettings` dan panggil `onStartRender`. #39: `audioLanguage` (L1717); kata pratinjau diambil dengan kunci bahasa (L1678). #36b: klip dengan pratinjau subtitle membawa `subtitle_words` (`editedWords ?? whisperWords`, L1679) |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1630-1670 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1324-1384 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1394-1440 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L731-816 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L442-452 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L487-517 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L1049-1074 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L1130-1154 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1191-1220 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L82-110 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1832-1970 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L2055-2464 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2465-3048 | Gaya, font, posisi subtitle, pilihan bahasa audio (#39, L2953-2977, state milik `App`), kamus koreksi kata (#11, L2979-3044, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L292-297 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L289 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L340-345 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L3049-3670 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3671-3988 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L3989-4056 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L4057-5074 | Kolom kanan, pratinjau 9:16. Overlay subtitle L4291-4387: event asli #36a (L4328-4341) atau contoh gaya; kartu "Subtitle asli (pratinjau)" L4512-4632 (tombol, status, daftar potongan yang bisa diklik untuk seek; #36b: tombol Sunting/Selesai, input per baris dengan pecah/gabung/hapus, peringatan > 22 karakter, tombol kembalikan ke hasil Whisper) |
| `src/components/ClipStudioSection.tsx` | state pratinjau subtitle | L560-667 | #36a: `subtitlePreviews` per kunci `start_end_bahasa` (`subtitlePreviewKey`, bahasa #39 ikut kunci; klip yang di-trim = kunci baru), `requestSubtitlePreview(clip, force)` (`force` saat hasil sudah ada = tombol "Buat ulang" menjalankan Whisper lagi; `.then/.catch`, bukan try/catch, agar React Compiler tetap menganalisis komponen), hitung ulang otomatis saat kamus #11/`text_case` berubah (`subtitleSignature`), `activeSubtitleEventIndex` dari `currentTime - clipStart`. Tipe `SubtitlePreviewEntry` L50-59. #36b (L612-665): `requestSubtitlePreview(clip, {force, words, edited})` (`words` diisi = backend tanpa Whisper; hitung ulang kamus/`text_case` juga mengirim kata yang ada), `whisperWords`/`whisperSource`/`editedWords` per klip, `subtitleEditMode`, `subtitleLines` dari `linesFromPreview`, aksi ketik ulang/pecah (posisi kursor di `subtitleCursorRef`)/gabung/hapus/kembalikan, `generateSubtitlePreview` (konfirmasi bila ada suntingan) |
| `src/utils/subtitlePreview.ts` | `fetchSubtitlePreview` | L58-87 | #36a: `POST /api/preview-subtitles`; #39: `audio_language` (L73, tidak dikirim bila `auto`), helper `AUDIO_LANGUAGE_OPTIONS`, `parseAudioLanguage`, `audioLanguageParam`, `subtitlePreviewKey` (L14-24); juga `SUBTITLE_HIGHLIGHT_COLORS` (L43, sama dengan `highlight_color` di `generate_ass_file`), `findActiveSubtitleEvent` (L90), `groupSubtitleChunks` (L98). #36b: fungsi murni sunting `linesFromPreview` (L133), `linesToWords` (L146), `retypeLine` (L155: jumlah kata sama = waktu dipertahankan, beda = rentang baris dibagi rata), `wordsBeforeCursor` (L171), `splitLine` (L175), `mergeLines` (L185), `SUBTITLE_LINE_MAX_CHARS` (L128) |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L5075-5137 | Tombol render, progres inline |
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
