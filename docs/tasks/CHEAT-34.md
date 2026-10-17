# CHEAT-34: `ref_recall` per sumber referensi dan `ref_recall_independen`
Status: REVIEW
Risiko: rendah (hanya skrip uji dan angka baseline, backend dan prompt tidak berubah, tanpa Gemini)

## Tujuan
Golden fixtures memisahkan recall referensi menurut sumber kandidatnya dan memakai `ref_recall_independen` (referensi dari heatmap dan Short saja) sebagai penentu `--compare`, supaya perubahan prompt tidak tampak membaik hanya karena Gemini makin cocok dengan pilihannya sendiri.

## Kondisi sekarang (diverifikasi di kode)
- `scripts/golden_fixtures.py` `cmd_run` (L485) dan `cmd_score` (L680) membangun `refs` hanya dari `start`/`end`; `source` di `labels.json` tidak dibaca.
- `score_video` (L178-240) menghitung satu `ref_recall` (persen referensi yang ditutup >= 50% oleh klip, toleransi `REF_TOLERANCE`). `summarize` (L243-259) merata-ratakan per video. `compare` (L262-285) memperlakukan `ref_recall` sebagai rate penentu (turun > 5 poin = LEBIH BURUK).
- Bukti masalah (#31): tanpa heatmap `ref_recall` 70,85 -> 83,3, tetapi naiknya dari referensi bersumber gemini (7/12 -> 11/12), sementara referensi bersumber heatmap turun (8/10 -> 7/10).
- Sumber di `labels.json`: `gemini` (6), `heatmap` (5), `short+heatmap` (1).

## Area yang boleh disentuh
- `scripts/golden_fixtures.py`:
  - `cmd_run` (L485) dan `cmd_score` (L680): `refs` ikut membawa `source` (dan judul untuk rincian).
  - `score_video` (L178-240): `ref_recall` total tetap; tambah `ref_recall_independen` (referensi yang sumbernya memuat `heatmap` atau `short`), `ref_recall_gemini` (sumber `gemini` saja), dan rincian per referensi di `details` (judul, sumber, tertangkap atau tidak).
  - `summarize` (L243-259): rata-rata dua metrik baru.
  - `compare` (L262-285): `ref_recall_independen` menjadi rate penentu; `ref_recall` total dan `ref_recall_gemini` menjadi info.
  - Baris ringkasan `[ok]` per video di `cmd_run`/`cmd_score` boleh menampilkan recall independen.
  - `cmd_selftest` (L697-773): kasus baru; kasus `compare` lama disesuaikan bila perlu dengan alasan tertulis.
  - Docstring awal file (daftar metrik).
- `tests/golden/baseline.json` dan `tests/golden/baseline-noheatmap.json`: dinilai ulang dari run yang sama (`score 20261013-150232.json --save-baseline` dan `score 20261017-171927-noheatmap.json --save-baseline`), tanpa Gemini.
- `docs/codemap/golden-fixtures.md`, `CLAUDE.md` (bagian Golden fixtures, satu kalimat soal metrik penentu).
- `TASKS.md` dan kontrak ini.

## Di luar scope (jangan dikerjakan)
- `backend/` apa pun, prompt.
- `labels.json` (isi referensi dan sumbernya tetap).
- Metrik lain, ambang (`REF_TOLERANCE`, `WORSE_RATE`, dll.), aturan model/mode heatmap.
- Menjalankan Gemini.

## Keputusan yang boleh diambil AI sendiri
- Nama field tambahan dan bentuk rincian per referensi.
- Referensi tanpa `source` (label lama): dihitung di total saja, tidak di independen maupun gemini.
- Perlakuan bila video tidak punya referensi independen: metrik `None` (n/a) untuk video itu, seperti `ref_recall` sekarang.

## Kriteria selesai (ya/tidak)
- [x] Laporan run dan baseline memuat `ref_recall` (total), `ref_recall_independen`, `ref_recall_gemini`, serta rincian per referensi (judul, sumber, tertangkap).
- [x] `--compare` memutuskan LEBIH BURUK dari `ref_recall_independen` (turun > 5 poin); `ref_recall` total dan `ref_recall_gemini` hanya info.
- [x] Kedua baseline dinilai ulang dari run yang sama tanpa Gemini: semua metrik lama (termasuk `ref_recall` total 70,85 dan 83,3, `heat_lift`, `models_used`, mode heatmap) tidak berubah, hanya bertambah metrik baru.
- [x] Angka baru konsisten dengan hitungan manual #31 (sumber gemini 7/12 vs 11/12, heatmap+short 10/12 vs 9/12 di tingkat referensi-ulangan).
- [x] `selftest` lulus (21 kasus lama + kasus baru), `run --mock` dan `run --mock --no-heatmap` jalan, `check_codemap.py` lulus, `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\golden_fixtures.py selftest`
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock` dan `run --mock --no-heatmap`
- `venv\Scripts\python.exe scripts\golden_fixtures.py score 20261013-150232.json --save-baseline` dan `score 20261017-171927-noheatmap.json --save-baseline`, lalu bandingkan isi baseline sebelum dan sesudah (metrik lama identik).
- `score <laporan> --compare` untuk kedua mode: exit 0, semua "sama".
- `venv\Scripts\python.exe scripts\check_codemap.py`. Smoke test sekali sebagai pengaman (backend tidak berubah).

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `scripts/golden_fixtures.py`: fungsi baru `ref_group` (L181-188, sumber -> `independen`/`gemini`/`None`) dan `labels_refs` (L191-194, referensi dengan `title` dan `source`, dipakai `cmd_run` dan `cmd_score`); `score_video` (L197-266) menghitung `ref_recall_independen`, `ref_recall_gemini`, rincian `details.ref_hits` (judul, sumber, grup, rentang, tertangkap), `ref_recall` total tidak berubah; `summarize` rata-rata dua metrik baru; `compare` `ref_recall_independen` = rate penentu, `ref_recall` dan `ref_recall_gemini` = info; baris `[ok]` di `cmd_run`/`cmd_score` menampilkan `ref ind`; `cmd_score` menyalin `heatmap_sent` dari laporan lama (lihat CATATAN); `cmd_selftest` 3 kasus baru; docstring metrik.
- `tests/golden/baseline.json`, `tests/golden/baseline-noheatmap.json`: dinilai ulang lewat `score 20261013-150232.json --save-baseline` dan `score 20261017-171927-noheatmap.json --save-baseline`.
- `docs/codemap/golden-fixtures.md`, `CLAUDE.md` (bagian Golden fixtures: metrik penentu).
HASIL_TEST:
- `golden_fixtures.py selftest`: 24/24 lulus (21 lama tanpa perubahan + recall per sumber, independen n/a tanpa referensi independen, compare penentu independen).
- Baseline sebelum/sesudah dinilai ulang (dicek dengan skrip: semua key dan nilai lama di `total`, `per_video`, `model`, `models_used`, `duration_pref`, `repeat`, `heatmap`, `thresholds` identik): `baseline.json` True, `baseline-noheatmap.json` True. Key baru hanya `ref_recall_independen` dan `ref_recall_gemini` (total dan per_video).
- Angka baru:
  | | dengan heatmap | tanpa heatmap |
  | --- | --- | --- |
  | ref_recall_independen (penentu) | 83,3 (10/12) | 75,0 (9/12) |
  | ref_recall_gemini (info) | 58,35 (7/12) | 91,65 (11/12) |
  | ref_recall total (info) | 70,85 | 83,3 |
  Cocok dengan hitungan manual #31 di tingkat referensi-ulangan.
- `score 20261013-150232.json --compare` dan `score 20261017-171927-noheatmap.json --compare`: exit 0, semua "sama", tabel memuat `ref_recall_independen` (sama) serta `ref_recall`/`ref_recall_gemini` (info).
- Rincian `details.ref_hits` di laporan rescore berisi grup/sumber/tertangkap per referensi (mis. A ulangan 2 tanpa heatmap: kedua referensi heatmap tidak tertangkap).
- `run --mock` dan `run --mock --no-heatmap`: jalan, TOTAL memuat ketiga recall.
- `check_codemap.py`: SEMUA CEK LULUS (224 simbol). Smoke test 11/11 lulus. `npm run build` tidak dijalankan (`src/` tidak berubah). Gemini tidak dipanggil.
CODEMAP_DIPERBARUI: ya, `golden-fixtures.md` (rentang semua fungsi, baris baru `ref_group` dan `labels_refs`, `score_video`/`compare`/`cmd_score`/`cmd_selftest`, risiko: alasan dan angka baseline recall per sumber).
CATATAN:
- Perbaikan di luar rencana tetapi di area kontrak: `cmd_score` sebelumnya tidak menyalin `heatmap_sent` dari laporan lama (kekurangan #31), sehingga penilaian ulang baseline tanpa heatmap mengubah `per_video.heatmap_sent` dari False menjadi None dan melanggar kriteria "nilai lama identik". Ditambah 2 baris di `cmd_score` (hanya bila key ada, sehingga baseline.json tidak mendapat key baru).
- Keputusan sendiri: grup `independen` = sumber memuat `heatmap` atau `short` (termasuk `short+heatmap`); referensi tanpa sumber hanya masuk total; video tanpa referensi independen = n/a.
- Dampak untuk #1: penentu sekarang `ref_recall_independen` (83,3 dengan heatmap, 75,0 tanpa). Turun > 5 poin = LEBIH BURUK, setara kehilangan ±1 momen independen per ulangan di satu video.
- Kosmetik (di luar area, tidak diubah): kolom nama metrik di tabel `print_compare` selebar 12 karakter, jadi baris `ref_recall_independen` sedikit tidak rata.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
