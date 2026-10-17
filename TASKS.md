# TASKS — Kustomisasi Cheat Clip PRO

> File ini adalah **baton** antar sesi. Setiap sesi AI membaca file ini lebih dulu, mengerjakan **satu task**, lalu memperbarui status di sini.
> Dibuat: 2026-10-10

***

## Baton saat ini

```text
fase_aktif:      Fase 2 — Inti AI
task_aktif:      34
status:          34 REVIEW
langkah_berikut: Pemilik mencoba #34 lalu /done 34. Setelah itu /mulai 33 (heatmap buatan), lalu /mulai 1 (skor 7 dimensi; golden wajib dengan dan tanpa heatmap), kemudian #2 dan #3. #32 bersama/setelah #1
blocker:         #3 menunggu skor #1. Baseline golden gemini-3.8-flash (key kedua); key utama habis kuota s.d. ±2026-10-14 08:00
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
| 28 | Unduhan HD YouTube: format HD (klien `android_vr`) ditolak 403 bila diambil ffmpeg (`--download-sections`, URL stream), jadi app hanya mendapat 360p (format 18). Riset: klien lain, `yt-dlp-ejs`, atau unduh native lalu potong lokal | `backend/video_engine.py` (`get_yt_dlp_base_cmd`, `download_clip_segment`, `download_full_raw_video`) | Segmen dari video YouTube 4K terunduh ≥ 1080p (cek ffprobe), waktu unduh wajar, fallback tetap ada | SKIPPED |

***

## Fase 2 — Inti AI

| ID | Upgrade                                                                                                                                                                                                                                     | Area kode                                                                                                                | Selesai jika                                                       | Status |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------ |
| 17b | Golden fixtures: 2–3 transkrip contoh (dari K3) dengan momen terbaik yang sudah diketahui + skrip pembanding hasil analisis. Dipecah dari task 17 | Baru: folder fixtures + skrip uji, memakai pipeline `backend/routers/analyze.py` | Satu perintah membandingkan hasil analisis dengan momen terbaik. Wajib DONE sebelum #1, #2, #12 | DONE   |
| 1  | Skor 7 dimensi (Prompt Match, Hook, Retention, Clarity, Emotional Pull, Payoff, Editability) + penjelasan + label skor. Aturan: kandidat beragam, skor independen, tanpa klaim "pasti viral", hook tanpa fakta baru, tandai "butuh konteks" | `backend/schemas/analyze.py` (`ViralClip`), `backend/routers/analyze.py` (prompt ±945–1110), kartu klip di `src/App.tsx` | Setiap klip menampilkan 7 skor + penjelasan yang merujuk transkrip | TODO   |
| 2  | Prompt Match gate: Prompt Match < 50 → skor total × 0,85                                                                                                                                                                                    | Pasca-proses di `backend/routers/analyze.py`                                                                             | Unit test kasus di bawah dan di atas ambang lulus                  | TODO   |
| 12 | Guardrail output: kutipan dicek ke transkrip, timestamp di dalam durasi, overlap > 70% digabung (40–70% ditinjau), transkrip dibungkus `<TRANSCRIPT_DATA>`, jumlah klip tidak dipaksa saat momen bagus sedikit                              | `backend/routers/analyze.py` (prompt + validasi setelah parse, termasuk logika target jumlah klip ±895–945)              | Golden fixtures lulus: tanpa kutipan karangan, tanpa duplikat      | DONE   |
| 29 | Klip fallback heatmap saat rentang khusus: batas akhir memakai `duration` relatif sehingga klip terbalik lalu dijepit guardrail jadi satu klip panjang. Temuan review #12 | `backend/routers/analyze.py` (klip fallback heatmap ±1345–1420), `scripts/smoke_test.py` | Klip fallback dengan rentang berada di dalam rentang dan sepanjang target | DONE   |
| 30 | Klip fallback heatmap saling tumpang tindih: kandidat hanya berjarak 25 s padahal target `auto`/`60s` sampai 85 s, sehingga guardrail menggabungkan klip dan menyisakan klip skor tertinggi (bisa klip 5 s di ujung rentang). Temuan #29 | `backend/routers/analyze.py` (klip fallback heatmap L1345-1425), `scripts/smoke_test.py` | Klip fallback tidak tumpang tindih (tidak ada yang digabung atau ditandai overlap oleh guardrail), rentang 60-110 dengan `auto` menghasilkan lebih dari 1 klip dan tidak ada klip < 10 s bila ada kandidat lain | DONE   |
| 31 | Golden fixtures tanpa heatmap: opsi `run --no-heatmap` yang mengosongkan heatmap sebelum dikirim ke backend (penilaian `heat_lift` tetap memakai heatmap asli), untuk mengukur kualitas jalur video upload/Drive dan YouTube tanpa heatmap. Ketiga video K3 berheatmap asli, jadi jalur itu belum pernah diukur. Temuan K3 Tahap 2 | `scripts/golden_fixtures.py`, `docs/codemap/golden-fixtures.md` | `run --no-heatmap` (dan `--mock`) jalan, laporan menandai mode tanpa heatmap, `--compare` tidak mencampur hasil tanpa heatmap dengan baseline biasa, `selftest` lulus. Satu run Gemini tanpa heatmap dicatat sebagai titik awal | DONE   |
| 32 | Label heatmap akustik yang jujur di prompt: video upload/Drive memakai energi audio (RMS) tetapi prompt menyebutnya `audience_interest` dan meminta "Prioritise high-interest peaks" (`analyze.py` ±L981-984), padahal suara keras belum tentu menarik. Bedakan sumber heatmap (penonton YouTube vs energi audio) di prompt. Perubahan prompt: dikerjakan bersama atau setelah #1 | `backend/routers/analyze.py` (sumber heatmap, `heatmap_note`), golden fixtures | Prompt menyebut sumber heatmap dengan benar untuk tiap jalur, jalur YouTube tidak berubah, golden `run --repeat 2 --compare` exit 0 dan (bila #31 ada) `--no-heatmap` tidak memburuk | TODO   |
| 33 | Heatmap akustik palsu saat audio gagal: `compute_audio_energy_heatmap` memakai batas 30 s untuk ekstraksi audio FFmpeg (`video_engine.py` ±L594); bila gagal/timeout semua nilai rata lalu fungsi membuat pola sinus buatan (±L627-628) yang dikirim ke Gemini sebagai minat penonton. Video upload panjang (mis. podcast 2 jam) berisiko. Belum diuji, terbaca dari kode | `backend/video_engine.py` (`compute_audio_energy_heatmap`), `scripts/smoke_test.py` | Tidak ada heatmap buatan: gagal/datar menghasilkan heatmap kosong (prompt jatuh ke "No audience interest data"), batas waktu ekstraksi menyesuaikan durasi, video sintetis panjang lulus, smoke test lulus | TODO   |
| 34 | `ref_recall` per sumber referensi: total sekarang mencampur referensi dari kandidat Gemini dan dari heatmap/Short, sehingga bisa naik hanya karena Gemini cocok dengan pilihannya sendiri (#31: tanpa heatmap sumber gemini 7/12 -> 11/12, sumber heatmap 8/10 -> 7/10). Tambah `ref_recall` per `source` dan angka utama `ref_recall_independen` (hanya heatmap + short) sebagai penentu `--compare`; total tetap ditampilkan sebagai informasi. Sebelum #1 | `scripts/golden_fixtures.py` (`score_video`, `summarize`, `compare`, `print_compare`, selftest), `tests/golden/baseline.json` dan `baseline-noheatmap.json` (dinilai ulang lewat `score --save-baseline` dari run yang sama), `docs/codemap/golden-fixtures.md`, `CLAUDE.md` | Laporan dan baseline memuat recall per sumber dan `ref_recall_independen`; `--compare` memutuskan lebih buruk dari `ref_recall_independen`; kedua baseline dinilai ulang tanpa Gemini dengan metrik lain tidak berubah; `selftest` lulus | REVIEW |
| 3  | Preset bobot (Founder, Edukasi, Hiburan, Gaming, General) + hitung ulang ranking lokal                                                                                                                                                      | `src/App.tsx`                                                                                                            | Ganti preset → ranking berubah tanpa memanggil AI                  | TODO   |

Bobot default (jumlah 100): Prompt Match 25 · Hook 20 · Retention 20 · Clarity 15 · Emotional Pull 10 · Payoff 7 · Editability 3.
Preset lain: lihat `D:\Clipper\clipper app\foundation\06_SCORING_SYSTEM.md` §7–10.

***

## Fase 3 — Lapisan campaign

| ID | Upgrade                                                                                                                                                                          | Area kode                                                                                                             | Selesai jika                                                   | Status |
| -- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------ |
| 20 | Campaign Profile (menyerap #4 dan #13): sumber resmi, platform, credit line persis, hashtag wajib, durasi min–maks, gaya terlarang, brief, audiens, eksklusi, CPM, batas bayaran | Baru: `backend/campaigns/*.json` + router + form UI                                                                   | Satu profil otomatis terpakai di analisis, render, dan caption | TODO   |
| 21 | Compliance checker: durasi, credit/hashtag persis, source resmi, musik/overlay terlarang                                                                                         | Baru: `backend/services/compliance_service.py` + panel ✓/⚠️ di UI                                                     | Klip yang melanggar brief tertandai sebelum ekspor             | TODO   |
| 11 | Koreksi subtitle sebelum render                                                                                                                                                  | `src/components/ClipStudioSection.tsx`, `backend/schemas/render.py`, `generate_ass_file` di `backend/video_engine.py` | Kata yang dikoreksi muncul benar di video hasil render         | TODO   |
| 22 | Posting kit (menyerap #19 dan #6): per klip MP4 + SRT + `metadata.json` (skor, prompt, versi prompt, model) + caption per platform, dibuat setelah klip dipilih                  | `backend/services/render_service.py`, `backend/routers/analyze.py`                                                    | Satu folder per klip siap unggah ke TikTok, Reels, Shorts, X   | TODO   |

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
| 23 | Campaign ledger (menyerap #14): campaign, klip, URL, views hari ke-1/3/7, status, pendapatan, acceptance rate | Korelasi skor AI vs views nyata bisa dilihat | TODO   |
| 24 | Antrean multi-source                                                                                          | 10 video diproses tanpa ditunggui            | TODO   |
| 5  | Provider AI kedua + circuit breaker                                                                           | Analisis tetap jalan saat kuota Gemini habis | TODO   |

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
| K4 | Campaign pertama untuk titik uji (platform + niche)           | <br />  |

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

