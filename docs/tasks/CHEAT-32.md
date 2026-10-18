# CHEAT-32: Label heatmap akustik yang jujur di prompt
Status: REVIEW
Risiko: sedang (perubahan teks prompt, wajib golden dua mode; jalur YouTube dan tanpa heatmap harus identik dengan sekarang)

## Tujuan
Prompt Gemini menyebut sumber heatmap dengan benar: retensi penonton YouTube tetap "audience_interest", sedangkan heatmap dari energi audio (upload, Google Drive, dan YouTube tanpa heatmap yang jatuh ke Whisper) diberi label energi audio dan diperlakukan sebagai petunjuk lemah, bukan minat penonton.

## Kondisi sekarang (diverifikasi di kode)
- `backend/routers/analyze.py` mengisi variabel `heatmap` dari tiga tempat:
  - L561 cabang YouTube: `metadata.get("heatmap")`, retensi penonton asli.
  - L405 cabang upload/Drive (`is_uploaded`, L344): `compute_audio_energy_heatmap`, energi audio (RMS).
  - L819-821 jalur Whisper: bila `heatmap` masih kosong (YouTube tanpa heatmap atau upload yang heatmap-nya kosong), `compute_audio_energy_heatmap` dari audio yang diunduh. Jadi video YouTube pun bisa memakai heatmap akustik.
- Prompt tidak membedakan sumbernya: `heatmap_note` L1048-1052 selalu "Columns: start|end|audience_interest(0-1). Prioritise high-interest peaks." bila `heatmap` terisi; header transkrip L1116 "Transcript (start|end[|interest] text)"; kolom angka per baris dari `transcript_dump` L1023-1025.
- Golden fixtures hanya menguji heatmap penonton asli (mode biasa) dan heatmap kosong (`--no-heatmap`). Jalur akustik tidak punya pengukuran golden.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. Variabel lokal `heatmap_source` di `analyze_video`: `"viewer"` saat heatmap YouTube terisi (L561), `"audio"` saat heatmap diisi `compute_audio_energy_heatmap` (L405, L821), selain itu tidak dipakai (heatmap kosong).
2. Fungsi kecil level modul, mis. `build_heatmap_prompt_parts(has_heatmap, source)`, yang mengembalikan teks `heatmap_note` dan label kolom untuk header transkrip:
   - `viewer` dan kosong: teks **persis sama** dengan sekarang (jalur YouTube dan tanpa heatmap tidak berubah satu karakter pun).
   - `audio`: label kolom `audio_energy(0-1)`, dengan penjelasan bahwa angka itu kekerasan suara, bukan minat penonton; hanya petunjuk lemah untuk momen hidup (tawa, suara meninggi, tepuk tangan); jangan memilih momen hanya karena keras; nilai klip terutama dari isi, hook, dan alur cerita.
3. Header transkrip L1116 memakai label kolom dari fungsi itu (`[|interest]` untuk viewer, `[|energy]` untuk audio).
4. Angka per baris (`transcript_dump`) tidak diubah; hanya labelnya.

## Area yang boleh disentuh
- `backend/routers/analyze.py`:
  - fungsi baru kecil level modul untuk teks heatmap prompt (dekat `apply_clip_scores`, ±L60-105);
  - cabang upload/Drive heatmap akustik (L395-436): set `heatmap_source`;
  - cabang YouTube metadata (L555-580): set `heatmap_source`;
  - jalur Whisper heatmap akustik (L819-823): set `heatmap_source`;
  - `heatmap_note` (L1048-1052) dan header transkrip di teks prompt (L1116).
- `scripts/smoke_test.py`: klien palsu menyimpan `contents` prompt; cek baru bahwa prompt jalur upload memakai label energi audio, dan fungsi teks heatmap untuk `viewer`/kosong menghasilkan teks lama persis. Cek lama tidak diubah logikanya.
- `docs/codemap/analisis-ai.md`, `docs/codemap/sumber-video.md` (rentang baris dan risiko), `CLAUDE.md` bila deskripsi smoke test perlu ditambah, `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Pesan progres SSE yang menyebut "audience interest data points" untuk heatmap akustik (L412): catat saja, tidak diubah.
- Klip fallback heatmap (L1430-1518) yang tetap memakai energi audio untuk memilih rentang.
- `compute_audio_energy_heatmap`, `get_average_heatmap_value`, cara menghitung angka engagement.
- Mode golden baru untuk heatmap akustik (butuh audio asli; jadikan task terpisah bila perlu).
- Semua `src/`, teks prompt lain (skor #1, bahasa, judul), `clip_guardrails.py`, baseline golden.

## Keputusan yang boleh diambil AI sendiri
- Nama fungsi dan variabel, kalimat persis untuk label akustik (selama isinya sesuai desain poin 2).
- Cara smoke test menangkap prompt (mis. menyimpan `contents` di `FakeGeminiClient.calls`).

## Kriteria selesai (ya/tidak)
- [x] Prompt jalur upload/Drive dan jalur Whisper dengan heatmap akustik memakai label `audio_energy` beserta peringatan "bukan minat penonton, petunjuk lemah"; tidak menyebut `audience_interest` atau "Prioritise high-interest peaks".
- [x] Teks `heatmap_note` dan header transkrip untuk heatmap YouTube dan untuk heatmap kosong identik karakter per karakter dengan sebelum task (dibuktikan smoke test terhadap string lama).
- [x] Smoke test lulus (13 cek lama + cek baru), `check_codemap.py` lulus, `git diff` hanya menyentuh area di atas.
- [ ] (sebagian: mode biasa lulus, tanpa heatmap belum diukur setara) Golden `run --repeat 2 --compare` dan `run --no-heatmap --repeat 2 --compare` keduanya exit 0 dengan `gemini-3.8-flash`, dicatat di laporan. Karena kedua jalur itu tidak berubah, hasil ini menjadi bukti tidak ada efek samping; jalur akustik sendiri tidak terukur golden (dicatat sebagai risiko).

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --repeat 2 --compare` dan `run --no-heatmap --repeat 2 --compare` (±12 permintaan 3.8-flash; jangan analisis di UI sebelum golden selesai).
- `venv\Scripts\python.exe scripts\check_codemap.py`
- Pemilik (opsional): analisis satu video upload yang punya audio, lalu cek log backend atau perilaku klip; tidak ada perubahan UI yang terlihat.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/routers/analyze.py`: fungsi baru `build_heatmap_prompt_parts` (L106-115); `heatmap_source = "audio"` di cabang upload/Drive (L416), `"viewer"` di cabang YouTube (L569), `"audio"` di fallback Whisper setelah heatmap energi audio dihitung (L836); `heatmap_note`/`heatmap_column` dari fungsi itu (L1063); header transkrip `start|end[|{heatmap_column}]` (L1127).
- `scripts/smoke_test.py`: `FakeGeminiClient.prompts` menyimpan isi prompt; `OLD_VIEWER_NOTE`/`OLD_EMPTY_NOTE`; cek baru `run_heatmap_prompt_check` (fungsi teks untuk viewer/kosong = string lama; prompt upload dengan heatmap akustik palsu memuat `audio_energy(0-1)`, "NOT viewer interest", `[|energy]`, tanpa `audience_interest`/"Prioritise high-interest"; upload dengan heatmap akustik kosong memakai teks lama); docstring.
- `CLAUDE.md`: deskripsi smoke test ditambah cek #32.
- `docs/codemap/analisis-ai.md`, `sumber-video.md`, `transkrip.md`.
HASIL_TEST:
- Smoke test: 14/14 lulus. Cek baru: "label heatmap di prompt: upload akustik = audio_energy + peringatan; YouTube dan kosong = teks lama persis".
- `check_codemap.py`: SEMUA CEK LULUS (16 catatan, 228 simbol).
- Golden mode biasa: `run --repeat 2 --compare` exit 0, 3.8-flash di 6/6 analisis (laporan 20261018-152851). `ref_recall_independen` 83,3 = baseline, grounded 100, karangan/salah tempat/duplikat 0, avoid 0,5 = baseline.
- Golden tanpa heatmap: BELUM DIUKUR SETARA. Tiga percobaan terhalang kuota/server (rincian di CATATAN): exit 3 (campuran 3.7/3.8, kuota habis), exit 2 dengan 3.8-flash penuh (independen 58,35 vs 75,0), exit 3 (kuota habis). Wajib diukur ulang dengan 3.8-flash penuh sebelum DONE.
- Bukti tambahan: prompt yang dikirim ke Gemini untuk 3 video golden x (heatmap penonton, heatmap kosong) identik byte per byte antara HEAD b47e36b dan kode ini (6 hash SHA-256 sama, klien Gemini palsu, worktree sementara sudah dihapus). Golden tidak bisa membedakan kode sebelum dan sesudah #32.
CODEMAP_DIPERBARUI: ya. `analisis-ai.md`: baris baru `build_heatmap_prompt_parts`, deskripsi "bahasa + dump transkrip" dan "teks prompt" (#32), risiko baru tentang `heatmap_source` dan jalur akustik yang tidak terukur golden, rujukan L875 -> L890, semua rentang `analyze.py` dipetakan ulang (difflib HEAD -> kerja). `sumber-video.md`: rentang + `heatmap_source` di cabang upload dan YouTube. `transkrip.md`: rentang + heatmap energi audio di fallback Whisper.
CATATAN:
- Keputusan sendiri: label `audio_energy(0-1)` dan kalimat peringatan (kekerasan suara, bukan minat penonton, petunjuk lemah untuk tawa/suara meninggi/tepuk tangan, jangan memilih momen hanya karena keras); label header `[|energy]`; angka per baris tidak diubah.
- Risiko: jalur akustik (upload/Drive/fallback Whisper) tidak punya pengukuran golden; dampaknya pada kualitas klip video upload belum terukur, hanya teksnya yang dibuktikan smoke test. Klip fallback heatmap dan pesan SSE langkah 2 ("audience interest data points", L425) masih memperlakukan energi audio sebagai minat penonton (di luar scope).
- Temuan: `ref_recall_independen` mode tanpa heatmap sangat berisik (prompt identik pernah 75,0 dan 58,35; hanya 6 referensi independen). Penentu `--compare` dengan `--repeat 2` bisa gagal tanpa perubahan apa pun; layak task kecil terpisah (repeat lebih banyak atau toleransi).
- Perlu dicek pemilik: (opsional) analisis satu video upload yang punya audio; ulangi `run --no-heatmap --repeat 2 --compare` dengan 3.8-flash penuh saat kuota pulih (jangan analisis di UI dulu).
- Draf (2026-10-18, sebelum /tutup): implementasi selesai, smoke 14/14, codemap lulus. Golden pertama TIDAK SETARA karena server/kuota, bukan prompt: mode biasa exit 1 (A run 1 gagal 503 "high demand" di semua flash; 5 analisis lain 3.8-flash, grounded 100, karangan 0, `ref_recall_independen` 91,65 dari video yang berhasil; laporan 20261018-145159), tanpa heatmap exit 3 (C run 1 jatuh ke 3.7-flash karena 429 kuota harian proyek; metrik tidak ada yang lebih buruk, `ref_recall_independen` 83,3 vs baseline 75,0; laporan 20261018-150222-noheatmap). Kuota 3.8-flash proyek baru habis s.d. ±2026-10-19 08:00. Ulangi kedua mode sebelum /tutup.
- Golden kedua (2026-10-18 15:08, key lain): mode biasa exit 3 (3.8-flash 503 saat pemilihan model, seluruh run memakai 3.7-flash; tidak ada metrik lebih buruk, independen 83,3; laporan 20261018-151600). Tanpa heatmap exit 2 dengan 3.8-flash penuh: `ref_recall_independen` 58,35 vs baseline 75,0, metrik lain sama (laporan 20261018-152109-noheatmap). Bukti bukan efek #32: prompt yang dikirim ke Gemini untuk ketiga video golden, mode heatmap penonton dan heatmap kosong, identik byte per byte antara HEAD (b47e36b) dan kode kerja (hash SHA-256 enam prompt sama; skrip pembanding memakai klien Gemini palsu, worktree HEAD sementara sudah dihapus). Angka 58,35 juga pernah muncul dengan prompt yang sama (run 3.6-flash 20261017-220505), sedangkan run 20261018-143128 dengan prompt sama mendapat 75,0: variasi model pada 6 referensi independen, bukan regresi.
- Golden ketiga (2026-10-18 ±15:20, key sama): mode biasa LULUS, exit 0, 3.8-flash di semua 6 analisis, tidak ada 429/503 (laporan 20261018-152851): `ref_recall_independen` 83,3 (= baseline), grounded 100, karangan/salah tempat/duplikat 0, avoid 0,5 (= baseline). Tanpa heatmap exit 3 (laporan 20261018-154230-noheatmap): kuota harian 3.8-flash key ini habis di tengah run (18 kali 429, 12 kali 503), A/B/C campuran 3.7/3.8-flash, tidak setara. Sesuai CLAUDE.md: mode tanpa heatmap BELUM DIUKUR SETARA; prompt jalur ini terbukti identik dengan sebelum #32 (hash), tetapi pengukuran 3.8-flash penuh tetap wajib sebelum DONE.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
