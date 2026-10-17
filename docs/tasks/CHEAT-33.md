# CHEAT-33: Heatmap akustik tanpa data buatan
Status: REVIEW
Risiko: sedang (mengubah data yang dikirim ke Gemini untuk video upload/Drive; prompt tidak berubah)

## Tujuan
`compute_audio_energy_heatmap` tidak pernah mengirim heatmap buatan: bila audio tidak bisa diukur (tidak ada trek audio, file gagal dibaca, timeout) atau volumenya rata, fungsi mengembalikan heatmap kosong sehingga analisis jatuh ke jalur "No audience interest data".

## Kondisi sekarang (diverifikasi di kode dan diukur)
- `backend/video_engine.py` `compute_audio_energy_heatmap` (L573-635): ekstraksi WAV 8 kHz mono lewat FFmpeg dengan `timeout=30` (L594), RMS per 1% durasi, lalu dinormalisasi ke 0,1-1,0. Bila semua nilai sama (L626-628, gagal/timeout/tanpa audio), fungsi membuat pola sinus `0.3 + 0.4 * (0.5 + 0.5 * sin(i * 0.2))`.
- Diukur di sesi `/mulai 33` (video sintetis 40 s):
  - Video tanpa trek audio dan file rusak: keduanya menghasilkan pola sinus yang sama (0,5; 0,54; 0,578; ...), dikirim ke Gemini sebagai `audience_interest`.
  - Nada konstan (seperti video smoke test): selisih RMS hanya 6,2% dari maksimum, tetapi dinormalisasi menjadi rentang penuh 0,1-1,0 (derau diperbesar).
  - Ekstraksi audio video 1 jam 720p (1,3 GB): 5 detik. Batas 30 s baru terlewati untuk video sangat panjang/besar atau disk lambat, jadi bukan penyebab utama.
  - File WAV sementara tidak dihapus bila ekstraksi timeout atau error.
- Pemanggil: `analyze.py` L352 (upload/Drive) dan L757 (YouTube jalur Whisper). Heatmap kosong sudah ditangani: prompt memakai "No audience interest data" (±L981-984), kolom engagement dihilangkan (±L957), UI `HeatmapTimeline.tsx` menampilkan keadaan kosong (L44, L143).
- SSE upload (`analyze.py` ±L354-360) selalu berbunyi "Acoustic engagement heatmap parsed — N audience interest data points", termasuk bila N = 0.

## Area yang boleh disentuh
- `backend/video_engine.py` `compute_audio_energy_heatmap` (L573-635): hapus pola sinus; kembalikan `[]` bila ekstraksi gagal/timeout/tanpa audio atau audio rata; batas waktu menyesuaikan durasi; file sementara selalu dihapus. Boleh mengganti WAV sementara dengan pipe PCM bila lebih sederhana.
- `backend/routers/analyze.py` L352-366 (blok SSE langkah 2 upload): teks SSE saat heatmap kosong (mis. "No usable audio energy, relying on transcript"). Hanya teks, alur tidak berubah.
- `scripts/smoke_test.py`: satu cek baru untuk `compute_audio_energy_heatmap` (tanpa audio, file rusak, nada rata = `[]`; audio dengan bagian keras = heatmap 100 titik dengan puncak di bagian keras); boleh menambah parameter opsional ke `make_synthetic_video` (default tetap). Cek lama tidak diubah logikanya; bila hasilnya bergeser karena heatmap video smoke kini kosong, dicatat di laporan.
- `docs/codemap/sumber-video.md` (dan catatan lain yang menyebut fungsi ini), `CLAUDE.md` (deskripsi smoke test).
- `TASKS.md` dan kontrak ini.

## Di luar scope (jangan dikerjakan)
- Prompt dan label heatmap akustik di prompt (#32).
- Cara heatmap dipakai (`get_average_heatmap_value`, engagement, klip fallback), golden fixtures (jalur YouTube, tidak memakai fungsi ini).
- Frontend.
- Metode pengukuran lain (mis. deteksi tawa/teriak, loudness LUFS).

## Keputusan yang boleh diambil AI sendiri
- Ambang "audio rata" (relatif terhadap RMS maksimum; nada konstan terukur 6,2%, ucapan normal jauh di atasnya) dan batas waktu per durasi (minimal tetap 30 s).
- WAV sementara atau pipe PCM; log peringatan yang jelas untuk tiap alasan heatmap kosong.
- Cara membuat audio sintetis berbagian keras untuk smoke test.

## Kriteria selesai (ya/tidak)
- [x] Tidak ada lagi heatmap buatan: video tanpa audio, file rusak, ekstraksi gagal/timeout, dan audio rata mengembalikan `[]`, dengan log peringatan berisi alasannya.
- [x] Audio dengan variasi nyata tetap menghasilkan 100 titik 0,1-1,0 dengan puncak di bagian yang keras.
- [x] Batas waktu ekstraksi menyesuaikan durasi (tetap minimal 30 s) dan file sementara tidak tertinggal saat gagal/timeout.
- [x] Upload tanpa heatmap tetap selesai dianalisis (smoke test analyze mock/fallback lulus) dan SSE tidak lagi menyebut "0 audience interest data points".
- [x] Smoke test lulus (11 cek lama + cek baru), `check_codemap.py` lulus, `git diff` hanya menyentuh area di atas.

## Cara menguji
- `venv\Scripts\python.exe scripts\smoke_test.py` (termasuk cek heatmap akustik baru).
- Uji manual sementara di scratchpad: file tanpa audio, file rusak, nada konstan, audio berbagian keras, dan `timeout` dipaksa kecil (monkeypatch) untuk memastikan `[]` dan file sementara terhapus.
- `venv\Scripts\python.exe scripts\check_codemap.py`.
- Golden fixtures tidak wajib: prompt tidak berubah dan golden memakai jalur YouTube (tidak memanggil fungsi ini). Uji manual UI opsional: upload video tanpa audio, pastikan analisis jalan dan grafik heatmap kosong.

## Laporan implementer
STATUS: REVIEW
FILE_DIUBAH:
- `backend/video_engine.py` `compute_audio_energy_heatmap` (sekarang L576-642) + konstanta `AUDIO_FLAT_SPREAD = 0.10`: pola sinus dihapus; audio dibaca lewat pipe PCM s16le (tanpa WAV sementara); `[]` + log peringatan untuk timeout, error FFmpeg (tanpa trek audio/file rusak), audio terlalu pendek, senyap (RMS maks < 1), dan volume rata (selisih RMS < 10% dari maksimum); batas waktu `max(30, min(900, durasi/10))` s. Normalisasi 0,1-1,0 untuk audio bervariasi tidak berubah.
- `backend/routers/analyze.py` blok SSE langkah 2 upload (L352-375): bila heatmap kosong, event `Dialogue Fallback` "No usable audio energy (no audio track, unreadable, or flat volume)"; bila ada, event lama tidak berubah. Alur tidak berubah.
- `scripts/smoke_test.py`: `make_synthetic_video` parameter opsional `audio`/`audio_filter` (default lama), cek baru `run_audio_heatmap_check`, docstring.
- `CLAUDE.md` (jebakan no. 5 L225-1552, deskripsi smoke test), codemap (lihat bawah).
HASIL_TEST:
- Uji manual di scratchpad (video sintetis 40 s): nada konstan -> `[]` "volume is flat (spread 6.2% < 10%)"; tanpa audio -> `[]` "no usable audio track"; file rusak -> `[]` (alasan FFmpeg); audio keras di 20-26 s -> 100 titik, puncak di 20,4 s, rata-rata 1,00 di 20-26 s vs 0,10 di luar; timeout dipaksa (monkeypatch `subprocess.run`) -> `[]`; file `temp_heat_*` tertinggal: 0. Sebelum perbaikan: tanpa audio dan file rusak menghasilkan sinus identik (0,5; 0,54; 0,578; ...), nada konstan dinormalisasi jadi 0,1-1,0.
- Ekstraksi audio video 1 jam 720p (1,3 GB): 5 s (dasar batas waktu).
- `venv\Scripts\python.exe scripts\smoke_test.py`: 12/12 lulus (11 lama + "heatmap energi audio tanpa data buatan"). Cek baru dijalankan dengan `video_engine.py` dari HEAD: FAIL "tanpa audio: heatmap tidak kosong".
- Hasil cek lama yang bergeser (tetap lulus): video smoke bernada konstan kini tanpa heatmap, jadi kandidat fallback urut transkrip. "tanpa tumpang tindih": tanpa rentang 0-25, 25-70, 70-120 (sebelumnya 10-35, 55-100, 105-120), rentang 60-110 60-85, 85-110 (sebelumnya 65-90, 90-110). "guardrail buang semua -> fallback" 2 klip, "rentang 22-38" 22-37 (sama).
- `check_codemap.py`: SEMUA CEK LULUS (224 simbol). `npm run build` tidak dijalankan (`src/` tidak berubah). Golden tidak dijalankan (prompt tidak berubah, golden memakai jalur YouTube).
CODEMAP_DIPERBARUI: ya. `sumber-video.md` (baris `compute_audio_energy_heatmap` L576-642 + perilaku baru, label `analyze.py` bergeser); rentang baris yang bergeser +11 di `analyze.py` (setelah L360) dan +7 di `video_engine.py` (setelah L635) di `analisis-ai.md`, `transkrip.md`, `face-tracking.md`, `render-server.md`, `subtitle-dan-judul.md`, `unduhan-raw.md` (termasuk rujukan teks L822, L818/L870/L1067/L931/L974, `build_ffmpeg_filtergraph` L2534-2849 yang sebelumnya sudah basi).
CATATAN:
- Keputusan sendiri: ambang rata 10% (nada konstan 6,2%); senyap = RMS maks < 1; batas waktu `max(30, min(900, durasi/10))`; pipe PCM menggantikan WAV sementara (tidak ada file tertinggal); teks SSE baru memakai stage `Dialogue Fallback` yang sama dengan jalur YouTube tanpa heatmap.
- Dampak: video upload tanpa audio, rusak audionya, atau bervolume rata kini dianalisis dari transkrip saja (prompt "No audience interest data"), bukan diarahkan ke puncak palsu. Memori: pipe PCM 8 kHz untuk video 2 jam ±115 MB (sama dengan pembacaan WAV sebelumnya).
- Batas 30 s ternyata jarang terlewati (5 s/jam di SSD); risiko tersisa hanya file sangat besar/disk lambat, kini dengan batas proporsional.
- Line ending: `sed` membuang CR dari `docs/codemap/analisis-ai.md`, dikembalikan ke CRLF. Isi commit tidak terpengaruh (blob LF).
- Uji manual UI belum dilakukan (opsional): upload video tanpa audio, pastikan analisis jalan dan grafik heatmap kosong.
- `docs/.obsidian/` (untracked) tidak disentuh dan tidak di-commit.

## Review (sesi baru)
VERDICT: PASS | FIX_REQUIRED
ALASAN:
