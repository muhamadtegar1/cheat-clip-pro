---
fitur: render di browser (FFmpeg WebAssembly)
file_utama: [src/services/clientRenderer.ts, src/App.tsx]
---
# Render browser

Jalur render alternatif tanpa beban CPU server: browser mengambil segmen mentah dari backend (atau file upload lokal), lalu FFmpeg WASM melakukan crop/scale ke rasio target dan menghasilkan MP4 yang langsung diunduh. Aktif bila pengaturan encoder `browser_wasm` atau `renderEngine === 'client'`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/App.tsx` | cabang mode browser di `handleStartBatchRender` | L303-459 | Per klip: minta segmen raw, polling status, render WASM, unduh |
| `src/App.tsx` | ambil segmen raw | L347-398 | Upload: object URL lokal. YouTube: `POST /api/download-raw-clip` lalu polling `/api/download-raw-clip-status/{id}` |
| `src/services/clientRenderer.ts` | `getFFmpeg` | L24-71 | Muat core FFmpeg WASM dari CDN (unpkg, fallback jsDelivr) |
| `src/services/clientRenderer.ts` | `renderClipClientSide` | L77-174 | Potong + crop/scale/background, keluarkan `Blob` MP4 |
| `src/services/clientRenderer.ts` | `ClientRenderOptions` | L8-19 | Opsi render |
| `src/services/clientRenderer.ts` | `triggerBrowserDownload` | L179-188 | Simpan `Blob` sebagai file |

## Input / output
- Input: URL segmen dari [[unduhan-raw]] (atau object URL file upload + `startTime/endTime`), `aspectRatio`, `backgroundStyle`.
- Output: file MP4 diunduh langsung oleh browser. Hasil akhir tidak ditulis ke server, tetapi segmen raw dari `/api/download-raw-clip` tetap tersimpan di `backend/exports` (dan ikut cleanup, lihat [[penyimpanan-dan-cleanup]]).

## Risiko
- Fitur jauh lebih sedikit dari [[render-server]]: `renderClipClientSide` hanya memakai video, rentang waktu, rasio, dan background. `titleText` dan `subtitles` ada di opsi tetapi **tidak dipakai**. Tidak ada face tracking, watermark, BGM, atau SFX.
- Butuh internet untuk memuat core WASM dari CDN pada pemakaian pertama.
- Lambat dan boros RAM untuk klip panjang; berjalan di tab browser.

## Terkait
[[index]] · [[render-server]] · [[unduhan-raw]] · [[clip-studio]] · [[frontend-app]]
