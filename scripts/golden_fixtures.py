"""Golden fixtures analisis AI untuk Cheat Clip PRO (task 17b, Tahap 1: cek objektif).

Jalankan dari root repo:
    venv\\Scripts\\python.exe scripts\\golden_fixtures.py selftest
    venv\\Scripts\\python.exe scripts\\golden_fixtures.py fetch [--force]
    venv\\Scripts\\python.exe scripts\\golden_fixtures.py run [--mock] [--repeat N] [--model M] [--only A,B] [--save-baseline] [--compare]
    venv\\Scripts\\python.exe scripts\\golden_fixtures.py score <laporan-run.json> [--compare]

- `fetch`  : ambil metadata, heatmap, dan transkrip (lewat fungsi backend yang sama dengan app) ke
             tests/golden/data/<video_id>/. Folder data di-ignore git (transkrip milik channel lain).
- `run`    : jalankan POST /api/analyze lewat TestClient dengan transkrip tersimpan sebagai `subtitles`.
             `--model auto` (default) mengunci satu model flash yang benar-benar menjawab untuk semua video.
             Model yang dipakai backend (bisa fallback) dicatat per video dari event SSE.
             `fetch_video_metadata` diganti data tersimpan, `fetch_transcript` dan unduh audio diblokir,
             jadi tidak ada panggilan ke YouTube. Default Gemini flash dengan key dari backend/.env.
             Gemini yang sibuk (503/429) diulang otomatis (--retries, --retry-wait).
- `score`  : nilai ulang klip mentah dari laporan run tersimpan (tanpa Gemini), mis. setelah penilai diubah.
- `selftest`: uji fungsi penilai dengan kasus buatan (tanpa jaringan, tanpa Gemini).

Metrik (per video, lalu total):
  grounded   : persen key_quotes yang ada di transkrip sekitar rentang klip (fuzzy, ambang QUOTE_MATCH).
               Kutipan bersambung "..." dinilai per potongan (potongan < 3 kata diabaikan).
  misplaced  : kutipan yang ada di transkrip tetapi di luar rentang klipnya.
  fabricated : kutipan yang tidak ditemukan di mana pun di transkrip.
  valid_time : persen klip dengan 0 <= start < end <= durasi dan start <= hook_time <= end.
  duplicates : jumlah pasangan klip dengan overlap > DUP_OVERLAP dari klip yang lebih pendek.
  avoid_hits : jumlah klip yang > AVOID_SHARE durasinya berada di rentang "jangan dipilih".
  heat_lift  : rata-rata heatmap klip terpilih dibagi rata-rata heatmap video (informasi).
  ref_recall : persen momen referensi yang tertangkap (Tahap 2, "n/a" bila label kosong).

`--compare`: rate turun > WORSE_RATE poin atau hitungan naik > COUNT_NOISE = LEBIH BURUK (exit 2).
Model per video berbeda dari baseline = perbandingan tidak setara (exit 3), apa pun nilai metriknya.
`score <laporan> --save-baseline` menimpa baseline dari laporan yang dinilai ulang (hanya bila penilai diubah).
Variasi antar run Gemini dengan prompt sama: karangan/salah tempat 0-1, jadi untuk perubahan prompt
pakai `run --repeat 2 --compare`.
"""

import argparse
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
LABELS_PATH = GOLDEN_DIR / "labels.json"
BASELINE_PATH = GOLDEN_DIR / "baseline.json"
DATA_DIR = GOLDEN_DIR / "data"
RUNS_DIR = DATA_DIR / "runs"

DEFAULT_MODEL = "auto"  # model flash pertama yang benar-benar menjawab untuk key ini (lihat resolve_model)
QUOTE_MATCH = 0.85      # rasio kemiripan minimum agar kutipan dianggap ada di transkrip
QUOTE_WINDOW = 5.0      # detik toleransi di luar rentang klip saat mencari kutipan
DUP_OVERLAP = 0.70      # overlap > 70% dari klip lebih pendek = duplikat (sesuai #12)
AVOID_SHARE = 0.50      # klip > 50% di zona "jangan dipilih" = pelanggaran
REF_TOLERANCE = 5.0     # detik toleransi untuk mencocokkan momen referensi (Tahap 2)
WORSE_RATE = 5.0        # penurunan > 5 poin persen dianggap lebih buruk di --compare
COUNT_NOISE = 1.0       # naik <= 1 (karangan, duplikat, zona terlarang) masih variasi wajar antar run Gemini
TRANSIENT_RE = re.compile(r"high demand|overloaded|unavailable|503|429|rate limit|quota|timed out|timeout", re.IGNORECASE)


# ── Utilitas ─────────────────────────────────────────────────────────────────

def hms_to_seconds(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parts = [float(p) for p in str(value).strip().split(":")]
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def seconds_to_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\[[^\]]*\]", " ", text)          # [Music], [Tertawa]
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def load_labels() -> dict:
    return json.loads(LABELS_PATH.read_text(encoding="utf-8"))


def lines_to_srt(lines: list) -> str:
    blocks = []
    for i, line in enumerate(lines, 1):
        start = float(line["start"])
        end = start + max(0.1, float(line.get("duration") or 0.1))
        text = " ".join(str(line.get("text") or "").split())
        if text:
            blocks.append(f"{i}\n{seconds_to_srt(start)} --> {seconds_to_srt(end)}\n{text}\n")
    return "\n".join(blocks)


# ── Penilai ──────────────────────────────────────────────────────────────────

def quote_fragments(quote: str) -> list:
    """Pecah kutipan bersambung ("...", "…") menjadi potongan yang dinilai sendiri-sendiri."""
    parts = [normalize_text(p) for p in re.split(r"\.{2,}|…", quote or "")]
    long_parts = [p for p in parts if len(p.split()) >= 3]
    return long_parts or [p for p in parts if p]


def text_contains(hay: str, q: str) -> bool:
    """True bila potongan `q` (sudah dinormalisasi) ada di `hay`, persis atau fuzzy >= QUOTE_MATCH."""
    if not q or not hay:
        return False
    if q in hay:
        return True
    q_words, h_words = q.split(), hay.split()
    n = len(q_words)
    if len(h_words) < max(1, n // 2):
        return False
    matcher = difflib.SequenceMatcher(None, "", q)
    for size in sorted({max(1, n - 2), n, n + 2, n + 4}):
        for i in range(0, max(1, len(h_words) - size + 1)):
            matcher.set_seq1(" ".join(h_words[i:i + size]))
            if (matcher.real_quick_ratio() >= QUOTE_MATCH and matcher.quick_ratio() >= QUOTE_MATCH
                    and matcher.ratio() >= QUOTE_MATCH):
                return True
    return False


def window_text(transcript: list, start: float, end: float) -> str:
    window = [l for l in transcript if l["end"] >= start - QUOTE_WINDOW and l["start"] <= end + QUOTE_WINDOW]
    return normalize_text(" ".join(l["text"] for l in window))


def classify_quote(quote: str, transcript: list, start: float, end: float, full_text: str) -> str:
    """'grounded' (ada di sekitar klip), 'misplaced' (ada di video, bukan di klip), atau 'fabricated'."""
    frags = quote_fragments(quote)
    if not frags:
        return "fabricated"
    hay = window_text(transcript, start, end)
    if all(text_contains(hay, f) for f in frags):
        return "grounded"
    if all(text_contains(full_text, f) for f in frags):
        return "misplaced"
    return "fabricated"


def heat_mean(heatmap: list, start: float, end: float):
    total, weight = 0.0, 0.0
    for p in heatmap:
        w = overlap(start, end, float(p["start_time"]), float(p["end_time"]))
        if w > 0:
            total += float(p["value"]) * w
            weight += w
    return total / weight if weight else None


def score_video(clips: list, transcript: list, duration: float, heatmap: list, avoid: list, references: list) -> dict:
    """Nilai satu hasil analisis. `transcript` = [{start, end, text}], `avoid`/`references` = [{start, end}] detik."""
    quotes_total = quotes_ok = 0
    valid = 0
    avoid_hits = []
    ungrounded = []
    full_text = normalize_text(" ".join(l["text"] for l in transcript))
    for c in clips:
        s, e = float(c["start_time"]), float(c["end_time"])
        hook = float(c.get("hook_time", s))
        if 0.0 <= s < e <= duration + 0.5 and s - 0.5 <= hook <= e + 0.5:
            valid += 1
        for q in c.get("key_quotes") or []:
            quotes_total += 1
            verdict = classify_quote(q, transcript, s, e, full_text)
            if verdict == "grounded":
                quotes_ok += 1
            else:
                ungrounded.append({"clip": c.get("title", ""), "start": s, "end": e, "kind": verdict, "quote": q[:160]})
        length = max(0.001, e - s)
        inside = sum(overlap(s, e, a["start"], a["end"]) for a in avoid)
        if inside / length > AVOID_SHARE:
            avoid_hits.append({"clip": c.get("title", ""), "start": s, "end": e})

    duplicates = []
    for i in range(len(clips)):
        for j in range(i + 1, len(clips)):
            a, b = clips[i], clips[j]
            a0, a1, b0, b1 = float(a["start_time"]), float(a["end_time"]), float(b["start_time"]), float(b["end_time"])
            shorter = max(0.001, min(a1 - a0, b1 - b0))
            if overlap(a0, a1, b0, b1) / shorter > DUP_OVERLAP:
                duplicates.append([i, j])

    lift = None
    if heatmap and clips:
        video_mean = sum(float(p["value"]) for p in heatmap) / len(heatmap)
        clip_means = [m for m in (heat_mean(heatmap, float(c["start_time"]), float(c["end_time"])) for c in clips) if m is not None]
        if video_mean > 0 and clip_means:
            lift = round((sum(clip_means) / len(clip_means)) / video_mean, 3)

    recall = None
    if references:
        hit = 0
        for r in references:
            if any(overlap(float(c["start_time"]) - REF_TOLERANCE, float(c["end_time"]) + REF_TOLERANCE, r["start"], r["end"])
                   >= 0.5 * (r["end"] - r["start"]) for c in clips):
                hit += 1
        recall = round(100.0 * hit / len(references), 1)

    n = len(clips)
    return {
        "clips": n,
        "grounded": round(100.0 * quotes_ok / quotes_total, 1) if quotes_total else None,
        "quotes": quotes_total,
        "misplaced": sum(1 for u in ungrounded if u["kind"] == "misplaced"),
        "fabricated": sum(1 for u in ungrounded if u["kind"] == "fabricated"),
        "valid_time": round(100.0 * valid / n, 1) if n else None,
        "duplicates": len(duplicates),
        "avoid_hits": len(avoid_hits),
        "heat_lift": lift,
        "ref_recall": recall,
        "details": {"ungrounded": ungrounded, "duplicate_pairs": duplicates, "avoid_clips": avoid_hits},
    }


def summarize(per_video: dict) -> dict:
    def mean(key):
        vals = [v[key] for v in per_video.values() if v.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
    return {
        "clips": sum(v["clips"] for v in per_video.values()),
        "grounded": mean("grounded"),
        "misplaced": sum(v.get("misplaced", 0) for v in per_video.values()),
        "fabricated": sum(v.get("fabricated", 0) for v in per_video.values()),
        "valid_time": mean("valid_time"),
        "duplicates": sum(v["duplicates"] for v in per_video.values()),
        "avoid_hits": sum(v["avoid_hits"] for v in per_video.values()),
        "heat_lift": (round(sum(v["heat_lift"] for v in per_video.values() if v["heat_lift"] is not None)
                            / max(1, sum(1 for v in per_video.values() if v["heat_lift"] is not None)), 3)
                      if any(v["heat_lift"] is not None for v in per_video.values()) else None),
        "ref_recall": mean("ref_recall"),
    }


def compare(current: dict, baseline: dict) -> list:
    """Baris perbandingan metrik total. Rate turun > WORSE_RATE atau hitungan naik = 'LEBIH BURUK'."""
    rows = []
    for key, kind in (("grounded", "rate"), ("fabricated", "count"), ("misplaced", "count"),
                      ("valid_time", "rate"), ("duplicates", "count"),
                      ("avoid_hits", "count"), ("heat_lift", "info"), ("ref_recall", "rate"), ("clips", "info")):
        cur, base = current.get(key), baseline.get(key)
        if cur is None or base is None:
            rows.append((key, base, cur, "", "n/a"))
            continue
        delta = round(cur - base, 3)
        if kind == "rate":
            verdict = "LEBIH BURUK" if delta < -WORSE_RATE else ("lebih baik" if delta > WORSE_RATE else "sama")
        elif kind == "count":
            if delta > COUNT_NOISE:
                verdict = "LEBIH BURUK"
            elif delta > 0:
                verdict = "naik (dalam variasi)"
            else:
                verdict = "lebih baik" if delta < 0 else "sama"
        else:
            verdict = "info"
        rows.append((key, base, cur, delta, verdict))
    return rows


# ── fetch ────────────────────────────────────────────────────────────────────

def cmd_fetch(args) -> int:
    import backend.config  # noqa: F401  efek samping: PATH FFmpeg/yt-dlp, .env
    from backend.services.youtube_service import fetch_transcript, fetch_video_metadata

    labels = load_labels()
    ok = True
    for v in labels["videos"]:
        if args.only and v["code"] not in args.only:
            continue
        vid = v["video_id"]
        out = DATA_DIR / vid
        if (out / "transcript.json").exists() and (out / "metadata.json").exists() and not args.force:
            print(f"[skip] {v['code']} {vid}: sudah ada (pakai --force untuk ambil ulang)")
            continue
        out.mkdir(parents=True, exist_ok=True)
        try:
            t0 = time.time()
            meta = fetch_video_metadata(f"https://www.youtube.com/watch?v={vid}")
            lines = fetch_transcript(vid)
            if not lines:
                raise RuntimeError("transkrip kosong")
            (out / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            (out / "transcript.json").write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
            print(f"[ok]   {v['code']} {vid}: {len(lines)} baris transkrip, durasi {meta.get('duration')}s, "
                  f"heatmap {len(meta.get('heatmap') or [])} titik ({time.time() - t0:.1f}s)")
        except Exception as e:
            ok = False
            print(f"[FAIL] {v['code']} {vid}: {e!r}")
    return 0 if ok else 1


def load_fixture(v: dict):
    out = DATA_DIR / v["video_id"]
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    lines = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
    transcript = [{"start": float(l["start"]), "end": float(l["start"]) + float(l.get("duration") or 0.1),
                   "text": str(l.get("text") or "")} for l in lines]
    return meta, lines, transcript


def check_labels(v: dict, duration: float, transcript: list) -> list:
    """Cek kewajaran label. Mengembalikan daftar catatan untuk pemilik (label tidak diubah)."""
    notes = []
    ranges = sorted((hms_to_seconds(a["start"]), hms_to_seconds(a["end"]), a["kind"]) for a in v["avoid"])
    for s, e, kind in ranges:
        if not (0 <= s < e <= duration + 1.0):
            notes.append(f"{kind} {s:.0f}-{e:.0f}s di luar durasi {duration:.0f}s")
        speech = [l for l in transcript if overlap(s, e, l["start"], l["end"]) > 0]
        if not speech and kind not in ("intro", "outro"):
            notes.append(f"{kind} {s:.0f}-{e:.0f}s tidak memuat ucapan di transkrip")
    for (s1, e1, k1), (s2, e2, k2) in zip(ranges, ranges[1:]):
        if s2 < e1:
            notes.append(f"{k1} dan {k2} tumpang tindih")
    return notes


# ── run ──────────────────────────────────────────────────────────────────────

def read_sse_events(client, payload: dict) -> list:
    events = []
    with client.stream("POST", "/api/analyze", json=payload) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


def resolve_model(api_key: str, requested: str) -> str:
    """`auto`: model flash pertama (urutan backend) yang benar-benar menjawab permintaan kecil untuk key ini.
    Dipakai untuk semua video dalam satu run supaya hasilnya setara."""
    if requested != "auto":
        return requested
    from google import genai
    from google.genai import types
    from backend.services.ai_service import get_flash_models_for_key

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))
    for model in get_flash_models_for_key(client):
        try:
            client.models.generate_content(model=model, contents="Reply with OK.",
                                           config=types.GenerateContentConfig(max_output_tokens=5))
            return model
        except Exception as e:
            print(f"       model {model} tidak bisa dipakai: {str(e)[:120]}")
    raise RuntimeError("tidak ada model flash yang menjawab untuk key ini")


def model_used(events: list, fallback: str) -> str:
    """Model yang benar-benar menghasilkan analisis (event SSE langkah 4 'Clip Verification & Alignment')."""
    for e in reversed(events):
        if e.get("model") and e.get("stage") == "Clip Verification & Alignment":
            return e["model"]
    return fallback


def model_mismatch(current: dict, baseline: dict) -> list:
    """Kode video yang modelnya berbeda dari baseline (perbandingan tidak setara)."""
    return sorted(code for code, model in current.items() if code in baseline and baseline[code] != model)


def unique_path(path: Path) -> Path:
    candidate, n = path, 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        n += 1
    return candidate


def cmd_run(args) -> int:
    import backend.config  # noqa: F401  efek samping: memuat backend/.env (GEMINI_API_KEY)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.routers.analyze as analyze_mod

    api_key = "mock" if args.mock else (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        print("[FAIL] GEMINI_API_KEY tidak ada. Simpan key lewat UI atau pakai --mock.")
        return 1
    if args.mock:
        model = "mock"
    else:
        try:
            model = resolve_model(api_key, args.model)
        except Exception as e:
            print(f"[FAIL] memilih model: {e}")
            return 1
        print(f"Model run ini: {model}" + (" (dipilih otomatis)" if args.model == "auto" else ""))

    labels = load_labels()
    videos = [v for v in labels["videos"] if not args.only or v["code"] in args.only]
    fixtures = {}
    for v in videos:
        try:
            fixtures[v["video_id"]] = load_fixture(v)
        except FileNotFoundError:
            print(f"[FAIL] data {v['code']} {v['video_id']} belum ada. Jalankan `golden_fixtures.py fetch` dulu.")
            return 1

    current = {"vid": None}
    calls = {"metadata": 0}

    def fake_metadata(url, custom_proxy=None, cookies_content=None):
        calls["metadata"] += 1
        meta = fixtures[current["vid"]][0]
        return {"title": meta.get("title", ""), "channel": meta.get("channel", ""), "duration": float(meta["duration"]),
                "heatmap": meta.get("heatmap") or [], "is_live": False, "live_status": "not_live"}

    def blocked(*a, **kw):
        raise RuntimeError("golden fixtures: panggilan YouTube diblokir")

    originals = (analyze_mod.fetch_video_metadata, analyze_mod.fetch_transcript, analyze_mod.download_youtube_audio_file)
    analyze_mod.fetch_video_metadata = fake_metadata
    analyze_mod.fetch_transcript = blocked
    analyze_mod.download_youtube_audio_file = blocked

    app = FastAPI()
    app.include_router(analyze_mod.router)
    client = TestClient(app)

    runs = []
    failed = False
    try:
        for r in range(args.repeat):
            per_video = {}
            for v in videos:
                vid = v["video_id"]
                current["vid"] = vid
                meta, lines, transcript = fixtures[vid]
                duration = float(meta["duration"])
                avoid = [{"start": hms_to_seconds(a["start"]), "end": hms_to_seconds(a["end"])} for a in v["avoid"]]
                refs = [{"start": hms_to_seconds(x["start"]), "end": hms_to_seconds(x["end"])} for x in v.get("references") or []]
                payload = {"url": f"https://www.youtube.com/watch?v={vid}", "duration": args.duration,
                           "api_key": api_key, "model": model, "target_clip_count": "auto",
                           "subtitles": lines_to_srt(lines), "subtitles_filename": f"{vid}.srt"}
                t0 = time.time()
                for attempt in range(args.retries + 1):
                    try:
                        events = read_sse_events(client, payload)
                    except Exception as e:
                        events = [{"error": repr(e)}]
                    done = [e for e in events if e.get("done")]
                    errors = [e for e in events if e.get("error")]
                    if done and not errors:
                        used = model_used(events, model)
                        if used != model and attempt < args.retries:
                            print(f"       {v['code']}: backend pindah ke {used} (fallback), ulangi dengan {model} "
                                  f"dalam {args.retry_wait}s ({attempt + 1}/{args.retries})")
                            time.sleep(args.retry_wait)
                            continue
                        break
                    msg = str(errors[0].get("error")) if errors else ""
                    if attempt < args.retries and TRANSIENT_RE.search(msg):
                        print(f"       {v['code']}: error sementara, coba lagi dalam {args.retry_wait}s ({attempt + 1}/{args.retries})")
                        time.sleep(args.retry_wait)
                        continue
                    break
                elapsed = round(time.time() - t0, 1)
                if errors or not done:
                    failed = True
                    msg = errors[0].get("error") if errors else "event done tidak ditemukan"
                    print(f"[FAIL] run {r + 1} {v['code']} {vid}: {msg}")
                    per_video[v["code"]] = {"error": str(msg)[:300], "seconds": elapsed}
                    continue
                clips = done[-1]["result"].get("clips") or []
                score = score_video(clips, transcript, duration, meta.get("heatmap") or [], avoid, refs)
                score["seconds"] = elapsed
                score["model_used"] = model_used(events, model)
                score["raw_clips"] = [{k: c.get(k) for k in ("title", "start_time", "end_time", "hook_time",
                                                             "virality_score", "key_quotes")} for c in clips]
                score["label_notes"] = check_labels(v, duration, transcript)
                per_video[v["code"]] = score
                print(f"[ok]   run {r + 1} {v['code']} {vid}: {score['clips']} klip, grounded {score['grounded']}% "
                      f"(salah tempat {score['misplaced']}, karangan {score['fabricated']}), "
                      f"valid {score['valid_time']}%, dup {score['duplicates']}, avoid {score['avoid_hits']}, "
                      f"lift {score['heat_lift']}, {elapsed}s, model {score['model_used']}")
                if score["model_used"] != model:
                    print(f"       PERINGATAN: backend pindah dari {model} ke {score['model_used']} (fallback)")
                for note in score["label_notes"]:
                    print(f"       catatan label: {note}")
            runs.append(per_video)
    finally:
        analyze_mod.fetch_video_metadata, analyze_mod.fetch_transcript, analyze_mod.download_youtube_audio_file = originals

    return finish(runs, failed, {"model": model, "model_requested": args.model, "duration_pref": args.duration,
                                 "repeat": args.repeat, "metadata_calls_from_file": calls["metadata"]},
                  args, mock=args.mock)


def models_of(runs: list) -> dict:
    """Model per kode video dari run terakhir yang berhasil (untuk baseline dan cek kesetaraan)."""
    models = {}
    for pv in runs:
        for code, s in pv.items():
            if "error" not in s:
                models.setdefault(code, set()).add(s.get("model_used") or "?")
    return {code: (next(iter(m)) if len(m) == 1 else "campuran:" + ",".join(sorted(m))) for code, m in models.items()}


def total_of(runs: list):
    scored = [{k: v for k, v in pv.items() if "error" not in v} for pv in runs]
    totals = [summarize(pv) for pv in scored if pv]
    if not totals:
        return None
    total = {}
    for k in totals[0].keys():
        vals = [t[k] for t in totals if t[k] is not None]
        total[k] = round(sum(vals) / len(vals), 3) if vals else None
    return total


def print_compare(total: dict, models: dict) -> int:
    """Tabel selisih. Exit 2 bila ada metrik lebih buruk, 3 bila model berbeda dari baseline (tidak setara)."""
    if not BASELINE_PATH.exists():
        print("[FAIL] baseline belum ada. Jalankan `run --save-baseline` dulu.")
        return 1
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    base_models = base.get("models_used") or {}
    print(f"\nBanding dengan baseline {base['created']} (model {base_models or base.get('model')}):")
    print(f"{'metrik':<12}{'baseline':>10}{'sekarang':>10}{'selisih':>10}  status")
    worse = False
    for key, b, c, d, verdict in compare(total, base["total"]):
        worse |= verdict == "LEBIH BURUK"
        print(f"{key:<12}{str(b):>10}{str(c):>10}{str(d):>10}  {verdict}")
    print("HASIL: ada metrik yang lebih buruk" if worse else "HASIL: tidak ada metrik yang lebih buruk")
    if not base_models:
        print("PERINGATAN: baseline tidak mencatat model yang dipakai. Buat ulang dengan `run --save-baseline`.")
        return 3
    mismatched = model_mismatch(models, base_models)
    if mismatched:
        for code in mismatched:
            print(f"PERINGATAN: video {code} memakai {models[code]}, baseline {base_models[code]}. Perbandingan tidak setara.")
        return 3
    return 2 if worse else 0


def finish(runs: list, failed: bool, info: dict, args, mock: bool, suffix: str = "") -> int:
    """Hitung total, simpan laporan run (folder data, di-ignore git), lalu baseline/compare bila diminta."""
    total = total_of(runs)
    if total is None:
        print("[FAIL] tidak ada video yang berhasil dianalisis")
        return 1
    models = models_of(runs)
    report = {
        "created": datetime.now().isoformat(timespec="seconds"), **info, "models_used": models,
        "thresholds": {"QUOTE_MATCH": QUOTE_MATCH, "QUOTE_WINDOW": QUOTE_WINDOW, "DUP_OVERLAP": DUP_OVERLAP,
                       "AVOID_SHARE": AVOID_SHARE, "REF_TOLERANCE": REF_TOLERANCE},
        "total": total,
        "runs": runs,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = unique_path(RUNS_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}{'-mock' if mock else ''}{suffix}.json")
    run_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\nTOTAL:", json.dumps(total, ensure_ascii=False))
    print(f"Laporan lengkap: {run_path.relative_to(REPO_ROOT)}")
    if "metadata_calls_from_file" in info:
        print(f"Metadata dari file: {info['metadata_calls_from_file']} kali, YouTube tidak dipanggil.")
    if failed:
        print("[FAIL] ada video yang gagal dianalisis (lihat di atas). Total di atas hanya dari video yang berhasil;"
              " baseline dan --compare tidak dijalankan.")
        return 1

    if getattr(args, "save_baseline", False):
        if mock:
            print("[FAIL] baseline tidak disimpan dari run --mock")
            return 1
        if any(m.startswith("campuran:") for m in models.values()):
            print(f"[FAIL] baseline tidak disimpan: model berganti di tengah run ({models}). Ulangi run.")
            return 1
        baseline = {
            "created": report["created"], "model": info["model"], "models_used": models,
            "duration_pref": info["duration_pref"],
            "repeat": info["repeat"], "thresholds": report["thresholds"], "total": total,
            "per_video": {code: {k: v for k, v in s.items() if k not in ("details", "label_notes", "raw_clips")}
                          for code, s in runs[-1].items()},
        }
        BASELINE_PATH.write_text(json.dumps(baseline, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Baseline disimpan: {BASELINE_PATH.relative_to(REPO_ROOT)}")

    if args.compare:
        return print_compare(total, models)
    return 0


# ── score ────────────────────────────────────────────────────────────────────

def cmd_score(args) -> int:
    """Nilai ulang klip mentah dari laporan run tersimpan, tanpa memanggil Gemini."""
    path = Path(args.report)
    if not path.is_absolute():
        path = (REPO_ROOT / path) if (REPO_ROOT / path).exists() else (RUNS_DIR / path)
    old = json.loads(path.read_text(encoding="utf-8"))
    labels = {v["code"]: v for v in load_labels()["videos"]}
    runs = []
    for r, per_video in enumerate(old["runs"]):
        rescored = {}
        for code, s in per_video.items():
            if "error" in s or "raw_clips" not in s:
                print(f"[skip] run {r + 1} {code}: {'error' if 'error' in s else 'laporan lama tanpa raw_clips'}")
                continue
            v = labels[code]
            meta, _, transcript = load_fixture(v)
            avoid = [{"start": hms_to_seconds(a["start"]), "end": hms_to_seconds(a["end"])} for a in v["avoid"]]
            refs = [{"start": hms_to_seconds(x["start"]), "end": hms_to_seconds(x["end"])} for x in v.get("references") or []]
            score = score_video(s["raw_clips"], transcript, float(meta["duration"]), meta.get("heatmap") or [], avoid, refs)
            score["raw_clips"] = s["raw_clips"]
            score["seconds"] = s.get("seconds")
            score["model_used"] = s.get("model_used") or "?"
            rescored[code] = score
            print(f"[ok]   run {r + 1} {code}: {score['clips']} klip, grounded {score['grounded']}% "
                  f"(salah tempat {score['misplaced']}, karangan {score['fabricated']}), valid {score['valid_time']}%, "
                  f"dup {score['duplicates']}, avoid {score['avoid_hits']}, lift {score['heat_lift']}")
        runs.append(rescored)
    info = {"model": old.get("model"), "duration_pref": old.get("duration_pref"), "repeat": old.get("repeat"),
            "rescored_from": path.name}
    return finish(runs, False, info, args, mock=old.get("model") == "mock", suffix="-rescore")


# ── selftest ─────────────────────────────────────────────────────────────────

def cmd_selftest(args) -> int:
    transcript = [
        {"start": 0.0, "end": 10.0, "text": "Welcome back to the show, today we talk about growth."},
        {"start": 10.0, "end": 20.0, "text": "The biggest mistake founders make is hiring too fast."},
        {"start": 20.0, "end": 30.0, "text": "This episode is sponsored by a very nice product."},
        {"start": 30.0, "end": 40.0, "text": "Kalau mau sukses kamu harus konsisten setiap hari."},
        {"start": 40.0, "end": 50.0, "text": "Thanks for watching, see you next time."},
    ]
    heatmap = [{"start_time": i * 10.0, "end_time": (i + 1) * 10.0, "value": v} for i, v in enumerate([0.2, 1.0, 0.1, 0.6, 0.1])]
    avoid = [{"start": 20.0, "end": 30.0}]
    cases = []

    def clip(s, e, quotes, hook=None, title="c"):
        return {"title": title, "start_time": s, "end_time": e, "hook_time": s if hook is None else hook, "key_quotes": quotes}

    r = score_video([clip(10, 20, ["The biggest mistake founders make is hiring too fast"]),
                     clip(30, 40, ["kamu harus konsisten setiap hari"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan persis dan dinormalisasi lulus", r["grounded"] == 100.0))
    r = score_video([clip(10, 20, ["the biggest mistake founder make is hiring to fast"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan sedikit berbeda (fuzzy) lulus", r["grounded"] == 100.0))
    r = score_video([clip(10, 20, ["Revenue doubled after we fired the whole marketing team"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan karangan gagal (fabricated)", r["grounded"] == 0.0 and r["fabricated"] == 1 and r["misplaced"] == 0))
    r = score_video([clip(40, 50, ["The biggest mistake founders make is hiring too fast"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan dari bagian lain video gagal (misplaced)", r["grounded"] == 0.0 and r["misplaced"] == 1 and r["fabricated"] == 0))
    r = score_video([clip(0, 20, ["Welcome back to the show... founders make is hiring too fast"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan bersambung '...' dari potongan asli lulus", r["grounded"] == 100.0))
    r = score_video([clip(0, 20, ["Welcome back to the show... founders should always raise more money"])], transcript, 50, heatmap, avoid, [])
    cases.append(("kutipan bersambung dengan potongan karangan gagal", r["grounded"] == 0.0 and r["fabricated"] == 1))
    r = score_video([clip(10, 20, []), clip(45, 60, []), clip(30, 40, [], hook=45), clip(-1, 5, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("timestamp di luar durasi / hook di luar klip gagal", r["valid_time"] == 25.0))
    r = score_video([clip(10, 20, []), clip(11, 21, []), clip(30, 40, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("overlap 90% terhitung duplikat", r["duplicates"] == 1))
    r = score_video([clip(10, 20, []), clip(17, 27, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("overlap 30% bukan duplikat", r["duplicates"] == 0))
    r = score_video([clip(20, 30, []), clip(18, 28, []), clip(10, 21, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("klip di zona sponsor terhitung (100% dan 80%), 9% tidak", r["avoid_hits"] == 2))
    r = score_video([clip(10, 20, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("heatmap lift klip puncak > 1", r["heat_lift"] is not None and r["heat_lift"] > 1.0))
    r = score_video([clip(10, 20, [])], transcript, 50, heatmap, avoid, [{"start": 11, "end": 19}, {"start": 31, "end": 39}])
    cases.append(("recall referensi 50%", r["ref_recall"] == 50.0))
    r = score_video([clip(10, 20, [])], transcript, 50, heatmap, avoid, [])
    cases.append(("recall n/a tanpa referensi", r["ref_recall"] is None))
    rows = {k: verdict for k, _, _, _, verdict in compare(
        {"grounded": 80.0, "valid_time": 100.0, "duplicates": 3, "avoid_hits": 0, "fabricated": 2, "heat_lift": 1.1, "ref_recall": None, "clips": 9},
        {"grounded": 95.0, "valid_time": 100.0, "duplicates": 1, "avoid_hits": 1, "fabricated": 1, "heat_lift": 1.0, "ref_recall": None, "clips": 10})}
    cases.append(("compare: grounded turun dan duplikat +2 lebih buruk, karangan +1 dalam variasi",
                  rows["grounded"] == "LEBIH BURUK" and rows["duplicates"] == "LEBIH BURUK"
                  and rows["fabricated"] == "naik (dalam variasi)"
                  and rows["avoid_hits"] == "lebih baik" and rows["valid_time"] == "sama"))
    cases.append(("model berbeda dari baseline terdeteksi",
                  model_mismatch({"A": "gemini-3.8-flash", "B": "x"}, {"A": "gemini-2.5-flash", "B": "x"}) == ["A"]
                  and model_mismatch({"A": "m"}, {"A": "m"}) == []))
    cases.append(("model dari event SSE langkah 4, fallback bila tidak ada",
                  model_used([{"stage": "Language & Context Assembly", "model": "req"},
                              {"stage": "Clip Verification & Alignment", "model": "dipakai"}], "req") == "dipakai"
                  and model_used([{"stage": "x"}], "mock") == "mock"))
    srt = lines_to_srt([{"text": "halo", "start": 3661.5, "duration": 2.25}])
    cases.append(("SRT jam:menit:detik,ms", "01:01:01,500 --> 01:01:03,750" in srt))
    cases.append(("hms_to_seconds", hms_to_seconds("00:13:33") == 813.0 and hms_to_seconds("01:31") == 91.0))

    for name, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    passed = sum(ok for _, ok in cases)
    print(f"\n{passed}/{len(cases)} kasus lulus.")
    return 0 if passed == len(cases) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden fixtures analisis AI Cheat Clip PRO")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_fetch = sub.add_parser("fetch", help="Ambil metadata, heatmap, transkrip ke tests/golden/data/")
    p_fetch.add_argument("--force", action="store_true", help="Ambil ulang walau data sudah ada")
    p_fetch.add_argument("--only", type=lambda s: s.upper().split(","), default=None, help="Kode video, mis. A,C")
    p_run = sub.add_parser("run", help="Jalankan analisis pada fixture dan beri nilai")
    p_run.add_argument("--mock", action="store_true", help="Key mock, tanpa Gemini")
    p_run.add_argument("--model", default=DEFAULT_MODEL, help="Nama model Gemini, atau auto (default)")
    p_run.add_argument("--duration", default="auto", help="Preferensi durasi klip (15s/30s/60s/auto)")
    p_run.add_argument("--repeat", type=int, default=1)
    p_run.add_argument("--only", type=lambda s: s.upper().split(","), default=None, help="Kode video, mis. A,C")
    p_run.add_argument("--retries", type=int, default=2, help="Ulangi video bila Gemini memberi error sementara")
    p_run.add_argument("--retry-wait", type=int, default=30, help="Detik tunggu sebelum mengulang")
    p_run.add_argument("--save-baseline", action="store_true", help="Simpan metrik run ini ke tests/golden/baseline.json")
    p_run.add_argument("--compare", action="store_true", help="Bandingkan dengan baseline (exit 2 bila ada yang lebih buruk)")
    p_score = sub.add_parser("score", help="Nilai ulang laporan run tersimpan tanpa Gemini")
    p_score.add_argument("report", help="Path laporan di tests/golden/data/runs/")
    p_score.add_argument("--save-baseline", action="store_true", help="Simpan hasil nilai ulang sebagai baseline")
    p_score.add_argument("--compare", action="store_true", help="Bandingkan dengan baseline (exit 2 bila ada yang lebih buruk)")
    sub.add_parser("selftest", help="Uji fungsi penilai tanpa jaringan dan tanpa Gemini")
    args = parser.parse_args()
    return {"fetch": cmd_fetch, "run": cmd_run, "score": cmd_score, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
