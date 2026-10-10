<!-- Template kontrak. Salin file ini menjadi docs/tasks/CHEAT-<ID>.md, lalu isi. -->
<!-- Sumber: TASKS.md, bagian "Template kontrak ringan". -->

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

---

<!-- Prompt review (tempel di sesi Claude baru). Hapus bagian ini dari salinan CHEAT-<ID>.md bila tidak perlu. -->

```text
Baca TASKS.md dan docs/tasks/CHEAT-<ID>.md. Review perubahan pada `git diff` terhadap kontrak itu saja.
Cek: semua kriteria selesai terpenuhi, tidak ada perubahan di luar area yang diizinkan, test lulus, codemap terdampak sudah diperbarui.
Tulis VERDICT (PASS/FIX_REQUIRED) + alasan di bagian Review kontrak, lalu perbarui status di TASKS.md.
```
