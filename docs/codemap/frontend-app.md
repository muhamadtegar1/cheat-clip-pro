---
fitur: frontend utama (App.tsx)
file_utama: [src/App.tsx, src/types.ts, src/components/ClipScorePanel.tsx, src/utils/clipScores.ts, src/components/ClipChoiceControls.tsx, src/utils/clipChoices.ts, src/utils/api.ts, src/locales/LanguageContext.tsx, src/locales/id.ts, src/locales/en.ts]
---
# Frontend app

React 19 + Vite. Hampir semua UI dan state ada di satu komponen `App` (`src/App.tsx`, ±4808 baris): form analisis, progres SSE, riwayat, player YouTube, daftar klip, ekspor, dan peluncur render. Studio render ada di [[clip-studio]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `src/App.tsx` | `App` | L32-5142 | Komponen utama |
| `src/App.tsx` | state form + preferensi | L33-168 | URL, sumber, draf input API key + `geminiKeyStatus` (L56-61), model, durasi, jumlah klip, rentang, subtitle manual, bahasa audio #39 (`audioLanguage`, L140-146, `localStorage` `cheat_clip_audio_language`; #40: lewat `readStoredAudioLanguage`/`storeAudioLanguage`, storage diblokir = Otomatis tanpa galat); #42 `strictModel` (L110-117, `cheat_clip_strict_model`, dibaca/ditulis dalam try/catch) |
| `src/App.tsx` | `handleAnalyze` | L1385-1759 | Upload audio (bila upload), cek cache, `POST /api/analyze`, baca stream SSE, simpan cache. #39: akhiran cache `_lang_<kode>` hanya bila bukan `auto` (L1436), jadi kunci Otomatis tidak berubah |
| `src/App.tsx` | kirim request + baca stream SSE | L1596-1714 | `fetch('/api/analyze')` (`strict_model` #42 di L1603, `audio_language` #39 di L1611, tidak dikirim bila `auto`), `response.body.getReader()`, parsing event |
| `src/App.tsx` | `saveGeminiKey` | L779-791 | `PUT /api/settings/gemini-key` (opsional retry) |
| `src/App.tsx` | `handleSaveApiKey` | L793-811 | Tombol Simpan / Enter di input key. Input dikosongkan setelah tersimpan |
| `src/App.tsx` | `handleDeleteApiKey` | L813-830 | Tombol Hapus: `DELETE /api/settings/gemini-key` |
| `src/App.tsx` | muat status key + migrasi | L832-849 | Key lama di `localStorage` dipindah ke backend lalu dihapus, kemudian `GET /api/settings/gemini-key` |
| `src/App.tsx` | `fetchModels` | L853-881 | `GET /api/models` tanpa key di query, hanya bila backend punya key asli (bukan `mock`) |
| `src/App.tsx` | `refreshHistory` | L943-1008 | Bangun riwayat dari key `cheat_clip_cache_*` |
| `src/App.tsx` | `loadFromHistory` | L1015-1134 | Muat hasil lama dari cache |
| `src/App.tsx` | `clearAllHistory` | L1148-1160 | Hapus semua cache analisis |
| `src/App.tsx` | `initPlayer` | L1192-1261 | YouTube IFrame player |
| `src/App.tsx` | `playClip` | L1296-1335 | Putar satu klip di player |
| `src/App.tsx` | `toggleMarkedClip` | L913-921 | Checklist klip (disimpan per video, kunci `start_end` di `localStorage` `marked_clips_<video_id>`, dibaca ulang setiap `result` berubah) |
| `src/App.tsx` | `openTrimmer` | L93-96 | #41: buka trimmer dan kosongkan `trimmerAppliedRef` (L92, versi klip yang sudah diterapkan selama modal terbuka; unduh raw menerapkan rentang tanpa menutup modal) |
| `src/App.tsx` | `handleApplyAdjustedClipToResults` | L1909-1952 | #41: terapkan rentang/judul dari trimmer ke `result.clips` dengan klip asal `trimmerAppliedRef ?? trimmerClip`; `false` tanpa perubahan bila klip asal tidak ada lagi di `result`; tolak (toast `adjustDurationDuplicate`, `false`) bila rentang baru sama persis dengan klip lain; pindahkan tanda `markedClips` ke kunci baru (ditulis ke `localStorage` sebelum `setResult`), isi `clipRangeChange` (state L97-98) untuk Clip Studio, perbarui `activeClip` bila klip itu yang aktif |
| `src/App.tsx` | `handleStartBatchRender` | L322-604 | Render: mode browser (L320-476) atau `POST /api/render-batch` (L478-596; `subtitle_replacements` #11 di L515, hanya bila kamus tidak kosong; `audio_language` #39 di L516; `kit_meta` #22 di L544-551 dari `result` dan `customPrompt` saat ini) |
| `src/App.tsx` | `handleRetryBatchClip` | L606-647 | Retry klip gagal |
| `src/App.tsx` | `handleExportJSON` | L2241-2253 | Ekspor hasil ke JSON |
| `src/App.tsx` | `handleExportSRT` | L2255-2287 | Ekspor transkrip ke SRT |
| `src/App.tsx` | `handleCopyAllMarkdown` | L2289-2319 | Salin semua klip sebagai Markdown |
| `src/App.tsx` | filter + urutan klip | L2321-2367 | `searchQuery`, `viralityFilter`, `sortBy`; `clipTiers` (L2340, #1b) = label relatif dari semua `result.clips`, bukan daftar yang difilter; `clipChoices` (L2342, #35) = hook `useClipChoices` |
| `src/App.tsx` | JSX header | L2431-2542 | Badge cookies, Clear Temp, tombol Update (disembunyikan) |
| `src/App.tsx` | JSX form analisis | L2543-3425 | Tab sumber, kartu AI (L2940-3097, API key L2946-3032, kotak centang "hanya model pilihan" #42 L3071-3091), parameter klip, subtitle, bahasa audio (#39, L3346-3364), rentang |
| `src/App.tsx` | JSX riwayat | L3426-3791 | Daftar analisis sebelumnya |
| `src/App.tsx` | JSX progres | L3920-4125 | Bar progres + stepper 4 langkah (saat `loading`) |
| `src/App.tsx` | JSX dashboard hasil | L4126-4993 | Player, heatmap, ringkasan AI (baris "Model AI:" L4483-4496 dengan lencana model cadangan bila `model_fallback`, #42), kartu klip (L4460-4993; `ClipTierBadges` di header L4766 dan `ClipScorePanel` sesudah kutipan L4795, #1b; `ClipChoiceControls` L4797, #35; tombol Pilihan CSV/JSON di toolbar L4624-4643); tombol "Sesuaikan Durasi" #41 L4876-4889 membuka trimmer |
| `src/App.tsx` | JSX Clip Studio + modal | L5016-5139 | `ClipStudioSection` (dengan `transcript` untuk pratinjau subtitle #36a, L5038; `audioLanguage`/`onAudioLanguageChange` #39, L5039; `onAdjustClip`/`clipRangeChange` #41, L5041-5042), `ClipTrimmerModal` (`onApply` #41 L5074-5083: terapkan tanpa unduh raw + toast + tutup), `CookiesModal`, `AppUpdateModal`, `ClipTrimmerModal` |
| `src/types.ts` | tipe bersama | L1-261 | `AnalyzeResponse`, `ViralClip` (dengan `scores`, `score_reason`, `needs_context`, `score_label` dari #1), `ClipScores`, `ClipChoice`/`ClipChoiceRecord` (#35), `SubtitleReplacement` + `RenderSettings.subtitleReplacements` (#11), `SubtitlePreviewEvent`/`SubtitlePreviewResponse` (#36a; `indices`, `source: 'edited'` dari #36b), `SubtitleWord` + `ViralClip.subtitle_words` (#36b), `AudioLanguage` + `RenderSettings.audioLanguage` (#39), `BatchRenderProgress` |
| `src/components/ClipScorePanel.tsx` | `ClipTierBadges` | L19-52 | #1b: pil label relatif Prioritas/Cadangan + lencana "Butuh konteks" di header kartu |
| `src/components/ClipScorePanel.tsx` | `ClipScorePanel` | L54-96 | #1b: bar 6-7 skor dimensi + `score_reason`; tidak dirender untuk klip tanpa skor |
| `src/utils/clipScores.ts` | `computeClipTiers` | L23-34 | #1b: sekitar 30% teratas klip bertanda skor (ceil, minimal 1, skor sama dengan batas ikut) = `priority`, sisanya `backup`; kunci `clipKey` = `start_end` |
| `src/App.tsx` | `handleExportChoices` | L2343-2347 | #35: unduh semua pilihan Pakai/Lewati (JSON/CSV) + toast. Lihat [[pilihan-klip]] |
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
| `cheat_clip_selected_model`, `cheat_clip_strict_model` (#42), `cheat_clip_duration_pref`, `cheat_clip_target_clip_count`, `cheat_clip_clip_count_mode` | Preferensi form |
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
