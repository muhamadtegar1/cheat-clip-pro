# CHEAT-1b: Tampilan skor 7 dimensi dan label relatif di kartu klip
Status: DONE
Risiko: rendah (hanya frontend, tanpa perubahan prompt atau backend)

## Tujuan
Kartu klip menampilkan label prioritas relatif per hasil analisis, 7 skor dimensi, alasan skor, dan tanda "butuh konteks" dari respons #1, dan semuanya disembunyikan untuk klip tanpa skor.

## Kondisi sekarang (diverifikasi di kode)
- Backend (#1, DONE) sudah mengirim per klip `scores` (7 dimensi 0-100, `prompt_match` null tanpa fokus pencarian), `score_reason`, `needs_context`, `score_label` (absolut 80/60), dan `virality_score` = rata-rata dimensi.
- `src/types.ts` `ViralClip` (L14-25) belum punya field tersebut, jadi frontend mengabaikannya.
- `src/App.tsx` kartu klip: `sortedClips.map` mulai L4502, badge skor di header L4610-4613 (`virality_score`, gaya high >= 90), kutipan L4630-4637, saran judul/caption sesudahnya, detail saat kartu dibuka L4801.
- Cache riwayat menyimpan seluruh respons (`localStorage.setItem(targetCacheKey, JSON.stringify(resultData))`, L1674), jadi analisis yang dibuat setelah #1 sudah membawa skor; analisis lama tidak.
- Temuan #1: skor Gemini menggelembung (total 84-94, semua `score_label` = `strong`), tetapi urutan dalam satu video punya sinyal (AUC 0,59-0,70, 30% teratas cocok pilihan pemilik 45% vs acak 30%). Uji UI pemilik: semua klip yang diambil layak tayang. Karena itu label absolut `score_label` tidak dipakai di UI.

## Desain yang diusulkan (bisa dikoreksi pemilik saat menyetujui)
1. **Label relatif per hasil analisis**, dihitung di frontend dari semua klip bertanda skor di `result.clips` (bukan dari daftar yang sedang difilter): urutkan `virality_score` turun, sekitar 30% teratas (dibulatkan ke atas, minimal 1) = **"Prioritas"**, sisanya = **"Cadangan"**. Klip dengan skor sama dengan batas ikut "Prioritas". Label dibaca sebagai urutan prioritas, bukan vonis kualitas; tooltip menjelaskannya.
2. **Header kartu**: pil label relatif di samping badge skor yang sudah ada, plus lencana "Butuh konteks" bila `needs_context` true.
3. **Panel skor ringkas** di bawah kutipan: 7 dimensi (Prompt Match hanya bila tidak null) sebagai bar kecil dengan angka, lalu `score_reason`. Dibuat sebagai komponen baru agar `App.tsx` hanya mendapat beberapa baris (sesuai risiko codemap `frontend-app.md`).
4. Klip tanpa `scores` (analisis lama dari riwayat, klip fallback heatmap): label, lencana, dan panel tidak dirender sama sekali; kartu tampil seperti sekarang.
5. `score_label` dari backend hanya ditambahkan ke tipe, tidak ditampilkan.

## Area yang boleh disentuh
- `src/types.ts`: `ViralClip` (L14-25) + tipe baru `ClipScores`.
- `src/components/ClipScorePanel.tsx` (baru): panel skor, pil label, dan lencana butuh konteks.
- `src/utils/clipScores.ts` (baru, ditambahkan saat implementasi): fungsi penghitung label relatif dan helper skor. Dipisah dari file komponen karena aturan lint `react-refresh/only-export-components` menolak ekspor fungsi biasa dari file komponen (3 error baru bila digabung).
- `src/App.tsx`: header kartu klip (±L4600-4630) untuk pil label dan lencana, sesudah blok kutipan (±L4630-4637) untuk panel, satu `useMemo` kecil untuk label relatif dari `result.clips` (dekat filter + urutan klip, ±L2248-2284), dan impor komponen.
- `src/locales/id.ts`, `src/locales/en.ts`: string baru di bagian `results` (label, tooltip, nama 7 dimensi, "Butuh konteks", judul panel).
- `docs/codemap/frontend-app.md` (komponen baru, rentang baris bergeser), `docs/codemap/index.md` bila perlu, `TASKS.md`, kontrak ini.

## Di luar scope (jangan dikerjakan)
- Badge `virality_score` yang ada, filter "high >= 90", urutan klip, ekspor teks/Markdown/JSON, `ClipStudioSection.tsx`.
- Semua backend, prompt, `score_label` absolut di backend, smoke test, golden.
- Tombol Pakai/Lewati (#35), Prompt Match gate (#2), preset bobot (#3).
- CSS global di luar gaya inline atau kelas kecil yang dibutuhkan komponen baru.

## Keputusan yang boleh diambil AI sendiri
- Tata letak dan gaya panel (bar, warna, ukuran) selama ringkas dan konsisten dengan kartu yang ada.
- Nama komponen, fungsi, dan kunci locale; urutan dimensi di panel.
- Apakah panel selalu tampil atau hanya saat kartu dibuka, selama alasan skor dan label terlihat tanpa klik tambahan.

## Kriteria selesai (ya/tidak)
- [x] Untuk hasil analisis dengan skor, setiap kartu menampilkan label relatif ("Prioritas"/"Cadangan" dalam id, "Priority"/"Backup" dalam en), sekitar 30% teratas per hasil analisis = Prioritas, dihitung dari semua klip hasil analisis sehingga tidak berubah saat filter atau pencarian dipakai.
- [x] Panel menampilkan 6 skor (7 bila ada fokus pencarian) dan `score_reason`; lencana "Butuh konteks" muncul hanya bila `needs_context` true.
- [x] Klip tanpa `scores` (riwayat lama, fallback) tampil seperti sebelum task tanpa error di console.
- [x] Semua string baru ada di `id.ts` dan `en.ts`; `npm run build` lulus; smoke test dan `check_codemap.py` lulus; `git diff` hanya menyentuh area di atas.

## Cara menguji
- `npm run build`
- `npm run lint` (catat bila ada error lama yang tidak terkait; file baru tidak boleh menambah error)
- `venv\Scripts\python.exe scripts\smoke_test.py` dan `venv\Scripts\python.exe scripts\check_codemap.py`
- Pemilik, tanpa kuota Gemini: buka dari riwayat analisis yang dibuat setelah #1 (mis. uji UI 2026-10-18), cek label, panel, dan lencana di id dan en; buka satu analisis lama dari sebelum #1 dan pastikan kartunya normal; coba filter/pencarian dan pastikan label tidak berubah.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `src/types.ts`: tipe baru `ClipScores` (L15-23); `ViralClip` + `scores`, `score_reason`, `needs_context`, `score_label` (opsional, null untuk analisis lama/fallback).
- `src/components/ClipScorePanel.tsx` (baru): `ClipTierBadges` (L19-52, pil Prioritas/Cadangan + lencana Butuh konteks), `ClipScorePanel` (L54-96, bar skor per dimensi + `score_reason`, tidak dirender tanpa skor).
- `src/utils/clipScores.ts` (baru): `SCORE_DIMENSIONS`, `clipKey`, `hasClipScores`, `computeClipTiers` (L23-34).
- `src/App.tsx` (+8 baris): impor (L13-14), `clipTiers` `useMemo` dari `result?.clips` (L2269), `<ClipTierBadges>` di header kartu (L4619), `<ClipScorePanel>` sesudah kutipan (L4648).
- `src/locales/id.ts`, `src/locales/en.ts`: `scoreTierPriority`, `scoreTierBackup`, `scoreTierTooltip`, `needsContextBadge`, `needsContextTooltip`, `scorePanelTitle`, `scoreReasonLabel`, `scoreDimensions` di `results`.
HASIL_TEST:
- `npm run build` (tsc -b + vite): lulus.
- Lint: file baru dan yang diubah tanpa error (`npx eslint` pada 5 file: bersih). `npm run lint` total 97 masalah (88 error, 9 warning), sama dengan sebelum task (`App.tsx` 27 sebelum dan sesudah, dicek dengan stash); tidak ada error baru.
- Smoke test: 14/14 lulus. `check_codemap.py`: SEMUA CEK LULUS (232 simbol).
- Uji browser (pratinjau frontend Vite, data contoh disuntikkan ke `localStorage` riwayat, tanpa Gemini dan tanpa mengubah `.env`; data dihapus setelah uji):
  - 7 klip (6 bertanda skor 93/91/89/87/85/85 + 1 tanpa skor): 2 Prioritas (93, 91), 4 Cadangan, klip tanpa skor tanpa label dan panel. Lencana Butuh konteks hanya di 2 klip dengan `needs_context` true. Panel menampilkan 6 skor (`prompt_match` null disembunyikan) + alasan.
  - Filter "Menengah/Rendah (<90%)": klip 3-6 tetap Cadangan (label tidak dihitung ulang dari daftar yang difilter).
  - Bahasa Indonesia: "★ Prioritas", "⚠ Butuh konteks", "SKOR AI (0-100)", "Retensi", "Kejelasan", "Daya Emosi", "Kemudahan Edit", "Alasan:". Bahasa Inggris: "★ Priority", "Backup", "⚠ Needs context", "AI SCORES (0-100)".
  - Analisis lama tanpa skor: 2 kartu normal dengan badge lama (95%/80% Viralitas), tanpa label/panel. Error console hanya 503 dari proxy `/api` (backend tidak dinyalakan di pratinjau) dan peringatan `src=""` pemutar yang sudah ada.
CODEMAP_DIPERBARUI: ya. `frontend-app.md`: `file_utama` + baris `ClipTierBadges`, `ClipScorePanel`, `computeClipTiers`, `hasClipScores`, deskripsi `clipTiers`, kartu klip, `types.ts`, risiko label relatif; semua rentang `App.tsx`/`types.ts` dipetakan ulang (difflib HEAD -> kerja). Rentang `App.tsx` yang bergeser juga di `penyimpanan-dan-cleanup.md`, `render-browser.md`, `sistem-update.md` (termasuk rujukan basi `SELF_UPDATE_DISABLED` L25 -> L27 yang ditemukan cek codemap), `sumber-video.md`, `unduhan-raw.md`.
CATATAN:
- Keputusan sendiri: panel selalu tampil di kartu (tanpa klik), bar skor ungu dengan angka; label Prioritas hijau, Cadangan abu-abu, Butuh konteks kuning; urutan dimensi Prompt Match, Hook, Retention, Clarity, Emotional Pull, Payoff, Editability; skor sama dengan batas ikut Prioritas.
- Di luar area awal: `src/utils/clipScores.ts` (baru), dicatat di Area kontrak. Alasan: aturan lint `react-refresh/only-export-components` memberi 3 error baru bila fungsi diekspor dari file komponen.
- `score_label` absolut dari backend ditambahkan ke tipe tetapi tidak ditampilkan. Badge `virality_score`, filter "high >= 90", dan ekspor tidak diubah.
- Perlu dicek pemilik: buka dari riwayat analisis asli yang dibuat setelah #1 (data dengan skor nyata) dan nilai apakah panel nyaman dibaca; panel menambah tinggi kartu.
- `.claude/launch.json` (konfigurasi pratinjau frontend) dibuat untuk uji browser, tidak di-commit.

## Review (sesi baru)
VERDICT: PASS
ALASAN:
- Lingkup: commit `4c354db` hanya menyentuh `src/types.ts`, `src/App.tsx` (+8 baris: impor, `clipTiers` useMemo, `<ClipTierBadges>` di header, `<ClipScorePanel>` sesudah kutipan), `src/components/ClipScorePanel.tsx` (baru), `src/utils/clipScores.ts` (baru), `src/locales/id.ts`, `src/locales/en.ts`, `docs/codemap/*`, kontrak. Badge `virality_score`, filter, urutan, ekspor, `ClipStudioSection.tsx`, backend tidak diubah. Catatan: `src/utils/clipScores.ts` ditambahkan ke Area saat implementasi (alasan lint `react-refresh/only-export-components` masuk akal, tercatat di kontrak dan laporan); pemilik sebaiknya menyetujui tambahan ini secara eksplisit.
- Label relatif: `computeClipTiers` (`src/utils/clipScores.ts` L23-34) memakai `ceil(30%)` minimal 1 dari semua klip bertanda skor; `useMemo` di `App.tsx` bergantung pada `result?.clips`, bukan `filteredClips`, jadi label tidak berubah saat filter/pencarian. String id "★ Prioritas"/"Cadangan", en "★ Priority"/"Backup". Terpenuhi (dari kode). Catatan kecil: skor sama dengan batas ikut Prioritas, jadi bisa lebih dari 30% bila banyak skor kembar (sesuai desain kontrak).
- Panel: `ClipScorePanel` merender dimensi yang bernilai number saja, jadi `prompt_match` null tersembunyi (6 skor) dan tampil bila ada (7), plus `score_reason`. Lencana Butuh konteks hanya bila `needs_context` truthy. Terpenuhi.
- Klip tanpa skor: `hasClipScores` false -> panel `null`, tidak masuk `clipTiers` -> tanpa pil; field opsional di `types.ts`, tidak ada akses tanpa guard. Terpenuhi dari kode; tampilan riwayat asli perlu dicek pemilik.
- Locale: 8 kunci baru di `results` ada di `id.ts` dan `en.ts` dengan bentuk sama (build `tsc -b` lulus terhadap tipe `Translations`).
- Test (dijalankan reviewer): `npm run build` lulus (hanya peringatan ukuran chunk lama). `npx eslint` pada 5 file baru/diubah selain App.tsx: bersih. `App.tsx`: 27 masalah (23 error, 4 warning) sekarang dan di `fe2120c` (sebelum task), tidak ada error baru. Smoke test 14/14 lulus. `check_codemap.py`: SEMUA CEK LULUS (232 simbol).
- Codemap: `frontend-app.md` memuat `ClipTierBadges`, `ClipScorePanel`, `computeClipTiers`, `hasClipScores`, kartu klip dan risiko label relatif; rentang bergeser di catatan lain diperbarui. Cek codemap lulus.
- Kualitas: tidak ada rahasia ter-commit, tidak ada format ulang di luar baris baru. `onClick` panel memakai `stopPropagation` agar klik panel tidak membuka/menutup kartu.
- Perlu dicek pemilik: buka analisis asli dari riwayat setelah #1 (id dan en), nilai keterbacaan panel (menambah tinggi kartu), buka analisis lama sebelum #1 dan pastikan kartu normal, coba filter/pencarian dan pastikan label tetap.
