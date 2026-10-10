---
fitur: Clip Studio, trimmer, heatmap timeline
file_utama: [src/components/ClipStudioSection.tsx, src/components/ClipTrimmerModal.tsx, src/components/HeatmapTimeline.tsx]
---
# Clip Studio

Panel pengaturan render di bawah hasil analisis (`ClipStudioSection`, ±4800 baris): rasio, background, face tracking, judul/hook, subtitle, BGM, SFX, watermark, encoder, nama file, mode separate/merged, dan daftar klip terpilih. Pratinjau langsung di kolom kanan. Tombol render memanggil `onStartRender` → `handleStartBatchRender` di [[frontend-app]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/components/ClipStudioSection.tsx` | `ClipStudioSection` | L255-4783 | Komponen utama |
| `src/components/ClipStudioSection.tsx` | `STUDIO_PREFS_KEY` | L176 | Key `localStorage` preferensi (`cheat_clip_studio_preferences`) |
| `src/components/ClipStudioSection.tsx` | `DEFAULT_STUDIO_PREFS` | L211-242 | Nilai default semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `getSavedStudioPreferences` | L244-253 | Baca preferensi tersimpan |
| `src/components/ClipStudioSection.tsx` | simpan preferensi | L1384-1453 | `useEffect` yang menulis preferensi tiap ada perubahan |
| `src/components/ClipStudioSection.tsx` | `handleLaunch` | L1496-1567 | Susun objek `RenderSettings` dan panggil `onStartRender` |
| `src/components/ClipStudioSection.tsx` | `handleResetToDefaults` | L1455-1494 | Reset semua pengaturan |
| `src/components/ClipStudioSection.tsx` | `formatTitleSmart` | L1151-1211 | Format judul untuk pratinjau (meniru `wrap_title_smart`) |
| `src/components/ClipStudioSection.tsx` | `getDefaultPositions` | L1221-1267 | Posisi default judul/subtitle per rasio |
| `src/components/ClipStudioSection.tsx` | `initPreviewPlayer` | L558-643 | Player pratinjau |
| `src/components/ClipStudioSection.tsx` | `fetchHardwareSupport` | L378-388 | `GET /api/hardware-accel` |
| `src/components/ClipStudioSection.tsx` | `handleUploadFont` | L423-453 | Upload font kustom |
| `src/components/ClipStudioSection.tsx` | `uploadBgmFile` | L876-901 | Upload BGM |
| `src/components/ClipStudioSection.tsx` | `uploadHookSfxFile` | L957-981 | Upload SFX hook |
| `src/components/ClipStudioSection.tsx` | `uploadWatermarkFile` | L1018-1047 | Upload watermark |
| `src/components/ClipStudioSection.tsx` | `getFriendlyErrorMessage` | L40-68 | Pesan error render yang ramah |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: rasio + face | L1650-1788 | Kanvas, background, centering |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: judul/hook | L1873-2282 | Banner judul, prefix/suffix |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: subtitle | L2283-2773 | Gaya, font, posisi subtitle (lokasi UI untuk task #11) |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: audio + watermark | L2774-3395 | BGM, SFX, voice boost, watermark |
| `src/components/ClipStudioSection.tsx` | JSX kontrol: encoder + nama file + mode | L3396-3713 | Akselerasi hardware, nama file, separate/merged |
| `src/components/ClipStudioSection.tsx` | JSX daftar klip terpilih | L3714-3781 | Checklist klip |
| `src/components/ClipStudioSection.tsx` | JSX pratinjau | L3782-4663 | Kolom kanan, pratinjau 9:16 |
| `src/components/ClipStudioSection.tsx` | JSX footer + progres batch | L4664-4726 | Tombol render, progres inline |
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
