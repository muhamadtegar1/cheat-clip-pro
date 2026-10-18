---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L284-4995 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L192 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L228-260 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L273-282 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1454-1524 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1569-1641 | Susun objek `RenderSettings` dan panggil `onStartRender` |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1527-1567 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1221-1281 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1291-1337 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L628-713 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L414-424 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L459-489 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L946-971 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L1027-1051 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1088-1117 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L56-84 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1724-1862 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L1947-2356 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2357-2914 | Gaya, font, posisi subtitle, kamus koreksi kata (#11, L2845-2910, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L266-271 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L263 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L312-317 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L2915-3536 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3537-3854 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L3855-3922 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L3923-4875 | Kolom kanan, pratinjau 9:16. Overlay subtitle L4157-4253: event asli #36a (L4194-4207) atau contoh gaya; kartu "Subtitle asli (pratinjau)" L4378-4433 (tombol, status, daftar potongan yang bisa diklik untuk seek) |
| `src/components/ClipStudioSection.tsx` | state pratinjau subtitle | L532-564 | #36a: `subtitlePreviews` per kunci `start_end` (klip yang di-trim = kunci baru), `requestSubtitlePreview` (`.then/.catch`, bukan try/catch, agar React Compiler tetap menganalisis komponen), hitung ulang otomatis saat kamus #11/`text_case` berubah (`subtitleSignature`), `activeSubtitleEventIndex` dari `currentTime - clipStart`. Tipe `SubtitlePreviewEntry` L36 |
| `src/utils/subtitlePreview.ts` | `fetchSubtitlePreview` | L39-65 | #36a: `POST /api/preview-subtitles`; juga `SUBTITLE_HIGHLIGHT_COLORS` (L24, sama dengan `highlight_color` di `generate_ass_file`), `findActiveSubtitleEvent` (L68), `groupSubtitleChunks` (L76) |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L4876-4938 | Tombol render, progres inline |
| `src/components/ClipTrimmerModal.tsx` | `ClipTrimmerModal` | L49-1601 | Atur ulang start/end klip dengan konteks ±120 s |
| `src/components/ClipTrimmerModal.tsx` | `handlePointerDown` | L426-532 | Drag handle start/end/playhead |
| `src/components/ClipTrimmerModal.tsx` | `getAdjustedClip` | L560-569 | Klip hasil trim (dikirim ke `handleApplyAdjustedClipToResults`) |
| `src/components/HeatmapTimeline.tsx` | `HeatmapTimeline` | L13-318 | Grafik retensi SVG, klik untuk seek |

## Input / output
- Input: `result.clips`, `markedClips`, `videoId`, `batchProgress`, `transcript` (#36a, fallback pratinjau subtitle) (props dari `App`).
- Output: objek `RenderSettings` (lihat `src/types.ts`) yang dipetakan ke `RenderSettingsModel` di [[render-server]].

## Risiko
- Pratinjau di browser meniru logika render server (posisi, wrap judul, ukuran font). Mengubah satu sisi tanpa sisi lain membuat pratinjau tidak sama dengan hasil ([[subtitle-dan-judul]]).
- Pratinjau subtitle asli (#36a) hanya meniru teks, potongan, waktu, dan warna sorot ASS; ukuran/outline libass tidak ditiru piksel per piksel. Hasil disimpan di state komponen, hilang saat halaman dimuat ulang. Lihat [[subtitle-dan-judul]].
- Pratinjau memakai skala `320/1080` atau `320/1920` (asumsi kanvas tetap, lihat [[render-server]]).
- Pilihan encoder `browser_wasm` mengalihkan ke [[render-browser]] dengan fitur jauh lebih sedikit.
- `ClipStudioModal.tsx` adalah versi lama yang tidak dipakai. Edit `ClipStudioSection.tsx`.

## Terkait
[[index]] · [[frontend-app]] · [[render-server]] · [[render-browser]] · [[subtitle-dan-judul]] · [[face-tracking]]
