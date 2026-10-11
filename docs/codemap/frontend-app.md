---
fitur: frontend utama (App.tsx)
file_utama: [src/App.tsx, src/types.ts, src/utils/api.ts, src/locales/LanguageContext.tsx, src/locales/id.ts, src/locales/en.ts]
---
# Frontend app

React 19 + Vite. Hampir semua UI dan state ada di satu komponen `App` (`src/App.tsx`, ±4800 baris): form analisis, progres SSE, riwayat, player YouTube, daftar klip, ekspor, dan peluncur render. Studio render ada di [[clip-studio]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/App.tsx` | `App` | L27-4951 | Komponen utama |
| `src/App.tsx` | state form + preferensi | L28-139 | URL, sumber, draf input API key + `geminiKeyStatus` (L51-56), model, durasi, jumlah klip, rentang, subtitle manual |
| `src/App.tsx` | `handleAnalyze` | L1346-1716 | Upload audio (bila upload), cek cache, `POST /api/analyze`, baca stream SSE, simpan cache |
| `src/App.tsx` | kirim request + baca stream SSE | L1555-1671 | `fetch('/api/analyze')`, `response.body.getReader()`, parsing event |
| `src/App.tsx` | `saveGeminiKey` | L740-752 | `PUT /api/settings/gemini-key` (opsional retry) |
| `src/App.tsx` | `handleSaveApiKey` | L754-772 | Tombol Simpan / Enter di input key. Input dikosongkan setelah tersimpan |
| `src/App.tsx` | `handleDeleteApiKey` | L774-791 | Tombol Hapus: `DELETE /api/settings/gemini-key` |
| `src/App.tsx` | muat status key + migrasi | L793-810 | Key lama di `localStorage` dipindah ke backend lalu dihapus, kemudian `GET /api/settings/gemini-key` |
| `src/App.tsx` | `fetchModels` | L814-842 | `GET /api/models` tanpa key di query, hanya bila backend punya key asli (bukan `mock`) |
| `src/App.tsx` | `refreshHistory` | L904-969 | Bangun riwayat dari key `cheat_clip_cache_*` |
| `src/App.tsx` | `loadFromHistory` | L976-1095 | Muat hasil lama dari cache |
| `src/App.tsx` | `clearAllHistory` | L1109-1121 | Hapus semua cache analisis |
| `src/App.tsx` | `initPlayer` | L1153-1222 | YouTube IFrame player |
| `src/App.tsx` | `playClip` | L1257-1296 | Putar satu klip di player |
| `src/App.tsx` | `toggleMarkedClip` | L874-882 | Checklist klip (disimpan per video) |
| `src/App.tsx` | `handleStartBatchRender` | L293-565 | Render: mode browser (L299-455) atau `POST /api/render-batch` (L457-565) |
| `src/App.tsx` | `handleRetryBatchClip` | L567-608 | Retry klip gagal |
| `src/App.tsx` | `handleExportJSON` | L2168-2180 | Ekspor hasil ke JSON |
| `src/App.tsx` | `handleExportSRT` | L2182-2214 | Ekspor transkrip ke SRT |
| `src/App.tsx` | `handleCopyAllMarkdown` | L2216-2246 | Salin semua klip sebagai Markdown |
| `src/App.tsx` | filter + urutan klip | L2248-2284 | `searchQuery`, `viralityFilter`, `sortBy` |
| `src/App.tsx` | JSX header | L2348-2459 | Badge cookies, Clear Temp, tombol Update (disembunyikan) |
| `src/App.tsx` | JSX form analisis | L2460-3301 | Tab sumber, kartu AI (L2857-2993, API key L2863-2949), parameter klip, subtitle, rentang |
| `src/App.tsx` | JSX riwayat | L3302-3667 | Daftar analisis sebelumnya |
| `src/App.tsx` | JSX progres | L3796-4001 | Bar progres + stepper 4 langkah (saat `loading`) |
| `src/App.tsx` | JSX dashboard hasil | L4002-4817 | Player, heatmap, ringkasan AI, kartu klip (L4336-4817) |
| `src/App.tsx` | JSX Clip Studio + modal | L4840-4948 | `ClipStudioSection`, `CookiesModal`, `AppUpdateModal`, `ClipTrimmerModal` |
| `src/types.ts` | tipe bersama | L1-175 | `AnalyzeResponse`, `ViralClip`, `RenderSettings`, `BatchRenderProgress` |
| `src/utils/api.ts` | `resilientFetch` | L16-65 | Fetch dengan retry/timeout |
| `src/locales/LanguageContext.tsx` | `LanguageProvider` | L33-59 | Bahasa UI (id/en) |
| `src/locales/LanguageContext.tsx` | `useLanguage` | L61-67 | Hook `t` untuk teks UI |

## Key `localStorage`
| Key | Isi |
| --- | --- |
| `cheat_clip_gemini_api_key` | **Tidak dipakai lagi** (task #7). Hanya dibaca sekali untuk migrasi ke backend, lalu dihapus (L795-800). Key disimpan di `backend/.env`, lihat [[sistem-update]] |
| `cheat_clip_cache_<video>_<pref...>` / `cheat_clip_ts_...` | Hasil analisis + waktu, sumber riwayat |
| `cheat_clip_selected_model`, `cheat_clip_duration_pref`, `cheat_clip_target_clip_count`, `cheat_clip_clip_count_mode` | Preferensi form |
| `cheat_clip_studio_preferences` | Preferensi Clip Studio ([[clip-studio]]) |
| `cheatclip_youtube_cookies` | Cookies YouTube ([[cookies-dan-proxy]]) |

## Input / output
- Input: aksi user, event SSE dari [[analisis-ai]] dan [[render-server]].
- Output: request ke backend (lewat proxy Vite `/api`), file JSON/SRT yang diunduh browser.

## Risiko
- Komponen raksasa dengan puluhan `useState`. Tambah fitur sebagai komponen terpisah bila memungkinkan, jangan menambah ke `App`.
- Semua teks UI harus ditambahkan ke **dua** file locale (`src/locales/id.ts` dan `src/locales/en.ts`, ±688 baris masing-masing).
- **Komponen mati**: `src/components/ClipStudioModal.tsx` dan `src/components/BatchRenderProgressModal.tsx` tidak diimpor di mana pun. Jangan edit file itu dengan anggapan mengubah UI aktif.
- Kunci cache memuat model, jumlah klip, prompt, rentang, dan subtitle manual. Mengubah format kunci membuat riwayat lama tidak terbaca.
- Gemini key tidak pernah disimpan di browser. UI hanya tahu `configured`, `source`, dan 4 karakter terakhir. Jangan menambah `api_key` kembali ke body `/api/analyze` atau query `/api/models`.
- Cookies YouTube masih di `localStorage` (`cheatclip_youtube_cookies`).

## Terkait
[[index]] · [[clip-studio]] · [[analisis-ai]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sistem-update]] · [[sumber-video]]
