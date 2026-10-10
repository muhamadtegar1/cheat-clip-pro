---
fitur: frontend utama (App.tsx)
file_utama: [src/App.tsx, src/types.ts, src/utils/api.ts, src/locales/LanguageContext.tsx, src/locales/id.ts, src/locales/en.ts]
---
# Frontend app

React 19 + Vite. Hampir semua UI dan state ada di satu komponen `App` (`src/App.tsx`, ±4800 baris): form analisis, progres SSE, riwayat, player YouTube, daftar klip, ekspor, dan peluncur render. Studio render ada di [[clip-studio]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/App.tsx` | `App` | L27-4838 | Komponen utama |
| `src/App.tsx` | state form + preferensi | L28-135 | URL, sumber, API key, model, durasi, jumlah klip, rentang, subtitle manual |
| `src/App.tsx` | `handleAnalyze` | L1271-1642 | Upload audio (bila upload), cek cache, `POST /api/analyze`, baca stream SSE, simpan cache |
| `src/App.tsx` | kirim request + baca stream SSE | L1480-1597 | `fetch('/api/analyze')`, `response.body.getReader()`, parsing event |
| `src/App.tsx` | `fetchModels` | L738-767 | `GET /api/models` saat API key diisi |
| `src/App.tsx` | `refreshHistory` | L829-894 | Bangun riwayat dari key `cheat_clip_cache_*` |
| `src/App.tsx` | `loadFromHistory` | L901-1020 | Muat hasil lama dari cache |
| `src/App.tsx` | `clearAllHistory` | L1034-1046 | Hapus semua cache analisis |
| `src/App.tsx` | `initPlayer` | L1078-1147 | YouTube IFrame player |
| `src/App.tsx` | `playClip` | L1182-1221 | Putar satu klip di player |
| `src/App.tsx` | `toggleMarkedClip` | L799-807 | Checklist klip (disimpan per video) |
| `src/App.tsx` | `handleStartBatchRender` | L289-561 | Render: mode browser (L295-451) atau `POST /api/render-batch` (L453-561) |
| `src/App.tsx` | `handleRetryBatchClip` | L563-604 | Retry klip gagal |
| `src/App.tsx` | `handleExportJSON` | L2094-2106 | Ekspor hasil ke JSON |
| `src/App.tsx` | `handleExportSRT` | L2108-2140 | Ekspor transkrip ke SRT |
| `src/App.tsx` | `handleCopyAllMarkdown` | L2142-2172 | Salin semua klip sebagai Markdown |
| `src/App.tsx` | filter + urutan klip | L2174-2210 | `searchQuery`, `viralityFilter`, `sortBy` |
| `src/App.tsx` | JSX header | L2274-2385 | Badge cookies, Clear Temp, tombol Update (disembunyikan) |
| `src/App.tsx` | JSX form analisis | L2386-3188 | Tab sumber, kartu AI (API key L2783-2880), parameter klip, subtitle, rentang |
| `src/App.tsx` | JSX riwayat | L3189-3554 | Daftar analisis sebelumnya |
| `src/App.tsx` | JSX progres | L3683-3888 | Bar progres + stepper 4 langkah (saat `loading`) |
| `src/App.tsx` | JSX dashboard hasil | L3889-4704 | Player, heatmap, ringkasan AI, kartu klip (L4223-4704) |
| `src/App.tsx` | JSX Clip Studio + modal | L4727-4835 | `ClipStudioSection`, `CookiesModal`, `AppUpdateModal`, `ClipTrimmerModal` |
| `src/types.ts` | tipe bersama | L1-175 | `AnalyzeResponse`, `ViralClip`, `RenderSettings`, `BatchRenderProgress` |
| `src/utils/api.ts` | `resilientFetch` | L16-65 | Fetch dengan retry/timeout |
| `src/locales/LanguageContext.tsx` | `LanguageProvider` | L33-59 | Bahasa UI (id/en) |
| `src/locales/LanguageContext.tsx` | `useLanguage` | L61-67 | Hook `t` untuk teks UI |

## Key `localStorage`
| Key | Isi |
| --- | --- |
| `cheat_clip_gemini_api_key` | **Gemini API key (teks biasa)**. Dibaca L51, ditulis L2824 |
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
- API key di `localStorage` (target task #7).

## Terkait
[[index]] · [[clip-studio]] · [[analisis-ai]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sistem-update]] · [[sumber-video]]
