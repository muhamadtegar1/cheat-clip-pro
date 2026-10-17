# CHEAT-31: Golden fixtures tanpa heatmap (`run --no-heatmap`)
Status: DONE
Risiko: rendah (hanya skrip uji, backend dan prompt tidak berubah)

## Tujuan
Golden fixtures bisa mengukur kualitas analisis saat video tidak punya heatmap, dengan baseline terpisah, supaya dampak perubahan prompt (#1, #2, #32) pada jalur tanpa heatmap ikut terukur.

## Kondisi sekarang (diverifikasi di kode)
- `scripts/golden_fixtures.py` `cmd_run` (L397-525): `fake_metadata` selalu mengirim heatmap asli dari `metadata.json` ke backend. Ketiga video K3 punya heatmap YouTube, jadi jalur tanpa heatmap belum pernah diukur.
- Transkrip dikirim sebagai `subtitles`, unduh audio diblokir. Karena itu bila heatmap dikosongkan, backend tidak membuat heatmap akustik (hanya dibuat di cabang Whisper, `analyze.py` ±L755) dan prompt memakai "No audience interest data" (`analyze.py` ±L981-984), tanpa kolom engagement per baris (±L957).
- Artinya `--no-heatmap` mengukur persis jalur **YouTube tanpa heatmap**. Untuk jalur **upload/Drive** (heatmap energi audio, `compute_audio_energy_heatmap`) ini hanya pendekatan: mengukur seberapa baik analisis dari transkrip saja, bukan pengaruh heatmap akustik.
- `finish` (L575-621) dan `print_compare` (L550-572) hanya mengenal satu `BASELINE_PATH` (`tests/golden/baseline.json`). `cmd_score` (L626-655) menilai ulang memakai heatmap dari `metadata.json`.

## Area yang boleh disentuh
- `scripts/golden_fixtures.py`:
  - `cmd_run` (L397-525): opsi `--no-heatmap`, `fake_metadata` mengirim heatmap kosong. Penilaian `heat_lift` tetap memakai heatmap asli (supaya tetap terlihat apakah klip jatuh di bagian yang disukai penonton).
  - `finish` (L575-621), `print_compare` (L550-572): baseline terpisah `tests/golden/baseline-noheatmap.json` untuk mode tanpa heatmap; laporan run mencatat `heatmap: "none"` dan nama file laporan diberi akhiran `-noheatmap`.
  - `cmd_score` (L626-655): ikut mode dari laporan yang dinilai ulang (simpan/banding ke baseline yang sesuai).
  - `cmd_selftest` (L660-729): kasus baru untuk pemilihan baseline per mode.
  - `main` (±L733-760): argumen `--no-heatmap` di `run`.
  - Docstring/konstanta di awal file bila perlu.
- `tests/golden/baseline-noheatmap.json` (file baru, dibuat lewat `run --no-heatmap --save-baseline`).
- `docs/codemap/golden-fixtures.md`, `CLAUDE.md` (bagian Golden fixtures: perintah `--no-heatmap`).
- `TASKS.md` dan kontrak ini.

## Di luar scope (jangan dikerjakan)
- `backend/` apa pun: prompt, `analyze.py`, heatmap akustik (#32, #33).
- Mensimulasikan heatmap akustik (butuh audio video, unduhan YouTube diblokir di golden).
- Mengubah metrik, ambang, atau `labels.json`; mengubah `tests/golden/baseline.json`.
- `fetch`, `resolve_model`, logika retry/kuota.

## Keputusan yang boleh diambil AI sendiri
- Nama opsi, nama file baseline, dan cara mode dicatat di laporan.
- Jumlah ulangan run awal: `--repeat 2` (setara dengan baseline utama) bila kuota cukup; bila kuota habis di tengah, berhenti dan laporkan, jangan simpan baseline dari run yang gagal.
- Model run awal: sama dengan baseline utama (`gemini-3.8-flash`) agar hasil dengan dan tanpa heatmap bisa dibandingkan; bila model itu tidak tersedia, laporkan dulu sebelum memakai model lain.

## Kriteria selesai (ya/tidak)
- [x] `run --no-heatmap` mengirim heatmap kosong ke backend (dibuktikan: prompt/SSE tanpa heatmap, mis. event langkah 2 "No heatmap"), sedangkan `heat_lift` tetap dihitung dari heatmap asli.
- [x] Laporan run mode ini mencatat `heatmap: "none"` dan berakhiran `-noheatmap`.
- [x] `--save-baseline` dan `--compare` mode tanpa heatmap memakai `tests/golden/baseline-noheatmap.json`; mode biasa tetap memakai `tests/golden/baseline.json` dan perilakunya tidak berubah. `score` mengikuti mode laporan.
- [x] `run --no-heatmap --mock` dan `run --mock` jalan, `selftest` lulus (19 kasus lama + kasus baru).
- [x] Satu run Gemini `--no-heatmap --repeat 2 --save-baseline` dengan model yang sama dengan baseline utama, hasilnya (termasuk `ref_recall` dan `heat_lift`) dicatat di laporan implementer berdampingan dengan baseline utama.
- [x] `tests/golden/baseline.json` tidak berubah; `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\golden_fixtures.py selftest`
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --mock` dan `run --mock --no-heatmap` (cek nama laporan, mode tercatat, baseline biasa tidak tersentuh).
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --no-heatmap --repeat 2 --save-baseline` (memakai kuota Gemini, ±6 analisis), lalu `run --no-heatmap --compare` tidak wajib (kuota).
- `score <laporan -noheatmap> --compare` membandingkan ke baseline tanpa heatmap.
- `venv\Scripts\python.exe scripts\check_codemap.py`. Smoke test tidak wajib (backend tidak berubah), tetap dijalankan sekali sebagai pengaman.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `scripts/golden_fixtures.py`: konstanta `BASELINE_NOHEAT_PATH`; fungsi baru `heatmap_sent` (L393-400, baca event SSE `Retention Decoded`/`Dialogue Fallback`) dan `baseline_path` (L403-405); `cmd_run` (L416-553) opsi `--no-heatmap` (`fake_metadata` kirim heatmap kosong, `heatmap_sent` dicatat per video, run gagal bila backend menerima heatmap tidak sesuai mode, info `heatmap: none/youtube`); `finish` (L608-658) akhiran laporan `-noheatmap`, baseline disimpan ke file sesuai mode, baseline mode `none` mencatat `heatmap`; `print_compare` (L578-605) baseline per mode, exit 3 bila mode baseline berbeda; `cmd_score` (L663-692) mengikuti `heatmap` laporan lama; `cmd_selftest` 2 kasus baru; argumen `--no-heatmap`; docstring. `heat_lift` tetap dinilai dari heatmap asli `metadata.json`.
- `tests/golden/baseline-noheatmap.json` (baru, dari run Gemini di bawah).
- `docs/codemap/golden-fixtures.md`, `CLAUDE.md` (bagian Golden fixtures: perintah dan penjelasan `--no-heatmap`).
HASIL_TEST:
- `golden_fixtures.py selftest`: 21/21 lulus (19 lama + baseline per mode + `heatmap_sent`).
- `run --mock`: laporan `20261017-171404-mock.json`, `heatmap: youtube`, `heatmap_sent` True untuk A/B/C.
- `run --mock --no-heatmap`: laporan `20261017-171418-mock-noheatmap.json`, `heatmap: none`, `heatmap_sent` False untuk A/B/C, `heat_lift` sama dengan mode biasa (dari heatmap asli).
- `score 20261017-171418-mock-noheatmap.json --compare`: laporan `...-mock-noheatmap-rescore.json`, exit 1 "baseline baseline-noheatmap.json belum ada" (sebelum baseline dibuat).
- Run Gemini `run --no-heatmap --repeat 2 --model gemini-3.8-flash --save-baseline`: exit 0, 6/6 analisis, semua `gemini-3.8-flash` (B run 2 sempat fallback ke 3.7 lalu diulang otomatis). Laporan `20261017-171927-noheatmap.json`, baseline `tests/golden/baseline-noheatmap.json` (`heatmap: none`).
- Berdampingan (sama model, repeat 2):
  | metrik | dengan heatmap (baseline.json) | tanpa heatmap |
  | --- | --- | --- |
  | ref_recall | 70,85 | 83,3 |
  | heat_lift | 1,496 | 1,23 |
  | grounded / valid_time | 100 / 100 | 100 / 100 |
  | fabricated / misplaced / duplicates | 0 / 0 / 0 | 0 / 0 / 0 |
  | avoid_hits | 0,5 | 0,5 |
  | clips | 29 | 30,5 |
- Per sumber referensi (tertangkap dari 2 ulangan): sumber gemini 7/12 dengan heatmap vs 11/12 tanpa; sumber heatmap 8/10 vs 7/10; short 2/2 vs 2/2.
- `git diff --quiet tests/golden/baseline.json`: tidak berubah.
- `check_codemap.py`: SEMUA CEK LULUS (222 simbol). Smoke test: 11/11 lulus (pengaman, backend tidak berubah). `npm run build` tidak dijalankan (`src/` tidak berubah).
CODEMAP_DIPERBARUI: ya, `golden-fixtures.md` (rentang baris semua fungsi, baris baru `heatmap_sent` dan `baseline_path`, `cmd_run`/`finish`/`print_compare`/`cmd_score`/`cmd_selftest`, output `baseline-noheatmap.json`, risiko: `--no-heatmap` persis untuk YouTube tanpa heatmap dan hanya pendekatan untuk upload/Drive).
CATATAN:
- Keputusan sendiri: nama opsi `--no-heatmap`, file `baseline-noheatmap.json`, akhiran `-noheatmap`; field `heatmap` hanya ditulis ke baseline untuk mode `none` sehingga format `baseline.json` tidak berubah; run gagal (exit 1, baseline tidak disimpan) bila `heatmap_sent` tidak sesuai mode; `--compare` exit 3 bila mode baseline berbeda.
- Tafsiran hasil: `ref_recall` lebih tinggi tanpa heatmap BUKAN bukti tanpa heatmap lebih baik. Kenaikannya dari referensi bersumber Gemini (7/12 -> 11/12), sementara referensi bersumber heatmap turun (8/10 -> 7/10) dan `heat_lift` turun 1,50 -> 1,23. Tanpa heatmap Gemini mengikuti seleranya sendiri, jadi lebih cocok dengan referensi yang kandidatnya dari Gemini. Sampel kecil (2 ulangan) dan run berjarak 4 hari.
- Saran (di luar scope): pecah `ref_recall` per `source` di laporan golden agar efek ini langsung terlihat saat mengukur #1.
- Keputusan untuk pemilik: aturan kerja `CLAUDE.md` belum mewajibkan golden `--no-heatmap` untuk perubahan prompt (hanya ditulis "ukur di kedua mode"). Biaya ±6 analisis Gemini tambahan per perubahan.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit. Laporan run ada di `tests/golden/data/runs/` (di-ignore git).

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
