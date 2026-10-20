# CHEAT-39: Pilihan bahasa audio untuk transkripsi Whisper
Status: REVIEW
Risiko: sedang (menyentuh jalur Whisper analisis, pratinjau subtitle, dan render separate/merged; tidak menyentuh prompt Gemini)

## Tujuan
Pemilik bisa memilih bahasa audio (Otomatis, English, Indonesia, beberapa bahasa lain), dan pilihan itu diteruskan sebagai `language` ke Whisper di transkrip analisis, pratinjau subtitle, dan render, dengan Otomatis berperilaku persis seperti sekarang.

## Kondisi sekarang (diverifikasi di kode)
- `transcribe_local_video_file` (`backend/video_engine.py` L668-715): `transcribe(..., word_timestamps=True, fp16=False, verbose=False, initial_prompt="Transkrip video percakapan dalam Bahasa Indonesia atau English.")`, tanpa `language`. Dipanggil di `backend/routers/analyze.py` L500 (upload/Drive) dan L806 (fallback Whisper YouTube tanpa caption).
- `transcribe_clip_words` (L1175-1260): `transcribe(video_path, word_timestamps=True, fp16=False)`, bahasa ditebak sendiri per klip. Dipanggil `render_service.py` L239 (separate), L500 (merged), dan `subtitle_preview_service.py` L40 (`_transcribe_segment`).
- Cache kata pratinjau backend dikunci `(video_id, start, end)` (`subtitle_preview_service.py` `_cache_key` L25-26); state pratinjau Clip Studio dikunci `start_end`. Render memakai kata pratinjau (#36b) bila ada, jadi pratinjau dari bahasa lama akan ikut ke render kalau kuncinya tidak membedakan bahasa.
- Cache analisis frontend (`src/App.tsx` L1490 dan L1677, hanya YouTube) dikunci video, durasi, model, jumlah klip, prompt, rentang, subtitle manual. Parser riwayat (L921-924) mengambil sisa kunci setelah `duration_pref` sebagai satu akhiran, jadi akhiran tambahan aman.
- #38 memilih default `small` (multibahasa) dan data menunjukkan `small.en` tidak lebih akurat dari `small`, jadi task ini **tidak** menambah peralihan ke model `.en`.
- Deteksi bahasa untuk prompt Gemini (`analyze.py` L1032, `detect_transcript_language` dari teks transkrip) tidak disentuh.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Backend**
   - Konstanta daftar kode yang diizinkan di satu tempat (mis. `WHISPER_AUDIO_LANGUAGES` di `video_engine.py` dekat konstanta #38): `en`, `id`, `ms`, `es`, `pt`, `fr`, `de`, `ar`, `hi`, `ja`, `ko`. Kosong/`None`/`auto` = Otomatis.
   - `transcribe_local_video_file(file_path, progress_callback=None, language=None)`: Otomatis = argumen `transcribe` identik dengan sekarang (termasuk `initial_prompt`). Bahasa dipilih = `language=<kode>` dan `initial_prompt` tidak dikirim (prompt "Indonesia atau English" bertentangan dengan pilihan eksplisit).
   - `transcribe_clip_words(..., language=None)`: Otomatis = identik; bahasa dipilih = `language=<kode>`.
   - Schema: `AnalyzeRequest.audio_language`, `RenderSettingsModel.audio_language`, `PreviewSubtitlesRequest.audio_language`, opsional, divalidasi terhadap daftar (kode lain = 422).
   - `analyze.py`: teruskan `request.audio_language` ke dua panggilan `transcribe_local_video_file` (L500, L806). Tidak ada perubahan lain di generator.
   - `render_service.py`: teruskan `settings.audio_language` ke dua panggilan `transcribe_clip_words` (L239, L500). Retry memakai settings batch yang tersimpan, jadi ikut otomatis.
   - `subtitle_preview_service.py`: teruskan bahasa ke `_transcribe_segment`, dan kunci cache menjadi `(video_id, start, end, bahasa)`.
2. **Frontend**
   - Satu state `audioLanguage` di `App` (default `auto`, disimpan di `localStorage` `cheat_clip_audio_language`), dengan dropdown "Bahasa audio" di form analisis (dekat pilihan sumber subtitle). Dikirim sebagai `audio_language` ke `/api/analyze` hanya bila bukan `auto`.
   - Cache analisis YouTube: akhiran `_lang_<kode>` hanya bila bukan `auto` (kunci Otomatis tidak berubah, riwayat lama tetap terbaca).
   - `ClipStudioSection` menerima `audioLanguage` (dan setter) lewat props, menampilkan dropdown yang sama di bagian subtitle (satu state, jadi tidak bisa berbeda dengan form), mengirimnya di `RenderSettings.audioLanguage` -> `audio_language` (`handleStartBatchRender`) dan di permintaan pratinjau. Kunci state pratinjau menjadi `start_end` + bahasa, sehingga pratinjau/suntingan dari bahasa lain tidak dipakai render.
   - String baru di `src/locales/id.ts` dan `en.ts`. Nama bahasa ditulis dalam bahasanya sendiri (English, Bahasa Indonesia, Español, ...), sama di kedua locale.
3. **Smoke test**: Whisper dipalsukan (model palsu yang mencatat argumen `transcribe`), tanpa memuat model asli.

## Area yang boleh disentuh
- `backend/video_engine.py`: konstanta bahasa di dekat konstanta Whisper #38 (L250-268), `transcribe_local_video_file` (L668-715), `transcribe_clip_words` (L1175-1260; hanya tanda tangan dan argumen `transcribe` di cabang Whisper).
- `backend/schemas/analyze.py`: `AnalyzeRequest` (L54-66). `backend/schemas/render.py`: `RenderSettingsModel` (L10-62), `PreviewSubtitlesRequest` (L73-85).
- `backend/routers/analyze.py`: hanya dua panggilan `transcribe_local_video_file` (L500, L806).
- `backend/services/render_service.py`: hanya dua panggilan `transcribe_clip_words` (L239, L500).
- `backend/services/subtitle_preview_service.py`: `_cache_key` (L25-26), `_transcribe_segment` (L37-45), `_load_words` (L48-82).
- `src/App.tsx`: state form + preferensi (L32-143), kunci cache analisis (L1484-1490, L1677), body `fetch('/api/analyze')` (L1560-1574), JSX form analisis bagian subtitle/parameter (L2475-3316), pemetaan `audio_language` di `handleStartBatchRender` (±L485-498), props `ClipStudioSection` (L4887-4910).
- `src/components/ClipStudioSection.tsx`: props, state/permintaan pratinjau subtitle (L551-656), `handleLaunch` (L1661-1737), JSX kontrol subtitle (L2453-3010).
- `src/utils/subtitlePreview.ts`: `SubtitlePreviewRequest` dan `fetchSubtitlePreview` (L13-72). `src/types.ts`: `RenderSettings`.
- `src/locales/id.ts`, `src/locales/en.ts`.
- `scripts/smoke_test.py`: cek baru #39; cek lama tidak diubah logikanya.
- `docs/codemap/` (transkrip, subtitle-dan-judul, analisis-ai, render-server, clip-studio, frontend-app), plus merapikan rujukan baris di kolom keterangan yang tertinggal dari #38: `subtitle-dan-judul.md` (`build_subtitle_events`), `render-server.md` (AMF), `unduhan-raw.md` (format). `CLAUDE.md` (deskripsi smoke), `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Terjemahan subtitle (keputusan pemilik 2026-10-19).
- Peralihan otomatis ke model `.en` saat English dipilih, dan perubahan pemilihan model #38.
- Prompt Gemini, deskripsi field `ViralClipGemini`/`VideoAnalysis`, deteksi bahasa untuk prompt (`detect_transcript_language`), golden fixtures.
- Pemilihan trek caption YouTube berdasarkan bahasa (jalur YouTube dengan caption tidak memakai Whisper dan tidak berubah).
- Opsi `transcribe` lain (`word_timestamps`, `fp16`, `verbose`, suhu, dsb.) dan `initial_prompt` di mode Otomatis.
- Render di browser (`browser_wasm`, `clientRenderer.ts`), `ClipStudioModal.tsx`, `BatchRenderProgressModal.tsx`.
- Perbaikan kekurangan #36b (pratinjau gagal, batas 60 karakter).

## Keputusan yang boleh diambil AI sendiri
- Nama field/konstanta/state/kunci `localStorage`, susunan daftar bahasa (selama memuat Otomatis, English, Indonesia), letak persis dropdown dalam bagian yang disebut, teks label dan bantuan.
- Bentuk validasi schema (Literal, pattern, atau validator) selama kode di luar daftar ditolak 422.
- Cara memalsukan Whisper di smoke test.

## Kriteria selesai (ya/tidak)
- [x] Otomatis identik dengan sekarang: tanpa `audio_language` (atau `auto`), argumen `transcribe` di `transcribe_local_video_file` dan `transcribe_clip_words` sama persis dengan sebelum task (dibuktikan smoke test dengan model palsu), kunci cache analisis frontend dan request `/api/analyze` tidak berubah.
- [x] Bahasa dipilih diteruskan sebagai `language=<kode>` ke Whisper di: analisis upload/Drive, fallback Whisper YouTube, pratinjau subtitle, render separate, render merged, dan retry (dibuktikan smoke test untuk analisis, pratinjau, separate, merged).
- [x] Bahasa dipilih menghapus `initial_prompt` di transkrip analisis; mode Otomatis tetap memakainya.
- [x] Kode bahasa di luar daftar ditolak 422 di `/api/analyze`, `/api/render-batch`, dan `/api/preview-subtitles`.
- [x] Cache pratinjau backend dan state pratinjau Clip Studio membedakan bahasa: ganti bahasa lalu pratinjau = Whisper jalan lagi, dan render tidak memakai kata pratinjau dari bahasa lain.
- [x] UI: dropdown di form analisis dan di bagian subtitle Clip Studio memakai satu state, tersimpan setelah muat ulang, teks di `id.ts` dan `en.ts`.
- [x] Klip Inggris pendek dengan English dipilih tertranskripsi sebagai Inggris (perlu dicek pemilik; boleh juga dibuktikan implementer dengan `whisper_bench.py --language en` pada klip uji #38). Dibuktikan implementer (bench + uji browser) dan dicek pemilik 2026-10-20: subtitle Inggris akurat.
- [x] Prompt Gemini tidak berubah (diff `analyze.py` hanya dua panggilan Whisper).
- [x] Smoke test lulus (cek lama + cek #39), `npm run build` lulus, `npm run lint` tidak menambah error baru, `check_codemap.py` lulus, rujukan baris #38 di codemap sudah dirapikan.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`
- `npm run build` dan `npm run lint`
- `venv\Scripts\python.exe scripts\check_codemap.py`
- Implementer (opsional, data): `venv\Scripts\python.exe scripts\whisper_bench.py tests\whisper_bench\<klip Inggris pendek> --ref <acuan> --models small --runs 1 --language en` dibanding tanpa `--language`.
- Pemilik: `npm run dev`, pilih English, buat pratinjau subtitle satu klip Inggris pendek (mis. 15 s) di Clip Studio; log backend tidak menunjukkan deteksi bahasa salah dan subtitle berbahasa Inggris. Ganti ke Otomatis, pratinjau lagi: Whisper jalan ulang. Render klip itu dan pastikan subtitle sama dengan pratinjau.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/video_engine.py`: `WHISPER_AUDIO_LANGUAGES` (L272) dan `normalize_audio_language` (L275-282); `transcribe_local_video_file` (L682-741) menerima `language` (dipilih = `language=<kode>` tanpa `initial_prompt`, None = argumen lama persis); `transcribe_clip_words` (L1201-1291) menerima `language` (dipilih = `language=<kode>`, None = argumen lama persis).
- `backend/schemas/render.py`: `_check_audio_language` + tipe `AudioLanguage` (L5-14, impor lambat `video_engine`), `RenderSettingsModel.audio_language` (L52), `PreviewSubtitlesRequest.audio_language` (L101). `backend/schemas/analyze.py`: `AnalyzeRequest.audio_language` (L69).
- `backend/routers/analyze.py`: hanya dua panggilan `transcribe_local_video_file` (L500, L806) diberi `language=request.audio_language`.
- `backend/services/render_service.py`: dua panggilan `transcribe_clip_words` (separate L244, merged L506) diberi `language=settings.audio_language`; retry memakai settings batch.
- `backend/services/subtitle_preview_service.py`: `_cache_key` memuat bahasa (`auto` bila None), `_transcribe_segment` dan `_load_words` meneruskan bahasa.
- `src/types.ts` (`AudioLanguage`, `RenderSettings.audioLanguage`), `src/utils/subtitlePreview.ts` (`AUDIO_LANGUAGE_OPTIONS`, `parseAudioLanguage`, `audioLanguageParam`, `subtitlePreviewKey`, `audio_language` di `fetchSubtitlePreview`), `src/App.tsx` (state + `localStorage` `cheat_clip_audio_language`, dropdown di form, akhiran cache `_lang_<kode>` hanya bila bukan `auto` di kunci cache dan kunci timestamp riwayat, `audio_language` di `/api/analyze` dan `/api/render-batch`, props ke Clip Studio), `src/components/ClipStudioSection.tsx` (props, dropdown di bagian subtitle, kunci pratinjau per bahasa, `audioLanguage` di `handleLaunch` dan permintaan pratinjau), `src/locales/id.ts`, `src/locales/en.ts`.
- `scripts/smoke_test.py`: cek baru `run_audio_language_check`; dua fake `transcribe_clip_words` lama (#36a, #36b) hanya ditambah parameter `language=None` agar menerima argumen baru, logikanya tidak berubah.
- `CLAUDE.md` (deskripsi smoke), `docs/codemap/` (lihat di bawah), `TASKS.md`, kontrak ini.
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: `20/20 cek lulus. SMOKE TEST LULUS`, termasuk `[PASS] bahasa audio Whisper (#39): Otomatis = argumen transcribe sama dengan sebelum #39 (initial_prompt tetap), bahasa dipilih = language tanpa initial_prompt, diteruskan di analisis/pratinjau/separate/retry/merged, cache pratinjau per bahasa, 'xx' = 422`.
- `npm run build`: lulus (`built in ...`, hanya peringatan ukuran chunk yang sudah ada).
- `npm run lint`: masalah lama tetap ada; jumlah per file yang diubah sama dengan HEAD (`App.tsx` 27/27, `ClipStudioSection.tsx` 32/32, `subtitlePreview.ts`, `types.ts`, `id.ts`, `en.ts` 0/0), jadi tidak ada error baru.
- `venv\Scripts\python.exe scripts\check_codemap.py`: `SEMUA CEK LULUS`.
- `whisper_bench.py` (model `small`, klip Inggris 15,9 s dari video B 240,9 s, `--runs 1`): Otomatis WER 0,0%, bahasa `en`, 18,25 s; `--language en` WER 0,0%, 15,89 s. Klip ini tidak salah tebak, jadi data hanya menunjukkan `language` tidak merugikan.
- Uji manual oleh implementer di browser bawaan (2026-10-20), tanpa kuota Gemini: klip Inggris 90 s (360p, dari audio uji #38) di-upload lewat `/api/upload-video`, dianalisis lewat `/api/analyze` dengan key `mock` per request dan `audio_language=en` (log `Transcribing local file with Whisper: ... (language=en)`), hasilnya dimasukkan ke riwayat `localStorage` browser bawaan lalu dibuka di UI. Pratinjau Otomatis: log `(language=auto)`, body tanpa `audio_language`. Ganti ke English di Clip Studio: dropdown form ikut berubah, tersimpan, kartu kembali ke "Generate subtitles"; pratinjau English: log `(language=en)`, body `audio_language: "en"`. Kembali ke Otomatis: pratinjau lama tampil tanpa request baru. Muat ulang: English tetap terpilih, pratinjau English dari cache backend (tanpa log Whisper baru). Render 2 klip (English): klip 1 `memakai 27 kata dari pratinjau (Whisper dilewati)`, klip 2 Whisper `(language=en)`; 27 baris `Dialogue` klip 1 identik dengan event pratinjau (teks dan waktu). `audio_language: "xx"` = 422 dengan pesan daftar pilihan.
- Pemilik menonton dua klip hasil uji: subtitle bahasa Inggris akurat dan tepat.
CODEMAP_DIPERBARUI: ya. `transkrip.md` (`normalize_audio_language`, `transcribe_local_video_file`, dua potongan Whisper `analyze.py`, risiko bahasa), `subtitle-dan-judul.md` (`transcribe_clip_words`, `_cache_key`, `_load_words`, `_transcribe_segment`, risiko), `render-server.md` (`_check_audio_language`, `RenderSettingsModel`, `PreviewSubtitlesRequest`), `analisis-ai.md` (`AnalyzeRequest`), `clip-studio.md` (dropdown, kunci pratinjau, `handleLaunch`, `fetchSubtitlePreview`, props), `frontend-app.md` (state, cache, request, JSX form, props, tipe). Rentang yang bergeser diperbarui di semua catatan terdampak (juga `arsitektur-backend`, `cookies-dan-proxy`, `face-tracking`, `penyimpanan-dan-cleanup`, `pilihan-klip`, `render-browser`, `sistem-update`, `sumber-video`, `unduhan-raw`). Rujukan baris yang tertinggal dari #38 dirapikan (`build_subtitle_events`, AMF, format unduhan), plus rujukan lama yang ternyata usang: `build_ffmpeg_filtergraph` di paragraf `render-server.md`, `subtitle_words` di `handleLaunch` (`clip-studio.md`), baris kamus `render_service` di paragraf `subtitle-dan-judul.md`.
CATATAN:
- Keputusan sendiri: daftar bahasa `auto, en, id, ms, es, pt, fr, de, ar, hi, ja, ko`; validasi lewat `AfterValidator` (`AudioLanguage`) yang memakai `normalize_audio_language` dari `video_engine` (satu sumber daftar di backend; frontend punya salinan di `AUDIO_LANGUAGE_OPTIONS` dan tipe `AudioLanguage`, keduanya diberi komentar agar disamakan); `audio_language` dikirim sebagai argumen kata kunci `language=`; frontend tidak mengirim field bila `auto`; dropdown Clip Studio memakai label dari `t.form` agar teks sama dengan form.
- Ditemukan saat uji browser dan sudah diperbaiki: kunci timestamp riwayat (`cheat_clip_ts_...`) awalnya tidak diberi akhiran `_lang_`, sehingga analisis dengan bahasa terpilih selalu tampil "just now".
- Perilaku penting: bahasa yang salah pilih membuat Whisper **menerjemahkan kasar** ke bahasa itu (uji: audio Inggris dengan `id` menjadi "Dia dan Yakov Sinai, lihat pasangan halestone..."), bukan menghasilkan teks rusak. Teks bantuan di kedua locale dan codemap ditulis jujur soal ini dan menyarankan Otomatis bila ragu.
- Pilihan bahasa tidak memengaruhi jalur YouTube dengan caption (tanpa Whisper) dan tidak mengubah deteksi bahasa untuk prompt Gemini.
- Video hasil uji terlihat kurang HD karena sumber uji hanya 640x360 (audio uji #38), bukan karena #39. Untuk sumber YouTube, app memang mendapat 360p (#28, SKIPPED).
- Sisa uji: dua klip di `EXPORTS_DIR` (`clip_1/2_batch_1792454168_d822f0.mp4`, tidak boleh dihapus AI), upload uji di `backend/temp_clips/uploads` (auto-cleanup), riwayat palsu di `localStorage` browser bawaan, konfigurasi `backend` di `.claude/launch.json` (file lokal, tidak di-commit).

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
