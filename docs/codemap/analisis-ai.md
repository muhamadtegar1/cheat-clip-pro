---
fitur: analisis AI (pencarian klip viral)
file_utama: [backend/routers/analyze.py, backend/schemas/analyze.py, backend/services/ai_service.py, backend/utils/text.py]
---
# Analisis AI

`POST /api/analyze` adalah **satu generator async sepanjang ±1300 baris** (`analyze_video`, L278-1630) yang mengalirkan progres lewat SSE lalu mengirim `{"done": true, "result": AnalyzeResponse}`. Catatan ini mencakup langkah 4 (prompt + Gemini) dan pasca-proses. Langkah 1 sampai 3 ada di [[sumber-video]] dan [[transkrip]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | `analyze_video` | L311-1680 | Endpoint SSE, berisi semua langkah |
| `backend/routers/analyze.py` | cek API key + mode mock | L315-320 | Key `mock` mengaktifkan data contoh tanpa Gemini |
| `backend/routers/analyze.py` | mock short-circuit | L928-997 | Klip dan heatmap contoh, lalu `done` |
| `backend/routers/analyze.py` | target jumlah klip | L1000-1051 | `target_clip_count` atau otomatis berdasarkan durasi. Sejak #12 rentang adalah batas atas ("QUALITY OVER QUANTITY"), boleh lebih sedikit |
| `backend/routers/analyze.py` | bahasa + dump transkrip + durasi | L1053-1095 | `detect_transcript_language`, batas 2000/3500 baris, `duration_instruction`, `heatmap_note`/`heatmap_column` dari `build_heatmap_prompt_parts` (#32), `custom_prompt` |
| `backend/routers/analyze.py` | teks prompt | L1097-1153 | `has_focus` + `scoring_instruction` (aturan skor 7 dimensi independen, `score_reason` merujuk transkrip tanpa klaim pasti viral, judul/hook tanpa fakta baru, `needs_context`, kandidat beragam; #1), lalu prompt utama: konteks, aturan bahasa, aturan judul, header transkrip `start|end[|interest]` atau `[|energy]` untuk heatmap akustik (#32), transkrip dalam `<TRANSCRIPT_DATA>` (data, bukan instruksi), aturan kutipan satu potongan bersambung di dalam klip (#12) |
| `backend/routers/analyze.py` | pilih model + daftar fallback | L1155-1186 | #42: `build_model_fallback_chain` (ai_service): model diminta, lalu `gemini-2.5-flash` (Flash stabil generasi lain), lalu Flash lain, maks 4. `strict_model` = hanya model diminta |
| `backend/routers/analyze.py` | panggilan Gemini + retry | L1188-1436 | `generate_content` dengan `response_schema=VideoAnalysis`, timeout 120 s, heartbeat SSE. #42: 503/500 dicoba ulang di model yang sama sampai `GEMINI_BUSY_MAX_ATTEMPTS` (3) dengan jeda `GEMINI_BUSY_RETRY_DELAYS` (3 lalu 8 s sebelum percobaan ke-2 dan ke-3, acak ±25%) atau `Retry-After` (maks 30 s), event SSE "Transient Retry"; 429, 404, timeout, dan error lain langsung model berikut. Pesan akhir (L1393-1436): 503/500 = server Google penuh, tunggu 1-5 menit, tanpa saran ganti key; 429 = kuota (mode `strict_model`: pesan kuota untuk model diminta saja); 503 ditambah catatan bila `strict_model`. Event "Flash Fallback" menyebut quota/404/timeout/still busy, selain itu "failed" |
| `backend/routers/analyze.py` | batas 90 s + guardrail | L1438-1475 | `guard_clips` (fungsi lokal): urutkan start/end, jepit ke `start_bound`/`end_bound` (catat `clamped`), batas 90 s (mode auto), lalu `apply_guardrails` (#12) |
| `backend/routers/analyze.py` | klip fallback dari heatmap | L1477-1565 | Kalau AI mengembalikan 0 klip atau guardrail membuang semuanya. `pick_fallback_spans` (fungsi lokal): kandidat urut engagement, dijepit ke `start_bound` (#29), jarak awal >= 25 s, akhir `min(end_bound, start + target)` dengan target per klip yang diterima, kandidat yang menimpa klip lain atau < 10 s dilewati (turun ke 5 s bila tidak ada klip sama sekali), maks 5 (#30). Klip fallback ikut lewat `guard_clips` (`fallback_clips` di ringkasan) |
| `backend/routers/analyze.py` | SSE verifikasi + guardrail | L1567-1590 | Event "Clip Verification & Alignment" (jumlah setelah guardrail) dan "Clip Guardrails" (`guardrails`) |
| `backend/routers/analyze.py` | rekonstruksi klip final | L1592-1626 | Transkrip per klip, sanitasi judul, hashtag huruf kecil, `guardrail_notes` |
| `backend/routers/analyze.py` | susun `AnalyzeResponse` | L1627-1670 | Maks 200 klip, heatmap, transkrip, ringkasan. #42: `requested_model`, `model_fallback` (model berhasil != model diminta) |
| `backend/routers/analyze.py` | `parse_lenient_json_analysis` | L149-245 | Perbaiki JSON rusak/terpotong dari model |
| `backend/routers/analyze.py` | `apply_clip_scores` | L79-108 | Task #1: `scores` dari field datar `score_<dimensi>`, total = rata-rata dimensi tersedia (`prompt_match` hanya bila `has_focus`), `score_label` strong >= 80 / fair 60-79 / weak < 60, urut total turun. Klip tanpa skor lengkap tidak diubah. Dipanggil sekali setelah parse (jalur `parsed` dan parser toleran) |
| `backend/routers/analyze.py` | `_score_fields` | L71-76 | Salin field skor datar, `score_reason`, `needs_context` dari dict klip (dipakai `_format_parsed_dict`) |
| `backend/routers/analyze.py` | `build_heatmap_prompt_parts` | L111-120 | Task #32: catatan heatmap + label kolom transkrip per sumber. `viewer` (retensi YouTube) dan heatmap kosong memakai teks lama persis; `audio` (energi audio RMS dari upload/Drive atau fallback Whisper) diberi label `audio_energy`, bukan minat penonton, hanya petunjuk lemah |
| `backend/routers/analyze.py` | `_format_parsed_dict` | L123-146 | Normalisasi hasil parse |
| `backend/routers/analyze.py` | `health_check` | L268-294 | `GET /api/health` |
| `backend/routers/analyze.py` | `list_available_models` | L304-307 | `GET /api/models` |
| `backend/schemas/analyze.py` | `ClipScores` | L6-14 | 7 skor 0-100, `prompt_match` None tanpa fokus pencarian (#1) |
| `backend/schemas/analyze.py` | `ViralClip` | L16-31 | Klip yang dikirim ke frontend, termasuk `guardrail_notes` (#12) dan `scores`, `score_reason`, `needs_context`, `score_label` (#1, ditampilkan di #1b; None untuk klip fallback) |
| `backend/schemas/analyze.py` | `ViralClipGemini` | L33-50 | Skema output yang diminta dari Gemini (deskripsi field ikut jadi instruksi). Sejak #1 tanpa `virality_score`; skor datar `score_<dimensi>` (bukan objek bersarang, karena regex parser toleran tidak membaca kurung bersarang), `score_reason`, `needs_context` |
| `backend/schemas/analyze.py` | `VideoAnalysis` | L52-54 | `summary` + `clips` |
| `backend/schemas/analyze.py` | `AnalyzeRequest` | L56-70 | Input endpoint. #39: `audio_language` (L69, kode Whisper atau None = Otomatis, divalidasi `AudioLanguage` dari `schemas/render.py`). #42: `strict_model` (L70) |
| `backend/schemas/analyze.py` | `AnalyzeResponse` | L83-97 | Output akhir. #22: `prompt_version` (L95). #42: `requested_model`, `model_fallback` (L96-97) |
| `backend/routers/analyze.py` | `_compute_prompt_version` | L248-258 | #22: `PROMPT_VERSION` (L261) = sha256 12 karakter dari `routers/analyze.py` + `schemas/analyze.py` (CRLF dinormalisasi), dihitung saat impor, diisi di respons mock (L986) dan final (L1667). Berubah setiap kode analisis berubah; dicatat di metadata posting kit |
| `backend/services/ai_service.py` | `get_flash_models_for_key` | L41-70 | Model Flash yang tersedia untuk key |
| `backend/services/ai_service.py` | `build_model_fallback_chain` | L85-95 | #42: urutan model analisis (lihat "pilih model"). Konstanta `STABLE_FALLBACK_MODEL`, `MAX_MODELS_IN_CHAIN`, `GEMINI_BUSY_*`, `GEMINI_RETRY_AFTER_CAP` di L75-82 |
| `backend/services/ai_service.py` | `gemini_retry_after_seconds` | L98-113 | #42: header `Retry-After` (detik) dari `error.response.headers`, dibatasi 30 s, None bila tidak ada/tidak valid |
| `backend/services/ai_service.py` | `list_available_gemini_models` | L116-177 | Daftar model untuk dropdown UI |
| `backend/utils/text.py` | `sanitize_first_person_title` | L361-411 | Buang sudut pandang orang pertama dari judul |
| `backend/utils/text.py` | `lowercase_hashtags_in_string` | L136-140 | Hashtag huruf kecil |
| `backend/utils/clip_guardrails.py` | `apply_guardrails` | L94-178 | Guardrail #12: timestamp dijepit ke rentang (klip < `MIN_CLIP_SECONDS` 5 s dibuang, hook diperbaiki), kutipan diverifikasi/diganti, overlap > 70% digabung (skor tertinggi), 40-70% ditandai |
| `backend/utils/clip_guardrails.py` | `quote_is_grounded` | L64-69 | Kutipan (per potongan "...") ada di transkrip ±5 s dari klip, fuzzy `QUOTE_MATCH` 0,85 |
| `backend/utils/clip_guardrails.py` | `fill_quote` | L72-83 | Pengganti kutipan: baris di dalam klip dengan engagement tertinggi, lalu terpanjang |

## Input / output
- Input: `AnalyzeRequest` (`url`, `duration` 15s/30s/60s/auto, `api_key`, `model`, `custom_prompt`, `range_start/end`, `subtitles`, `target_clip_count`, `proxy`, `cookies`, `strict_model` #42, `audio_language` #39 yang hanya dipakai jalur Whisper).
- Output SSE: event progres `{step, step_progress, overall_progress, stage, detail, message}` (stage "Clip Guardrails" juga membawa `guardrails`: ringkasan jumlah klip/kutipan yang diubah), event error `{error, status}`, event akhir `{done: true, result}`.
- Konsumen: `handleAnalyze` di [[frontend-app]] membaca stream dan menyimpan hasil ke cache `localStorage`.

## Risiko
- Fungsi raksasa. Ubah per potongan, jangan pindahkan blok tanpa alasan. Semua langkah berbagi variabel lokal (`duration`, `heatmap`, `enriched_transcript`, `is_mock`). Dengan `range_start`/`range_end`, `duration` berubah menjadi panjang relatif (`end_bound - start_bound`, L890) sedangkan timestamp transkrip tetap absolut: batas klip harus memakai `start_bound`/`end_bound`, bukan `duration` (bug #29).
- Skor (#1): Gemini memberi 7 skor dimensi, backend menghitung `virality_score` (rata-rata) dan label; Prompt Match gate (#2) dan preset bobot (#3) belum. Frontend masih memakai `virality_score` (badge, filter "high" >= 90 yang kini jarang terisi karena rata-rata dimensi lebih rendah dari angka lama Gemini). Validasi kutipan, overlap, dan timestamp ada di `clip_guardrails.py` (#12) dan berlaku untuk klip Gemini maupun JSON toleran, tetapi tidak untuk mode mock (short-circuit lebih awal). Ambang kutipan sengaja sama dengan penilai [[golden-fixtures]]; mengubah salah satunya membuat ukuran tidak setara.
- Mengubah deskripsi field di `ViralClipGemini` berarti mengubah prompt. Setiap perubahan prompt wajib diukur dengan [[golden-fixtures]] (`run --repeat 2 --compare`). Skrip itu mengganti `fetch_video_metadata`, `fetch_transcript`, dan `download_youtube_audio_file` di modul ini, jadi nama dan cara impornya jangan diubah.
- Sumber heatmap (#32): variabel lokal `heatmap_source` diisi `"viewer"` di cabang YouTube dan `"audio"` saat `compute_audio_energy_heatmap` dipakai (cabang upload/Drive dan fallback Whisper bila heatmap YouTube kosong). Jalur baru yang mengisi `heatmap` wajib mengisi `heatmap_source` juga. Golden fixtures tidak mengukur jalur akustik (hanya heatmap penonton dan kosong); smoke test memeriksa teksnya. Klip fallback heatmap dan pesan SSE langkah 2 masih memperlakukan energi audio sebagai minat penonton.
- Aturan bahasa (zero-translation) dan aturan judul ditulis berulang di prompt dan di skema.
- Mode mock dipakai untuk uji tanpa kuota Gemini. `scripts/smoke_test.py` bergantung padanya, dan juga mengganti `genai.Client` serta `get_flash_models_for_key` di modul ini dengan klien palsu (skenario 429, 503/429 per model untuk retry dan model cadangan #42 dengan `GEMINI_BUSY_RETRY_DELAYS` di-nol-kan lewat modul ini, JSON rusak, dan klip di luar durasi yang memicu fallback heatmap, dengan dan tanpa rentang, plus video 120 s untuk klip fallback `auto` tanpa tumpang tindih). Mengganti nama atau cara impor keduanya akan memutus smoke test.

## Terkait
[[index]] · [[sumber-video]] · [[transkrip]] · [[frontend-app]]
