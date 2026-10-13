---
jenis: indeks
diverifikasi_pada_commit: 4b32420
---
# Codemap Cheat Clip PRO

Peta kode level fitur. Setiap catatan menyebut file, fungsi kunci beserta rentang baris, input/output, dan risiko.
Rentang baris diverifikasi terhadap kode pada commit `4b32420`. Kalau kamu mengubah kode di area sebuah catatan, perbarui rentang barisnya di catatan itu (aturan kerja no. 7 di `TASKS.md`).

Format baris tabel: `| file | simbol | Lawal-akhir | peran |`. Simbol dalam backtick adalah nama fungsi/kelas asli. Simbol tanpa backtick adalah label untuk potongan di dalam fungsi besar.

## Gambaran besar

```text
Browser (React, Vite :5173)                Backend (FastAPI, uvicorn :8000)
  App.tsx ──POST /api/analyze (SSE)──────▶  routers/analyze.py ─▶ youtube_service / gdrive_service / Whisper ─▶ Gemini
  ClipStudioSection ─POST /api/render-batch▶ routers/render.py ─▶ services/render_service.py ─▶ video_engine.py (yt-dlp + FFmpeg)
           ◀── SSE /api/render-progress ────
  clientRenderer.ts (FFmpeg WASM, opsional)  ◀─ /api/download-raw-clip (routers/downloads.py)
```

## Catatan

### Backend
- [[arsitektur-backend]]: startup, router, konfigurasi, folder kerja, variabel `.env`
- [[sumber-video]]: deteksi sumber YouTube / Google Drive / upload, metadata, heatmap
- [[transkrip]]: rantai fallback transkrip 7 tier, Supadata, Whisper, subtitle manual
- [[analisis-ai]]: pipeline `POST /api/analyze`, prompt Gemini, parsing, pasca-proses klip
- [[render-server]]: batch render, antrean, encoder, filtergraph FFmpeg, ZIP
- [[subtitle-dan-judul]]: transkripsi kata per kata, file `.ass` karaoke, overlay judul, font, watermark
- [[face-tracking]]: deteksi wajah pembicara dan saliency untuk crop vertikal
- [[unduhan-raw]]: unduh segmen/video asli lewat yt-dlp, format kualitas
- [[cookies-dan-proxy]]: cookies YouTube, proxy Webshare, anti bot
- [[penyimpanan-dan-cleanup]]: folder cache dan output permanen, auto-cleanup 1 jam, kuota 5 GB
- [[sistem-update]]: self-update (dimatikan di fork ini), restart, akses admin

### Frontend
- [[frontend-app]]: `App.tsx`, form analisis, riwayat/cache `localStorage`, player, daftar klip, ekspor
- [[clip-studio]]: pengaturan render, preferensi studio, peluncuran batch, trimmer, heatmap
- [[render-browser]]: render di browser dengan FFmpeg WebAssembly

### Pengujian
- [[golden-fixtures]]: alat ukur perubahan prompt AI dari 3 transkrip tersimpan (task 17b)

## Jebakan lintas fitur
- Hasil render permanen di `EXPORTS_DIR` (default `~/CheatClip`). Auto-cleanup hanya membersihkan folder cache. Lihat [[penyimpanan-dan-cleanup]].
- Kanvas 1080×1920 ditulis langsung (±80 literal) di `video_engine.py`. Lihat [[render-server]].
- Self-update `git pull` dimatikan lewat `SELF_UPDATE_DISABLED`. Lihat [[sistem-update]].
