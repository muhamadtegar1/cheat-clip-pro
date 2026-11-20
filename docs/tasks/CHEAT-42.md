# CHEAT-42: Analisis Gemini tahan server sibuk
Status: REVIEW

## Tujuan
Gangguan 503/500 sesaat dari Gemini dipulihkan dengan coba ulang pada model yang sama sebelum pindah model, rantai cadangan tidak lagi berisi Flash preview bertetangga saja, pemilik bisa mengunci ke model pilihan, hasil dari model cadangan diberi lencana, dan pesan 503/429 jujur.

## Area yang boleh disentuh
- `backend/routers/analyze.py`:
  - pilih model + daftar fallback (± L1151-1182): rantai dibangun lewat helper baru, mode "hanya model pilihan".
  - panggilan Gemini + retry (± L1184-1379): `MAX_RETRIES = 1` diganti coba ulang 503/500 dengan jeda bertahap + acak, hormati `Retry-After` bila ada; 429 dan 404 tetap langsung pindah model; event SSE "Transient Retry" memakai jeda sebenarnya.
  - pesan error akhir (± L1381-1412): 503 tanpa saran ganti key ("server Google penuh, tunggu 1-5 menit"), 429 tetap pesan kuota.
  - susun `AnalyzeResponse` (± L1640-1650): isi `requested_model` dan `model_fallback`.
- `backend/schemas/analyze.py`: `AnalyzeRequest` (± L56-69) field baru `strict_model: bool = False`; `AnalyzeResponse` (± L82-94) field baru `requested_model`, `model_fallback`.
- `backend/services/ai_service.py`: helper baru murni `build_model_fallback_chain(requested, discovered, strict)` (urutan: model diminta, lalu `gemini-2.5-flash` stabil bila bukan yang diminta, lalu Flash lain terurut seperti sekarang, maks 4; `strict` = hanya model diminta) dan konstanta jeda retry. `get_flash_models_for_key` dan `KNOWN_FLASH_MODELS` tidak diubah kecuali perlu untuk helper.
- `src/types.ts`: `AnalyzeResponse` (+ `requested_model?`, `model_fallback?`).
- `src/App.tsx`: state + `localStorage` (dibungkus try/catch) untuk "hanya model pilihan" di dekat `selectedModel` (± L100-110), kotak centang di bawah pilihan model (± L3030-3065), `strict_model` di body `/api/analyze` (± L1594), lencana "model cadangan" di baris ringkasan hasil di samping "Model AI:" (± L4450-4460).
- `src/locales/id.ts`, `src/locales/en.ts`: teks kotak centang, lencana, dan `resilienceDesc` diperbarui agar sesuai perilaku baru.
- `scripts/smoke_test.py`: `FakeGeminiClient` mode baru + cek (lihat Cara menguji). Jeda retry di-nol-kan lewat konstanta modul selama tes.
- `docs/codemap/analisis-ai.md`, `docs/codemap/frontend-app.md`: rentang baris dan perilaku baru.

## Di luar scope (jangan dikerjakan)
- Teks prompt, deskripsi field `ViralClipGemini`/`VideoAnalysis`, pasca-proses klip (golden tidak perlu diulang). Catatan: `PROMPT_VERSION` (#22) tetap berubah karena dihitung dari isi `routers/analyze.py`; itu metadata, bukan perubahan prompt.
- Coba ulang otomatis dengan hitung mundur setelah semua model gagal 503 (opsional di TASKS.md, ditunda agar task kecil; bisa jadi task terpisah).
- Lencana per kartu klip dan field `model_fallback` di `kit_meta`/posting kit (#22) atau data Pakai/Lewati (#35).
- Dropdown daftar model (`list_available_gemini_models`), mode mock, cache riwayat `localStorage` (hasil lama tanpa field baru = tanpa lencana).
- Panggilan Gemini lain di luar `analyze_video`.

## Keputusan yang boleh diambil AI sendiri
- Angka jeda persis (sekitar 3/8/20 s + acak ±25%, maks 3 percobaan per model) dan batas atas `Retry-After` (mis. 30 s).
- Timeout 120 s tidak dicoba ulang pada model yang sama (langsung model berikut), agar satu model tidak menahan analisis > 6 menit.
- Nama field, kunci `localStorage`, dan gaya lencana mengikuti pola yang ada.
- Pesan error backend tetap bahasa Inggris seperti pesan lain di endpoint ini.

## Kriteria selesai (ya/tidak)
- [x] Mock 503 sementara (gagal 2x lalu sukses) pulih pada model yang sama: hanya model diminta yang dipanggil, tidak ada event "Flash Fallback", `model_fallback` false.
- [x] 503 terus-menerus berakhir dengan status 503 dan pesan tanpa saran ganti API key; tiap model dicoba maksimal 3 kali.
- [x] 429 tetap langsung pindah model (1 panggilan per model) dan berakhir dengan pesan kuota status 429.
- [x] Rantai cadangan: setelah model diminta, `gemini-2.5-flash` lebih dulu dari Flash preview lain (bila bukan model diminta), maks 4.
- [x] `strict_model: true` tidak pernah memanggil model lain (503 dan 429).
- [x] Hasil dari model cadangan: `model_fallback` true, `requested_model` terisi, lencana tampil di ringkasan hasil; hasil dari model diminta tanpa lencana. (field dibuktikan smoke test; tampilan lencana belum diuji di browser)
- [x] Kotak centang "hanya model pilihan" tersimpan, dua bahasa, `localStorage` diblokir tidak menjatuhkan App. (kode: baca/tulis dalam try/catch, teks di id/en; belum diuji di browser)
- [x] Smoke test, `npm run build`, `scripts/check_codemap.py` lulus; `npm run lint` tanpa error baru.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`: cek baru dengan `FakeGeminiClient` (jeda retry di-nol-kan): `busy_then_ok` (503, 503, sukses), `busy` (503 terus), `rate_limit` (cek lama + jumlah panggilan per model), `strict` untuk 503 dan 429, fallback 429 lalu sukses di model kedua (`model_fallback` true), dan urutan `build_model_fallback_chain`.
- `npm run build`, `npm run lint`, `venv\Scripts\python.exe scripts\check_codemap.py`.
- Browser (key `mock` tidak melewati Gemini, jadi cukup cek UI): kotak centang tersimpan setelah reload, lencana dicek dengan hasil yang `model_fallback` true (mis. dari respons yang dipalsukan) bila memungkinkan.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH: `backend/routers/analyze.py`, `backend/schemas/analyze.py`, `backend/services/ai_service.py`, `src/App.tsx`, `src/types.ts`, `src/locales/id.ts`, `src/locales/en.ts`, `scripts/smoke_test.py`, `docs/codemap/` (analisis-ai, frontend-app, sumber-video, transkrip, pilihan-klip, unduhan-raw, penyimpanan-dan-cleanup, sistem-update: rentang baris)
HASIL_TEST:
- Smoke test 30/30 lulus, termasuk 7 cek baru #42: urutan rantai (`gemini-3.8-flash` → `gemini-2.5-flash` → 3.7 → 3.6; strict = 1 model), Retry-After (5 → 5, 120 → 30, tanggal/tanpa header → None), 503 2x lalu sukses = 3 panggilan model yang sama tanpa "Flash Fallback" dan `model_fallback` false, 503 terus = 4 model x 3 percobaan, status 503, pesan tanpa "change", 429 = 4 model x 1 panggilan tanpa "Transient Retry", 429 lalu sukses = `gemini-2.5-flash` dengan `model_fallback` true dan `requested_model` terisi, strict 503 = 3 panggilan model yang sama dan strict 429 = 1 panggilan, keduanya tanpa model lain. Cek lama `RATE_LIMIT -> 429` tetap 4 model.
- `npm run build` lulus. `eslint src/App.tsx`: 27 masalah, sama persis dengan `App.tsx` di HEAD (tanpa masalah baru); `types.ts` dan locales bersih.
- `scripts/check_codemap.py`: SEMUA CEK LULUS (298 simbol).
- Uji browser belum dijalankan (kotak centang dan lencana hanya dicek lewat build dan smoke backend).
CODEMAP_DIPERBARUI: ya. `analisis-ai` (rantai model, retry, pesan error, field respons/request, helper `ai_service`, catatan smoke), `frontend-app` (`strictModel`, kotak centang, `strict_model` di request, lencana, kunci `localStorage`), rentang baris yang bergeser di catatan lain.
CATATAN:
- Timeout 120 s tidak dicoba ulang di model yang sama (langsung model berikut), sesuai keputusan di kontrak.
- Bila satu model kena 429 dan model lain 503, pesan akhir tetap pesan kuota (prioritas lama `encountered_quota_error` dipertahankan).
- `PROMPT_VERSION` (#22) berubah karena isi `routers/analyze.py` berubah; teks prompt tidak berubah.
- Hasil di cache riwayat lama tidak punya `model_fallback`, jadi tampil tanpa lencana.
- Worktree memakai `node_modules` checkout utama lewat junction (di-ignore git) agar build dan `check_codemap.py` jalan.
- Perbaikan temuan minor reviewer `/tutup` (PASS): (1) event "Flash Fallback" menyebut "still busy after N attempts" hanya untuk 503/500, error lain "failed"; (2) `GEMINI_BUSY_RETRY_DELAYS` jadi (3, 8) karena maks 3 percobaan hanya memakai 2 jeda (20 s tidak pernah terpakai); (3) pesan 429 mode `strict_model` menyebut model diminta saja, bukan "across all available models" (cek smoke ditambah). Smoke 30/30, codemap lulus setelah perbaikan.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
