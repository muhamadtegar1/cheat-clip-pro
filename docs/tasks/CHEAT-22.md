# CHEAT-22: Posting kit per klip
Status: DONE

## Riwayat
- 2026-10-20: draf dibuat. Pemilik memberi izin mengerjakan #22 (Fase 3) sebelum Fase 2 selesai, karena #2/#3 menunggu data produksi (aturan no. 6).

## Tujuan
Setiap klip yang selesai dirender (mode `separate`) punya satu folder siap unggah berisi MP4, SRT, `metadata.json`, dan caption per platform (TikTok, Reels, Shorts, X), tersimpan permanen di `EXPORTS_DIR` dan ikut di ZIP batch, tanpa memanggil Gemini lagi.

## Desain
1. **Lokasi**: `EXPORTS_DIR/kits/<YYYY-MM-DD>_<batch_id>/<NN>_<judul-aman>/`, dengan `NN` = nomor klip dua digit. MP4 asli tetap di `EXPORTS_DIR/clip_{n}_{batch_id}.mp4` (URL unduh tidak berubah); di folder kit dibuat hardlink `video.mp4` (gagal hardlink, mis. beda drive, = salin).
2. **Isi folder**:
   - `video.mp4`
   - `subtitles.srt`: dari kata yang benar-benar dipakai render (kata pratinjau #36b atau hasil Whisper), dipotong per baris lewat `build_subtitle_events` dengan kamus #11, sehingga baris SRT = baris karaoke di video. Huruf asli (bukan `text_case` video), karena SRT dipakai sebagai caption platform. Tidak dibuat bila subtitle dimatikan atau tidak ada kata.
   - `metadata.json`: `schema_version`, sumber (`video_id`, URL, judul video, channel), klip (nomor, rentang, durasi, judul tampil, `hook_time`, `key_quotes`, transkrip), skor 7 dimensi + total + `score_label` + `score_reason` + `needs_context` (null bila klip tanpa skor), model Gemini, `prompt_version`, fokus pencarian (`custom_prompt`), bahasa audio, pengaturan render ringkas (rasio, gaya caption, encoder), `created_at`, daftar file kit.
   - `caption_tiktok.txt`, `caption_reels.txt`, `caption_shorts.txt` (baris 1 judul ≤ 100 karakter, lalu deskripsi), `caption_x.txt` (≤ 280 karakter).
3. **Caption per platform tanpa Gemini**: disusun dari `caption_suggestion`, `hashtag_suggestion`, judul klip, dan baris kredit `Source: <channel> <URL sumber>` (URL dihilangkan untuk sumber upload/Drive). Aturan per platform (batas karakter, jumlah hashtag maksimal, letak kredit) disimpan sebagai satu tabel konstanta di modul baru agar mudah diubah, nanti juga oleh Campaign Profile #20. Hashtag dirapikan (huruf kecil, tanpa duplikat, diawali `#`). Klip tanpa `caption_suggestion` (fallback heatmap, hasil lama) memakai judul klip.
4. **`prompt_version`**: hash pendek (sha256, 12 karakter) dari teks sumber `backend/routers/analyze.py` + `backend/schemas/analyze.py`, dihitung sekali saat modul dimuat, dikirim di `AnalyzeResponse.prompt_version`. Teks prompt tidak berubah (tidak perlu golden fixtures). Hasil analisis lama di riwayat tanpa field ini = `null` di metadata.
5. **Data dari frontend**: `RenderBatchRequest` mendapat field opsional `kit_meta` (judul video, channel, model, `prompt_version`, `custom_prompt`), diisi `handleStartBatchRender` dari hasil analisis yang aktif. Request lama tanpa `kit_meta` tetap valid (field kosong = `null`).
6. **Kegagalan kit tidak menggagalkan klip**: galat penulisan kit dicatat di log dan di status klip (`kit_error`), klip tetap `completed`. Retry klip menulis ulang kit klip itu.
7. **ZIP batch**: tetap berisi MP4 bernama judul seperti sekarang, ditambah folder `kits/<NN>_<judul-aman>/` berisi file kit selain `video.mp4` (MP4 tidak digandakan di ZIP).
8. **UI**: setelah batch selesai, panel progres Clip Studio menampilkan satu baris "Posting kit tersimpan di <folder>" (string baru di `id.ts` dan `en.ts`). Tidak ada tombol buka folder.

## Area yang boleh disentuh
- Baru: `backend/services/posting_kit.py` (caption per platform, SRT, `metadata.json`, tulis folder kit).
- `backend/services/render_service.py`: akhir blok sukses `render_single_batch_clip` (L121-344, sekitar L325-330) untuk memanggil penulis kit dan menyimpan kata yang dipakai; `update_batch_summary_and_zip` (L347-396) untuk folder kit di ZIP dan path kit di status batch; `process_batch_rendering` (L661-701) dan `process_batch_retry` (L704-757) hanya untuk meneruskan `kit_meta`.
- `backend/schemas/render.py`: `RenderBatchRequest` (L78-84) field `kit_meta` opsional (model kecil baru di file yang sama).
- `backend/routers/render.py`: `start_batch_render` (L39-100) hanya bila perlu menyimpan `kit_meta` ke `BATCH_REQUESTS`.
- `backend/schemas/analyze.py`: `AnalyzeResponse` (L82-92) field `prompt_version` opsional. `ViralClip`, `ViralClipGemini`, `VideoAnalysis` tidak diubah.
- `backend/routers/analyze.py`: konstanta `PROMPT_VERSION` di tingkat modul dan argumen `prompt_version=` di dua konstruksi `AnalyzeResponse` (mock L959, final L1617). Tidak ada perubahan teks prompt atau pasca-proses.
- `src/types.ts`: `AnalyzeResponse.prompt_version?`, `BatchRenderProgress.kit_dir?`.
- `src/App.tsx`: body `fetch('/api/render-batch')` di `handleStartBatchRender` (±L471-540) untuk `kit_meta`.
- `src/components/ClipStudioSection.tsx`: panel progres batch di dekat tautan ZIP (±L4850) untuk baris folder kit.
- `src/locales/id.ts`, `src/locales/en.ts`: string folder kit.
- `scripts/smoke_test.py`: satu cek baru #22 dan pemanggilannya; cek lama tidak diubah.
- `docs/codemap/render-server.md`, `penyimpanan-dan-cleanup.md`, `analisis-ai.md`, `clip-studio.md`, `frontend-app.md`, `index.md` (catatan baru bila perlu, mis. `posting-kit.md`), `CLAUDE.md` (deskripsi smoke test), `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Mode `merged` (video highlight gabungan) dan render di browser (FFmpeg WASM): tanpa kit.
- Campaign Profile (#20): kredit/hashtag wajib per campaign, compliance (#21), ledger (#23).
- Caption baru dari Gemini, perubahan teks prompt, `ViralClipGemini`/`VideoAnalysis`.
- Auto-posting atau unggah ke platform (masuk "Sengaja tidak dikerjakan").
- Tombol buka folder di Explorer, pengaturan kit di UI (on/off, template caption).
- Mengubah nama atau lokasi MP4 hasil render, URL unduh, atau isi MP4 di ZIP.
- Kit untuk klip lama yang dirender sebelum task ini.

## Keputusan yang boleh diambil AI sendiri
- Nama fungsi, nama field `metadata.json` di luar yang disebut, format nama folder aman (karakter yang dibuang, panjang maksimal).
- Nilai awal tabel aturan platform (batas karakter, jumlah hashtag) selama dicatat di kontrak dan codemap sebagai nilai yang perlu dicek pemilik terhadap aturan platform terbaru.
- Teks string UI dan letaknya di panel progres.
- Detail pemalsuan di smoke test.

## Kriteria selesai (ya/tidak)
- [x] Render `separate` 1 klip menghasilkan folder kit di `EXPORTS_DIR/kits/...` berisi `video.mp4` (isi sama dengan MP4 hasil render), `subtitles.srt`, `metadata.json`, dan 4 file caption.
- [x] Baris SRT sama dengan baris karaoke di video (teks dan waktu dari `build_subtitle_events` atas kata yang dipakai render), termasuk saat kata berasal dari pratinjau/suntingan #36b dan kamus #11; subtitle dimatikan = tanpa SRT, kit tetap dibuat.
- [x] `metadata.json` valid JSON dan memuat skor, model, `prompt_version`, fokus pencarian, rentang klip, dan sumber; klip tanpa skor dan request tanpa `kit_meta` tidak gagal (field `null`).
- [x] Caption tiap platform mematuhi tabel aturannya (batas karakter, jumlah hashtag), memuat baris kredit, dan tidak kosong untuk klip tanpa `caption_suggestion`.
- [x] `prompt_version` muncul di respons `/api/analyze` (mock dan asli) tanpa perubahan teks prompt.
- [x] Galat penulisan kit tidak mengubah status klip menjadi gagal; retry menulis ulang kit.
- [x] ZIP batch berisi MP4 seperti sebelumnya plus folder kit tanpa MP4 ganda.
- [x] Panel progres Clip Studio menampilkan folder kit (id dan en).
- [x] `npm run build` lulus, lint tidak menambah masalah di file yang disentuh, smoke test lulus (termasuk cek #22), `check_codemap.py` lulus.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`: cek baru #22 merender 1 klip sintetis dengan `kit_meta`, kata subtitle dari request, dan kamus, lalu memeriksa isi folder kit, SRT terhadap `build_subtitle_events`, JSON, batas caption, isi ZIP, klip tanpa skor/tanpa `kit_meta`, dan kit gagal ditulis (dipalsukan) = klip tetap `completed`. Folder kit dibuat di `EXPORTS_DIR` sementara milik smoke test.
- `npm run build`, `npm run lint` (bandingkan jumlah masalah file yang disentuh), `venv\Scripts\python.exe scripts\check_codemap.py`.
- Browser bawaan (`npm run dev`): analisis key `mock` atau hasil dari riwayat, render 1 klip di Clip Studio, pastikan baris folder kit tampil dan folder berisi file yang benar.
- Perlu dicek pemilik: isi caption terasa layak untuk diunggah, batas platform masih sesuai aturan terbaru, dan alur unggah manual dari folder kit nyaman.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/services/posting_kit.py` (baru): `PLATFORM_RULES`, `safe_name`, `kit_batch_dir`, `clip_kit_dirname`, `build_srt`, `PLACEHOLDER_CHANNELS`, `public_source_url`, `credit_line`, `build_platform_captions`, `build_metadata`, `write_clip_kit`.
- `backend/services/render_service.py`: import; `render_single_batch_clip` parameter `video_id`, `kit_meta`, variabel `words_used` (L147, diisi L279 bila subtitle aktif), blok posting kit setelah MP4 valid (L331-352, galat = `kit_error`); `update_batch_summary_and_zip` menambah `kits/<NN>_<judul>/` tanpa `video.mp4` ke ZIP; `process_batch_rendering` dan `process_batch_retry` meneruskan `video_id` + `kit_meta`.
- `backend/schemas/render.py`: model `KitMeta` (semua opsional, tanpa batas panjang agar render tidak gagal 422) dan `RenderBatchRequest.kit_meta`.
- `backend/schemas/analyze.py`: `AnalyzeResponse.prompt_version`.
- `backend/routers/analyze.py`: `import hashlib`, `_compute_prompt_version` + `PROMPT_VERSION`, argumen `prompt_version=` di dua konstruksi `AnalyzeResponse` (mock, final). Teks prompt, `ViralClipGemini`, `VideoAnalysis`, pasca-proses tidak berubah.
- `src/types.ts`: `AnalyzeResponse.channel?` (field sudah dikirim backend, belum diketik) dan `prompt_version?`, `BatchRenderProgress.kit_dir?`.
- `src/App.tsx`: `kit_meta` di body `/api/render-batch` (`handleStartBatchRender`).
- `src/components/ClipStudioSection.tsx`: baris folder kit di panel progres batch.
- `src/locales/id.ts`, `en.ts`: `postingKitSaved`.
- `scripts/smoke_test.py`: `run_posting_kit_check` (cek 13) + pemanggilan; `main` mengalihkan `posting_kit.EXPORTS_DIR` ke folder sementara untuk seluruh run (render cek 4 juga menulis kit), dikembalikan di `finally`. Cek lama tidak diubah.
- `CLAUDE.md` (deskripsi smoke), codemap, `TASKS.md`, kontrak ini.
- `backend/routers/render.py` tidak perlu diubah (`kit_meta` ikut tersimpan di `BATCH_REQUESTS`).
HASIL_TEST:
- `venv\Scripts\python.exe scripts\smoke_test.py`: `23/23 cek lulus. SMOKE TEST LULUS`, termasuk `[PASS] posting kit per klip (#22): folder kit 7 file, video.mp4 = MP4 render, SRT = baris karaoke (huruf asli, kamus), metadata, batas caption, ZIP tanpa MP4 ganda, retry menulis ulang, tanpa skor/kit_meta/subtitle, kit gagal = klip tetap selesai, prompt_version di respons mock dan Gemini`. Setelah run, `~/CheatClip/kits` tidak ada (kit smoke di folder sementara).
- `npm run build`: lulus (`built in 860ms`, hanya peringatan ukuran chunk lama).
- Lint (eslint JSON, `git show HEAD:<file>` lewat stdin vs sesudah, error/warning): `App.tsx` 23/4 = 23/4, `ClipStudioSection.tsx` 30/2 = 30/2, `types.ts`, `id.ts`, `en.ts` 0 = 0.
- `venv\Scripts\python.exe scripts\check_codemap.py`: `SEMUA CEK LULUS` (293 simbol).
- Browser bawaan (`backend` + `frontend`): video sintetis 40 s di `uploads`, hasil analisis `mock` (diambil lewat `fetch` dengan key `mock`) dimasukkan ke riwayat `localStorage`, Load Analysis, centang klip 1, Batch Render 1 Clip (encoder `h264_amf`, Whisper `small`). Panel menampilkan "Posting kit (MP4, SRT, metadata, per-platform captions) saved to D:\CheatClip\kits\2026-10-20_batch_...". Folder berisi 7 file; `fsutil hardlink list` menunjukkan `video.mp4` dan `clip_1_<batch>.mp4` satu file (hardlink); SRT 2 baris dari kata Whisper; `metadata.json` berisi model `Mock Gemini`, `prompt_version` `64a7e740d4b9`, skor. Semua file uji (video, MP4, kit, riwayat `localStorage`) dihapus setelah uji.
CODEMAP_DIPERBARUI: ya. `render-server.md` (baris `KitMeta`, 7 baris `posting_kit.py`, blok kit di `render_single_batch_clip`, output ZIP/SSE), `analisis-ai.md` (`_compute_prompt_version`, `AnalyzeResponse.prompt_version`), `penyimpanan-dan-cleanup.md` (`EXPORTS_DIR/kits/` permanen), `clip-studio.md` (baris folder kit), `frontend-app.md` (`kit_meta`), `index.md`. Rentang yang bergeser digeser dari hunk `git diff`, termasuk di `pilihan-klip.md`, `sistem-update.md`, `subtitle-dan-judul.md`, `sumber-video.md`, `transkrip.md`, `unduhan-raw.md`.
CATATAN:
- Temuan uji browser, diperbaiki di task ini: untuk video upload/Drive yang dimuat dari riwayat, `handleStartBatchRender` mengirim `video_url` = URL watch YouTube buatan (`watch?v=upload_...`), dan channel upload adalah placeholder "Local Upload". `public_source_url` membuang URL untuk ID `upload_`/`gdrive_`, dan `credit_line` tidak memakai channel placeholder. Akibatnya kriteria "memuat baris kredit" berlaku untuk sumber YouTube/channel nyata; klip upload tanpa channel nyata tidak punya baris kredit (lebih baik daripada kredit palsu). Kredit wajib per campaign menunggu #20.
- `PLATFORM_RULES` nilai awal konservatif, perlu dicek pemilik terhadap aturan platform terbaru: TikTok 2200 karakter/5 hashtag, Reels 2200/5, Shorts 5000/3 (judul 100), X 280/2. Panjang dihitung `len()` Python (URL di X tidak dihitung 23 karakter seperti aturan X, jadi lebih ketat).
- Hashtag diambil dari `hashtag_suggestion` lalu dari caption (dipindah dari badan caption), huruf kecil, unik.
- `prompt_version` adalah hash kode analisis, bukan nomor versi manual: berubah juga bila `analyze.py` berubah tanpa mengubah prompt.
- `custom_prompt` di `kit_meta` diambil dari isi kolom fokus saat render; bila hasil lama dimuat dari riwayat lalu kolom itu diubah, nilainya bisa berbeda dari fokus saat analisis (hasil analisis tidak menyimpan fokusnya).
- Fallback ZIP on-the-fly di `routers/render.py` (`download_batch_zip`, hanya bila ZIP cache hilang) belum membawa folder kit (di luar area).
- Uji browser: backend sempat restart karena `smoke_test.py` disimpan saat render berjalan (jebakan no. 4); render diulang dan berhasil.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: commit `d986eea` hanya menyentuh file di Area (posting_kit.py baru, render_service.py, schemas/render.py, schemas/analyze.py, routers/analyze.py, types.ts, App.tsx, ClipStudioSection.tsx, id.ts/en.ts, smoke_test.py, codemap, CLAUDE.md, kontrak). `routers/render.py` tidak diubah. Teks prompt, `ViralClipGemini`, `VideoAnalysis`, dan pasca-proses tidak berubah: diff `analyze.py` hanya `import hashlib`, `_compute_prompt_version`/`PROMPT_VERSION`, dan argumen `prompt_version=` di dua `AnalyzeResponse`.
- Folder kit 7 file, `video.mp4` = MP4 render, SRT = baris karaoke, metadata, ZIP, retry, kit gagal: dibuktikan smoke test yang saya jalankan sendiri, `23/23 cek lulus. SMOKE TEST LULUS` dengan `[PASS] posting kit per klip (#22)` (termasuk log `Posting kit klip 1 gagal ditulis: smoke22: disk penuh` lalu klip tetap selesai). Setelah run, `~/CheatClip/kits` tidak ada.
- SRT: `build_srt` memakai `build_subtitle_events(words, text_case="original", word_replacements=...)` atas `words_used`, yang diisi dari `words` yang sama dengan masukan `generate_ass_file` (pratinjau #36b atau Whisper) hanya bila `caption_style != "none"` (`render_service.py` L278-279). Subtitle mati = SRT tidak ditulis dan SRT lama dihapus saat retry.
- Galat kit: blok `try/except` terpisah setelah MP4 valid (`render_service.py` L331-352), hanya mengisi `kit_error`; status `completed` tidak disentuh.
- ZIP: file kit ditambahkan di `kits/<NN>_<judul>/` dengan `video.mp4` dilewati (`render_service.py` L405-412); nama folder memakai prefiks NN sehingga tidak bentrok.
- Batas caption: uji mandiri `build_platform_captions` dengan caption 10.000 karakter + 9 hashtag, channel 500 karakter, judul 240 karakter, klip tanpa caption, dan caption hanya hashtag: semua platform di bawah `max_chars`, jumlah hashtag <= `max_hashtags`, judul Shorts <= 100, tidak ada yang kosong. Kredit untuk upload (`Local Upload`, URL `watch?v=upload_x`) kosong, bukan kredit palsu.
- `npm run build` exit 0. Lint (HEAD sebelum task vs sesudah, error/warning): App.tsx 23/4 = 23/4, ClipStudioSection.tsx 30/2 = 30/2, types.ts/id.ts/en.ts 0/0. `check_codemap.py`: `SEMUA CEK LULUS` (293 simbol). String `postingKitSaved` ada di id.ts dan en.ts.
- Catatan kecil (tidak memblokir): (a) fallback ZIP on-the-fly di `routers/render.py` belum membawa folder kit (sudah dicatat implementer, di luar area); (b) bila retry suatu klip gagal setelah sebelumnya sukses, `kit_dir` lama tetap ada di status klip, tetapi ZIP hanya memuat klip `completed` sehingga tidak berdampak; (c) `prompt_version` berubah setiap `analyze.py` berubah, bukan hanya teks prompt (disebut di kontrak).
- Perlu dicek pemilik: caption terasa layak diunggah, nilai `PLATFORM_RULES` (TikTok/Reels 2200/5, Shorts 5000/3 judul 100, X 280/2) sesuai aturan platform terbaru, panel Clip Studio menampilkan baris folder kit, dan alur unggah manual dari folder kit nyaman.
