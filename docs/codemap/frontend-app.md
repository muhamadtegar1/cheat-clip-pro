---
fitur: frontend utama (App.tsx)
file_utama: [src/App.tsx, src/types.ts, src/components/ClipScorePanel.tsx, src/utils/clipScores.ts, src/components/ClipChoiceControls.tsx, src/utils/clipChoices.ts, src/utils/api.ts, src/locales/LanguageContext.tsx, src/locales/id.ts, src/locales/en.ts]
---
# Frontend app

React 19 + Vite. Hampir semua UI dan state ada di satu komponen `App` (`src/App.tsx`, ±4800 baris): form analisis, progres SSE, riwayat, player YouTube, daftar klip, ekspor, dan peluncur render. Studio render ada di [[clip-studio]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/App.tsx` | `App` | L31-4997 | Komponen utama |
| `src/App.tsx` | state form + preferensi | L32-143 | URL, sumber, draf input API key + `geminiKeyStatus` (L55-60), model, durasi, jumlah klip, rentang, subtitle manual |
| `src/App.tsx` | `handleAnalyze` | L1351-1721 | Upload audio (bila upload), cek cache, `POST /api/analyze`, baca stream SSE, simpan cache |
| `src/App.tsx` | kirim request + baca stream SSE | L1560-1676 | `fetch('/api/analyze')`, `response.body.getReader()`, parsing event |
| `src/App.tsx` | `saveGeminiKey` | L745-757 | `PUT /api/settings/gemini-key` (opsional retry) |
| `src/App.tsx` | `handleSaveApiKey` | L759-777 | Tombol Simpan / Enter di input key. Input dikosongkan setelah tersimpan |
| `src/App.tsx` | `handleDeleteApiKey` | L779-796 | Tombol Hapus: `DELETE /api/settings/gemini-key` |
| `src/App.tsx` | muat status key + migrasi | L798-815 | Key lama di `localStorage` dipindah ke backend lalu dihapus, kemudian `GET /api/settings/gemini-key` |
| `src/App.tsx` | `fetchModels` | L819-847 | `GET /api/models` tanpa key di query, hanya bila backend punya key asli (bukan `mock`) |
| `src/App.tsx` | `refreshHistory` | L909-974 | Bangun riwayat dari key `cheat_clip_cache_*` |
| `src/App.tsx` | `loadFromHistory` | L981-1100 | Muat hasil lama dari cache |
| `src/App.tsx` | `clearAllHistory` | L1114-1126 | Hapus semua cache analisis |
| `src/App.tsx` | `initPlayer` | L1158-1227 | YouTube IFrame player |
| `src/App.tsx` | `playClip` | L1262-1301 | Putar satu klip di player |
| `src/App.tsx` | `toggleMarkedClip` | L879-887 | Checklist klip (disimpan per video) |
| `src/App.tsx` | `handleStartBatchRender` | L297-570 | Render: mode browser (L303-459) atau `POST /api/render-batch` (L461-570; `subtitle_replacements` #11 di L498, hanya bila kamus tidak kosong) |
| `src/App.tsx` | `handleRetryBatchClip` | L572-613 | Retry klip gagal |
| `src/App.tsx` | `handleExportJSON` | L2173-2185 | Ekspor hasil ke JSON |
| `src/App.tsx` | `handleExportSRT` | L2187-2219 | Ekspor transkrip ke SRT |
| `src/App.tsx` | `handleCopyAllMarkdown` | L2221-2251 | Salin semua klip sebagai Markdown |
| `src/App.tsx` | filter + urutan klip | L2253-2299 | `searchQuery`, `viralityFilter`, `sortBy`; `clipTiers` (L2272, #1b) = label relatif dari semua `result.clips`, bukan daftar yang difilter; `clipChoices` (L2274, #35) = hook `useClipChoices` |
| `src/App.tsx` | JSX header | L2363-2474 | Badge cookies, Clear Temp, tombol Update (disembunyikan) |
| `src/App.tsx` | JSX form analisis | L2475-3316 | Tab sumber, kartu AI (L2872-3008, API key L2878-2964), parameter klip, subtitle, rentang |
| `src/App.tsx` | JSX riwayat | L3317-3682 | Daftar analisis sebelumnya |
| `src/App.tsx` | JSX progres | L3811-4016 | Bar progres + stepper 4 langkah (saat `loading`) |
| `src/App.tsx` | JSX dashboard hasil | L4017-4862 | Player, heatmap, ringkasan AI, kartu klip (L4351-4862; `ClipTierBadges` di header L4649 dan `ClipScorePanel` sesudah kutipan L4678, #1b; `ClipChoiceControls` L4680, #35; tombol Pilihan CSV/JSON di toolbar L4507-4526) |
| `src/App.tsx` | JSX Clip Studio + modal | L4885-4994 | `ClipStudioSection` (dengan `transcript` untuk pratinjau subtitle #36a, L4907), `CookiesModal`, `AppUpdateModal`, `ClipTrimmerModal` |
| `src/types.ts` | tipe bersama | L1-255 | `AnalyzeResponse`, `ViralClip` (dengan `scores`, `score_reason`, `needs_context`, `score_label` dari #1), `ClipScores`, `ClipChoice`/`ClipChoiceRecord` (#35), `SubtitleReplacement` + `RenderSettings.subtitleReplacements` (#11), `SubtitlePreviewEvent`/`SubtitlePreviewResponse` (#36a; `indices`, `source: 'edited'` dari #36b), `SubtitleWord` + `ViralClip.subtitle_words` (#36b), `BatchRenderProgress` |
| `src/components/ClipScorePanel.tsx` | `ClipTierBadges` | L19-52 | #1b: pil label relatif Prioritas/Cadangan + lencana "Butuh konteks" di header kartu |
| `src/components/ClipScorePanel.tsx` | `ClipScorePanel` | L54-96 | #1b: bar 6-7 skor dimensi + `score_reason`; tidak dirender untuk klip tanpa skor |
| `src/utils/clipScores.ts` | `computeClipTiers` | L23-34 | #1b: sekitar 30% teratas klip bertanda skor (ceil, minimal 1, skor sama dengan batas ikut) = `priority`, sisanya `backup`; kunci `clipKey` = `start_end` |
| `src/App.tsx` | `handleExportChoices` | L2275-2279 | #35: unduh semua pilihan Pakai/Lewati (JSON/CSV) + toast. Lihat [[pilihan-klip]] |
| `src/components/ClipChoiceControls.tsx` | `ClipChoiceControls` | L34-103 | #35: tombol Pakai/Lewati + alasan di kartu klip. Lihat [[pilihan-klip]] |
| `src/utils/clipChoices.ts` | `useClipChoices` | L68-152 | #35: muat/simpan/batal pilihan lewat `/api/clip-choices` |
| `src/utils/clipScores.ts` | `hasClipScores` | L15-16 | Klip punya minimal satu skor inti (tanpa Prompt Match) |
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
- Label skor (#1b) sengaja relatif per hasil analisis: skor Gemini menggelembung (84-94) sehingga `score_label` absolut dari backend selalu `strong` dan tidak ditampilkan. Badge `virality_score`, filter "high >= 90", dan ekspor tetap memakai angka lama. Helper skor ada di `src/utils/clipScores.ts`, bukan di file komponen, karena aturan lint `react-refresh/only-export-components`.
- Komponen raksasa dengan puluhan `useState`. Tambah fitur sebagai komponen terpisah bila memungkinkan, jangan menambah ke `App`.
- Semua teks UI harus ditambahkan ke **dua** file locale (`src/locales/id.ts` dan `src/locales/en.ts`, ±688 baris masing-masing).
- **Komponen mati**: `src/components/ClipStudioModal.tsx` dan `src/components/BatchRenderProgressModal.tsx` tidak diimpor di mana pun. Jangan edit file itu dengan anggapan mengubah UI aktif.
- Kunci cache memuat model, jumlah klip, prompt, rentang, dan subtitle manual. Mengubah format kunci membuat riwayat lama tidak terbaca.
- Gemini key tidak pernah disimpan di browser. UI hanya tahu `configured`, `source`, dan 4 karakter terakhir. Jangan menambah `api_key` kembali ke body `/api/analyze` atau query `/api/models`.
- Cookies YouTube masih di `localStorage` (`cheatclip_youtube_cookies`).

## Terkait
[[index]] · [[clip-studio]] · [[analisis-ai]] · [[render-server]] · [[render-browser]] · [[cookies-dan-proxy]] · [[sistem-update]] · [[sumber-video]] · [[pilihan-klip]]
