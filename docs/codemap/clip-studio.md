---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L269-4874 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L177 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L213-245 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L258-267 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1404-1474 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1519-1591 | Susun objek `RenderSettings` dan panggil `onStartRender` |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1477-1517 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1171-1231 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1241-1287 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L578-663 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L398-408 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L443-473 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L896-921 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L977-1001 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1038-1067 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L41-69 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1674-1812 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L1897-2306 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2307-2864 | Gaya, font, posisi subtitle, kamus koreksi kata (#11, L2795-2860, hanya saat subtitle aktif) |
| `src/components/ClipStudioSection.tsx` | `sanitizeSubtitleReplacements` | L251-256 | #11: baris kamus yang dikirim ke render (trim, `from` satu kata 1-40, `to` maks 60, maks 100; batas di `SUBTITLE_REPLACEMENT_LIMITS` L248 sama dengan backend) |
| `src/components/ClipStudioSection.tsx` | state kamus koreksi | L296-301 | #11: `subtitleReplacements` (preferensi studio) + `activeSubtitleReplacements` yang dikirim di `handleLaunch` |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L2865-3486 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3487-3804 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L3805-3872 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L3873-4754 | Kolom kanan, pratinjau 9:16 |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L4755-4817 | Tombol render, progres inline |
| `src/components/ClipTrimmerModal.tsx` | `ClipTrimmerModal` | L49-1601 | Atur ulang start/end klip dengan konteks ±120 s |
| `src/components/ClipTrimmerModal.tsx` | `handlePointerDown` | L426-532 | Drag handle start/end/playhead |
| `src/components/ClipTrimmerModal.tsx` | `getAdjustedClip` | L560-569 | Klip hasil trim (dikirim ke `handleApplyAdjustedClipToResults`) |
| `src/components/HeatmapTimeline.tsx` | `HeatmapTimeline` | L13-318 | Grafik retensi SVG, klik untuk seek |

## Input / output
- Input: `result.clips`, `markedClips`, `videoId`, `batchProgress` (props dari `App`).
- Output: objek `RenderSettings` (lihat `src/types.ts`) yang dipetakan ke `RenderSettingsModel` di [[render-server]].

## Risiko
- Pratinjau di browser meniru logika render server (posisi, wrap judul, ukuran font). Mengubah satu sisi tanpa sisi lain membuat pratinjau tidak sama dengan hasil ([[subtitle-dan-judul]]).
- Pratinjau memakai skala `320/1080` atau `320/1920` (asumsi kanvas tetap, lihat [[render-server]]).
- Pilihan encoder `browser_wasm` mengalihkan ke [[render-browser]] dengan fitur jauh lebih sedikit.
- `ClipStudioModal.tsx` adalah versi lama yang tidak dipakai. Edit `ClipStudioSection.tsx`.

## Terkait
[[index]] · [[frontend-app]] · [[render-server]] · [[render-browser]] · [[subtitle-dan-judul]] · [[face-tracking]]
