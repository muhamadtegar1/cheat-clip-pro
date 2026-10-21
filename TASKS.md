# TASKS — Kustomisasi Cheat Clip PRO

> File ini adalah **baton** antar sesi. Setiap sesi AI membaca file ini lebih dulu, mengerjakan **satu task**, lalu memperbarui status di sini.
> Dibuat: 2026-10-10

***

## Baton saat ini

```text
fase_aktif:      Fase 2 — Inti AI
task_aktif:      —
status:          41 DONE
langkah_berikut: Pemilik produksi campaign brand dengan app yang ada (2026-10-20): brief dicek manual, credit/hashtag ditempel ke caption posting kit, posting dan views H1/H3/H7 dicatat di tracker spreadsheet (#20/#21/#23 SKIPPED). Isi kolom "File hasil render" agar data bisa digabung dengan skor/pilihan app. Setelah ±20-30 posting punya views H7: baca tracker, rumuskan ulang #2/#3, lalu #37. Isi metrik titik uji Fase 3. Ditunda (keputusan pemilik 2026-10-19): task kecil toleransi/repeat penentu golden --compare, kerjakan sebelum perubahan prompt berikutnya. #28b hanya bila perlu. Kekurangan kecil yang dibiarkan: review #28 (`import threading` di tengah modul, kuota 5 GB auto-cleanup bisa menghapus cache yang sedang dipotong), review #40 (input baris sunting tetap menampilkan ketikan saat pratinjau gagal; batas 60 karakter UI dihitung unit UTF-16), review #22 (ZIP on-the-fly di `routers/render.py` tanpa folder kit), `localStorage` lain di `App.tsx` tanpa try/catch
blocker:         #2/#3/#37 BLOCKED menunggu data campaign nyata (tracker spreadsheet + pilihan #35). Kuota gemini-3.8-flash 20 permintaan/hari per proyek Google (bukan per key); golden butuh key dari proyek yang kuotanya belum terpakai
```

***

## Aturan kerja

1. **Satu kontrak = satu fitur kecil = satu commit.** Kontrak disimpan di `docs/tasks/CHEAT-<ID>.md` (template di bagian bawah).
2. **Implementasi:** Claude, satu sesi, hanya menyentuh area kode yang disebut di kontrak.
3. **Review:** sesi Claude **baru**, hanya membaca kontrak + `git diff` + hasil test. Verdict: `PASS` atau `FIX_REQUIRED`.
4. **DONE** hanya ditetapkan oleh pemilik proyek setelah mencoba hasilnya.
5. Setiap perubahan prompt AI wajib lulus golden fixtures (#17b).
6. Jangan kerjakan task dari fase berikutnya sebelum task fase aktif selesai, kecuali disetujui.
7. Setiap task yang mengubah kode wajib memperbarui catatan `docs/codemap/` yang terdampak (setelah P3 selesai).
8. Task berisiko tinggi (#7 keamanan, #16 penghapusan file, #12 guardrail AI) wajib di-review dengan `/review` di sesi Claude Code yang benar-benar baru, bukan hanya subagent dari `/tutup`.

**Status:** `TODO` → `IN_PROGRESS` → `REVIEW` → `DONE`
Jalur lain: `REVIEW` → `FIX_REQUIRED` → `IN_PROGRESS` · `BLOCKED` (tulis alasannya) · `SKIPPED` (tulis alasannya)

***

## Fase 0 — Persiapan (wajib sebelum menyentuh kode)

| ID | Pekerjaan                    | Detail                                                                                                                                                              | Selesai jika                                                          | Status |
| -- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------ |
| P0 | Amankan hasil render         | Pindahkan 3 MP4 + 3 ZIP dari `backend/exports` ke folder di luar Cheat. Auto-cleanup menghapus file > 1 jam, 15 detik setelah backend menyala                       | File aman di luar folder Cheat                                        | DONE   |
| P1 | Fork + amankan update        | Fork ke GitHub sendiri, ganti remote `origin`, buat branch `custom`. Matikan/arahkan ulang tombol update UI dan `update.bat`                                        | `git remote -v` menunjuk ke fork. Update tidak menarik dari repo asli | DONE   |
| P2 | Sistem kerja                 | Buat folder `docs/tasks/` + salin template kontrak dari file ini                                                                                                    | Template siap dipakai                                                 | DONE   |
| 17a | Smoke test | Skrip uji satu perintah: analyze `mock` → render 1 klip dari video sintetis buatan FFmpeg (tanpa YouTube). Mock ditambah skenario `RATE_LIMIT` dan `MALFORMED_JSON` | Satu perintah menjalankan semua cek, lulus pada kode asli | DONE |
| P3 | CLAUDE.md + codemap per fitur | `CLAUDE.md` di root (dibaca otomatis Claude Code): cara menjalankan app + smoke test, aturan kerja (baca TASKS.md + kontrak, sentuh hanya area yang diizinkan), jebakan yang diketahui (auto-cleanup `exports`, 1080×1920 hardcoded, self-update `git pull`). `docs/codemap/` berisi ±12 catatan per fitur: file + fungsi kunci dengan rentang baris, input/output, risiko, dan link `[[...]]` antar catatan. Folder `docs/` bisa dibuka sebagai vault Obsidian. Level fitur, bukan per fungsi | Claude Code di sesi baru bisa menunjuk file + rentang baris untuk tiap fitur tanpa grep panjang. Graph Obsidian menampilkan semua catatan saling terhubung | DONE |
| P3b | Otomasi alur Claude Code | 4 skill di `.claude/skills/` (dengan `disable-model-invocation: true`): `/mulai <ID>` (baca TASKS.md + kontrak, tulis draf kontrak bila belum ada lalu BERHENTI menunggu persetujuan), `/tutup` (smoke test, laporan, codemap, status REVIEW, commit, panggil subagent reviewer), `/review <ID>` (review penuh di sesi baru), `/done <ID>` (tandai DONE, log, commit). Subagent `.claude/agents/reviewer.md` dengan tools Read, Grep, Glob, Bash saja (tanpa Edit), bukti hanya dari kontrak + `git diff` + test yang ia jalankan sendiri. Skrip `scripts/baton.js` + hook `SessionStart` (matcher startup, clear, compact) di `.claude/settings.json` yang mencetak blok Baton | Sesi baru tanpa prompt pembuka sudah tahu baton. Satu task selesai dengan alur `/mulai` → setujui kontrak → `/tutup` → `/done` | DONE |

***

## Fase 1 — Perbaikan cepat

| ID | Upgrade                                                                                                              | Area kode                                                                                                                      | Selesai jika                                                                                                          | Status |
| -- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- | ------ |
| 16 | Pisahkan output permanen dari cache. Render ke folder permanen (mis. `Videos/CheatClip`), cleanup hanya untuk `temp` | `backend/services/system_service.py` (`auto_cleanup_expired_files`), `backend/config.py`, `backend/services/render_service.py` | Klip berumur > 1 jam tetap ada setelah cleanup berjalan                                                               | DONE   |
| 9  | Sumber sampai 2160p + bitrate AMF lebih tinggi                                                                       | `backend/video_engine.py` baris ±806, ±858, ±1055 (format yt-dlp) dan ±289 (AMF)                                               | Video 4K terunduh tinggi 2160 (cek ffprobe). Output tetap 1080×1920 dan lebih tajam. Fallback 720p/480p tidak berubah | DONE   |
| 7  | Amankan API key + endpoint admin                                                                                     | `src/App.tsx` (±baris 2820), `backend/schemas/analyze.py`, `backend/routers/system.py` (`verify_admin_access`)                 | Key tidak ada di `localStorage`. Endpoint update/restart menolak request tanpa key admin                              | DONE   |
| 28 | Unduhan HD YouTube: format HD (klien `android_vr`) ditolak 403 bila diambil ffmpeg (`--download-sections`, URL stream), jadi app hanya mendapat 360p (format 18). Riset: klien lain, `yt-dlp-ejs`, atau unduh native lalu potong lokal | `backend/video_engine.py` (`get_yt_dlp_base_cmd`, `download_clip_segment`, `download_full_raw_video`) | Segmen dari video YouTube 4K terunduh ≥ 1080p (cek ffprobe), waktu unduh wajar, fallback tetap ada | DONE   |

***

## Fase 2 — Inti AI

| ID | Upgrade                                                                                                                                                                                                                                     | Area kode                                                                                                                | Selesai jika                                                       | Status |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------ |
| 17b | Golden fixtures: 2–3 transkrip contoh (dari K3) dengan momen terbaik yang sudah diketahui + skrip pembanding hasil analisis. Dipecah dari task 17 | Baru: folder fixtures + skrip uji, memakai pipeline `backend/routers/analyze.py` | Satu perintah membandingkan hasil analisis dengan momen terbaik. Wajib DONE sebelum #1, #2, #12 | DONE   |
| 1  | Skor 7 dimensi (Prompt Match, Hook, Retention, Clarity, Emotional Pull, Payoff, Editability) + penjelasan + label skor. Aturan: kandidat beragam, skor independen, tanpa klaim "pasti viral", hook tanpa fakta baru, tandai "butuh konteks" | `backend/schemas/analyze.py` (`ViralClip`), `backend/routers/analyze.py` (prompt ±1008–1051), golden fixtures. UI dipecah ke #1b | Respons API memuat 7 skor + penjelasan yang merujuk transkrip + kode label + `needs_context`, golden dua mode exit 0 | DONE   |
| 1b | Tampilan skor 7 dimensi di kartu klip: label RELATIF per hasil analisis (sekitar 30% teratas "Prioritas", sisanya "Cadangan"; bukan ambang absolut 80/60 karena skor Gemini menggelembung 85-93, lihat laporan #1), total, 7 skor, penjelasan, lencana "butuh konteks"; disembunyikan bila klip tanpa skor (cache lama, fallback). Label dibaca sebagai urutan prioritas, bukan vonis kualitas (uji pemilik: semua klip layak tayang). Dipecah dari #1 | `src/types.ts`, kartu klip di `src/App.tsx`, `src/locales/id.ts`, `src/locales/en.ts` | Kartu menampilkan label relatif dan skor dari respons #1 (id dan en), klip tanpa skor tidak rusak, `npm run build` lulus | DONE   |
| 35 | Catat pilihan pemilik per klip: tombol Pakai/Lewati + alasan singkat opsional di kartu klip, disimpan permanen (file JSON di luar cache) bersama video, rentang klip, 7 skor, total, peringkat, rata-rata heatmap, model, dan waktu. Fondasi kalibrasi skor (#2, #3) dan cikal bakal ledger #23 | Baru: endpoint kecil di backend + penyimpanan JSON; tombol di kartu klip `src/App.tsx`; `src/locales/id.ts`, `src/locales/en.ts` | Pilihan tersimpan dan tetap ada setelah backend restart, bisa diekspor untuk dianalisis (skor vs pilihan), `npm run build` dan smoke test lulus | DONE |
| 2  | Prompt Match gate: Prompt Match < 50 → skor total × 0,85                                                                                                                                                                                    | Pasca-proses di `backend/routers/analyze.py`                                                                             | Unit test kasus di bawah dan di atas ambang lulus                  | BLOCKED (menunggu data #35: ambang absolut Prompt Match < 50 hampir tidak terpicu karena skor menggelembung; rumuskan ulang secara relatif setelah ada data pilihan pemilik) |
| 12 | Guardrail output: kutipan dicek ke transkrip, timestamp di dalam durasi, overlap > 70% digabung (40–70% ditinjau), transkrip dibungkus `<TRANSCRIPT_DATA>`, jumlah klip tidak dipaksa saat momen bagus sedikit                              | `backend/routers/analyze.py` (prompt + validasi setelah parse, termasuk logika target jumlah klip ±895–945)              | Golden fixtures lulus: tanpa kutipan karangan, tanpa duplikat      | DONE   |
| 29 | Klip fallback heatmap saat rentang khusus: batas akhir memakai `duration` relatif sehingga klip terbalik lalu dijepit guardrail jadi satu klip panjang. Temuan review #12 | `backend/routers/analyze.py` (klip fallback heatmap ±1345–1420), `scripts/smoke_test.py` | Klip fallback dengan rentang berada di dalam rentang dan sepanjang target | DONE   |
| 30 | Klip fallback heatmap saling tumpang tindih: kandidat hanya berjarak 25 s padahal target `auto`/`60s` sampai 85 s, sehingga guardrail menggabungkan klip dan menyisakan klip skor tertinggi (bisa klip 5 s di ujung rentang). Temuan #29 | `backend/routers/analyze.py` (klip fallback heatmap L1345-1425), `scripts/smoke_test.py` | Klip fallback tidak tumpang tindih (tidak ada yang digabung atau ditandai overlap oleh guardrail), rentang 60-110 dengan `auto` menghasilkan lebih dari 1 klip dan tidak ada klip < 10 s bila ada kandidat lain | DONE   |
| 31 | Golden fixtures tanpa heatmap: opsi `run --no-heatmap` yang mengosongkan heatmap sebelum dikirim ke backend (penilaian `heat_lift` tetap memakai heatmap asli), untuk mengukur kualitas jalur video upload/Drive dan YouTube tanpa heatmap. Ketiga video K3 berheatmap asli, jadi jalur itu belum pernah diukur. Temuan K3 Tahap 2 | `scripts/golden_fixtures.py`, `docs/codemap/golden-fixtures.md` | `run --no-heatmap` (dan `--mock`) jalan, laporan menandai mode tanpa heatmap, `--compare` tidak mencampur hasil tanpa heatmap dengan baseline biasa, `selftest` lulus. Satu run Gemini tanpa heatmap dicatat sebagai titik awal | DONE   |
| 32 | Label heatmap akustik yang jujur di prompt: video upload/Drive memakai energi audio (RMS) tetapi prompt menyebutnya `audience_interest` dan meminta "Prioritise high-interest peaks" (`analyze.py` ±L981-984), padahal suara keras belum tentu menarik. Bedakan sumber heatmap (penonton YouTube vs energi audio) di prompt. Perubahan prompt: dikerjakan bersama atau setelah #1 | `backend/routers/analyze.py` (sumber heatmap, `heatmap_note`), golden fixtures | Prompt menyebut sumber heatmap dengan benar untuk tiap jalur, jalur YouTube tidak berubah, golden `run --repeat 2 --compare` exit 0 dan (bila #31 ada) `--no-heatmap` tidak memburuk | DONE   |
| 33 | Heatmap akustik palsu saat audio gagal: `compute_audio_energy_heatmap` memakai batas 30 s untuk ekstraksi audio FFmpeg (`video_engine.py` ±L594); bila gagal/timeout semua nilai rata lalu fungsi membuat pola sinus buatan (±L627-628) yang dikirim ke Gemini sebagai minat penonton. Video upload panjang (mis. podcast 2 jam) berisiko. Belum diuji, terbaca dari kode | `backend/video_engine.py` (`compute_audio_energy_heatmap`), `scripts/smoke_test.py` | Tidak ada heatmap buatan: gagal/datar menghasilkan heatmap kosong (prompt jatuh ke "No audience interest data"), batas waktu ekstraksi menyesuaikan durasi, video sintetis panjang lulus, smoke test lulus | DONE   |
| 34 | `ref_recall` per sumber referensi: total sekarang mencampur referensi dari kandidat Gemini dan dari heatmap/Short, sehingga bisa naik hanya karena Gemini cocok dengan pilihannya sendiri (#31: tanpa heatmap sumber gemini 7/12 -> 11/12, sumber heatmap 8/10 -> 7/10). Tambah `ref_recall` per `source` dan angka utama `ref_recall_independen` (hanya heatmap + short) sebagai penentu `--compare`; total tetap ditampilkan sebagai informasi. Sebelum #1 | `scripts/golden_fixtures.py` (`score_video`, `summarize`, `compare`, `print_compare`, selftest), `tests/golden/baseline.json` dan `baseline-noheatmap.json` (dinilai ulang lewat `score --save-baseline` dari run yang sama), `docs/codemap/golden-fixtures.md`, `CLAUDE.md` | Laporan dan baseline memuat recall per sumber dan `ref_recall_independen`; `--compare` memutuskan lebih buruk dari `ref_recall_independen`; kedua baseline dinilai ulang tanpa Gemini dengan metrik lain tidak berubah; `selftest` lulus | DONE   |
| 3  | Preset bobot (Founder, Edukasi, Hiburan, Gaming, General) + hitung ulang ranking lokal                                                                                                                                                      | `src/App.tsx`                                                                                                            | Ganti preset → ranking berubah tanpa memanggil AI                  | BLOCKED (menunggu data #35 dan titik uji campaign: bobot preset masih tebakan, dimensi yang berguna berbeda per genre di K3; turunkan bobot dari pilihan pemilik dan views) |
| 38 | Model Whisper lebih akurat (permintaan pemilik 2026-10-19, akun clipping fokus bahasa Inggris): aplikasi sekarang memakai Whisper `base` (`video_engine.py` `get_whisper_model`) di CPU (iGPU AMD tanpa CUDA). Langkah pertama pengukuran: `base` vs `small`/`small.en` vs `medium`/`medium.en` pada 1 klip Inggris dan 1 klip Indonesia ±60 s (waktu, RAM puncak, kata salah dibanding transkrip acuan). Dari hasilnya pilih model default dan jadikan pengaturan (env/`.env`) yang dipakai transkrip analisis dan subtitle klip; model dimuat sekali seperti sekarang | `backend/video_engine.py` (`get_whisper_model`, `release_whisper_model`), `backend/config.py` bila perlu, skrip ukur baru di `scripts/` | Tabel ukur (waktu, RAM, kata salah per model dan bahasa) tercatat di kontrak; model default dipilih pemilik dari data itu; pengaturan model berlaku di analisis dan render; smoke test lulus | DONE   |
| 39 | Pilihan bahasa audio untuk transkripsi: Otomatis (default, perilaku sekarang) / English / Indonesia / beberapa bahasa lain, dipilih di UI dan diteruskan sebagai `language` ke Whisper di transkrip analisis (`video_engine.py` ±L668, sekarang `initial_prompt` "Bahasa Indonesia atau English") dan subtitle per kata klip (±L1170, sekarang tebak sendiri per klip). Bukan terjemahan: subtitle tetap bahasa asli audio (terjemahan sengaja tidak dikerjakan, keputusan pemilik 2026-10-19). Bila #38 memilih model `.en`, dipakai hanya saat bahasa English; bahasa lain memakai model multibahasa. Setelah #38 | `backend/video_engine.py` (transkripsi), `backend/schemas/analyze.py` dan `render.py` (field bahasa), `backend/services/subtitle_preview_service.py`, `render_service.py`, UI pilihan bahasa di `src/` + `src/locales/id.ts`, `en.ts` | Bahasa terpilih dipakai Whisper di analisis, pratinjau subtitle, dan render; Otomatis identik dengan sekarang; klip Inggris pendek tidak salah tebak bahasa saat English dipilih; prompt Gemini tidak berubah; smoke test dan `npm run build` lulus | DONE   |
| 40 | Perbaikan kecil sisa review #39 dan #36b: `localStorage` bahasa audio dibungkus try/catch, smoke test fallback Whisper YouTube dengan bahasa, `editedWords` baru ditulis setelah pratinjau sukses (render tidak memakai suntingan yang pratinjaunya gagal), kata > 60 karakter ditolak di input sunting. Dikerjakan atas permintaan pemilik 2026-10-20 | `src/utils/subtitlePreview.ts`, `src/App.tsx` (state `audioLanguage`), `src/components/ClipStudioSection.tsx` (pratinjau dan sunting subtitle), `src/locales/id.ts`, `en.ts`, `scripts/smoke_test.py` | Storage diblokir tidak menjatuhkan App, smoke fallback Whisper YouTube `[None, "en"]`, pratinjau gagal tidak mengubah kata render, kata > 60 ditolak di UI, build/smoke/codemap lulus | DONE |

Bobot default (jumlah 100): Prompt Match 25 · Hook 20 · Retention 20 · Clarity 15 · Emotional Pull 10 · Payoff 7 · Editability 3.
Preset lain: lihat `D:\Clipper\clipper app\foundation\06_SCORING_SYSTEM.md` §7–10.

***

## Fase 3 — Lapisan campaign

| ID | Upgrade                                                                                                                                                                          | Area kode                                                                                                             | Selesai jika                                                   | Status |
| -- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| 20 | Campaign Profile (menyerap #4 dan #13): sumber resmi, platform, credit line persis, hashtag wajib, durasi min–maks, gaya terlarang, brief, audiens, eksklusi, CPM, batas bayaran | Baru: `backend/campaigns/*.json` + router + form UI                                                                   | Satu profil otomatis terpakai di analisis, render, dan caption | SKIPPED (pemilik 2026-10-20: brief dicek manual, data campaign di sheet Campaign tracker spreadsheet; buka lagi bila volume klip membuat langkah manual berat) |
| 21 | Compliance checker: durasi, credit/hashtag persis, source resmi, musik/overlay terlarang                                                                                         | Baru: `backend/services/compliance_service.py` + panel ✓/⚠️ di UI                                                     | Klip yang melanggar brief tertandai sebelum ekspor             | SKIPPED (pemilik 2026-10-20: compliance dicek manual terhadap brief; buka lagi bila klip sering ditolak karena hal yang bisa dicek mesin) |
| 11 | Koreksi subtitle sebelum render                                                                                                                                                  | `src/components/ClipStudioSection.tsx`, `backend/schemas/render.py`, `generate_ass_file` di `backend/video_engine.py` | Kata yang dikoreksi muncul benar di video hasil render         | DONE   |
| 36a | Pratinjau subtitle asli di Clip Studio: tombol "Buat subtitle" menjalankan Whisper per kata pada segmen klip sebelum render (proses sama dengan render, dimajukan), kamus #11 diterapkan ke hasilnya, lalu subtitle karaoke tampil di pratinjau mengikuti gaya/font/posisi yang dipilih dan sinkron dengan pemutar pratinjau. Hasil disimpan sementara per klip; ditandai usang bila klip di-trim | Baru: endpoint pratranskripsi di backend (memakai `transcribe_clip_words` + segmen klip); `src/components/ClipStudioSection.tsx` (pratinjau); `src/locales/id.ts`, `src/locales/en.ts` | Kata yang akan dibakar ke video terlihat di pratinjau sebelum render, sama dengan hasil render | DONE |
| 36b | Sunting subtitle per klip sebelum render: daftar kata/potongan dari #36a bisa diketik ulang, dihapus, dipecah, digabung (waktu kata dipertahankan); render memakai kata hasil suntingan tanpa menjalankan Whisper lagi | `src/components/ClipStudioSection.tsx`, `backend/schemas/render.py`, `backend/services/render_service.py` (pakai kata dari request bila ada) | Kata yang dikoreksi di pratinjau muncul persis sama di video hasil render, mode separate dan merged | DONE |
| 22 | Posting kit (menyerap #19 dan #6): per klip MP4 + SRT + `metadata.json` (skor, prompt, versi prompt, model) + caption per platform, dibuat setelah klip dipilih                  | `backend/services/render_service.py`, `backend/routers/analyze.py`                                                    | Satu folder per klip siap unggah ke TikTok, Reels, Shorts, X   | DONE   |
| 41 | Sesuaikan durasi klip sebelum render (permintaan pemilik 2026-10-21: klip kadang mulai di tempat yang salah dan berakhir menggantung). Trimmer yang sudah ada (`ClipTrimmerModal`, drag ±2 menit, waktu manual, preset, klik kalimat transkrip "Jadikan Mulai/Selesai") dibuka dari tombol "Sesuaikan durasi" yang jelas di kartu klip dan Clip Studio; tombol "Terapkan" tanpa unduh raw (unduh raw tetap pilihan terpisah); tombol geser −1/+1 detik untuk awal dan akhir; render, pratinjau/suntingan subtitle (#36a/#36b, dibuat ulang bila rentang berubah), Pakai/Lewati (#35), dan posting kit memakai rentang baru | `src/components/ClipTrimmerModal.tsx`, `src/App.tsx` (`handleApplyAdjustedClipToResults`, kartu klip), `src/components/ClipStudioSection.tsx`, `src/locales/*` | Pemilik bisa menggeser awal/akhir klip lalu render tanpa unduh raw, dan video hasil render memakai rentang baru | DONE   |

### 🚦 Titik uji — 1 campaign nyata

Jalankan satu campaign dari awal sampai submit. Catat di bawah, lalu putuskan urutan Fase 4–6.

| Metrik                          | Hasil  |
| ------------------------------- | ------ |
| Campaign / platform             | <br /> |
| Menit kerja manusia per klip    | <br /> |
| % kandidat Top 10 yang terpakai | <br /> |
| Klip ditolak brand + alasannya  | <br /> |
| Keputusan lanjutan              | <br /> |

***

## Fase 4 — Tracking dan skala

| ID | Upgrade                                                                                                       | Selesai jika                                 | Status |
| -- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------ |
| 23 | Campaign ledger (menyerap #14): campaign, klip, URL, views hari ke-1/3/7, status, pendapatan, acceptance rate | Korelasi skor AI vs views nyata bisa dilihat | SKIPPED (pemilik 2026-10-20: diganti sheet Posting di tracker spreadsheet, views H1/H3/H7, status, pendapatan; bahan #37) |
| 37 | Lingkar belajar dari performa (permintaan pemilik 2026-10-19): data ledger #23 (views hari ke-1/3/7, payout, acceptance rate, alasan ditolak brand) digabung dengan pilihan Pakai/Lewati #35 dan skor 7 dimensi, lalu laporan berkala menunjukkan dimensi skor, durasi, gaya hook, dan niche mana yang berkorelasi dengan klip berhasil. Dari situ aplikasi membuat **usulan** (bobot preset #3, ambang #2, contoh klip berhasil untuk prompt), bukan perubahan otomatis: pemilik menyetujui, perubahan prompt wajib lulus golden kedua mode. Aplikasi tidak mengubah kodenya sendiri (agentic editing tetap di daftar "Sengaja tidak dikerjakan"). Butuh #23 dan cukup klip tayang (puluhan) sebelum laporannya bermakna | Laporan korelasi performa bisa dibuat dari ledger; minimal satu usulan (bobot/ambang/contoh prompt) dihasilkan dari data nyata dan bisa diterima atau ditolak pemilik; usulan prompt yang diterima lulus golden | TODO   |
| 24 | Antrean multi-source                                                                                          | 10 video diproses tanpa ditunggui            | TODO   |
| 5  | Multi-provider AI + circuit breaker (diperluas 2026-10-17 atas permintaan pemilik): pemilik bisa memilih provider analisis (Gemini, Claude, GPT, dll.) dan ada cadangan otomatis ke provider lain saat kuota/error. Perlu: lapisan penghubung per provider (structured output tiap provider berbeda dari `response_schema` Gemini), API key tiap provider disimpan di backend seperti #7, baseline golden per provider (data K3 dipakai ulang), kalibrasi skor 7 dimensi (#1) dan label/preset (#1b, #3) dicek per provider karena skala skor tiap model berbeda. Dikerjakan setelah #1, #1b, #2, #3 stabil; boleh dimajukan dari Fase 4 atas persetujuan pemilik (aturan no. 6) | Analisis jalan dengan minimal 2 provider yang dipilih pemilik dan tetap jalan saat kuota provider utama habis; golden tiap provider exit 0 terhadap baseline-nya sendiri | TODO   |

***

## Fase 5 — Peningkatan views

| ID | Upgrade                          | Selesai jika                                  | Status |
| -- | -------------------------------- | --------------------------------------------- | ------ |
| 25 | Cold open memakai `hook_time`    | 2–3 detik terkuat muncul di awal klip         | TODO   |
| 26 | Hapus jeda dan filler            | Jeda panjang terpotong otomatis (bisa on/off) | TODO   |
| 27 | Varian hook/judul untuk A/B test | 2–3 varian per klip, tercatat di ledger       | TODO   |

***

## Fase 6 — Opsional (kerjakan hanya bila datanya mendukung)

| ID | Upgrade                                                                                                                             | Dikerjakan bila                                       | Status |
| -- | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------ |
| 10 | Output 1440p/4K dengan auto-cap (± 60 angka 1080×1920 di `video_engine.py` jadi variabel, line breaking subtitle ikut lebar kanvas) | Sering memakai rekaman vertikal 4K                    | TODO   |
| 15 | Riwayat analysis run yang tidak saling menimpa                                                                                      | Sering analisis ulang video sama dengan angle berbeda | TODO   |
| 18 | Verifikasi output lebih ketat + tombol batal render                                                                                 | Render sering gagal diam-diam atau terlalu lama       | TODO   |
| 8  | Status job render di SQLite                                                                                                         | Progres pernah hilang karena backend restart          | TODO   |

***

## Sengaja tidak dikerjakan

Auto-posting ke platform · posting massal konten identik ke banyak akun · auto-submit ke Whop · analisis hierarkis/chunking · shell Tauri/Rust · sistem project penuh · project lock · katalog error code · gate CI lengkap · mode konsensus 2 provider · kalibrasi skor antar-provider · timeline editor · agentic editing.

***

## Keputusan terbuka

| #  | Keputusan                                                     | Jawaban |
| -- | ------------------------------------------------------------- | ------- |
| K1 | Akun GitHub untuk fork                                        | muhamadtegar1 |
| K2 | GPU komputer (NVIDIA / AMD / Intel) untuk optimasi encoder #9 | AMD Radeon(TM) Graphics (iGPU, driver 31.0.12044.3). `h264_amf` diuji jalan 1080×1920. Tanpa NVENC/QSV |
| K3 | 2–3 video golden fixtures + momen terbaiknya (untuk 17b)      | Tahap 1 (2026-10-13): A `hbZbPHjE8NE` (Colin and Samir, podcast EN, 52:26), B `094y1Z2wpJg` (Veritasium, edukasi EN, 22:09), C `YzDyjAsd4Z8` (Billy Samuel, gaming ID, 29:16), masing-masing 3 rentang "jangan dipilih" (dibantu Gemini, diverifikasi pemilik). Transkrip disimpan lokal (di-ignore git), analisis memakai model flash. Tahap 2 (2026-10-17): 12 referensi (4 per video) di `labels.json`, dinilai pemilik dengan 5 cek; kandidat 6 dari Gemini, 6 dari puncak heatmap, B memakai Short resmi `8fNFd2Xswjs` (00:00-00:04 + 00:21-00:46 + 01:05-01:43). Shorts resmi A dan C tidak ditemukan. Baseline `ref_recall` 70,85% |
| K4 | Campaign pertama untuk titik uji (platform + niche)           | Belum dipilih. Pemilik langsung ikut campaign brand (2026-10-20); campaign dicatat di tracker spreadsheet (link di memori Claude), brief dicek manual |

***

## Log

| Tanggal    | Task | Status | Catatan                                                  |
| ---------- | ---- | ------ | -------------------------------------------------------- |
| 2026-10-10 | —    | —      | TASKS.md dibuat dari hasil analisis Cheat vs Clipper app |
| 2026-10-10 | P0 | DONE | Hasil render di `backend/exports` hanya uji coba, tidak perlu diamankan |
| 2026-10-10 | P3 | TODO | Ditambahkan: CLAUDE.md + codemap per fitur (alternatif ringan dari pemetaan Obsidian per fungsi) |
| 2026-10-10 | P3b | TODO | Ditambahkan: slash command /mulai /tutup /review /done, subagent reviewer, hook SessionStart untuk baton |
| 2026-10-11 | P1 | REVIEW | Fork `muhamadtegar1/cheat-clip-pro`, origin = fork, upstream = repo asli, branch `custom`. Self-update dimatikan via `SELF_UPDATE_DISABLED` (backend `routers/system.py` + `App.tsx`), `update.bat` hanya menampilkan petunjuk manual. `package-lock.json` di-restore (perubahan dependensi transitif, di luar scope) |
| 2026-10-11 | P1 | DONE | Ditetapkan DONE oleh pemilik proyek setelah dicek |
| 2026-10-11 | P2 | REVIEW | Folder `docs/tasks/` dibuat, template kontrak + prompt review disalin ke `docs/tasks/_TEMPLATE.md` |
| 2026-10-11 | P2 | DONE | Ditetapkan DONE oleh pemilik proyek setelah dicek |
| 2026-10-11 | P3 | REVIEW | `CLAUDE.md` + `docs/codemap/` (index + 14 catatan fitur), kontrak `docs/tasks/CHEAT-P3.md`. 190 rentang simbol diverifikasi otomatis terhadap AST, semua link `[[...]]` valid. Dikerjakan sebelum task 17 karena 17 menunggu K3 |
| 2026-10-11 | P3 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | P3b | REVIEW | 4 skill (`/mulai`, `/tutup`, `/review`, `/done`), subagent `reviewer`, hook SessionStart + `scripts/baton.js`, `scripts/check_codemap.py`. Hook dan skill diuji di sesi `claude -p` baru. Alur penuh dibuktikan pada task berikutnya |
| 2026-10-11 | 17a/17b | TODO | Task 17 dipecah atas persetujuan pemilik: 17a smoke test (Fase 0, tidak butuh K3), 17b golden fixtures (dipindah ke awal Fase 2, butuh K3) |
| 2026-10-11 | P3b | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | 17a | REVIEW | `scripts/smoke_test.py`: video sintetis FFmpeg, analyze `mock`, skenario `RATE_LIMIT` dan `MALFORMED_JSON` lewat klien Gemini palsu di skrip, render 1 klip 1080x1920. 5/5 lulus pada kode asli, tanpa perubahan `backend/` atau `src/` |
| 2026-10-11 | 17a | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | 16 | REVIEW | Output permanen di `EXPORTS_DIR` (default `~/CheatClip`, env `CHEAT_CLIP_EXPORTS_DIR`, fallback `backend/exports`). Auto-cleanup hanya folder cache, ZIP batch jadi cache di `temp_clips`. Smoke test 6/6 dengan cek cleanup baru. Default bukan `~/Videos` karena Defender Controlled Folder Access |
| 2026-10-11 | 16 | REVIEW | Review sesi baru: PASS |
| 2026-10-11 | 16 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | 7 | REVIEW | Gemini key pindah dari `localStorage` ke `backend/.env` lewat `/api/settings/gemini-key` (migrasi otomatis, key tidak pernah dikirim balik utuh). Endpoint admin hanya loopback + Origin localhost, update/restart wajib `ADMIN_API_KEY`, backend `--host 127.0.0.1`. Smoke test 7/7 dengan cek 6 baru |
| 2026-10-11 | 7 | REVIEW | Review sesi baru: PASS |
| 2026-10-11 | 7 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | 9 | TODO | K2 terjawab: AMD Radeon(TM) Graphics (iGPU), `h264_amf` berfungsi. Blocker #9 dicabut |
| 2026-10-11 | 28 | TODO | Ditemukan saat #9: unduhan YouTube selama ini 360p (format HD 403 lewat ffmpeg). Dipisah dari #9 atas persetujuan pemilik |
| 2026-10-11 | 9 | REVIEW | Batas format yt-dlp 2160p (metode 1, 2, video utuh), AMF `balanced`/`vbr_peak` 12M (6 → 12 Mbps, waktu render sama). Fallback 720p/480p utuh. Smoke test 7/7 dengan dan tanpa `--gpu` |
| 2026-10-11 | 9 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-11 | 28 | SKIPPED | Ditunda pemilik: kualitas render cukup, kontrak dinilai riskan. Riset (yt-dlp-ejs membuka 2160p, ffmpeg ke URL remote tidak andal, usulan cache native) disimpan di CHEAT-28.md. yt-dlp-ejs dicopot lagi dari venv. Fase 1 selesai, fase aktif → Fase 2 |
| 2026-10-13 | 17b | REVIEW | Golden fixtures Tahap 1: `scripts/golden_fixtures.py` (fetch/run/score/selftest), label K3 + baseline (hanya angka) di `tests/golden/`, transkrip lokal (di-ignore git). Baseline Gemini flash: 38 klip, grounded 97,9%, valid 100%, duplikat 0, zona terlarang 1, heat lift 1,38. Selftest 16/16, smoke test 7/7 |
| 2026-10-13 | 17b | REVIEW | Perbaikan temuan reviewer: model dikunci (`--model auto`), model yang dipakai dicatat per video, `--compare` exit 3 bila model beda, baseline ulang dengan `gemini-3.7-flash` (36 klip, grounded 100%, valid 100%, duplikat 0, zona terlarang 1, lift 1,46). Selftest 18/18, smoke test 7/7 |
| 2026-10-13 | 17b | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-13 | 12 | REVIEW | Guardrail output: `backend/utils/clip_guardrails.py` (timestamp, kutipan, overlap), prompt `<TRANSCRIPT_DATA>` + jumlah klip batas atas. Golden `--repeat 2 --compare` exit 0 (gemini-3.8-flash): grounded 100%, karangan/salah tempat/duplikat 0, zona terlarang 2→0,5, klip 36→29. Smoke test 8/8 |
| 2026-10-13 | 12 | REVIEW | Perbaikan temuan reviewer: guardrail sebelum fallback heatmap (semua klip dibuang -> fallback), urutkan/jepit timestamp sebelum batas 90 s. Smoke test 9/9 |
| 2026-10-13 | 12 | REVIEW | Review sesi baru: PASS |
| 2026-10-13 | 12 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-13 | 29 | TODO | Ditambahkan atas permintaan pemilik dari temuan review #12: klip fallback heatmap memakai `duration` relatif saat rentang khusus. Direproduksi (rentang 60-110 s: 1 klip 45 s, bukan klip 15 s). Kontrak `docs/tasks/CHEAT-29.md` |
| 2026-10-13 | 29 | REVIEW | Fallback heatmap: kandidat dijepit ke `start_bound`, sisa rentang < 5 s dilewati, akhir klip `min(end_bound, start + target)`. Smoke test 10/10 dengan cek baru rentang 22-38 s (gagal di kode lama). Reproduksi 60-110 `15s`: 2 klip di dalam rentang tanpa penjepitan; tanpa rentang identik. Catatan: `auto` dengan rentang sempit masih bisa tinggal 1 klip pendek karena overlap kandidat digabung guardrail (di luar scope) |
| 2026-10-13 | 29 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-13 | 30 | TODO | Ditambahkan atas permintaan pemilik dari temuan #29: klip fallback heatmap tumpang tindih (jarak kandidat 25 s vs target sampai 85 s). Rentang 60-110 `auto`: hanya 1 klip 105-110 (5 s) karena 65-110 digabung guardrail. Tanpa rentang `auto`: 55-100 dan 80-115 ditandai overlap. Kontrak ditulis lewat `/mulai 30` |
| 2026-10-13 | 30 | REVIEW | `pick_fallback_spans`: kandidat yang menimpa klip terpilih atau < 10 s dilewati (5 s bila tidak ada klip sama sekali), target `auto` per klip yang diterima. Rentang 60-110 `auto`: 65-90, 90-110 (dulu 1 klip 5 s); tanpa merge/overlap di semua durasi; `15s` tanpa rentang identik kecuali klip < 10 s. Smoke test 11/11 dengan cek baru video 120 s (gagal di kode lama), ±26 s |
| 2026-10-14 | 30 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-17 | K3 | — | Tahap 2 selesai: 12 referensi di `tests/golden/labels.json` (A 4, B 4, C 4), dinilai pemilik dari transkrip/visual. Batas dirapikan ke kalimat utuh dari transkrip. Run 20261013-150232 dinilai ulang dengan `score --save-baseline`: metrik lain sama, `ref_recall` baseline 70,85% (terlewat: A masa kecil, B analogi saham, C kuyang sekali tembak, C happy ending 1 ulangan). Blocker #1/#2 dibuka |
| 2026-10-17 | 31-33 | TODO | Ditambahkan atas permintaan pemilik dari temuan jalur tanpa heatmap YouTube: #31 golden `--no-heatmap`, #32 label heatmap akustik jujur di prompt, #33 heatmap sinus buatan saat ekstraksi audio gagal/timeout 30 s. Kontrak ditulis lewat `/mulai` |
| 2026-10-17 | 31 | REVIEW | `run --no-heatmap`: heatmap kosong ke backend (dicek dari event SSE), `heat_lift` tetap dari heatmap asli, baseline terpisah `baseline-noheatmap.json`, `score` ikut mode laporan. Selftest 21/21, mock dua mode, smoke 11/11. Run Gemini 3.8-flash x2 tanpa heatmap: `ref_recall` 83,3 (vs 70,85 dengan heatmap), `heat_lift` 1,23 (vs 1,50); kenaikan dari referensi bersumber Gemini (7/12 -> 11/12), bukan bukti tanpa heatmap lebih baik |
| 2026-10-17 | 31 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-17 | 34 | TODO | Ditambahkan atas persetujuan pemilik dari temuan #31: `ref_recall` per sumber + `ref_recall_independen` (heatmap + short) sebagai penentu `--compare`, dikerjakan sebelum #1. Bersamaan, aturan kerja `CLAUDE.md`: golden wajib dengan dan tanpa heatmap untuk perubahan prompt (commit `aturan:`). Kontrak ditulis lewat `/mulai 34` |
| 2026-10-17 | 34 | REVIEW | Recall per sumber: `ref_recall_independen` (heatmap + short) jadi penentu `--compare`, `ref_recall` total dan `ref_recall_gemini` info, rincian per referensi di laporan. Kedua baseline dinilai ulang tanpa Gemini, nilai lama identik: independen 83,3 (dengan heatmap) / 75,0 (tanpa), gemini 58,35 / 91,65. `cmd_score` kini menyalin `heatmap_sent` (kekurangan #31). Selftest 24/24, smoke 11/11 |
| 2026-10-17 | 34 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-17 | 33 | REVIEW | Heatmap akustik tanpa data buatan: pola sinus dihapus, `[]` untuk tanpa audio, file rusak, gagal/timeout, senyap, dan volume rata (< 10%); batas waktu sebanding durasi; pipe PCM tanpa file sementara; SSE upload jujur saat kosong. Terukur: ekstraksi audio 1 jam 5 s (timeout bukan penyebab utama). Smoke 12/12 (cek baru gagal di kode lama); cek fallback #30 bergeser karena video smoke bernada rata kini tanpa heatmap, tetap lulus |
| 2026-10-17 | 33 | REVIEW | Review subagent FIX_REQUIRED: rujukan "Format di L..." di `unduhan-raw.md` basi. Diperbaiki, plus atas permintaan pemilik ambang volume rata 10% -> 15% dan log "file cannot be read" vs "no usable audio track"; semua rujukan `video_engine.py` di codemap digeser +2 dan dicocokkan ke kode. Smoke 12/12, codemap lulus |
| 2026-10-17 | 33 | REVIEW | Review ulang subagent: PASS. Risiko tersisa: derau beramplitudo konstan lolos ambang 15% (bisa dibahas bersama #32) |
| 2026-10-17 | 33 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-17 | 1b | TODO | Dipecah dari #1 atas persetujuan pemilik: #1 = backend + golden, #1b = tampilan skor di kartu klip |
| 2026-10-17 | 5 | TODO | Diperluas atas permintaan pemilik: dari "provider AI kedua" menjadi pilihan multi-provider (Gemini, Claude, GPT, dll.) + cadangan otomatis, dengan baseline golden dan kalibrasi skor per provider. Setelah #1, #1b, #2, #3 |
| 2026-10-17 | 1 | REVIEW | Skor 7 dimensi di respons API (skor datar dari Gemini, total/label/urutan dihitung backend, `prompt_match` hanya dengan fokus). Golden dua mode exit 0 dengan 3.8-flash (`ref_recall_independen` 83,3 / 75,0 = baseline). Smoke 13/13. TEMUAN: skor menggelembung (semua strong, 83-95) dan tidak membedakan momen yang disetujui vs ditolak pemilik (selisih 1-2 poin). Kalibrasi skala lewat prompt dicoba lalu dikembalikan: golden memburuk (tanpa heatmap independen 75 -> 58,35, avoid naik) tanpa perbaikan pemisahan. #1b/#2/#3 perlu dibahas ulang |
| 2026-10-17 | 1 | REVIEW | Review sesi baru: PASS. Smoke 13/13, codemap lulus, golden biasa exit 0 (3.8-flash, independen 83,3). Golden tanpa heatmap tidak bisa diulang setara (kuota 3.8-flash habis, jatuh ke 3.6-flash, exit 3); diterima dari laporan implementer, ulangi sebelum DONE. Semua klip tetap `strong` (85-93) |
| 2026-10-18 | 1b | TODO | Diubah atas persetujuan pemilik: label relatif per hasil analisis (Prioritas/Cadangan), bukan ambang 80/60. Dasar: analisis K3, AUC skor dalam video 0,59-0,70, top 30% cocok pilihan pemilik 45% vs acak 30% |
| 2026-10-18 | 35 | TODO | Task baru: catat pilihan pemilik per klip (Pakai/Lewati + alasan) sebagai data kalibrasi skor |
| 2026-10-18 | 2 | BLOCKED | Menunggu data #35; ambang absolut tidak bermakna dengan skor 85-93 |
| 2026-10-18 | 3 | BLOCKED | Menunggu data #35 dan titik uji campaign; bobot preset belum bisa diturunkan dari 12 momen K3 |
| 2026-10-18 | 1 | REVIEW | Golden --no-heatmap diulang dengan 3.8-flash (key proyek baru): exit 0, `ref_recall_independen` 75,0 = baseline. Uji UI pemilik lulus. Siap /done 1 |
| 2026-10-18 | 1 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-18 | 32 | REVIEW | Label heatmap jujur di prompt: heatmap energi audio (upload/Drive/fallback Whisper) diberi label `audio_energy` sebagai petunjuk lemah; teks YouTube dan tanpa heatmap identik (hash prompt golden sama dengan HEAD). Smoke 14/14, codemap lulus, golden biasa exit 0 (3.8-flash, independen 83,3). BELUM DIUKUR SETARA tanpa heatmap (kuota habis); wajib sebelum DONE |
| 2026-10-18 | 1b | REVIEW | Kartu klip: label relatif Prioritas/Cadangan (sekitar 30% teratas per hasil analisis, stabil terhadap filter), panel 6-7 skor + alasan, lencana Butuh konteks; klip tanpa skor tidak berubah. Komponen baru `ClipScorePanel.tsx` + `utils/clipScores.ts` (lint). Build lulus, lint tanpa error baru, smoke 14/14, codemap lulus, uji browser dengan data contoh |
| 2026-10-18 | 1b | REVIEW | Review sesi baru: PASS |
| 2026-10-18 | 1b | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-18 | 35 | REVIEW | Pilihan Pakai/Lewati + alasan opsional di kartu klip, disimpan permanen di `EXPORTS_DIR/data/clip_choices.json` (tulis atomik, file rusak dibackup, guard lokal) bersama skor, peringkat, label, rata-rata heatmap, model; ekspor JSON/CSV di toolbar. Router `choices`, komponen `ClipChoiceControls`, hook `useClipChoices`. Build lulus, lint tanpa error baru, smoke 15/15 (cek baru), codemap lulus (catatan baru `pilihan-klip`), uji browser dengan folder sementara |
| 2026-10-18 | 35 | REVIEW | Review sesi baru: PASS |
| 2026-10-18 | 35 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-18 | 11 | REVIEW | Kamus koreksi subtitle "salah -> benar" di Clip Studio (preferensi studio), `subtitle_replacements` di `RenderSettingsModel`, diterapkan di `generate_ass_file` untuk mode separate dan merged (cocok tanpa beda huruf, tanda baca ujung dipertahankan, kosong = hapus). Build lulus, lint tanpa masalah baru, smoke 16/16 (cek baru), codemap lulus, uji render ujung ke ujung + frame video, uji browser |
| 2026-10-19 | 11 | REVIEW | Review sesi baru: PASS |
| 2026-10-19 | 11 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-19 | 36a/36b | TODO | Task baru atas permintaan pemilik: subtitle Whisper tampil di pratinjau Clip Studio sebelum render (36a), lalu bisa disunting per klip dan dipakai langsung saat render (36b). Lanjutan #11 (kamus koreksi tetap dipakai) |
| 2026-10-19 | 36a | REVIEW | Pratinjau subtitle asli di Clip Studio: tombol "Buat subtitle" -> `POST /api/preview-subtitles` (segmen + Whisper, cache memori, `_RENDER_SEMAPHORE`), overlay karaoke sinkron pemutar + daftar potongan yang bisa diklik, kamus #11/`text_case` tanpa Whisper ulang. Langkah A-D `generate_ass_file` dipindah ke `build_subtitle_events` (.ass identik pada 400 masukan acak). Build lulus, lint identik, smoke 17/17, codemap lulus, uji browser dengan Whisper sungguhan |
| 2026-10-19 | 36a | REVIEW | Perbaikan temuan reviewer: tombol "Buat ulang" mengirim `force` sehingga Whisper benar-benar dijalankan lagi (lewati cache); smoke 17/17 dengan cek `force` |
| 2026-10-19 | 36a | REVIEW | Review sesi baru: PASS |
| 2026-10-19 | 36a | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-19 | 36b | REVIEW | Render memakai kata pratinjau/suntingan (`subtitle_words`) tanpa Whisper (separate, merged, retry); sunting per baris di Clip Studio (ketik ulang, pecah, gabung, hapus, kembalikan); `build_subtitle_events` mendukung `group` (tanpa group .ass identik, 500 masukan acak). Build lulus, lint identik, smoke 18/18, codemap lulus, uji browser dengan Whisper sungguhan |
| 2026-10-19 | 36b | REVIEW | Review sesi baru: PASS |
| 2026-10-19 | 36b | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-19 | 32 | REVIEW | Golden --no-heatmap dengan 3.8-flash penuh (`--model gemini-3.8-flash`): exit 2, `ref_recall_independen` 66,7 vs baseline 75,0 (1 referensi dari 12), metrik lain sama/dalam variasi. Prompt jalur ini identik dengan sebelum #32, jadi variasi model; pemilik memutuskan terima, ukur ulang baseline, atau task toleransi. Run auto sebelumnya exit 3 (3.8-flash 504, jatuh ke 3.7) |
| 2026-10-19 | 32 | REVIEW | Golden --no-heatmap --repeat 4 (3.8-flash, key proyek lain): exit 2, independen 66,675 vs 75,0; per video A 37,5 / B 100 / C 62,5 vs baseline 0 / 100 / 100 (arah berlawanan). Nilai stabil 66,7 di dua pengukuran; baseline 2 run kebetulan tinggi. Menunggu keputusan pemilik (terima / baseline baru) |
| 2026-10-19 | 32 | REVIEW | Keputusan pemilik: selisih diterima sebagai variasi, baseline tanpa heatmap diganti dengan run 4 ulangan (`score --save-baseline`, tanpa kuota; independen 66,675). Run terpisah 2 ulangan vs baseline baru: exit 0. Siap /review 32 |
| 2026-10-19 | 32 | REVIEW | Review sesi baru: PASS |
| 2026-10-19 | 32 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-19 | 37 | TODO | Ditambahkan atas permintaan pemilik: lingkar belajar dari performa klip (views, payout, acceptance) yang menghasilkan usulan bobot/ambang/contoh prompt dengan persetujuan pemilik. Fase 4 setelah #23; kontrak ditulis lewat `/mulai` |
| 2026-10-19 | 38-39 | TODO | Ditambahkan atas permintaan pemilik (akun fokus bahasa Inggris): #38 ukur dan pilih model Whisper lebih akurat dari `base`, #39 pilihan bahasa audio untuk transkripsi (bukan terjemahan; terjemahan subtitle tidak dikerjakan). Ide lama "bahasa Indonesia dikunci" dibatalkan karena merusak video Inggris. Toleransi golden dan perbaikan kecil #36b ditunda |
| 2026-10-19 | 38 | REVIEW | Model Whisper lewat `CHEAT_CLIP_WHISPER_MODEL`, default `small` (pilihan pemilik), tidak dikenal = `base`; skrip ukur `scripts/whisper_bench.py`. Ukur 2 klip Inggris: `small` WER 2,4%/11,6% vs `base` 6,1%/12,0%, ±0,8x real-time, RAM 1,7 GB; `medium` tidak lebih akurat dan 2-3x lebih lambat. Ukur Indonesia dilewati atas keputusan pemilik. Smoke 19/19, codemap lulus |
| 2026-10-19 | 38 | REVIEW | Review sesi baru: PASS. Smoke 19/19, codemap lulus, skrip ukur jalan (run reviewer: `base` di klip Indonesia tidak stabil, 13,3% kata berbeda antar run). Tabel Indonesia tidak ada (keputusan pemilik). Temuan kecil: rujukan baris di keterangan codemap (`subtitle-dan-judul.md` `build_subtitle_events`, `render-server.md` AMF, `unduhan-raw.md` format) tidak ikut digeser +21 |
| 2026-10-19 | 38 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-20 | 39 | REVIEW | Bahasa audio Whisper (Otomatis/en/id/ms/es/pt/fr/de/ar/hi/ja/ko) di form analisis dan Clip Studio (satu state), diteruskan sebagai `language` ke Whisper di analisis upload/fallback YouTube, pratinjau, render separate/merged/retry; Otomatis identik dengan sebelumnya; cache pratinjau per bahasa; kode lain 422. Smoke 20/20, build lulus, lint tanpa error baru, codemap lulus (rujukan #38 dirapikan). Uji browser: log `language=en`, render = pratinjau; pemilik: subtitle Inggris akurat. Salah pilih bahasa = Whisper menerjemahkan kasar |
| 2026-10-20 | 39 | REVIEW | Review sesi baru: PASS. Smoke 20/20, build lulus, lint sama dengan induk, codemap lulus. Fallback Whisper YouTube hanya dibuktikan dari diff. Catatan kecil: `localStorage` bahasa audio tanpa try/catch |
| 2026-10-20 | 39 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-20 | 28 | IN_PROGRESS | Dibuka kembali atas keputusan pemilik sebelum produksi campaign. Riset ulang: `yt-dlp-ejs` + Node membuka format sampai 2160p (sesekali hanya 360p), unduhan native 1080p 10,5 menit 73 s. Kontrak ditulis ulang sebagai versi kecil #28a (cache stream 1080p, saklar `CHEAT_CLIP_YT_HD_CACHE`, metode lama tetap cadangan); 1440p/2160p dan unduh video asli jadi #28b. Kontrak disetujui pemilik |
| 2026-10-20 | 28 | REVIEW | Cache stream HD YouTube (#28a): `yt-dlp-ejs` + Node, unduh native 1080p sekali per video ke `temp_clips/yt_cache/` lalu potong lokal; saklar `CHEAT_CLIP_YT_HD_CACHE`, batas 2 GB, coba ulang ekstraksi, metode lama tetap cadangan. Perluasan kontrak (disetujui pemilik): `get_yt_dlp_base_cmd(solve_js_challenges=False)` = `--no-js-runtimes` agar metode lama tidak macet di HD. Uji nyata: 1080p 3/3 (66-76 s klip pertama), pakai ulang 18,5 s, 2 permintaan = 1 unduhan, saklar 0 = 360p 20 s; uji UI pratinjau + render AMF 1080x1920 dari cache. Smoke 21/21, codemap lulus |
| 2026-10-20 | 28 | REVIEW | Review sesi baru: PASS |
| 2026-10-20 | 28 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-20 | 40 | IN_PROGRESS | Dibuat atas permintaan pemilik dari catatan review #39 dan #36b (perbaikan kecil, tanpa izin fase) |
| 2026-10-20 | 40 | REVIEW | Bahasa audio lewat helper `localStorage` ber-try/catch, smoke cek 12 fallback Whisper YouTube `[None, "en"]`, `editedWords` hanya ditulis setelah pratinjau sukses, kata > 60 ditolak di input sunting. Uji UI: 61 ditolak tanpa request, 60 diterima, pratinjau gagal = render memakai kata pratinjau terakhir. Smoke 22/22, build lulus, lint tidak bertambah, codemap lulus |
| 2026-10-20 | 40 | REVIEW | Review sesi baru: PASS |
| 2026-10-20 | 40 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-20 | 22 | IN_PROGRESS | Dimulai atas izin pemilik (Fase 3 sebelum Fase 2 selesai, karena #2/#3 menunggu data produksi) |
| 2026-10-20 | 22 | REVIEW | Posting kit per klip di `EXPORTS_DIR/kits/` (video.mp4 hardlink, SRT = baris karaoke, metadata.json dengan `prompt_version`, caption TikTok/Reels/Shorts/X dari saran Gemini tanpa panggilan baru), ikut ZIP, kit gagal tidak menggagalkan klip. URL/kredit palsu untuk upload dari riwayat disaring. Smoke 23/23, build lulus, lint tidak bertambah, codemap lulus, uji browser render 1 klip |
| 2026-10-20 | 22 | REVIEW | Review sesi baru: PASS |
| 2026-10-20 | 22 | DONE | Ditetapkan DONE oleh pemilik proyek |
| 2026-10-20 | 20, 21, 23 | SKIPPED | Keputusan pemilik: langsung ikut campaign brand dengan app yang ada; brief dan compliance dicek manual, ledger diganti tracker spreadsheet. Dibuka lagi bila volume membuat langkah manual berat |
| 2026-10-21 | 41 | TODO | Ditambahkan atas permintaan pemilik: atur awal/akhir klip manual sebelum render, memakai trimmer yang sudah ada (izin aturan no. 6 dari pemilik) |
| 2026-10-21 | 41 | IN_PROGRESS | Kontrak disetujui pemilik |
| 2026-10-21 | 41 | REVIEW | Tombol Sesuaikan Durasi di kartu klip dan Clip Studio membuka trimmer; Terapkan tanpa unduh raw, tombol ±1 s, tanda render dan judul kustom ikut rentang baru, rentang kembar ditolak. Build lulus, lint tidak bertambah, smoke 23/23, codemap lulus, uji browser: render 12-21 s = MP4 9,03 s |
| 2026-10-21 | 41 | REVIEW | Perbaikan temuan reviewer subagent: Terapkan setelah Unduh raw di modal yang sama memakai rentang terakhir (`trimmerAppliedRef`), tidak lagi pesan duplikat keliru atau sukses palsu. Uji browser ulang lulus |
| 2026-10-21 | 41 | REVIEW | Review sesi baru: PASS |
| 2026-10-21 | 41 | REVIEW | Temuan pemilik: pratinjau Clip Studio berjalan sampai akhir rentang lama setelah Terapkan. Area player pratinjau ditambah ke kontrak atas persetujuan pemilik; pemantau waktu dan handler YouTube membaca `previewBoundsRef`. Build, lint sama, smoke, codemap lulus; uji browser: ulang di 16,08 s, Loop mati berhenti di 16,16 s. Perlu `/review 41` ulang |
| 2026-10-21 | 41 | REVIEW | Review sesi baru (ulang, perbaikan pratinjau): PASS |
| 2026-10-21 | 41 | DONE | Ditetapkan DONE oleh pemilik proyek |

***

## Alur sesi Claude Code (setelah P3b selesai)

```text
cd D:\Projects\cheat-clip-pro
claude                → baton termuat otomatis (hook SessionStart)
/mulai <ID>           → draf kontrak → pemilik proyek menyetujui → implementasi
/tutup                → test, laporan, codemap, TASKS.md (REVIEW), commit, subagent reviewer
(pemilik proyek mencoba hasilnya)
/done <ID>            → DONE, log, commit
```

Gunakan `/clear` atau sesi baru di antara task. Sebelum P3b selesai, pakai prompt manual: baca TASKS.md, kerjakan task <ID>, lalu jalankan langkah penutup (test, laporan, status, log, commit).

---

## Template kontrak ringan (`docs/tasks/CHEAT-<ID>.md`)

```markdown
# CHEAT-<ID> — <judul singkat>
Status: TODO | IN_PROGRESS | REVIEW | DONE | FIX_REQUIRED | BLOCKED

## Tujuan
Satu kalimat hasil akhir.

## Area yang boleh disentuh
- <file>: <fungsi/bagian> (± baris X–Y)

## Di luar scope (jangan dikerjakan)
- ...

## Keputusan yang boleh diambil AI sendiri
- ...

## Kriteria selesai (ya/tidak)
- [ ] ...

## Cara menguji
- ...

## Laporan implementer
STATUS:
FILE_DIUBAH:
HASIL_TEST:
CODEMAP_DIPERBARUI: ya/tidak (sebutkan catatan)
CATATAN:

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
```

### Prompt review (tempel di sesi Claude baru)

```text
Baca TASKS.md dan docs/tasks/CHEAT-<ID>.md. Review perubahan pada `git diff` terhadap kontrak itu saja.
Cek: semua kriteria selesai terpenuhi, tidak ada perubahan di luar area yang diizinkan, test lulus, codemap terdampak sudah diperbarui.
Tulis VERDICT (PASS/FIX_REQUIRED) + alasan di bagian Review kontrak, lalu perbarui status di TASKS.md.
```

