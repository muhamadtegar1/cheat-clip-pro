---
fitur: analisis AI (pencarian klip viral)
file_utama: [backend/routers/analyze.py, backend/schemas/analyze.py, backend/services/ai_service.py, backend/utils/text.py]
---
# Analisis AI

`POST /api/analyze` adalah **satu generator async sepanjang ±1300 baris** (`analyze_video`, L278-1630) yang mengalirkan progres lewat SSE lalu mengirim `{"done": true, "result": AnalyzeResponse}`. Catatan ini mencakup langkah 4 (prompt + Gemini) dan pasca-proses. Langkah 1 sampai 3 ada di [[sumber-video]] dan [[transkrip]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | `analyze_video` | L278-1630 | Endpoint SSE, berisi semua langkah |
| `backend/routers/analyze.py` | cek API key + mode mock | L282-287 | Key `mock` mengaktifkan data contoh tanpa Gemini |
| `backend/routers/analyze.py` | mock short-circuit | L892-960 | Klip dan heatmap contoh, lalu `done` |
| `backend/routers/analyze.py` | target jumlah klip | L963-1014 | `target_clip_count` atau otomatis berdasarkan durasi. Sejak #12 rentang adalah batas atas ("QUALITY OVER QUANTITY"), boleh lebih sedikit |
| `backend/routers/analyze.py` | bahasa + dump transkrip + durasi | L1016-1062 | `detect_transcript_language`, batas 2000/3500 baris, `duration_instruction`, `custom_prompt` |
| `backend/routers/analyze.py` | teks prompt | L1064-1120 | `has_focus` + `scoring_instruction` (aturan skor 7 dimensi independen, `score_reason` merujuk transkrip tanpa klaim pasti viral, judul/hook tanpa fakta baru, `needs_context`, kandidat beragam; #1), lalu prompt utama: konteks, aturan bahasa, aturan judul, transkrip dalam `<TRANSCRIPT_DATA>` (data, bukan instruksi), aturan kutipan satu potongan bersambung di dalam klip (#12) |
| `backend/routers/analyze.py` | pilih model + daftar fallback | L1122-1159 | Model diminta, lalu model Flash lain, dipotong maksimal 4 total |
| `backend/routers/analyze.py` | panggilan Gemini + retry | L1161-1389 | `generate_content` dengan `response_schema=VideoAnalysis`, timeout 120 s, heartbeat SSE |
| `backend/routers/analyze.py` | batas 90 s + guardrail | L1391-1428 | `guard_clips` (fungsi lokal): urutkan start/end, jepit ke `start_bound`/`end_bound` (catat `clamped`), batas 90 s (mode auto), lalu `apply_guardrails` (#12) |
| `backend/routers/analyze.py` | klip fallback dari heatmap | L1430-1518 | Kalau AI mengembalikan 0 klip atau guardrail membuang semuanya. `pick_fallback_spans` (fungsi lokal): kandidat urut engagement, dijepit ke `start_bound` (#29), jarak awal >= 25 s, akhir `min(end_bound, start + target)` dengan target per klip yang diterima, kandidat yang menimpa klip lain atau < 10 s dilewati (turun ke 5 s bila tidak ada klip sama sekali), maks 5 (#30). Klip fallback ikut lewat `guard_clips` (`fallback_clips` di ringkasan) |
| `backend/routers/analyze.py` | SSE verifikasi + guardrail | L1520-1543 | Event "Clip Verification & Alignment" (jumlah setelah guardrail) dan "Clip Guardrails" (`guardrails`) |
| `backend/routers/analyze.py` | rekonstruksi klip final | L1545-1579 | Transkrip per klip, sanitasi judul, hashtag huruf kecil, `guardrail_notes` |
| `backend/routers/analyze.py` | susun `AnalyzeResponse` | L1580-1620 | Maks 200 klip, heatmap, transkrip, ringkasan |
| `backend/routers/analyze.py` | `parse_lenient_json_analysis` | L132-228 | Perbaiki JSON rusak/terpotong dari model |
| `backend/routers/analyze.py` | `apply_clip_scores` | L74-103 | Task #1: `scores` dari field datar `score_<dimensi>`, total = rata-rata dimensi tersedia (`prompt_match` hanya bila `has_focus`), `score_label` strong >= 80 / fair 60-79 / weak < 60, urut total turun. Klip tanpa skor lengkap tidak diubah. Dipanggil sekali setelah parse (jalur `parsed` dan parser toleran) |
| `backend/routers/analyze.py` | `_score_fields` | L66-71 | Salin field skor datar, `score_reason`, `needs_context` dari dict klip (dipakai `_format_parsed_dict`) |
| `backend/routers/analyze.py` | `_format_parsed_dict` | L106-129 | Normalisasi hasil parse |
| `backend/routers/analyze.py` | `health_check` | L235-261 | `GET /api/health` |
| `backend/routers/analyze.py` | `list_available_models` | L271-274 | `GET /api/models` |
| `backend/schemas/analyze.py` | `ClipScores` | L4-12 | 7 skor 0-100, `prompt_match` None tanpa fokus pencarian (#1) |
| `backend/schemas/analyze.py` | `ViralClip` | L14-29 | Klip yang dikirim ke frontend, termasuk `guardrail_notes` (#12) dan `scores`, `score_reason`, `needs_context`, `score_label` (#1, ditampilkan di #1b; None untuk klip fallback) |
| `backend/schemas/analyze.py` | `ViralClipGemini` | L31-48 | Skema output yang diminta dari Gemini (deskripsi field ikut jadi instruksi). Sejak #1 tanpa `virality_score`; skor datar `score_<dimensi>` (bukan objek bersarang, karena regex parser toleran tidak membaca kurung bersarang), `score_reason`, `needs_context` |
| `backend/schemas/analyze.py` | `VideoAnalysis` | L50-52 | `summary` + `clips` |
| `backend/schemas/analyze.py` | `AnalyzeRequest` | L54-66 | Input endpoint |
| `backend/schemas/analyze.py` | `AnalyzeResponse` | L79-90 | Output akhir |
| `backend/services/ai_service.py` | `get_flash_models_for_key` | L41-70 | Model Flash yang tersedia untuk key |
| `backend/services/ai_service.py` | `list_available_gemini_models` | L73-134 | Daftar model untuk dropdown UI |
| `backend/utils/text.py` | `sanitize_first_person_title` | L361-411 | Buang sudut pandang orang pertama dari judul |
| `backend/utils/text.py` | `lowercase_hashtags_in_string` | L136-140 | Hashtag huruf kecil |
| `backend/utils/clip_guardrails.py` | `apply_guardrails` | L94-178 | Guardrail #12: timestamp dijepit ke rentang (klip < `MIN_CLIP_SECONDS` 5 s dibuang, hook diperbaiki), kutipan diverifikasi/diganti, overlap > 70% digabung (skor tertinggi), 40-70% ditandai |
| `backend/utils/clip_guardrails.py` | `quote_is_grounded` | L64-69 | Kutipan (per potongan "...") ada di transkrip ±5 s dari klip, fuzzy `QUOTE_MATCH` 0,85 |
| `backend/utils/clip_guardrails.py` | `fill_quote` | L72-83 | Pengganti kutipan: baris di dalam klip dengan engagement tertinggi, lalu terpanjang |

## Input / output
- Input: `AnalyzeRequest` (`url`, `duration` 15s/30s/60s/auto, `api_key`, `model`, `custom_prompt`, `range_start/end`, `subtitles`, `target_clip_count`, `proxy`, `cookies`).
- Output SSE: event progres `{step, step_progress, overall_progress, stage, detail, message}` (stage "Clip Guardrails" juga membawa `guardrails`: ringkasan jumlah klip/kutipan yang diubah), event error `{error, status}`, event akhir `{done: true, result}`.
- Konsumen: `handleAnalyze` di [[frontend-app]] membaca stream dan menyimpan hasil ke cache `localStorage`.

## Risiko
- Fungsi raksasa. Ubah per potongan, jangan pindahkan blok tanpa alasan. Semua langkah berbagi variabel lokal (`duration`, `heatmap`, `enriched_transcript`, `is_mock`). Dengan `range_start`/`range_end`, `duration` berubah menjadi panjang relatif (`end_bound - start_bound`, L875) sedangkan timestamp transkrip tetap absolut: batas klip harus memakai `start_bound`/`end_bound`, bukan `duration` (bug #29).
- Skor (#1): Gemini memberi 7 skor dimensi, backend menghitung `virality_score` (rata-rata) dan label; Prompt Match gate (#2) dan preset bobot (#3) belum. Frontend masih memakai `virality_score` (badge, filter "high" >= 90 yang kini jarang terisi karena rata-rata dimensi lebih rendah dari angka lama Gemini). Validasi kutipan, overlap, dan timestamp ada di `clip_guardrails.py` (#12) dan berlaku untuk klip Gemini maupun JSON toleran, tetapi tidak untuk mode mock (short-circuit lebih awal). Ambang kutipan sengaja sama dengan penilai [[golden-fixtures]]; mengubah salah satunya membuat ukuran tidak setara.
- Mengubah deskripsi field di `ViralClipGemini` berarti mengubah prompt. Setiap perubahan prompt wajib diukur dengan [[golden-fixtures]] (`run --repeat 2 --compare`). Skrip itu mengganti `fetch_video_metadata`, `fetch_transcript`, dan `download_youtube_audio_file` di modul ini, jadi nama dan cara impornya jangan diubah.
- Aturan bahasa (zero-translation) dan aturan judul ditulis berulang di prompt dan di skema.
- Mode mock dipakai untuk uji tanpa kuota Gemini. `scripts/smoke_test.py` bergantung padanya, dan juga mengganti `genai.Client` serta `get_flash_models_for_key` di modul ini dengan klien palsu (skenario 429, JSON rusak, dan klip di luar durasi yang memicu fallback heatmap, dengan dan tanpa rentang, plus video 120 s untuk klip fallback `auto` tanpa tumpang tindih). Mengganti nama atau cara impor keduanya akan memutus smoke test.

## Terkait
[[index]] · [[sumber-video]] · [[transkrip]] · [[frontend-app]]
