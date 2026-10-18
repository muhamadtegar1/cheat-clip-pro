# CHEAT-35: Catat pilihan Pakai/Lewati pemilik per klip
Status: DONE
Risiko: sedang (endpoint backend baru yang menulis file permanen; tanpa perubahan prompt AI)

## Tujuan
Pemilik bisa menandai setiap klip "Pakai" atau "Lewati" (plus alasan singkat opsional) di kartu klip, dan pilihan itu tersimpan permanen di file JSON di luar cache bersama data klip (video, rentang, 7 skor, total, peringkat, label relatif, rata-rata heatmap, model, waktu) sehingga bisa diekspor untuk menganalisis skor vs pilihan (fondasi #2, #3, cikal bakal ledger #23).

## Kondisi sekarang (diverifikasi di kode)
- Kartu klip: `src/App.tsx` header kartu dengan badge skor + `ClipTierBadges` (L4614-4636), kutipan (L4638-4646), `ClipScorePanel` (L4648), saran judul/caption sesudahnya.
- Checklist "tandai" (`markedClips`, `toggleMarkedClip` L876-884) hanya di `localStorage` per video, untuk memilih klip render. Bukan pilihan kualitas dan tidak permanen.
- `AnalyzeResponse` (`src/types.ts`) punya `video_id`, `title`, `heatmap`, `model`, `video_url`, `source_type`; tidak menyimpan prompt fokus (prompt hanya ada di state form `customPrompt` L100 dan di kunci cache).
- Output permanen: `EXPORTS_DIR` (default `~/CheatClip`, env `CHEAT_CLIP_EXPORTS_DIR`) tidak pernah disentuh auto-cleanup (`docs/codemap/penyimpanan-dan-cleanup.md`).
- Router di-include di `backend/main.py` L130-135, ekspor di `backend/routers/__init__.py`. Guard `verify_admin_access` (loopback + Origin localhost) ada di `backend/routers/system.py` L60.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Penyimpanan**: satu file `EXPORTS_DIR/data/clip_choices.json` (folder dibuat bila belum ada). Struktur `{"version": 1, "records": [...]}`. Satu record per (video_id, start_time, end_time); memilih ulang menimpa record yang sama (`updated_at` baru, `created_at` tetap). Tulis atomik (file sementara + `os.replace`) dengan kunci thread, supaya file tidak rusak bila backend restart (`--reload`) di tengah tulis. File rusak tidak ditimpa diam-diam: dibaca gagal → backup `clip_choices.corrupt-<waktu>.json` lalu mulai kosong, dicatat di log.
2. **Isi record**: `video_id`, `video_title`, `video_url`, `source_type`, `start_time`, `end_time`, `clip_title`, `choice` (`use` | `skip`), `reason` (opsional, maks 300 karakter), `scores` (7 dimensi), `virality_score`, `rank` dan `rank_total` (peringkat skor dalam hasil analisis), `tier` (`priority`/`backup`/null dari #1b), `needs_context`, `heatmap_avg` (rata-rata heatmap di rentang klip, null bila heatmap kosong), `heatmap_source` (sumber heatmap bila diketahui, kalau tidak null), `model`, `created_at`, `updated_at`. Dihitung frontend dari `result` yang sedang tampil, divalidasi backend dengan Pydantic.
3. **Endpoint** (router baru `backend/routers/choices.py`, guard `verify_admin_access`):
   - `PUT /api/clip-choices`: simpan/timpa satu pilihan.
   - `DELETE /api/clip-choices?video_id=&start_time=&end_time=`: batalkan pilihan.
   - `GET /api/clip-choices?video_id=`: pilihan untuk satu video (memulihkan tombol saat hasil dibuka dari riwayat).
   - `GET /api/clip-choices/export?format=json|csv`: seluruh record untuk dianalisis (CSV: satu baris per klip, kolom skor diratakan).
4. **UI**: komponen baru `src/components/ClipChoiceControls.tsx` di kartu klip sesudah `ClipScorePanel`: tombol "✓ Pakai" / "✕ Lewati" (klik lagi pada pilihan aktif = batal), kolom alasan singkat opsional yang muncul sesudah memilih (simpan saat blur/Enter), status kecil "tersimpan"/"gagal menyimpan". Tombol "Ekspor pilihan" (JSON/CSV) di toolbar hasil, dekat tombol ekspor yang ada. Pilihan dimuat sekali per hasil lewat `GET`. Bila backend mati, tombol tetap tampil dan menampilkan pesan gagal, tanpa merusak kartu.
5. Tidak menyentuh `markedClips` (tandai untuk render tetap terpisah) dan tidak mengubah urutan/filter klip.

## Area yang boleh disentuh
- `backend/routers/choices.py` (baru): endpoint di atas.
- `backend/services/choices_service.py` (baru): baca/tulis atomik JSON, upsert, ekspor CSV.
- `backend/schemas/choices.py` (baru): model Pydantic record/request.
- `backend/routers/__init__.py`: ekspor `choices_router`.
- `backend/main.py`: satu baris `app.include_router(choices_router)` dan impornya (±L12-19, L130-135).
- `src/components/ClipChoiceControls.tsx` (baru): tombol Pakai/Lewati + alasan.
- `src/utils/clipChoices.ts` (baru): panggilan API, hitung `rank`, `heatmap_avg`, payload record (dipisah dari komponen karena aturan lint `react-refresh/only-export-components`, pelajaran #1b).
- `src/types.ts`: tipe `ClipChoice`, `ClipChoiceRecord`.
- `src/App.tsx`: impor, state peta pilihan + `useEffect` muat `GET` saat `result` berubah, `<ClipChoiceControls>` sesudah `<ClipScorePanel>` (±L4648), tombol ekspor pilihan di toolbar hasil (dekat `handleExportJSON`/`handleCopyAllMarkdown`, ±L2170-2248 untuk handler, JSX toolbar terkait).
- `src/locales/id.ts`, `src/locales/en.ts`: string baru di `results`.
- `scripts/smoke_test.py`: satu cek baru (simpan, timpa, batal, baca per video, ekspor JSON/CSV, file tetap valid; `EXPORTS_DIR` diarahkan ke folder sementara agar data pemilik tidak tersentuh). `CLAUDE.md`: kalimat deskripsi smoke test (#35).
- `docs/codemap/`: catatan baru `pilihan-klip.md` + `index.md`, `frontend-app.md`, `arsitektur-backend.md` (router baru), `penyimpanan-dan-cleanup.md` (folder `data/` di `EXPORTS_DIR`); `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Prompt AI, skema `ViralClip`/`VideoAnalysis`, pasca-proses klip, golden fixtures.
- Kalibrasi skor, Prompt Match gate (#2), preset bobot (#3), ledger views/pendapatan (#23).
- Mengubah `markedClips`, filter, urutan, label relatif #1b, badge skor, ekspor JSON/SRT/Markdown yang ada.
- Menyimpan prompt fokus pencarian (tidak ada di `AnalyzeResponse`; mengambil dari state form tidak andal untuk hasil dari riwayat). Kehadiran `scores.prompt_match` sudah menandai analisis dengan fokus.
- Halaman/dasbor analisis pilihan di UI (cukup ekspor).
- `ClipStudioSection.tsx`, render, auto-cleanup.

## Keputusan yang boleh diambil AI sendiri
- Tata letak, warna, dan teks tombol selama ringkas dan konsisten dengan kartu.
- Nama fungsi, kunci locale, urutan kolom CSV, nama field tambahan yang murni turunan (mis. `has_focus`).
- Cara menghitung `heatmap_avg` (rata-rata titik heatmap yang jatuh di rentang klip, atau interpolasi bila tidak ada titik di dalamnya).
- Apakah alasan disimpan otomatis saat blur atau lewat tombol kecil.

## Kriteria selesai (ya/tidak)
- [x] Kartu klip menampilkan tombol Pakai/Lewati (id dan en); memilih menyimpan record lengkap (field di Desain no. 2) ke `EXPORTS_DIR/data/clip_choices.json`; memilih ulang menimpa, klik pilihan aktif membatalkan; alasan opsional tersimpan.
- [x] Pilihan tetap ada setelah backend restart dan halaman dimuat ulang (tombol aktif dipulihkan dari `GET` saat hasil dibuka dari riwayat).
- [x] Ekspor JSON dan CSV berisi semua record dengan skor, total, peringkat, label, heatmap_avg, model, pilihan, alasan, waktu.
- [x] Penulisan file atomik; file rusak dibackup, tidak ditimpa diam-diam; auto-cleanup tidak menyentuh file ini (berada di `EXPORTS_DIR`).
- [x] Endpoint menolak klien non-loopback/Origin asing seperti endpoint admin lain.
- [x] Klip tanpa skor (riwayat lama, fallback) tetap bisa dipilih (skor null) tanpa error; backend mati tidak merusak kartu.
- [x] Semua string baru di `id.ts` dan `en.ts`; `npm run build` lulus; lint tanpa error baru; smoke test (dengan cek baru) dan `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `npm run build`, `npm run lint` (bandingkan jumlah masalah `App.tsx` dengan sebelum task; file baru harus bersih).
- `venv\Scripts\python.exe scripts\smoke_test.py` (cek baru #35) dan `venv\Scripts\python.exe scripts\check_codemap.py`.
- Uji browser dengan `npm run dev` dan data riwayat contoh (tanpa Gemini): pilih Pakai/Lewati + alasan, cek isi `~/CheatClip/data/clip_choices.json` (atau `EXPORTS_DIR` sementara), restart backend, muat ulang, pastikan pilihan pulih; ekspor JSON/CSV; matikan backend dan pastikan kartu tidak rusak; cek id dan en.
- Pemilik: pakai di analisis nyata dari riwayat, pilih beberapa klip, lalu ekspor CSV dan pastikan bisa dibuka di spreadsheet.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/schemas/choices.py` (baru): `ClipChoiceRequest` (L10-28), `ClipChoiceRecord` (L31-33).
- `backend/services/choices_service.py` (baru): `choices_file_path`, `_load_records` (file rusak -> backup `clip_choices.corrupt-<waktu>.json`), `_write_records` (tmp + fsync + `os.replace`, di bawah `threading.Lock`), `save_choice`, `delete_choice`, `list_choices`, `export_csv` (BOM, skor diratakan).
- `backend/routers/choices.py` (baru): `GET/PUT/DELETE /api/clip-choices`, `GET /api/clip-choices/export?format=json|csv`, semua dengan `verify_admin_access`.
- `backend/routers/__init__.py` (+2), `backend/main.py` (+2: impor + `include_router`).
- `src/types.ts`: `ClipChoice`, `ClipChoiceRecord`.
- `src/utils/clipChoices.ts` (baru): `heatmapAverage`, `heatmapSource`, `computeClipRanks`, `useClipChoices`, `downloadClipChoicesExport`.
- `src/components/ClipChoiceControls.tsx` (baru): tombol Pakai/Lewati + alasan + status.
- `src/App.tsx` (+36): impor, `clipChoices` + `handleExportChoices` (L2273-2278), `<ClipChoiceControls>` sesudah `<ClipScorePanel>` (L4679), tombol Pilihan CSV/JSON di toolbar (L4506-4525).
- `src/locales/id.ts`, `src/locales/en.ts`: 14 kunci baru di `results`.
- `scripts/smoke_test.py`: `run_choices_check` (cek 8), `CLAUDE.md`: deskripsi smoke test.
HASIL_TEST:
- `npm run build`: lulus (hanya peringatan ukuran chunk lama).
- Lint: 5 file baru/diubah selain App.tsx bersih; `App.tsx` 27 masalah, `npm run lint` total 97 (88 error, 9 warning), sama persis dengan sebelum task (dicek dengan stash).
- Smoke test: 15/15 lulus, termasuk cek baru "pilihan klip (#35)": PUT dari LAN/Origin asing 403, pilihan salah dan end <= start 422, simpan, timpa (created_at tetap, updated_at baru, alasan di-trim), klip tanpa skor, video lain, GET per video, ekspor JSON 3 record, CSV header + 3 baris, DELETE lalu DELETE kedua deleted=false, tanpa file .tmp tertinggal, file rusak dibackup isinya utuh dan GET kembali kosong. `EXPORTS_DIR` dialihkan ke folder sementara.
- `check_codemap.py`: SEMUA CEK LULUS (17 catatan, 255 simbol).
- Uji browser (Vite + backend dengan `CHEAT_CLIP_EXPORTS_DIR` di folder sementara; data riwayat contoh disuntikkan lalu dihapus; data asli `~/CheatClip` tidak tersentuh): 3 kartu (2 bertanda skor, 1 tanpa skor) menampilkan tombol; Pakai di klip A dan Lewati + alasan di klip C tersimpan dengan rank 1/3 dan 3/3, tier priority/null, heatmap_avg 0,5 (benar untuk heatmap contoh), heatmap_source youtube_viewers, model; backend dimatikan: kartu tetap normal, klik memberi "Gagal menyimpan (backend menyala?)", ekspor memberi toast gagal; backend dinyalakan lagi + muat ulang: tombol aktif dan alasan pulih; klik Pakai aktif membatalkan (record terhapus); ekspor CSV berisi kolom skor/peringkat/heatmap/model; teks en "✓ Use", "✕ Skip", "Picks CSV/JSON".
CODEMAP_DIPERBARUI: ya. Catatan baru `pilihan-klip.md` (ditautkan dari `index.md`); `frontend-app.md` (file_utama, `handleExportChoices`, `ClipChoiceControls`, `useClipChoices`, kartu klip, tipe), `arsitektur-backend.md` (7 router, endpoint, `__init__` L1-17, daftar router L131-137), `penyimpanan-dan-cleanup.md` (folder `EXPORTS_DIR/data/`); rentang `App.tsx`/`main.py`/`types.ts` yang bergeser juga di `render-browser.md`, `sistem-update.md`, `sumber-video.md`, `unduhan-raw.md` (dipetakan ulang dengan difflib HEAD -> kerja).
CATATAN:
- Keputusan sendiri: input alasan muncul setelah memilih dan disimpan saat blur/Enter; tombol ekspor sebagai dua tautan teks di toolbar (Pilihan CSV, Pilihan JSON); warna Pakai hijau, Lewati merah; `heatmap_avg` ditimbang lama tumpang tindih titik heatmap; `heatmap_source` diturunkan dari `source_type` (`youtube_viewers` / `audio_energy`); `rank` berbagi peringkat untuk skor sama; kunci klip `video_id` + rentang dibulatkan 3 desimal.
- Risiko: endpoint memakai guard `verify_admin_access`. Bila pemilik memasang `ADMIN_API_KEY`, frontend tidak mengirim key sehingga pilihan gagal disimpan (sama seperti pengaturan Gemini key). Dicatat di codemap.
- `rank`, `tier`, `heatmap_avg` dihitung dari hasil yang tampil saat memilih; analisis ulang dengan rentang klip sama menimpa record lama untuk klip itu.
- Perlu dicek pemilik: pakai di analisis nyata dari riwayat, pilih beberapa klip, cek `~/CheatClip/data/clip_choices.json`, lalu ekspor CSV dan buka di spreadsheet.
- `.claude/launch.json` (konfigurasi pratinjau) dipakai untuk uji browser, dikembalikan ke isi semula, tidak di-commit.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: commit `6e74905` menyentuh 23 file, semuanya di "Area yang boleh disentuh" (router/schema/service baru, `routers/__init__.py` +2, `main.py` +2, komponen + util baru, `types.ts`, `App.tsx` +36, locale, `smoke_test.py`, `CLAUDE.md`, `docs/codemap/`, kontrak). `e0ff106` hanya `TASKS.md`. Tidak ada format ulang atau dependensi baru.
- Tombol + record lengkap: `ClipChoiceControls.tsx` (Pakai/Lewati, klik pilihan aktif = `onClear`, alasan maks 300 disimpan saat blur/Enter); `buildRecord` di `src/utils/clipChoices.ts` mengisi semua field Desain no. 2 (video, rentang, judul klip, 7 skor, total, rank/rank_total, tier, needs_context, heatmap_avg, heatmap_source, model); backend menambah `created_at`/`updated_at`, upsert per (video_id, rentang 3 desimal) dengan `created_at` dipertahankan (`choices_service.py` `save_choice`). Path `EXPORTS_DIR/data/clip_choices.json` (`choices_file_path`). Teks id dan en ada (14 kunci di kedua locale).
- Pemulihan setelah restart: `useClipChoices` memuat `GET /api/clip-choices?video_id=` setiap `video_id` berubah, data dari file permanen. Terbukti di smoke (GET per video setelah PUT); pemulihan di UI nyata perlu dicek pemilik.
- Ekspor: `GET /api/clip-choices/export?format=json|csv`; `CSV_COLUMNS` memuat skor per dimensi, virality_score, rank, tier, heatmap_avg/source, model, choice, reason, waktu, plus BOM untuk Excel. Smoke: ekspor JSON 3 record, CSV header + 3 baris.
- Atomik/rusak: `_write_records` tulis `.tmp` + fsync + `os.replace` di bawah `threading.Lock`; `_load_records` memindah file tak terbaca ke `clip_choices.corrupt-<waktu>.json` dan mencatat log (terlihat di output smoke). File berada di `EXPORTS_DIR`, di luar folder auto-cleanup.
- Guard: semua endpoint `Depends(verify_admin_access)`; smoke: PUT/GET dari LAN dan Origin asing 403.
- Tanpa skor / backend mati: `scores: null` bila `!hasClipScores`, schema semua opsional; smoke menyimpan klip tanpa skor. Fetch gagal hanya memberi status "error"/toast, tidak melempar ke render kartu.
- Test yang saya jalankan: `npm run build` lulus (hanya peringatan ukuran chunk lama); `scripts/smoke_test.py` 15/15 LULUS, exit 0, termasuk "[PASS] pilihan klip (#35)"; `check_codemap.py` SEMUA CEK LULUS (17 catatan, 255 simbol); eslint 5 file baru/diubah selain App.tsx bersih, `App.tsx` 27 masalah sesudah = 27 sebelum task (`git show 6e74905~1:src/App.tsx | eslint --stdin`).
- Codemap: catatan baru `pilihan-klip.md` + tautan di `index.md`; `arsitektur-backend.md`, `frontend-app.md`, `penyimpanan-dan-cleanup.md` diperbarui; rentang bergeser di catatan lain ikut disesuaikan.
- Catatan non-blokir (risiko, bukan pelanggaran kontrak):
  - Bila `ADMIN_API_KEY` dipasang, frontend tidak mengirim key sehingga simpan/muat/ekspor pilihan 401 (sudah dicatat implementer di codemap).
  - `_load_records` memperlakukan semua kegagalan baca (termasuk `PermissionError` sesaat karena file dikunci program lain di Windows) sebagai file rusak: file dipindah ke backup dan daftar mulai kosong. Data tidak hilang (ada di backup), tetapi pilihan lama tampak hilang sampai digabung manual. Jangan buka `clip_choices.json` di program yang mengunci file saat backend menulis.
  - Record dengan `start_time` non-angka (hanya bila file diedit manual) membuat `_same_clip` melempar `ValueError` yang tidak ditangkap router, hasilnya 500 generik.
- Perlu dicek pemilik: pakai di analisis nyata dari riwayat, pilih beberapa klip + alasan, restart backend dan muat ulang, pastikan tombol pulih; ekspor CSV dan buka di spreadsheet.
