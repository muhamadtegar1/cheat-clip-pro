---
fitur: pilihan Pakai/Lewati pemilik per klip
file_utama: [backend/routers/choices.py, backend/services/choices_service.py, backend/schemas/choices.py, src/components/ClipChoiceControls.tsx, src/utils/clipChoices.ts]
---
# Pilihan klip (Pakai/Lewati)

Task #35. Pemilik menandai tiap klip "Pakai" atau "Lewati" (plus alasan singkat opsional) di kartu klip. Pilihan disimpan permanen bersama data klip (video, rentang, 7 skor, total, peringkat, label relatif #1b, rata-rata heatmap, model, waktu) untuk menganalisis skor vs pilihan (fondasi kalibrasi #2, #3, cikal bakal ledger #23). Terpisah dari checklist "tandai" (`markedClips`, hanya `localStorage`, untuk memilih klip render).

## Penyimpanan
- Satu file `EXPORTS_DIR/data/clip_choices.json` (default `~/CheatClip/data/`), format `{"version": 1, "records": [...]}`. Di luar folder cache, jadi auto-cleanup tidak menyentuhnya ([[penyimpanan-dan-cleanup]]).
- Satu record per (`video_id`, `start_time`, `end_time`, dibulatkan 3 desimal). Memilih ulang menimpa record (`created_at` tetap, `updated_at` baru); batal = hapus record.
- Tulis atomik: file sementara `clip_choices.json.<pid>.tmp` + `os.fsync` + `os.replace`, di bawah `threading.Lock`.
- File yang tidak bisa dibaca dipindah ke `clip_choices.corrupt-<waktu>.json` lalu mulai kosong (log peringatan). Bila backup gagal, endpoint mengembalikan 500 dan file tidak ditimpa.
- Path dibaca saat dipanggil dari `backend.config.EXPORTS_DIR` (bukan saat impor), jadi smoke test bisa mengarahkannya ke folder sementara.

## File dan fungsi kunci

| File | Simbol | Baris | Peran |
| --- | --- | --- | --- |
| `backend/schemas/choices.py` | `ClipChoiceRequest` | L10-28 | Validasi record: `choice` `use`/`skip`, `reason` maks 300, skor, peringkat, `tier`, `heatmap_avg`, model |
| `backend/schemas/choices.py` | `ClipChoiceRecord` | L31-33 | Record tersimpan + `created_at`/`updated_at` (UTC ISO) |
| `backend/services/choices_service.py` | `choices_file_path` | L33-35 | `EXPORTS_DIR/data/clip_choices.json` |
| `backend/services/choices_service.py` | `_load_records` | L50-69 | Baca file; rusak -> backup + kosong |
| `backend/services/choices_service.py` | `_write_records` | L72-79 | Tulis atomik |
| `backend/services/choices_service.py` | `save_choice` | L82-98 | Upsert satu pilihan |
| `backend/services/choices_service.py` | `delete_choice` | L101-109 | Batalkan pilihan, `False` bila tidak ada |
| `backend/services/choices_service.py` | `list_choices` | L112-117 | Semua record atau per `video_id` |
| `backend/services/choices_service.py` | `export_csv` | L120-135 | CSV satu baris per klip, skor diratakan `score_<dimensi>`, `duration`, BOM untuk Excel |
| `backend/routers/choices.py` | `get_clip_choices` | L22-26 | `GET /api/clip-choices?video_id=` |
| `backend/routers/choices.py` | `put_clip_choice` | L30-36 | `PUT /api/clip-choices` (422 bila `end_time <= start_time`) |
| `backend/routers/choices.py` | `delete_clip_choice` | L40-49 | `DELETE /api/clip-choices?video_id=&start_time=&end_time=` |
| `backend/routers/choices.py` | `export_clip_choices` | L53-71 | `GET /api/clip-choices/export?format=json` atau `format=csv` (lampiran `clip_choices-<waktu>`) |
| `src/utils/clipChoices.ts` | `heatmapAverage` | L10-21 | Rata-rata heatmap di rentang klip, ditimbang lama tumpang tindih; `null` tanpa data |
| `src/utils/clipChoices.ts` | `heatmapSource` | L24-28 | `youtube_viewers` (YouTube) atau `audio_energy` (upload/Drive, #33); `null` bila heatmap kosong |
| `src/utils/clipChoices.ts` | `computeClipRanks` | L31-38 | Peringkat `virality_score` dalam hasil analisis (skor sama berbagi peringkat) |
| `src/utils/clipChoices.ts` | `useClipChoices` | L68-152 | Hook: muat pilihan per video (`GET`), `save` (`PUT`), `clear` (`DELETE`), status per klip |
| `src/utils/clipChoices.ts` | `downloadClipChoicesExport` | L155-173 | Unduh ekspor JSON/CSV lewat blob; `false` bila gagal |
| `src/components/ClipChoiceControls.tsx` | `ClipChoiceControls` | L34-103 | Tombol Pakai/Lewati (klik pilihan aktif = batal), input alasan (simpan saat blur/Enter), status simpan |
| `src/App.tsx` | `handleExportChoices` | L2322-2326 | Tombol "Pilihan CSV/JSON" di toolbar hasil + toast |

## Input / output
- Input: klik di kartu klip; data klip dari `result` yang sedang tampil (frontend menghitung `rank`, `tier`, `heatmap_avg`).
- Output: `EXPORTS_DIR/data/clip_choices.json`, unduhan `clip_choices-<waktu>.json` atau `.csv`.

## Risiko
- Endpoint memakai guard `verify_admin_access` dari [[sistem-update]]: tanpa `ADMIN_API_KEY` hanya loopback + Origin localhost. Bila pemilik memasang `ADMIN_API_KEY`, frontend tidak mengirim key, jadi pilihan gagal disimpan (sama seperti pengaturan Gemini key).
- Prompt fokus pencarian tidak disimpan (tidak ada di `AnalyzeResponse`); `scores.prompt_match` bukan null menandai analisis dengan fokus.
- `rank`, `tier`, dan `heatmap_avg` dihitung dari hasil yang sedang tampil saat memilih. Analisis ulang video yang sama dengan rentang yang sama menimpa record lama untuk klip itu.
- Kunci klip memakai `video_id` + rentang; klip hasil trim (rentang baru) menjadi record baru.

## Terkait
[[index]] · [[frontend-app]] · [[penyimpanan-dan-cleanup]] · [[arsitektur-backend]] · [[sistem-update]]
