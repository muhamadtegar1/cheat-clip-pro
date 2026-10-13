---
fitur: analisis AI (pencarian klip viral)
file_utama: [backend/routers/analyze.py, backend/schemas/analyze.py, backend/services/ai_service.py, backend/utils/text.py]
---
# Analisis AI

`POST /api/analyze` adalah **satu generator async sepanjang ±1250 baris** (`analyze_video`, L224-1477) yang mengalirkan progres lewat SSE lalu mengirim `{"done": true, "result": AnalyzeResponse}`. Catatan ini mencakup langkah 4 (prompt + Gemini) dan pasca-proses. Langkah 1 sampai 3 ada di [[sumber-video]] dan [[transkrip]].

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/routers/analyze.py` | `analyze_video` | L224-1477 | Endpoint SSE, berisi semua langkah |
| `backend/routers/analyze.py` | cek API key + mode mock | L228-233 | Key `mock` mengaktifkan data contoh tanpa Gemini |
| `backend/routers/analyze.py` | mock short-circuit | L827-892 | Klip dan heatmap contoh, lalu `done` |
| `backend/routers/analyze.py` | target jumlah klip | L895-943 | `target_clip_count` atau otomatis berdasarkan durasi |
| `backend/routers/analyze.py` | bahasa + dump transkrip + durasi | L945-991 | `detect_transcript_language`, batas 2000/3500 baris, `duration_instruction`, `custom_prompt` |
| `backend/routers/analyze.py` | teks prompt | L993-1040 | Prompt utama: konteks, aturan bahasa, aturan judul, transkrip |
| `backend/routers/analyze.py` | pilih model + daftar fallback | L1042-1074 | Model diminta, lalu model Flash lain, dipotong maksimal 4 total |
| `backend/routers/analyze.py` | panggilan Gemini + retry | L1076-1299 | `generate_content` dengan `response_schema=VideoAnalysis`, timeout 120 s, heartbeat SSE |
| `backend/routers/analyze.py` | klip fallback dari heatmap | L1301-1372 | Kalau AI mengembalikan 0 klip |
| `backend/routers/analyze.py` | rekonstruksi klip final | L1385-1426 | Batas 90 s (mode auto), transkrip per klip, sanitasi judul, hashtag huruf kecil |
| `backend/routers/analyze.py` | susun `AnalyzeResponse` | L1427-1467 | Maks 200 klip, heatmap, transkrip, ringkasan |
| `backend/routers/analyze.py` | `parse_lenient_json_analysis` | L87-174 | Perbaiki JSON rusak/terpotong dari model |
| `backend/routers/analyze.py` | `_format_parsed_dict` | L62-84 | Normalisasi hasil parse |
| `backend/routers/analyze.py` | `health_check` | L181-207 | `GET /api/health` |
| `backend/routers/analyze.py` | `list_available_models` | L217-220 | `GET /api/models` |
| `backend/schemas/analyze.py` | `ViralClip` | L4-14 | Klip yang dikirim ke frontend |
| `backend/schemas/analyze.py` | `ViralClipGemini` | L16-25 | Skema output yang diminta dari Gemini (deskripsi field ikut jadi instruksi) |
| `backend/schemas/analyze.py` | `VideoAnalysis` | L27-29 | `summary` + `clips` |
| `backend/schemas/analyze.py` | `AnalyzeRequest` | L31-43 | Input endpoint |
| `backend/schemas/analyze.py` | `AnalyzeResponse` | L56-67 | Output akhir |
| `backend/services/ai_service.py` | `get_flash_models_for_key` | L41-70 | Model Flash yang tersedia untuk key |
| `backend/services/ai_service.py` | `list_available_gemini_models` | L73-134 | Daftar model untuk dropdown UI |
| `backend/utils/text.py` | `sanitize_first_person_title` | L361-411 | Buang sudut pandang orang pertama dari judul |
| `backend/utils/text.py` | `lowercase_hashtags_in_string` | L136-140 | Hashtag huruf kecil |

## Input / output
- Input: `AnalyzeRequest` (`url`, `duration` 15s/30s/60s/auto, `api_key`, `model`, `custom_prompt`, `range_start/end`, `subtitles`, `target_clip_count`, `proxy`, `cookies`).
- Output SSE: event progres `{step, step_progress, overall_progress, stage, detail, message}`, event error `{error, status}`, event akhir `{done: true, result}`.
- Konsumen: `handleAnalyze` di [[frontend-app]] membaca stream dan menyimpan hasil ke cache `localStorage`.

## Risiko
- Fungsi raksasa. Ubah per potongan, jangan pindahkan blok tanpa alasan. Semua langkah berbagi variabel lokal (`duration`, `heatmap`, `enriched_transcript`, `is_mock`).
- Skor saat ini hanya satu angka `virality_score` 1-100 (target task #1, #2). Tidak ada validasi kutipan, overlap, atau timestamp di luar durasi (target task #12).
- Mengubah deskripsi field di `ViralClipGemini` berarti mengubah prompt. Setiap perubahan prompt wajib diukur dengan [[golden-fixtures]] (`run --repeat 2 --compare`). Skrip itu mengganti `fetch_video_metadata`, `fetch_transcript`, dan `download_youtube_audio_file` di modul ini, jadi nama dan cara impornya jangan diubah.
- Aturan bahasa (zero-translation) dan aturan judul ditulis berulang di prompt dan di skema.
- Mode mock dipakai untuk uji tanpa kuota Gemini. `scripts/smoke_test.py` bergantung padanya, dan juga mengganti `genai.Client` serta `get_flash_models_for_key` di modul ini dengan klien palsu (skenario 429 dan JSON rusak). Mengganti nama atau cara impor keduanya akan memutus smoke test.

## Terkait
[[index]] · [[sumber-video]] · [[transkrip]] · [[frontend-app]]
