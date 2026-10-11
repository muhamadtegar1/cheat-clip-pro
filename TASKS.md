# TASKS — Kustomisasi Cheat Clip PRO

> File ini adalah **baton** antar sesi. Setiap sesi AI membaca file ini lebih dulu, mengerjakan **satu task**, lalu memperbarui status di sini.
> Dibuat: 2026-10-10

***

## Baton saat ini

```text
fase_aktif:      Fase 1 — Perbaikan cepat
task_aktif:      —
status:          7 DONE
langkah_berikut: /mulai 9 (task terakhir Fase 1) setelah K2 (GPU) tersedia. Melompat ke Fase 2 (#17b) hanya dengan persetujuan pemilik (aturan 6)
blocker:         #9 butuh K2 (GPU)
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
| 9  | Sumber sampai 2160p + bitrate AMF lebih tinggi                                                                       | `backend/video_engine.py` baris ±806, ±858, ±1055 (format yt-dlp) dan ±289 (AMF)                                               | Video 4K terunduh tinggi 2160 (cek ffprobe). Output tetap 1080×1920 dan lebih tajam. Fallback 720p/480p tidak berubah | TODO   |
| 7  | Amankan API key + endpoint admin                                                                                     | `src/App.tsx` (±baris 2820), `backend/schemas/analyze.py`, `backend/routers/system.py` (`verify_admin_access`)                 | Key tidak ada di `localStorage`. Endpoint update/restart menolak request tanpa key admin                              | DONE   |

***

## Fase 2 — Inti AI

| ID | Upgrade                                                                                                                                                                                                                                     | Area kode                                                                                                                | Selesai jika                                                       | Status |
| -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------ |
| 17b | Golden fixtures: 2–3 transkrip contoh (dari K3) dengan momen terbaik yang sudah diketahui + skrip pembanding hasil analisis. Dipecah dari task 17 | Baru: folder fixtures + skrip uji, memakai pipeline `backend/routers/analyze.py` | Satu perintah membandingkan hasil analisis dengan momen terbaik. Wajib DONE sebelum #1, #2, #12 | TODO |
| 1  | Skor 7 dimensi (Prompt Match, Hook, Retention, Clarity, Emotional Pull, Payoff, Editability) + penjelasan + label skor. Aturan: kandidat beragam, skor independen, tanpa klaim "pasti viral", hook tanpa fakta baru, tandai "butuh konteks" | `backend/schemas/analyze.py` (`ViralClip`), `backend/routers/analyze.py` (prompt ±945–1110), kartu klip di `src/App.tsx` | Setiap klip menampilkan 7 skor + penjelasan yang merujuk transkrip | TODO   |
| 2  | Prompt Match gate: Prompt Match < 50 → skor total × 0,85                                                                                                                                                                                    | Pasca-proses di `backend/routers/analyze.py`                                                                             | Unit test kasus di bawah dan di atas ambang lulus                  | TODO   |
| 12 | Guardrail output: kutipan dicek ke transkrip, timestamp di dalam durasi, overlap > 70% digabung (40–70% ditinjau), transkrip dibungkus `<TRANSCRIPT_DATA>`, jumlah klip tidak dipaksa saat momen bagus sedikit                              | `backend/routers/analyze.py` (prompt + validasi setelah parse, termasuk logika target jumlah klip ±895–945)              | Golden fixtures lulus: tanpa kutipan karangan, tanpa duplikat      | TODO   |
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
| K2 | GPU komputer (NVIDIA / AMD / Intel) untuk optimasi encoder #9 | <br />  |
| K3 | 2–3 video golden fixtures + momen terbaiknya (untuk 17b)      | <br />  |
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

