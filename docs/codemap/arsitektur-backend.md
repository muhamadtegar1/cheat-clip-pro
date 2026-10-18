---
fitur: arsitektur backend
file_utama: [backend/main.py, backend/config.py, backend/video_engine.py, backend/routers/__init__.py]
---
# Arsitektur backend

FastAPI dengan 7 router modular. `backend/config.py` memuat `.env`, memperbaiki PATH, lalu mengimpor ulang konstanta dan fungsi dari `video_engine.py` supaya router/service cukup mengimpor dari `backend.config`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/main.py` | `background_storage_cleanup_worker` | L52-71 | Daemon cleanup: tunggu 15 detik, lalu tiap 30 menit. Lihat [[penyimpanan-dan-cleanup]] |
| `backend/main.py` | `lifespan` | L75-85 | Menyalakan daemon cleanup saat startup |
| `backend/main.py` | `add_security_headers` | L121-127 | Header keamanan di semua respons |
| `backend/main.py` | daftar router | L131-137 | analyze, render, media, cookies, downloads, system, choices (#35) |
| `backend/main.py` | mount SPA `dist/` | L144-158 | Kalau `dist/index.html` ada, backend juga menyajikan frontend hasil build |
| `backend/config.py` | `prepend_to_system_path` | L23-35 | Menambah folder Python/Scripts ke PATH |
| `backend/config.py` | muat `.env` | L44-48 | Urutan: `backend/.env`, `.env` root, lalu cwd |
| `backend/config.py` | impor ulang dari video_engine | L57-114 | Sumber tunggal `TEMP_DIR`, `EXPORTS_DIR`, fungsi render, dll. |
| `backend/video_engine.py` | konstanta folder | L21-26 | `temp_clips`, `EXPORTS_DIR` (env `CHEAT_CLIP_EXPORTS_DIR`, default `~/CheatClip`), `fonts`, `cookies.txt` |
| `backend/video_engine.py` | `ensure_ffmpeg_in_path` | L180-242 | Mencari FFmpeg (winget/brew), dipanggil saat impor (L245) |
| `backend/video_engine.py` | `get_preferred_video_encoder` | L331-346 | Dipanggil saat impor (L368), memilih encoder GPU/CPU. Lihat [[render-server]] |
| `backend/routers/__init__.py` | ekspor router | L1-17 | Nama router yang di-include `main.py` |
| `scripts/start-backend.js` | peluncur uvicorn | L244-260 | Mencari venv, menjalankan `uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` (hanya lokal, task #7) |

## Router dan endpoint

| Router | Endpoint utama | Catatan |
| --- | --- | --- |
| `backend/routers/analyze.py` | `POST /api/analyze` (SSE), `GET /api/health`, `GET /api/models` | [[analisis-ai]] |
| `backend/routers/render.py` | `POST /api/render-batch`, `GET /api/render-progress/{id}` (SSE), unduh hasil/ZIP, `POST /api/preview-subtitles` (#36a) | [[render-server]] |
| `backend/routers/media.py` | upload video/BGM/SFX/watermark/font, `GET /api/video/...`, `GET /api/detect-face` | [[sumber-video]], [[face-tracking]], [[subtitle-dan-judul]] |
| `backend/routers/cookies.py` | `POST/GET/DELETE /api/cookies` | [[cookies-dan-proxy]] |
| `backend/routers/downloads.py` | unduh video/segmen asli | [[unduhan-raw]] |
| `backend/routers/system.py` | storage, cleanup, versi, update, restart, `GET/PUT/DELETE /api/settings/gemini-key` | [[sistem-update]], [[penyimpanan-dan-cleanup]] |
| `backend/routers/choices.py` | `GET/PUT/DELETE /api/clip-choices`, `GET /api/clip-choices/export` | [[pilihan-klip]] (#35) |

## Input / output
- Input: request HTTP dari frontend (proxy Vite `/api` → `127.0.0.1:8000`, lihat `vite.config.ts`), variabel `.env`.
- Output: JSON, SSE (`backend/utils/sse.py` `_sse` L3-5), file media.

## Variabel `.env` yang dibaca
`GEMINI_API_KEY` (ditulis UI ke `backend/.env`), `CHEAT_CLIP_EXPORTS_DIR`, `SUPADATA_API_KEY(S)`, `WEBSHARE_*`, `PROXY_URL`, `HTTP(S)_PROXY`, `TEMP_MAX_AGE_SECONDS`, `TEMP_STORAGE_QUOTA_GB`, `CLEANUP_INTERVAL_SECONDS`, `ADMIN_API_KEY`/`CHEAT_CLIP_API_KEY`, `SERVER_MODE`, `ALLOW_SERVER_UPDATE`, `ALLOWED_ORIGINS`, `HOST`, `PORT`, `EMOJI_FONT_PATH`.

## Risiko
- Mengimpor `backend.config` saja sudah menjalankan efek samping: membuat folder, mencari FFmpeg, dan menguji encoder GPU (memanggil FFmpeg beberapa kali).
- `--reload` aktif: menyimpan file `.py` saat render berjalan akan me-restart backend dan menghentikan job (state job ada di memori).
- `backend/haarcascade_frontalface_default.xml` di root backend adalah duplikat dari file di `backend/cascades/`.

## Terkait
[[index]] · [[penyimpanan-dan-cleanup]] · [[render-server]] · [[sistem-update]] · [[pilihan-klip]]
