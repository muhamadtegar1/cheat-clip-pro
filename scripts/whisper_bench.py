"""Ukur model Whisper di komputer ini (task #38): waktu, RAM puncak, akurasi (WER), kestabilan.

Jalankan dari root repo:
    venv\\Scripts\\python.exe scripts\\whisper_bench.py <audio/video> --ref <acuan> [--start 0] [--duration 60]
        [--models base,small,small.en,medium,medium.en] [--runs 2] [--language en]

- `--ref` berupa file teks biasa (seluruh isinya acuan untuk rentang yang diukur) atau JSON transkrip
  `[{"text", "start", "duration"}]` (mis. tests/golden/data/<id>/transcript.json). Untuk JSON, rentang audio
  dirapatkan ke baris acuan yang utuh di dalam [start, start+duration] agar batas potongan tidak dihitung salah.
- Tiap model dijalankan di proses anak sendiri, jadi RAM puncak (PeakWorkingSetSize Windows) milik model itu saja.
- Opsi transcribe sama dengan `transcribe_clip_words` di backend/video_engine.py (`word_timestamps=True`, `fp16=False`);
  `--language` hanya untuk pengukuran, app belum memakainya (#39).
- Model yang belum ada diunduh `whisper.load_model` ke ~/.cache/whisper (small ±460 MB, medium ±1,5 GB).
- Keluaran: tabel di terminal + JSON di tests/whisper_bench/ (di-ignore git; audio dan acuan milik channel lain).
Skrip tidak mengimpor backend.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "tests" / "whisper_bench"
DEFAULT_MODELS = "base,small,small.en,medium,medium.en"


def peak_memory_mb() -> float:
    """RAM puncak proses ini (Windows). 0 bila tidak tersedia."""
    if os.name != "nt":
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        except Exception:
            return 0.0
    import ctypes
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
        return pmc.PeakWorkingSetSize / (1024.0 * 1024.0)
    return 0.0


def normalize_words(text: str) -> list:
    """Huruf kecil, tanpa tag [musik]/(tepuk tangan), tanpa tanda baca (apostrof di dalam kata dipertahankan)."""
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text.lower())
    text = text.replace("’", "'").replace("-", " ")
    words = []
    for w in re.findall(r"[\w']+", text):
        w = w.strip("'")
        if w:
            words.append(w)
    return words


def word_error_rate(ref: list, hyp: list) -> float:
    """WER = (sisip + hapus + ganti) / jumlah kata acuan, dalam persen."""
    if not ref:
        return 0.0 if not hyp else 100.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i] + [0] * len(hyp)
        for j, h in enumerate(hyp, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return round(100.0 * prev[-1] / len(ref), 1)


def load_reference(ref_path: Path, start: float, duration: float):
    """Kembalikan (teks acuan, start, duration). JSON transkrip dirapatkan ke baris yang utuh di dalam rentang."""
    raw = ref_path.read_text(encoding="utf-8")
    if ref_path.suffix.lower() != ".json":
        return raw, start, duration
    lines = json.loads(raw)
    end = start + duration
    inside = [ln for ln in lines
              if float(ln["start"]) >= start and float(ln["start"]) + float(ln.get("duration", 0)) <= end]
    if not inside:
        raise SystemExit(f"Tidak ada baris acuan utuh di rentang {start}-{end} s")
    seg_start = float(inside[0]["start"])
    seg_end = float(inside[-1]["start"]) + float(inside[-1].get("duration", 0))
    return " ".join(ln["text"] for ln in inside), seg_start, seg_end - seg_start


def extract_audio(src: Path, start: float, duration: float, dest: Path) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(src),
           "-t", f"{duration:.3f}", "-vn", "-ac", "1", "-ar", "16000", str(dest)]
    subprocess.run(cmd, check=True)


def worker(model_name: str, audio: str, runs: int, language: str) -> None:
    """Proses anak: muat satu model, transkripsi `runs` kali, cetak JSON hasil di baris terakhir."""
    import whisper

    t0 = time.perf_counter()
    model = whisper.load_model(model_name)
    load_s = time.perf_counter() - t0
    results = []
    for _ in range(runs):
        opts = {"word_timestamps": True, "fp16": False, "verbose": None}
        if language:
            opts["language"] = language
        t1 = time.perf_counter()
        res = model.transcribe(audio, **opts)
        secs = time.perf_counter() - t1
        words = [{"w": w.get("word", ""), "s": float(w.get("start", 0)), "e": float(w.get("end", 0))}
                 for seg in res.get("segments", []) for w in seg.get("words", [])]
        results.append({"seconds": round(secs, 2), "text": res.get("text", ""),
                        "language": res.get("language", ""), "words": words})
    print(json.dumps({"model": model_name, "load_seconds": round(load_s, 2),
                      "peak_ram_mb": round(peak_memory_mb()), "runs": results}))


def timestamps_ok(words: list, duration: float) -> bool:
    last = -1.0
    for w in words:
        if w["s"] > w["e"] + 0.01 or w["s"] < last - 0.01 or w["e"] > duration + 1.0:
            return False
        last = w["s"]
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="File audio/video lokal")
    ap.add_argument("--ref", help="Acuan: .txt atau JSON transkrip [{text,start,duration}]")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--models", default=DEFAULT_MODELS)
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--language", default="", help="Kode bahasa untuk Whisper (mis. en, id); kosong = tebak sendiri")
    ap.add_argument("--label", default="", help="Nama singkat klip untuk nama file laporan")
    ap.add_argument("--worker", help=argparse.SUPPRESS)
    ap.add_argument("--audio", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        worker(args.worker, args.audio, args.runs, args.language)
        return 0
    if not args.input or not args.ref:
        ap.error("input dan --ref wajib")

    src = Path(args.input)
    ref_text, start, duration = load_reference(Path(args.ref), args.start, args.duration)
    ref_words = normalize_words(ref_text)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    label = re.sub(r"[^\w.-]", "_", args.label or src.stem)[:40]
    audio = OUT_DIR / f"{stamp}-{label}.wav"
    extract_audio(src, start, duration, audio)
    print(f"Klip: {src.name} {start:.2f}-{start + duration:.2f} s ({duration:.1f} s), acuan {len(ref_words)} kata, "
          f"bahasa={args.language or 'tebak'}, runs={args.runs}")

    rows = []
    for model_name in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"- {model_name} ...", flush=True)
        cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", model_name, "--audio", str(audio),
               "--runs", str(args.runs), "--language", args.language]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = (proc.stdout.strip().splitlines() or [""])[-1]
        try:
            data = json.loads(last)
        except json.JSONDecodeError:
            print(f"  GAGAL (exit {proc.returncode}): {proc.stderr.strip()[-400:]}")
            rows.append({"model": model_name, "error": proc.stderr.strip()[-400:]})
            continue
        run_words = [normalize_words(r["text"]) for r in data["runs"]]
        wers = [word_error_rate(ref_words, w) for w in run_words]
        secs = [r["seconds"] for r in data["runs"]]
        row = {
            "model": model_name,
            "load_seconds": data["load_seconds"],
            "transcribe_seconds": secs,
            "realtime_factor": round(min(secs) / duration, 2) if duration else None,
            "peak_ram_mb": data["peak_ram_mb"],
            "wer": wers,
            "stability_wer": word_error_rate(run_words[0], run_words[1]) if len(run_words) > 1 else None,
            "language_detected": [r["language"] for r in data["runs"]],
            "timestamps_ok": all(timestamps_ok(r["words"], duration) for r in data["runs"]),
            "text_run1": data["runs"][0]["text"].strip() if data["runs"] else "",
        }
        rows.append(row)

    print()
    print(f"{'model':<11}{'muat s':>9}{'transkr s':>15}{'x real':>8}{'RAM MB':>8}{'WER %':>14}{'stabil %':>10}"
          f"{'bahasa':>9}{'waktu ok':>10}")
    for r in rows:
        if "error" in r:
            print(f"{r['model']:<11} GAGAL")
            continue
        print(f"{r['model']:<11}{r['load_seconds']:>9}{'/'.join(str(s) for s in r['transcribe_seconds']):>15}"
              f"{r['realtime_factor']:>8}{r['peak_ram_mb']:>8}{'/'.join(str(w) for w in r['wer']):>14}"
              f"{str(r['stability_wer']):>10}{'/'.join(sorted(set(r['language_detected']))):>9}"
              f"{('ya' if r['timestamps_ok'] else 'TIDAK'):>10}")
    print("x real = waktu transkripsi tercepat / durasi klip (1,0 = sama dengan durasi). "
          "stabil = WER run 1 vs run 2 (0 = identik). muat s termasuk unduh bila model belum ada di cache.")

    report = {"created": datetime.now().isoformat(timespec="seconds"), "input": src.name, "start": start,
              "duration": duration, "language": args.language, "runs": args.runs, "ref_words": len(ref_words),
              "results": rows}
    out = OUT_DIR / f"{stamp}-{label}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Laporan: {out}")
    return 0 if all("error" not in r for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
