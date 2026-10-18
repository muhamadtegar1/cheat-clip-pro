# CHEAT-1: Skor 7 dimensi per klip (backend dan golden)
Status: REVIEW
Risiko: tinggi (perubahan prompt dan skema output Gemini, wajib golden dua mode)

Dipecah atas persetujuan pemilik: task ini backend + golden; tampilan kartu klip dikerjakan di #1b.

## Tujuan
Respons `/api/analyze` membawa per klip 7 skor dimensi (Prompt Match, Hook, Retention, Clarity, Emotional Pull, Payoff, Editability), penjelasan singkat yang merujuk transkrip, kode label skor, dan tanda "butuh konteks", tanpa menurunkan kualitas pemilihan klip di golden fixtures dua mode.

## Kondisi sekarang (diverifikasi di kode)
- `backend/schemas/analyze.py`: `ViralClipGemini` (L17-26) dan `ViralClip` (L4-15) hanya punya satu `virality_score` 1-100 yang dikarang Gemini; `VideoAnalysis` (L28-30) meminta klip "sorted by virality_score desc".
- `backend/routers/analyze.py`: teks prompt L1008-1051 (diakhiri "Return clips sorted by virality_score desc"); jalur `parsed` L1195-1215 dan `_format_parsed_dict` L63-85 menyalin field per klip; parser toleran `parse_lenient_json_analysis` L88-175 mengambil `virality_score` lewat regex (default 75); mock L839-904; klip fallback heatmap L1356-1444 (skor 70-95 buatan); rekonstruksi `ViralClip` L1471-1501.
- `backend/utils/clip_guardrails.py` L146 memakai `virality_score` untuk urutan saat menggabung overlap.
- Frontend: `src/types.ts` `ViralClip` (L14-25); `src/App.tsx` kartu klip (badge skor ±L4610-4613 di dashboard hasil L4336-4817), filter/urut skor (±L2257-2279: "high" = >= 90), ekspor teks/markdown (±L1974, ±L2221); `src/components/ClipStudioSection.tsx` menampilkan `virality_score` sebagai pil (L3553-3554, L3772).
- Golden: baseline `gemini-3.8-flash`, mode biasa `ref_recall_independen` 83,3, tanpa heatmap 75,0; grounded 100, fabricated/misplaced/duplicates 0, avoid 0,5.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. Output Gemini per klip (skema `ViralClipGemini`) mendapat:
   - `scores`: objek 7 bilangan bulat 0-100 (`prompt_match`, `hook`, `retention`, `clarity`, `emotional_pull`, `payoff`, `editability`), dinilai terpisah per dimensi dengan definisi singkat di deskripsi field.
   - `score_reason`: 1-2 kalimat dalam bahasa video yang menyebut bagian transkrip (kutipan pendek atau detik) sebagai alasan; dilarang klaim "pasti viral"/jaminan.
   - `needs_context`: boolean, true bila klip butuh konteks dari luar rentangnya.
2. `virality_score` tidak lagi dikarang Gemini: dihitung backend sebagai rata-rata dimensi yang tersedia (dibulatkan). `prompt_match` hanya dinilai dan dihitung bila pengguna mengisi `custom_prompt`; tanpa itu bernilai null dan tidak ikut rata-rata. Bila `scores` tidak ada (parser toleran gagal membaca, klip fallback heatmap), perilaku lama dipertahankan dan field baru null.
3. Label dihitung backend dari total sebagai kode `score_label`: `strong` (>= 80), `fair` (60-79), `weak` (< 60). Teks tampilan (Kuat/Layak/Lemah) di #1b.
4. Aturan prompt tambahan: kandidat beragam (jenis momen dan topik berbeda, bukan variasi satu momen), skor per dimensi independen (bukan satu angka disalin ke semua), judul/hook/caption tanpa fakta yang tidak diucapkan di klip, tandai `needs_context`, tanpa klaim pasti viral. Klip tetap diurutkan dari total terbesar di backend.
5. Tidak ada perubahan UI di task ini. Frontend tetap memakai `virality_score` (badge, filter, urutan) dan mengabaikan field baru sampai #1b.

## Area yang boleh disentuh
- `backend/schemas/analyze.py`: `ViralClip`, `ViralClipGemini`, `VideoAnalysis` (deskripsi), model baru untuk skor.
- `backend/routers/analyze.py`: `_format_parsed_dict` (L63-85), `parse_lenient_json_analysis` (L88-175), mock (L839-904, contoh skor), teks prompt (L1008-1051), jalur `parsed` (L1195-1215), klip fallback heatmap (L1356-1444, hanya agar field baru null), rekonstruksi `ViralClip` (L1471-1501), fungsi kecil baru untuk total/label.
- `scripts/smoke_test.py`: JSON klien palsu memuat `scores`, cek baru bahwa total/label dihitung backend dan klip tanpa `scores` tetap jalan. Cek lama tidak diubah logikanya.
- `scripts/golden_fixtures.py`: `raw_clips` ikut menyimpan `scores`, `score_reason`, `needs_context` (untuk diperiksa), tanpa mengubah metrik.
- `tests/golden/baseline.json` dan `baseline-noheatmap.json`: hanya bila perubahan diterima pemilik (`run --save-baseline` di kedua mode setelah lulus).
- `docs/codemap/analisis-ai.md`, `docs/codemap/golden-fixtures.md`, `CLAUDE.md` bila perlu, `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Semua `src/` (tampilan skor di kartu klip = #1b), Prompt Match gate x0,85 (#2), preset bobot dan hitung ulang ranking lokal (#3), label heatmap akustik di prompt (#32).
- `ClipStudioSection.tsx`, ekspor teks/markdown/JSON (tetap memakai `virality_score`), filter "high >= 90" (catat dampaknya, jangan diubah).
- `clip_guardrails.py`, aturan bahasa/judul yang sudah ada, `labels.json`, metrik golden.

## Keputusan yang boleh diambil AI sendiri
- Nama dan bentuk persis field (dengan syarat isi desain di atas), definisi singkat tiap dimensi di deskripsi field.
- Iterasi teks prompt bila golden memburuk, selama aturan di desain tetap ada; setiap iterasi dicatat di laporan.

## Kriteria selesai (ya/tidak)
- [x] Respons `/api/analyze` (jalur Gemini dan mock) memuat per klip `scores` (7 dimensi; `prompt_match` null tanpa `custom_prompt`), `score_reason`, `needs_context`, `score_label` (`strong`/`fair`/`weak`), dan `virality_score` = rata-rata dimensi yang tersedia.
- [x] Pada run golden, setiap klip Gemini punya 7 skor (atau 6 + null) yang tidak semuanya sama, dan `score_reason` merujuk isi transkrip (dicek manual minimal 5 klip per video, dicatat di laporan); tidak ada klaim "pasti viral".
- [x] Klip tanpa `scores` (fallback heatmap, parser toleran) tetap jalan dengan field baru null dan `virality_score` seperti perilaku lama; frontend yang ada tidak rusak (`npm run build` tidak perlu karena `src/` tidak berubah).
- [x] Golden `run --repeat 2 --compare` dan `run --no-heatmap --repeat 2 --compare` keduanya exit 0 dengan `gemini-3.8-flash` (model sama dengan baseline), hasil dicatat di laporan (termasuk `ref_recall_independen`).
- [x] Smoke test lulus (12 cek lama + cek baru), `check_codemap.py` lulus, `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py`
- `venv\Scripts\python.exe scripts\golden_fixtures.py run --repeat 2 --compare` dan `run --no-heatmap --repeat 2 --compare` (±12 analisis Gemini; cek kuota dulu, satu permintaan kecil saat memilih model).
- Periksa `raw_clips` laporan golden: sebaran skor, `score_reason`, `needs_context`.
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Wajib `/review 1` di sesi baru sebelum DONE (risiko tinggi: perubahan prompt dan skema).

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/schemas/analyze.py`: model baru `ClipScores` (7 skor opsional); `ViralClip` + `scores`, `score_reason`, `needs_context`, `score_label` (semua opsional, None untuk klip tanpa skor), deskripsi `virality_score` (dihitung backend); `ViralClipGemini` tanpa `virality_score`, + `score_prompt_match`, `score_hook`, `score_retention`, `score_clarity`, `score_emotional_pull`, `score_payoff`, `score_editability`, `score_reason`, `needs_context` (datar); `VideoAnalysis` "strongest first".
- `backend/routers/analyze.py`: `SCORE_DIMENSIONS`, `_score_fields` (L66-71), `apply_clip_scores` (L74-103: total = rata-rata dimensi tersedia, `prompt_match` hanya bila `has_focus`, label strong >= 80 / fair 60-79 / weak < 60, urut total turun, klip tanpa skor lengkap tidak diubah); `_format_parsed_dict` + field skor; parser toleran: regex per `score_<dimensi>`, `score_reason`, `needs_context`; mock: 3 klip dengan skor (rata-rata = 95/88/72 lama); prompt: `has_focus` + `scoring_instruction` (L1064-1074) dan "Return clips ordered from strongest to weakest overall"; jalur `parsed` menyalin field skor; satu titik hitung `apply_clip_scores` tepat setelah parse (sekarang L1294-1295, jalur `parsed` dan teks); rekonstruksi `ViralClip` meneruskan field baru.
- `scripts/smoke_test.py`: `SCORED_CLIPS`/`SCORED_JSON`/`SCORED_TRUNCATED`, mode klien palsu `scored`/`scored_truncated`, cek baru `run_score_check`, docstring.
- `scripts/golden_fixtures.py`: `raw_clips` ikut menyimpan `scores`, `score_reason`, `needs_context`, `score_label`.
- `docs/codemap/analisis-ai.md`, `golden-fixtures.md`, `sumber-video.md`, `transkrip.md`, `CLAUDE.md` (jebakan no. 5 L278-1630, deskripsi smoke test).
HASIL_TEST:
- Smoke test: 13/13 lulus. Cek baru: "scored [87, 65]; scored+fokus [89, 61]; scored_truncated [87, 65]; mock bertanda skor" (total = rata-rata 6 dimensi, atau 7 dengan fokus; urutan dari backend; JSON terpotong dibaca regex parser toleran). Cek lama tetap lulus (MALFORMED_JSON, fallback heatmap dengan klip tanpa skor, dll.).
- Golden dengan kode akhir (prompt tanpa kalibrasi), key lama, `gemini-3.8-flash` di semua analisis:
  - `run --repeat 2 --compare` (laporan 20261017-204540): exit 0, "tidak ada metrik yang lebih buruk". grounded 100, fabricated/misplaced/duplicates 0, valid 100, `ref_recall_independen` 83,3 (= baseline), avoid 0,5 -> 1,5 (naik dalam variasi), heat_lift 1,496 -> 1,477; info: `ref_recall` 70,85 -> 79,15, `ref_recall_gemini` 58,35 -> 75,0.
  - `run --no-heatmap --repeat 2 --compare` (20261017-205026-noheatmap): exit 0. `ref_recall_independen` 75,0 (= baseline), metrik lain sama, avoid 0,5; info: `ref_recall` 83,3 -> 75,0, `ref_recall_gemini` 91,65 -> 75,0.
- Pemeriksaan skor (dari laporan golden di atas, 124 klip): semua klip punya 6 skor + `prompt_match` null (tanpa fokus), tidak ada klip yang semua dimensinya sama, 0 klaim "pasti viral/guaranteed/definitely", `needs_context` true di 5 (biasa) dan 10 (tanpa heatmap) klip. `score_reason` dicek manual 5 klip pertama tiap video (run 1 mode biasa): semuanya menyebut detik dan isi spesifik transkrip; klaim angka "42%" di video A dicocokkan ke transkrip (diucapkan).
- `check_codemap.py`: SEMUA CEK LULUS. `npm run build` tidak dijalankan (`src/` tidak berubah).
- Baseline golden tidak diperbarui (penentu `ref_recall_independen` sama dengan baseline; menyimpan run dengan avoid "naik dalam variasi" malah melonggarkan patokan).
CODEMAP_DIPERBARUI: ya. `analisis-ai.md`: baris baru `apply_clip_scores`, `_score_fields`, `ClipScores`; deskripsi `ViralClip`, `ViralClipGemini` (alasan skor datar), label "teks prompt" L1064-1120; semua rentang `analyze.py` dan `schemas/analyze.py` dipetakan ulang (difflib HEAD -> kerja) dan dicek ke kode; risiko skor diperbarui. `golden-fixtures.md`: `raw_clips` memuat skor + rentang bergeser. `sumber-video.md`, `transkrip.md`: rentang `analyze.py` bergeser.
CATATAN:
- Keputusan sendiri: skor datar di output Gemini (bukan objek bersarang) karena regex fallback parser toleran (`\{[^{}]*?...\}`) tidak membaca kurung bersarang dan akan kehilangan klip dari JSON terpotong; backend menyusunnya jadi objek `scores`. `virality_score` dihapus dari skema Gemini agar tidak menjangkar skor dimensi. `prompt_match` diminta 0 tanpa fokus lalu dibuang backend.
- Di luar rentang area yang tertulis: titik panggil `apply_clip_scores` di L1294-1295 (nomor sebelum task: ±L1221; blok `if parsed_data is not None`, tepat setelah jalur `parsed` L1195-1215 di kontrak) agar satu titik melayani jalur `parsed` dan teks.
- TEMUAN UTAMA (untuk pemilik, memengaruhi #1b/#2/#3): skor Gemini menggelembung dan tidak membedakan pilihan pemilik.
  - Kode akhir: semua 124 klip berlabel strong, total 83-95, tiap dimensi rata-rata ±89.
  - Skor momen yang disetujui pemilik di K3 vs yang ditolak (A2, A3, A★1, B3, B4, B★3, C1, C3, C5, C★2): 90,1 vs 88,7 (biasa), 81,6 vs 79,4 (tanpa heatmap, run lama 3.7), selisih 1-2 poin.
- Percobaan kalibrasi (atas persetujuan pemilik, lalu DIKEMBALIKAN): aturan skala (50 biasa, 70 bagus, 85+ hanya 1-2 momen istimewa, setiap klip punya kelemahan < 70). Run pertama terhenti kuota (key lama). Run penuh dengan key baru: mode biasa exit 3 (avoid 0,5 -> 2,0 LEBIH BURUK, video C sekali jatuh ke 3.7-flash), tanpa heatmap exit 2 (`ref_recall_independen` 75,0 -> 58,35 LEBIH BURUK, momen independen A terlewat di kedua ulangan). Label jadi 46 strong/13 fair dan 45/19, tetapi skor disetujui vs ditolak tetap 83,1 vs 82,1 dan 81,9 vs 79,9. Kesimpulan: kalibrasi lewat prompt merusak pemilihan klip tanpa membuat skor lebih cocok dengan selera pemilik. Teks kalibrasi dihapus; kode akhir identik dengan yang lulus golden (smoke 13/13, codemap lulus setelah pengembalian).
- Rekomendasi: skor 7 dimensi dipakai sebagai penjelasan klip, bukan dasar ranking. #1b sebaiknya tidak menonjolkan label (selalu "Kuat"); #2 (gate Prompt Match < 50) hampir tidak akan terpicu; #3 (preset bobot) perlu dasar ranking lain, mis. heatmap penonton (menangkap 6 dari 12 momen pilihan pemilik di K3). Perlu dibahas sebelum #1b/#2/#3.
- Frontend tidak berubah: badge/filter/urutan memakai `virality_score` yang kini rata-rata dimensi (83-95); filter "high >= 90" lebih jarang terisi dibanding angka lama Gemini.
- API key Gemini diganti pemilik di tengah task (kuota key lama habis); key baru juga memakai `gemini-3.8-flash`.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: commit `8162387` hanya menyentuh `backend/schemas/analyze.py`, `backend/routers/analyze.py`, `scripts/smoke_test.py`, `scripts/golden_fixtures.py`, `CLAUDE.md`, `docs/codemap/` (4 catatan) dan kontrak ini. Tidak ada `src/`, `clip_guardrails.py`, `labels.json`, atau baseline. Titik panggil `apply_clip_scores` (`analyze.py` L1294-1295) sedikit di luar rentang baris tertulis, tetapi di blok jalur `parsed`/teks yang memang disebut kontrak dan sudah dicatat implementer.
- Kriteria 1 (field respons): `ViralClip` + `scores`/`score_reason`/`needs_context`/`score_label` (`schemas/analyze.py` L16-31); `apply_clip_scores` (`analyze.py` L74-103) menghitung total = rata-rata dimensi tersedia, `prompt_match` dibuang tanpa `has_focus` (L1064), label 80/60. Mock membawa skor (L912-933). Dibuktikan smoke test sendiri: cek "skor 7 dimensi" lulus untuk JSON utuh, dengan fokus, terpotong, dan mock.
- Kriteria 2 (skor golden): laporan golden saya `20261017-215826.json` (3.8-flash, 64 klip): semua 6 skor + `prompt_match` null, 0 klip dengan semua dimensi sama, 0 klaim "pasti viral" (satu kecocokan kata "guarantee" di run 3.6-flash adalah isi materi: "cannot guarantee a mathematical proof", bukan klaim viral). 15 `score_reason` (5 per video, run 1) dibaca: semuanya menyebut detik dan isi spesifik transkrip.
- Kriteria 3 (klip tanpa skor): `apply_clip_scores` melewati klip tanpa 6 skor inti (field baru None, `virality_score` tidak diubah); smoke test fallback heatmap dan MALFORMED_JSON tetap lulus. `src/` tidak berubah.
- Kriteria 4 (golden dua mode): mode biasa saya jalankan sendiri, `run --repeat 2 --compare` exit 0 dengan 3.8-flash di ketiga video, `ref_recall_independen` 83,3 (= baseline), avoid 0,5 (= baseline), grounded 100, karangan/salah tempat/duplikat 0. Mode tanpa heatmap TIDAK bisa saya ulang setara: kuota harian 3.8-flash habis (429, limit 20), run jatuh ke 3.6-flash dan exit 3 (model berbeda, `ref_recall_independen` 58,35, tidak setara). Bukti mode ini hanya laporan implementer `20261017-205026-noheatmap.json` (ada di disk, `models_used` 3.8-flash di A/B/C, `ref_recall_independen` 75,0, avoid 0,5, memuat field skor sehingga dibuat dengan kode skor). Diterima sebagai bukti, tetapi ditandai: lihat catatan pemilik.
- Kriteria 5: smoke test saya 13/13 lulus; `check_codemap.py` "SEMUA CEK LULUS" (16 catatan, 227 simbol).
- Kualitas: tidak ada rahasia ter-commit, tidak ada format ulang. Catatan kecil (bukan blocker): (a) di jalur `_format_parsed_dict`/`parsed`, klip Gemini yang kehilangan satu dimensi skor kini mendapat `virality_score` 0 (Gemini tidak lagi mengirim `virality_score`) dan terurut paling bawah; parser toleran memberi 75. Jarang terjadi karena skema mewajibkan semua skor. (b) `apply_clip_scores` juga mengurutkan ulang klip tanpa skor; tidak berdampak pada jalur normal.
- Perlu dicek pemilik: (1) ulangi `golden_fixtures.py run --no-heatmap --repeat 2 --compare` saat kuota 3.8-flash pulih, sebelum `/done 1` (pengukuran reviewer tanpa heatmap tidak setara); (2) temuan implementer terkonfirmasi di run saya: semua 64 klip berlabel `strong`, total 85-93, jadi label belum membedakan kualitas; putuskan arah #1b/#2/#3 sebelum lanjut; (3) coba analisis di UI: badge skor kini rata-rata dimensi dan filter "high >= 90" lebih jarang terisi.
- Tambahan 2026-10-18 (pemilik meminta, key Gemini proyek baru): `run --no-heatmap --repeat 2 --compare` diulang dan lulus, exit 0, 3.8-flash di A/B/C (laporan `20261018-143128-noheatmap.json`). `ref_recall_independen` 75,0 (= baseline), grounded 100, karangan/salah tempat/duplikat 0, avoid 1,5 (naik dalam variasi). 61 klip: semua 6 skor + `prompt_match` null, 0 klip dengan semua dimensi sama, 0 klaim viral, total 84-94. Syarat pengukuran tanpa heatmap terpenuhi. Uji UI pemilik: analisis, kartu klip, dan render jalan; 5 klip yang diambil (3 di atas 90, 2 di bawah 90) semuanya layak tayang.
