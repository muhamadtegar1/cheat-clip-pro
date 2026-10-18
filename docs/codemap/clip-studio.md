---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L303-5156 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L211 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L247-279 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L292-301 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1546-1616 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1661-1737 | Susun objek `RenderSettings` dan panggil `onStartRender`. #36b: klip dengan pratinjau subtitle membawa `subtitle_words` (`editedWords ?? whisperWords`, L1674) |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1619-1659 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1313-1373 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1383-1429 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L720-805 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L433-443 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L478-508 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L1038-1063 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L1119-1143 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1180-1209 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L75-103 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1820-1958 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L2043-2452 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2453-3010 | Gaya, font, posisi subtitle, kamus koreksi kata (#11, L2941-3006, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L285-290 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L282 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L331-336 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L3011-3632 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3633-3950 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L3951-4018 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L4019-5036 | Kolom kanan, pratinjau 9:16. Overlay subtitle L4253-4349: event asli #36a (L4290-4303) atau contoh gaya; kartu "Subtitle asli (pratinjau)" L4474-4594 (tombol, status, daftar potongan yang bisa diklik untuk seek; #36b: tombol Sunting/Selesai, input per baris dengan pecah/gabung/hapus, peringatan > 22 karakter, tombol kembalikan ke hasil Whisper) |
| `src/components/ClipStudioSection.tsx` | state pratinjau subtitle | L551-656 | #36a: `subtitlePreviews` per kunci `start_end` (klip yang di-trim = kunci baru), `requestSubtitlePreview(clip, force)` (`force` saat hasil sudah ada = tombol "Buat ulang" menjalankan Whisper lagi; `.then/.catch`, bukan try/catch, agar React Compiler tetap menganalisis komponen), hitung ulang otomatis saat kamus #11/`text_case` berubah (`subtitleSignature`), `activeSubtitleEventIndex` dari `currentTime - clipStart`. Tipe `SubtitlePreviewEntry` L46-55. #36b (L601-654): `requestSubtitlePreview(clip, {force, words, edited})` (`words` diisi = backend tanpa Whisper; hitung ulang kamus/`text_case` juga mengirim kata yang ada), `whisperWords`/`whisperSource`/`editedWords` per klip, `subtitleEditMode`, `subtitleLines` dari `linesFromPreview`, aksi ketik ulang/pecah (posisi kursor di `subtitleCursorRef`)/gabung/hapus/kembalikan, `generateSubtitlePreview` (konfirmasi bila ada suntingan) |
| `src/utils/subtitlePreview.ts` | `fetchSubtitlePreview` | L44-72 | #36a: `POST /api/preview-subtitles`; juga `SUBTITLE_HIGHLIGHT_COLORS` (L29, sama dengan `highlight_color` di `generate_ass_file`), `findActiveSubtitleEvent` (L75), `groupSubtitleChunks` (L83). #36b: fungsi murni sunting `linesFromPreview` (L118), `linesToWords` (L131), `retypeLine` (L140: jumlah kata sama = waktu dipertahankan, beda = rentang baris dibagi rata), `wordsBeforeCursor` (L156), `splitLine` (L160), `mergeLines` (L170), `SUBTITLE_LINE_MAX_CHARS` (L113) |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L5037-5099 | Tombol render, progres inline |
| `src/components/ClipTrimmerModal.tsx` | `ClipTrimmerModal` | L49-1601 | Atur ulang start/end klip dengan konteks ±120 s |
| `src/components/ClipTrimmerModal.tsx` | `handlePointerDown` | L426-532 | Drag handle start/end/playhead |
| `src/components/ClipTrimmerModal.tsx` | `getAdjustedClip` | L560-569 | Klip hasil trim (dikirim ke `handleApplyAdjustedClipToResults`) |
| `src/components/HeatmapTimeline.tsx` | `HeatmapTimeline` | L13-318 | Grafik retensi SVG, klik untuk seek |

## Input / output
- Input: `result.clips`, `markedClips`, `videoId`, `batchProgress`, `transcript` (#36a, fallback pratinjau subtitle) (props dari `App`).
- Output: objek `RenderSettings` (lihat `src/types.ts`) yang dipetakan ke `RenderSettingsModel` di [[render-server]].

## Risiko
- Pratinjau di browser meniru logika render server (posisi, wrap judul, ukuran font). Mengubah satu sisi tanpa sisi lain membuat pratinjau tidak sama dengan hasil ([[subtitle-dan-judul]]).
- Pratinjau subtitle asli (#36a) hanya meniru teks, potongan, waktu, dan warna sorot ASS; ukuran/outline libass tidak ditiru piksel per piksel. Hasil dan suntingan (#36b) disimpan di state komponen, hilang saat halaman dimuat ulang. Kata yang dibuang kamus/pembersih tidak masuk baris mana pun, jadi ikut terbuang saat baris disunting. Lihat [[subtitle-dan-judul]].
- Pratinjau memakai skala `320/1080` atau `320/1920` (asumsi kanvas tetap, lihat [[render-server]]).
- Pilihan encoder `browser_wasm` mengalihkan ke [[render-browser]] dengan fitur jauh lebih sedikit.
- `ClipStudioModal.tsx` adalah versi lama yang tidak dipakai. Edit `ClipStudioSection.tsx`.

## Terkait
[[index]] · [[frontend-app]] · [[render-server]] · [[render-browser]] · [[subtitle-dan-judul]] · [[face-tracking]]
