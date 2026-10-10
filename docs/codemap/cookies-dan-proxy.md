---
fitur: cookies YouTube dan proxy
file_utama: [src/utils/cookieUtils.ts, src/components/CookiesModal.tsx, backend/routers/cookies.py, backend/video_engine.py, backend/utils/proxy.py]
---
# Cookies dan proxy

Cara aplikasi melewati blokir/bot check YouTube. **Cookies disimpan di `localStorage` browser** (bukan di server). Cookies dikirim di setiap request yang butuh YouTube, lalu backend menulis file cookies sementara per task dan langsung menghapusnya. Proxy diambil dari `.env`.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/utils/cookieUtils.ts` | `getStoredCookies` | L119-126 | Baca cookies dari `localStorage` (`cheatclip_youtube_cookies`) |
| `src/utils/cookieUtils.ts` | `setStoredCookies` | L131-139 | Simpan cookies |
| `src/utils/cookieUtils.ts` | `normalizeCookies` | L12-90 | JSON ekspor browser → format Netscape |
| `src/utils/cookieUtils.ts` | `hasStoredCookies` | L156-159 | Status untuk badge di header |
| `src/components/CookiesModal.tsx` | `CookiesModal` | L19-322 | UI upload/tempel/hapus cookies |
| `src/components/CookiesModal.tsx` | `handleSave` | L94-118 | Normalisasi lalu simpan ke `localStorage` (tanpa panggilan server) |
| `backend/routers/cookies.py` | `validate_youtube_cookies` | L101-139 | `POST /api/cookies`: validasi saja, dan menghapus file cookies lama di disk |
| `backend/routers/cookies.py` | `normalize_to_netscape` | L18-97 | Normalisasi format (sisi server) |
| `backend/routers/cookies.py` | `delete_youtube_cookies` | L163-171 | `DELETE /api/cookies` |
| `backend/video_engine.py` | `ephemeral_cookies_file` | L108-138 | File cookies sementara per task, dihapus setelah selesai |
| `backend/video_engine.py` | `get_effective_cookies_path` | L141-147 | Fallback ke `cookies.txt` di disk bila ada |
| `backend/video_engine.py` | `get_yt_dlp_cookies_args` | L379-384 | Argumen `--cookies` untuk yt-dlp |
| `backend/utils/proxy.py` | `get_proxy_url` | L34-56 | `PROXY_URL` / `WEBSHARE_*` / `HTTP(S)_PROXY` |
| `backend/utils/proxy.py` | `get_youtube_transcript_proxy_config` | L58-110 | Proxy untuk youtube-transcript-api |
| `backend/utils/proxy.py` | `mask_proxy_url` | L18-31 | Sembunyikan kredensial proxy di log |
| `backend/utils/proxy.py` | `create_http_client` | L115-136 | Session HTTP dengan timeout + proxy |

## Input / output
- Input: teks cookies dari user (JSON ekstensi browser atau Netscape), variabel proxy di `.env`.
- Output: argumen `--cookies <file sementara>` dan `--proxy` untuk yt-dlp; konfigurasi proxy untuk transkrip.
- Dipakai oleh [[transkrip]], [[unduhan-raw]], [[sumber-video]], dan `handleStartBatchRender`/`handleAnalyze` di [[frontend-app]] (mengirim field `cookies`).

## Risiko
- Cookies akun YouTube ada di `localStorage` dan terkirim di body request. Ini data sensitif; jangan log isinya.
- `cookies.txt` di disk diabaikan git (`.gitignore`) dan dilindungi dari cleanup ([[penyimpanan-dan-cleanup]]).
- Gemini API key juga tersimpan di `localStorage` (`cheat_clip_gemini_api_key`, lihat [[frontend-app]]). Target task #7.

## Terkait
[[index]] · [[transkrip]] · [[unduhan-raw]] · [[frontend-app]] · [[penyimpanan-dan-cleanup]]
