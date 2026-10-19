# CHEAT-38: Model Whisper lebih akurat (ukur dulu, lalu pengaturan model)
Status: REVIEW
Risiko: sedang (model lebih besar = transkripsi lebih lambat dan RAM lebih besar di CPU; tidak menyentuh prompt Gemini)

## Tujuan
Model Whisper dipilih pemilik dari data ukur di laptop ini (waktu, RAM, akurasi bahasa Inggris dan Indonesia), lalu dipakai lewat satu pengaturan untuk transkrip analisis dan subtitle klip, menggantikan `base` yang ditulis langsung di kode.

## Kondisi sekarang (diverifikasi di kode)
- `backend/video_engine.py` `get_whisper_model` (L251-261) memuat `whisper.load_model("base")` sekali (global `_WHISPER_MODEL`, L248). Nama model ditulis langsung; tidak ada pengaturan.
- Dua pemakai model yang sama: `transcribe_local_video_file` (L647-694, transkrip analisis upload/Drive dan fallback Whisper YouTube, `initial_prompt` "Bahasa Indonesia atau English") dan `transcribe_clip_words` (L1154-1239, subtitle per kata untuk render dan pratinjau #36a, tanpa `language`/`initial_prompt`).
- `release_whisper_model` (L264-275) tidak dipanggil di mana pun.
- Paket: `openai-whisper` 20250625, `torch` 2.14.1+cpu. Mesin: Ryzen 7 5700U (8 core), RAM 15,3 GB, tanpa CUDA, jadi Whisper berjalan di CPU (`fp16=False`). Cache model: hanya `~/.cache/whisper/base.pt`.
- Codemap `subtitle-dan-judul.md` mencatat `base` tidak stabil untuk bahasa Indonesia (uji 2026-10-19: sekitar separuh baris berbeda antara dua kali jalan).
- Acuan teks yang tersedia lokal (di-ignore git, milik channel lain, jangan di-commit): `tests/golden/data/094y1Z2wpJg/transcript.json` (Veritasium, terlihat seperti caption manual bahasa Inggris). Transkrip video C (`YzDyjAsd4Z8`, Indonesia) terlihat caption otomatis, jadi tidak layak sebagai acuan.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Skrip ukur baru** `scripts/whisper_bench.py` (tidak mengimpor `backend.main`):
   - Masukan: file audio/video lokal, `--start`/`--duration` (default 60 s), file teks acuan, daftar model (default `base,small,small.en,medium,medium.en`), `--language` opsional (hanya untuk ukur, tidak menyentuh app), `--runs` (default 2).
   - Per model: waktu muat, waktu transkripsi dan faktor real-time, RAM puncak proses (Windows `GetProcessMemoryInfo` lewat `ctypes`, tanpa dependensi baru), WER terhadap acuan (normalisasi huruf kecil dan tanpa tanda baca), kestabilan (WER antara run 1 dan run 2), dan cek stempel waktu kata (urut, di dalam segmen). Memakai `transcribe` dengan opsi yang sama seperti `transcribe_clip_words` (`word_timestamps=True`, `fp16=False`).
   - Keluaran: tabel di terminal + JSON di folder yang di-ignore git.
2. **Klip ukur**: 1 klip Inggris 60 s dari video B (audio diunduh sekali dengan yt-dlp, acuan dari `transcript.json` B dipotong ke rentang yang sama) dan 1 klip Indonesia 60 s. Untuk Indonesia, pemilik menyediakan video + teks acuan yang sudah dikoreksi manual (60 s cukup), karena caption otomatis tidak layak jadi acuan.
3. **Pengaturan model**: `get_whisper_model` membaca nama model dari env `CHEAT_CLIP_WHISPER_MODEL` (bisa diisi di `backend/.env`). Kosong = default. Nama tidak dikenal = peringatan di log lalu `base`. Log mencatat model yang dimuat.
4. **Default**: tetap `base` sampai pemilik memilih dari data, lalu default diganti ke pilihan pemilik di task ini. Default **wajib model multibahasa** (`small`/`medium`, bukan `.en`), karena sebelum #39 app belum tahu bahasa audio dan model `.en` merusak video Indonesia. Model `.en` hanya diukur sebagai data untuk #39.
5. Unduhan model (small ±460 MB, medium ±1,5 GB, `.en` ukuran sama, total ±4 GB) dilakukan oleh `whisper.load_model` dari server resmi OpenAI saat skrip ukur pertama kali jalan; diberitahukan ke pemilik sebelum dijalankan.

## Area yang boleh disentuh
- `backend/video_engine.py`: `get_whisper_model` dan global di atasnya (L246-261) untuk membaca nama model dari pengaturan; fungsi kecil baru di dekatnya untuk memilih nama model (agar bisa diuji tanpa memuat model).
- `scripts/whisper_bench.py` (baru).
- `scripts/smoke_test.py`: cek baru fungsi pemilihan nama model (env kosong, valid, tidak dikenal) tanpa memuat model; cek lama tidak diubah logikanya.
- `.gitignore`: folder keluaran skrip ukur dan audio uji.
- `docs/codemap/transkrip.md`, `docs/codemap/subtitle-dan-judul.md` (model, pengaturan, risiko RAM/waktu), `docs/codemap/index.md` bila ada skrip baru yang perlu dicatat, `CLAUDE.md` (cara menjalankan skrip ukur + deskripsi smoke), `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Pilihan bahasa audio (`language`) di app dan UI: itu #39. `initial_prompt` dan opsi `transcribe` di `transcribe_local_video_file`/`transcribe_clip_words` tidak diubah.
- Pemilihan model di UI. Pengaturan cukup lewat env/`.env`.
- Ganti mesin ke `faster-whisper` atau paket lain, dan perubahan `backend/requirements.txt`. Bila data menunjukkan model yang akurat terlalu lambat di CPU, catat sebagai usulan task terpisah.
- Memanggil `release_whisper_model`, mengubah semaphore render, atau pembagian model antara analisis dan render.
- Prompt Gemini, golden fixtures, `src/`.

## Keputusan yang boleh diambil AI sendiri
- Nama fungsi, nama env (selama diawali `CHEAT_CLIP_`), format tabel/JSON skrip ukur, cara normalisasi teks untuk WER.
- Rentang 60 s yang dipakai dari video B (pilih bagian dengan ucapan rapat, tanpa musik).

## Kriteria selesai (ya/tidak)
- [x] `scripts/whisper_bench.py` jalan pada file lokal dan menghasilkan, per model: waktu muat, waktu transkripsi, faktor real-time, RAM puncak, WER terhadap acuan, kestabilan antar run.
- [ ] Tabel ukur untuk klip Inggris (5 model) dan klip Indonesia (model multibahasa: `base`, `small`, `medium`) tercatat di Laporan implementer. (Sebagian: dua klip Inggris x 5 model tercatat; klip Indonesia dilewati atas keputusan pemilik 2026-10-19, lihat CATATAN.)
- [x] Pemilik memilih model default dari tabel itu (dicatat di kontrak); default adalah model multibahasa.
- [x] `CHEAT_CLIP_WHISPER_MODEL` dipakai `get_whisper_model`; kosong = default pilihan pemilik, nama tidak dikenal = peringatan + `base`; model yang dimuat tercatat di log. Berlaku untuk transkrip analisis dan subtitle klip (satu model global yang sama).
- [x] Smoke test lulus (cek lama + cek pemilihan nama model), `check_codemap.py` lulus, `git diff` hanya menyentuh area di atas, tidak ada transkrip/audio milik channel lain yang ter-commit.

## Cara menguji
- `venv\Scripts\python.exe scripts\whisper_bench.py <audio> --start <s> --duration 60 --ref <acuan> --runs 2` untuk klip Inggris dan Indonesia.
- `venv\Scripts\python.exe scripts\smoke_test.py`
- `venv\Scripts\python.exe scripts\check_codemap.py`
- Pemilik: isi `CHEAT_CLIP_WHISPER_MODEL` (atau pakai default baru), jalankan `npm run dev`, buat pratinjau subtitle satu klip Inggris di Clip Studio; cek log backend menyebut model yang benar dan subtitle lebih akurat dari sebelumnya. Waktu tunggu pratinjau akan lebih lama sesuai tabel ukur.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/video_engine.py`: `WHISPER_DEFAULT_MODEL`/`WHISPER_FALLBACK_MODEL`/`WHISPER_KNOWN_MODELS` dan `resolve_whisper_model_name` (L250-268); `get_whisper_model` memuat model dari fungsi itu dan mencatat namanya di log (L271-282). Default `small` (keputusan pemilik 2026-10-19).
- `scripts/whisper_bench.py` (baru), `scripts/smoke_test.py` (cek `run_whisper_model_name_check`), `.gitignore` (`tests/whisper_bench/`), `CLAUDE.md` (bagian "Model Whisper (#38)" + deskripsi smoke).
HASIL_TEST:
- Smoke test 19/19 lulus setelah default `small` (cek baru: "nama model Whisper dari env (#38): kosong = small, valid dipakai, tidak dikenal = base, model tidak dimuat"). `check_codemap.py`: SEMUA CEK LULUS.
- Muat model lewat app (`backend.video_engine.get_whisper_model()` tanpa env): log "Loading Whisper 'small' model for word-level timestamps...", dimensi model 12 lapis / 768 (= `small`).
- `scripts/whisper_bench.py` dijalankan pada dua klip Inggris (tabel di bawah); `--help` jalan. Tidak ada file `tests/whisper_bench/` yang ter-stage (`git check-ignore` menunjuk `.gitignore:158`).
- Ukur bahasa Inggris (2026-10-19, `--runs 2`, bahasa ditebak Whisper, semua model mendeteksi `en`, stempel waktu kata urut di semua model). Waktu = transkripsi run tercepat; "x real" = waktu / durasi klip.

Klip 1: Veritasium `094y1Z2wpJg` 240,9-298,0 s (57,1 s, narasi studio, 164 kata acuan dari caption manual)

| Model | Transkripsi | x real | RAM puncak | WER | Kestabilan |
|---|---|---|---|---|---|
| base | 12,6 s | 0,22 | 897 MB | 6,1% | 0,0 |
| small | 41,6 s | 0,73 | 1698 MB | 2,4% | 0,0 |
| small.en | 39,8 s | 0,70 | 1798 MB | 3,7% | 0,0 |
| medium | 97,4 s | 1,71 | 4421 MB | 4,9% | 0,0 |
| medium.en | 96,4 s | 1,69 | 4628 MB | 4,3% | 0,0 |

Klip 2: Colin and Samir `hbZbPHjE8NE` 1401,2-1459,4 s (58,2 s, podcast percakapan, 233 kata acuan dari caption manual verbatim)

| Model | Transkripsi | x real | RAM puncak | WER | Kestabilan |
|---|---|---|---|---|---|
| base | 18,8 s | 0,32 | 1005 MB | 12,0% | 0,0 |
| small | 50,9 s | 0,87 | 1781 MB | 11,6% | 0,0 |
| small.en | 50,0 s | 0,86 | 1941 MB | 12,9% | 0,0 |
| medium | 154,9 s | 2,66 | 4584 MB | 13,7% | 0,0 |
| medium.en | 140,4 s | 2,41 | 4607 MB | 12,4% | 0,0 |

- Rincian kata salah (difflib terhadap acuan): sebagian besar WER sama di semua model dan berasal dari acuan, bukan dari Whisper. Klip 1: editor caption mengganti "well" jadi "but", menghapus "kind of", menulis "ended" (±2,4% di semua model). Klip 2: "going to"/"gonna", "because"/"cause", "um" dan pengulangan "if I" yang ditulis caption tetapi dirapikan Whisper, dan potongan audio menangkap awal kalimat berikutnya ("last week so I flew all of my best friends") karena waktu caption sedikit bergeser (±11% di semua model).
- Salah dengar yang nyata, klip 1: `base` "Kontorovich", "drop so low" -> "drops solo", "Brownian" -> "brownie in"; `small` tidak ada selain "drop/drops"; `small.en` "Sinai" -> "sini"; `medium` "Kontorovich", "drops solo"; `medium.en` "Sinai", "hailstones". Klip 2: perbedaan antar model hanya 1-3 kata, semuanya kata pengisi.
- Kesimpulan Inggris: `small` paling akurat di dua klip, `medium`/`medium.en` tidak lebih akurat dari `small` tetapi 2-3x lebih lambat dan RAM 2,5x lipat. `small.en` tidak lebih baik dari `small`. Semua model stabil (hasil identik antar run) untuk bahasa Inggris.
- Dampak waktu (model global yang sama untuk transkrip analisis dan subtitle klip): `small` membuat pratinjau/render subtitle klip 60 s sekitar 50 s (sebelumnya ±15-20 s), dan fallback Whisper transkrip penuh video 1 jam sekitar 45-50 menit (sebelumnya ±15-20 menit). Fallback ini hanya dipakai untuk upload/Drive dan YouTube tanpa transkrip.
CODEMAP_DIPERBARUI: ya. `transkrip.md`: baris `resolve_whisper_model_name`, `get_whisper_model`, fungsi `scripts/whisper_bench.py`, risiko model. `subtitle-dan-judul.md`: risiko model global. Rentang `backend/video_engine.py` setelah L248 digeser +21 di `arsitektur-backend.md` (termasuk rujukan impor L389), `cookies-dan-proxy.md`, `face-tracking.md`, `render-server.md`, `subtitle-dan-judul.md`, `sumber-video.md`, `transkrip.md`, `unduhan-raw.md`.
CATATAN:
- Audio uji diunduh dengan yt-dlp (klien seperti app; format `bestaudio` biasa ditolak 403) ke `tests/whisper_bench/` (di-ignore git). Model small/medium/.en (±4 GB) terunduh ke `~/.cache/whisper`.
- Keputusan pemilik (2026-10-19): **default `small`**, berdasarkan data Inggris di atas. Ukur klip Indonesia **dilewati atas keputusan pemilik**: video yang disiapkan (Raditya Dika `l5pK6sfhxt0`, 29:15-30:15) tidak punya subtitle manual, dan pemilik memilih tidak mengoreksi acuan. Akibatnya tabel Indonesia (kriteria 2) tidak ada; dasar pilihan untuk bahasa Indonesia hanya catatan #36a (`base` tidak stabil, sekitar separuh baris berbeda antar run) dan pola umum Whisper (model lebih besar memperbaiki bahasa non-Inggris lebih banyak dari bahasa Inggris), belum diukur di laptop ini.
- Nama tidak dikenal tetap jatuh ke `base` (bukan default), sesuai Desain no. 3.
- Dampak yang perlu dirasakan pemilik: pratinjau subtitle dan render klip lebih lambat (±50 s per klip 60 s di laptop ini), fallback Whisper transkrip penuh ±0,8x durasi video. Kembali ke `base` cukup dengan `CHEAT_CLIP_WHISPER_MODEL=base` di `backend/.env` lalu restart backend.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
