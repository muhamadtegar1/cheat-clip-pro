"""Smoke test satu perintah untuk Cheat Clip PRO (task 17a).

Jalankan dari root repo:
    venv\\Scripts\\python.exe scripts\\smoke_test.py [--keep] [--gpu]

Cek yang dijalankan:
  1. POST /api/analyze dengan key `mock` pada video sintetis + SRT manual (tanpa Whisper).
  2. RATE_LIMIT: klien Gemini palsu selalu melempar 429, endpoint harus mengirim error status 429.
  3. MALFORMED_JSON: klien palsu mengembalikan JSON terpotong, parser toleran harus tetap menghasilkan klip.
     Klien palsu juga mengembalikan klip di luar durasi: guardrail membuang semuanya lalu fallback heatmap dipakai,
     tanpa rentang dan dengan `range_start`/`range_end` (task #29: klip di dalam rentang, sepanjang target).
     Task #30: pada video sintetis kedua (120 s), klip fallback `auto` tidak saling tumpang tindih dan tidak ada yang < 10 s.
     Task #33: heatmap energi audio kosong untuk video tanpa audio, file rusak, dan nada rata; berpuncak di bagian keras.
     Task #1: skor 7 dimensi dari klien palsu (JSON utuh, dengan fokus pencarian, terpotong) dan mock: total, label, urutan.
     Task #32: prompt jalur upload memberi label energi audio pada heatmap akustik; teks heatmap YouTube/kosong tidak berubah.
  4. POST /api/render-batch untuk 1 klip, output MP4 valid 1080x1920 dengan durasi yang benar di EXPORTS_DIR.
  5. auto_cleanup_expired_files menghapus cache lama tetapi tidak menyentuh EXPORTS_DIR (TTL dan kuota).
  6. Endpoint admin hanya untuk komputer sendiri, update/restart butuh ADMIN_API_KEY, Gemini key disimpan di .env tanpa bocor.
  7. Guardrail output (task #12): kutipan karangan diganti kalimat asli, timestamp dijepit/dibuang, overlap 80% digabung, 50% ditandai.
  8. Pilihan klip (task #35): simpan/timpa/batal/baca/ekspor JSON-CSV di EXPORTS_DIR/data, tulis atomik, file rusak dibackup, guard lokal.
  9. Nama model Whisper (task #38): CHEAT_CLIP_WHISPER_MODEL kosong = default, valid dipakai, tidak dikenal = base (tanpa memuat model).
  10. Bahasa audio Whisper (task #39): Otomatis identik dengan sebelumnya, bahasa dipilih sampai ke Whisper di analisis/pratinjau/render, 422.
  11. Cache HD YouTube (task #28): yt-dlp dipalsukan, saklar, coba ulang, batas ukuran, <720p ditolak, satu unduhan, potong lokal dari cache.
  12. Fallback Whisper YouTube (task #40): caption gagal, audio palsu, bahasa audio sampai ke Whisper ([None, 'en']).
  13. Posting kit (task #22): folder kit per klip (MP4, SRT = baris karaoke, metadata.json, caption per platform), ZIP,
      retry, kit gagal tidak menggagalkan klip, prompt_version di respons analisis. Folder kit di EXPORTS_DIR sementara.

Skrip tidak mengimpor `backend.main`, jadi daemon auto-cleanup tidak berjalan.
Semua file yang dibuat skrip ini dihapus di akhir (kecuali dengan --keep).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

VIDEO_DURATION = 40
RENDER_CLIP = (5.0, 15.0)
FALLBACK_RANGE = (22.0, 38.0)  # task #29: mulai di tengah baris, berakhir sebelum durasi video, panjang relatif (16 s) < detik absolut
OVERLAP_VIDEO = 120  # task #30: video kedua, cukup panjang untuk klip fallback `auto` yang dulu saling menimpa
OVERLAP_RANGE = (60.0, 110.0)
SRT_LINES = [
    (0, 5, "Hello and welcome to this synthetic smoke test video."),
    (5, 10, "Most people think finding viral moments is pure luck."),
    (10, 15, "But the truth is you can measure attention with data."),
    (15, 20, "Here is the one trick editors use to find the best hook."),
    (20, 25, "Short clips with a strong payoff keep viewers watching."),
    (25, 30, "Try this on your next video and compare the retention."),
    (30, 35, "That is the whole process from start to finish."),
    (35, 40, "Thanks for watching and see you in the next one."),
]

MALFORMED_JSON = (
    '```json\n{"summary": "Smoke test summary #SmokeTest", "clips": ['
    '{"title": "Measuring attention with data", "start_time": 5.0, "end_time": 15.0, "hook_time": 6.0, '
    '"virality_score": 84, "key_quotes": ["you can measure attention with data"], '
    '"title_suggestion": "Attention Is Measurable", "caption_suggestion": "Data beats luck #Editing", '
    '"hashtag_suggestion": "#Editing #Shorts",}, '
    '{"title": "The one trick editors use", "start_time": 15.0, "end_time": 25.0, "hook_time": 15.5, '
    '"virality_score": 79, "key_quotes": ["the one trick editors'
)

# Semua klip di luar durasi video (40 s): guardrail membuang semuanya, analisis harus jatuh ke klip fallback heatmap.
OUT_OF_RANGE_JSON = json.dumps({"summary": "Out of range #SmokeTest", "clips": [
    {"title": "Beyond the end", "start_time": 120.0, "end_time": 150.0, "hook_time": 121.0, "virality_score": 90,
     "key_quotes": ["this was never said"], "title_suggestion": "", "caption_suggestion": "", "hashtag_suggestion": ""},
    {"title": "Also beyond", "start_time": 200.0, "end_time": 230.0, "hook_time": 201.0, "virality_score": 80,
     "key_quotes": ["neither was this"], "title_suggestion": "", "caption_suggestion": "", "hashtag_suggestion": ""},
]})

# Task #1: skor 7 dimensi datar dari Gemini. Klip kedua lebih kuat agar urutan dari backend terlihat.
SCORED_CLIPS = [
    {"title": "Luck versus data", "start_time": 5.0, "end_time": 15.0, "hook_time": 5.5,
     "score_prompt_match": 40, "score_hook": 70, "score_retention": 60, "score_clarity": 80, "score_emotional_pull": 50,
     "score_payoff": 60, "score_editability": 70, "score_reason": "Opens with 'pure luck' then answers it with data.",
     "needs_context": False, "key_quotes": ["you can measure attention with data"],
     "title_suggestion": "", "caption_suggestion": "", "hashtag_suggestion": ""},
    {"title": "The one trick editors use", "start_time": 15.0, "end_time": 25.0, "hook_time": 15.5,
     "score_prompt_match": 100, "score_hook": 90, "score_retention": 85, "score_clarity": 88, "score_emotional_pull": 80,
     "score_payoff": 92, "score_editability": 85, "score_reason": "Promise of 'the one trick' is paid off at 20s.",
     "needs_context": True, "key_quotes": ["Short clips with a strong payoff keep viewers watching"],
     "title_suggestion": "", "caption_suggestion": "", "hashtag_suggestion": ""},
]
SCORED_JSON = json.dumps({"summary": "Scored #SmokeTest", "clips": SCORED_CLIPS})
# Terpotong di tengah klip ketiga: json.loads gagal, parser toleran harus membaca skor datar lewat regex.
SCORED_TRUNCATED = SCORED_JSON[:-2] + ', {"title": "Cut off", "start_time": 30.0, "score_hook": 4'

RESULTS = []


def report(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok))
    line = f"[{'PASS' if ok else 'FAIL'}] {name}"
    if detail:
        line += f": {detail}"
    print(line, flush=True)
    return ok


def fmt_srt_time(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(lines=None) -> str:
    blocks = []
    for i, (start, end, text) in enumerate(lines or SRT_LINES, 1):
        blocks.append(f"{i}\n{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n{text}")
    return "\n\n".join(blocks) + "\n"


def make_synthetic_video(path: Path, duration: int = VIDEO_DURATION, size: str = "1280x720",
                         audio: bool = True, audio_filter: str = "") -> None:
    sine = f"sine=frequency=440:sample_rate=44100:duration={duration}" + (f",{audio_filter}" if audio_filter else "")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={duration}",
        *(["-f", "lavfi", "-i", sine] if audio else []),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        *(["-c:a", "aac", "-shortest"] if audio else []), str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)


def ffprobe_video(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60).stdout
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "duration": float(data.get("format", {}).get("duration", 0.0)),
    }


def read_sse_events(client, payload: dict) -> list:
    events = []
    with client.stream("POST", "/api/analyze", json=payload) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


class FakeGeminiClient:
    """Pengganti `genai.Client` untuk skenario error. `mode` = 'rate_limit', 'malformed_json', 'out_of_range',
    'scored' atau 'scored_truncated' (#1)."""

    calls = []
    prompts = []  # task #32: isi prompt yang dikirim, untuk memeriksa teks heatmap

    def __init__(self, mode: str):
        self.mode = mode
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model=None, contents=None, config=None):
        FakeGeminiClient.calls.append(model)
        FakeGeminiClient.prompts.append(str(contents))
        if self.mode == "rate_limit":
            raise Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for this API key (smoke test).")
        if self.mode == "out_of_range":
            return SimpleNamespace(parsed=None, text=OUT_OF_RANGE_JSON)
        if self.mode == "scored":
            return SimpleNamespace(parsed=None, text=SCORED_JSON)
        if self.mode == "scored_truncated":
            return SimpleNamespace(parsed=None, text=SCORED_TRUNCATED)
        return SimpleNamespace(parsed=None, text=MALFORMED_JSON)


def patch_gemini(analyze_mod, mode: str):
    original = (analyze_mod.genai, analyze_mod.get_flash_models_for_key)
    analyze_mod.genai = SimpleNamespace(Client=lambda *a, **kw: FakeGeminiClient(mode))
    analyze_mod.get_flash_models_for_key = lambda client: []
    FakeGeminiClient.calls = []
    FakeGeminiClient.prompts = []
    return original


def restore_gemini(analyze_mod, original) -> None:
    analyze_mod.genai, analyze_mod.get_flash_models_for_key = original


def check_clips(result: dict, max_end: float) -> str:
    clips = result.get("clips") or []
    if not clips:
        return "tidak ada klip"
    for c in clips:
        if not (0.0 <= c["start_time"] < c["end_time"] <= max_end + 0.5):
            return f"timestamp tidak valid: {c['start_time']}-{c['end_time']}"
    return ""


def run_analyze_checks(client, analyze_mod, video_name: str, srt: str) -> None:
    base = {"url": video_name, "duration": "15s", "subtitles": srt, "subtitles_filename": "smoke.srt"}

    # 1. Mock
    try:
        events = read_sse_events(client, {**base, "api_key": "mock"})
        done = [e for e in events if e.get("done")]
        errors = [e for e in events if e.get("error")]
        if errors:
            report("analyze mock", False, errors[0]["error"])
        elif not done:
            report("analyze mock", False, "event done tidak ditemukan")
        else:
            problem = check_clips(done[-1]["result"], VIDEO_DURATION)
            n = len(done[-1]["result"].get("clips") or [])
            report("analyze mock", not problem, problem or f"{n} klip")
    except Exception as e:
        report("analyze mock", False, repr(e))

    # 2. RATE_LIMIT
    original = patch_gemini(analyze_mod, "rate_limit")
    try:
        events = read_sse_events(client, {**base, "api_key": "smoke-fake-key"})
        errors = [e for e in events if e.get("error")]
        done = [e for e in events if e.get("done")]
        ok = bool(errors) and errors[-1].get("status") == 429 and not done
        detail = f"status {errors[-1].get('status')}, {len(FakeGeminiClient.calls)} model dicoba" if errors else "tidak ada event error"
        report("analyze RATE_LIMIT -> 429", ok, detail)
    except Exception as e:
        report("analyze RATE_LIMIT -> 429", False, repr(e))
    finally:
        restore_gemini(analyze_mod, original)

    # 3b. Guardrail membuang semua klip -> fallback heatmap (task #12)
    original = patch_gemini(analyze_mod, "out_of_range")
    try:
        events = read_sse_events(client, {**base, "api_key": "smoke-fake-key"})
        done = [e for e in events if e.get("done")]
        errors = [e for e in events if e.get("error")]
        guard = [e.get("guardrails") for e in events if e.get("stage") == "Clip Guardrails"]
        if errors:
            report("analyze guardrail buang semua -> fallback", False, errors[0]["error"])
        elif not done:
            report("analyze guardrail buang semua -> fallback", False, "event done tidak ditemukan")
        else:
            result = done[-1]["result"]
            problem = check_clips(result, VIDEO_DURATION)
            titles = [c["title"] for c in result.get("clips") or []]
            if not problem and any(t in ("Beyond the end", "Also beyond") for t in titles):
                problem = "klip di luar durasi lolos"
            if not problem and not (guard and guard[-1].get("dropped_invalid") == 2 and guard[-1].get("fallback_clips")):
                problem = f"ringkasan guardrail tidak sesuai: {guard[-1] if guard else None}"
            report("analyze guardrail buang semua -> fallback", not problem,
                   problem or f"2 klip di luar durasi dibuang, {len(titles)} klip fallback heatmap")
    except Exception as e:
        report("analyze guardrail buang semua -> fallback", False, repr(e))
    finally:
        restore_gemini(analyze_mod, original)

    # 3c. Fallback heatmap dengan rentang khusus (task #29): klip di dalam rentang, sepanjang target, tanpa dijepit guardrail
    name = "analyze fallback heatmap dengan rentang"
    rs, re_, target = FALLBACK_RANGE[0], FALLBACK_RANGE[1], 15.0
    original = patch_gemini(analyze_mod, "out_of_range")
    try:
        events = read_sse_events(client, {**base, "api_key": "smoke-fake-key", "range_start": rs, "range_end": re_})
        done = [e for e in events if e.get("done")]
        errors = [e for e in events if e.get("error")]
        guard = [e.get("guardrails") for e in events if e.get("stage") == "Clip Guardrails"]
        if errors:
            report(name, False, errors[0]["error"])
        elif not done:
            report(name, False, "event done tidak ditemukan")
        else:
            clips = done[-1]["result"].get("clips") or []
            problem = "" if clips else "tidak ada klip"
            for c in clips:
                s, e = c["start_time"], c["end_time"]
                notes = [n for n in c.get("guardrail_notes") or [] if "timestamp adjusted" in n]
                if not (rs <= s < e <= re_):
                    problem = f"klip {s}-{e} di luar rentang {rs}-{re_}"
                elif abs((e - s) - min(target, re_ - s)) > 0.01:
                    problem = f"klip {s}-{e} panjangnya {e - s:.1f}s, seharusnya {min(target, re_ - s):.1f}s"
                elif notes:
                    problem = f"klip {s}-{e} dijepit guardrail: {notes[0]}"
                if problem:
                    break
            if not problem and not (guard and guard[-1].get("fallback_clips") == len(clips)):
                problem = f"ringkasan guardrail tidak sesuai: {guard[-1] if guard else None}"
            spans = ", ".join(f"{c['start_time']:g}-{c['end_time']:g}" for c in clips)
            report(name, not problem, problem or f"rentang {rs:g}-{re_:g}s: {len(clips)} klip fallback ({spans})")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        restore_gemini(analyze_mod, original)

    # 3. MALFORMED_JSON
    original = patch_gemini(analyze_mod, "malformed_json")
    try:
        events = read_sse_events(client, {**base, "api_key": "smoke-fake-key"})
        done = [e for e in events if e.get("done")]
        errors = [e for e in events if e.get("error")]
        if errors:
            report("analyze MALFORMED_JSON", False, errors[0]["error"])
        elif not done:
            report("analyze MALFORMED_JSON", False, "event done tidak ditemukan")
        else:
            problem = check_clips(done[-1]["result"], VIDEO_DURATION)
            n = len(done[-1]["result"].get("clips") or [])
            report("analyze MALFORMED_JSON", not problem, problem or f"{n} klip dari JSON rusak")
    except Exception as e:
        report("analyze MALFORMED_JSON", False, repr(e))
    finally:
        restore_gemini(analyze_mod, original)


def run_fallback_overlap_check(client, analyze_mod, uploads_dir: Path, work_dir: Path) -> None:
    """Task #30: klip fallback heatmap `auto` tidak saling tumpang tindih dan tidak ada klip < 10 s.

    Video 40 s terlalu pendek untuk klip `auto` yang saling menimpa, jadi cek ini memakai video sintetis 120 s sendiri.
    """
    name = "analyze fallback heatmap tanpa tumpang tindih"
    video_name = f"upload_smoke_overlap_{uuid.uuid4().hex[:8]}.mp4"
    video_path = uploads_dir / video_name
    lines = [(i * 5, i * 5 + 5, f"Synthetic sentence number {i} about finding viral moments.") for i in range(OVERLAP_VIDEO // 5)]
    rs, re_ = OVERLAP_RANGE
    original = None
    try:
        make_synthetic_video(work_dir / video_name, OVERLAP_VIDEO, "320x180")
        shutil.copy2(work_dir / video_name, video_path)
        base = {"url": video_name, "subtitles": build_srt(lines), "subtitles_filename": "overlap.srt", "api_key": "smoke-fake-key"}
        original = patch_gemini(analyze_mod, "out_of_range")
        problem, spans = "", []
        for label, extra in (("tanpa rentang", {}), (f"rentang {rs:g}-{re_:g}s", {"range_start": rs, "range_end": re_})):
            events = read_sse_events(client, {**base, "duration": "auto", **extra})
            done = [e for e in events if e.get("done")]
            errors = [e for e in events if e.get("error")]
            if errors or not done:
                problem = f"{label}: {errors[0]['error'] if errors else 'event done tidak ditemukan'}"
                break
            clips = sorted(done[-1]["result"].get("clips") or [], key=lambda c: c["start_time"])
            lo, hi = (rs, re_) if extra else (0.0, float(OVERLAP_VIDEO))
            notes = [n for c in clips for n in c.get("guardrail_notes") or [] if n.startswith(("merged", "overlaps", "timestamp"))]
            short = [c for c in clips if c["end_time"] - c["start_time"] < 10.0]
            if len(clips) < 2:
                problem = f"{label}: hanya {len(clips)} klip fallback"
            elif notes:
                problem = f"{label}: {notes[0]}"
            elif short:
                problem = f"{label}: klip {short[0]['start_time']:g}-{short[0]['end_time']:g} kurang dari 10 s"
            elif any(not (lo <= c["start_time"] < c["end_time"] <= hi) for c in clips):
                problem = f"{label}: klip di luar {lo:g}-{hi:g}s"
            elif any(a["end_time"] > b["start_time"] for a, b in zip(clips, clips[1:])):
                problem = f"{label}: klip saling tumpang tindih"
            if problem:
                break
            spans.append(f"{label}: " + ", ".join(f"{c['start_time']:g}-{c['end_time']:g}" for c in clips))
        report(name, not problem, problem or "; ".join(spans))
    except Exception as e:
        report(name, False, repr(e))
    finally:
        if original is not None:
            restore_gemini(analyze_mod, original)
        video_path.unlink(missing_ok=True)


def run_score_check(client, analyze_mod, video_name: str, srt: str) -> None:
    """Task #1: total = rata-rata dimensi (prompt_match hanya dengan fokus pencarian), label, urutan, mock dan JSON terpotong."""
    name = "skor 7 dimensi dihitung backend"
    base = {"url": video_name, "duration": "15s", "subtitles": srt, "subtitles_filename": "smoke.srt", "api_key": "smoke-fake-key"}
    dims = ("hook", "retention", "clarity", "emotional_pull", "payoff", "editability")
    problem, info = "", []
    try:
        for mode, extra, with_focus in (("scored", {}, False), ("scored", {"custom_prompt": "editing tips"}, True),
                                        ("scored_truncated", {}, False)):
            original = patch_gemini(analyze_mod, mode)
            try:
                events = read_sse_events(client, {**base, **extra})
            finally:
                restore_gemini(analyze_mod, original)
            done = [e for e in events if e.get("done")]
            if not done:
                problem = f"{mode}: event done tidak ditemukan"
                break
            clips = done[-1]["result"].get("clips") or []
            if len(clips) != 2:
                problem = f"{mode}: {len(clips)} klip, seharusnya 2"
                break
            totals = []
            for c, src in zip(clips, (SCORED_CLIPS[1], SCORED_CLIPS[0])):
                values = [src[f"score_{d}"] for d in dims] + ([src["score_prompt_match"]] if with_focus else [])
                expect = int(round(sum(values) / len(values)))
                label = "strong" if expect >= 80 else ("fair" if expect >= 60 else "weak")
                sc = c.get("scores") or {}
                if c["title"] != src["title"]:
                    problem = f"{mode}: urutan salah ({[x['title'] for x in clips]})"
                elif c["virality_score"] != expect or c.get("score_label") != label:
                    problem = f"{mode}: {c['title']} total {c['virality_score']}/{c.get('score_label')}, seharusnya {expect}/{label}"
                elif (sc.get("prompt_match") is None) == with_focus or any(sc.get(d) != src[f"score_{d}"] for d in dims):
                    problem = f"{mode}: scores tidak sesuai ({sc})"
                elif c.get("needs_context") is not src["needs_context"] or not c.get("score_reason"):
                    problem = f"{mode}: needs_context/score_reason tidak terbawa"
                if problem:
                    break
                totals.append(c["virality_score"])
            if problem:
                break
            info.append(f"{mode}{'+fokus' if with_focus else ''} {totals}")
        if not problem:
            events = read_sse_events(client, {**base, "api_key": "mock"})
            mock = (([e for e in events if e.get("done")] or [{}])[-1].get("result") or {}).get("clips") or []
            if not mock or any(not c.get("scores") or not c.get("score_label") for c in mock):
                problem = "mock: klip tanpa scores/score_label"
        report(name, not problem, problem or "; ".join(info) + "; mock bertanda skor")
    except Exception as e:
        report(name, False, repr(e))


# Task #32: teks heatmap prompt sebelum task, harus tetap persis sama untuk jalur YouTube dan tanpa heatmap.
OLD_VIEWER_NOTE = "Columns: start|end|audience_interest(0-1). Prioritise high-interest peaks."
OLD_EMPTY_NOTE = "No audience interest data. Use content hooks, energy, and story arcs."


def run_heatmap_prompt_check(client, analyze_mod, video_name: str, srt: str) -> None:
    """Task #32: heatmap energi audio diberi label jujur di prompt; teks YouTube dan tanpa heatmap tidak berubah."""
    name = "label heatmap di prompt"
    base = {"url": video_name, "duration": "15s", "subtitles": srt, "subtitles_filename": "smoke.srt", "api_key": "smoke-fake-key"}
    problem = ""
    try:
        build = analyze_mod.build_heatmap_prompt_parts
        if build(True, "viewer") != (OLD_VIEWER_NOTE, "interest"):
            problem = f"teks heatmap YouTube berubah: {build(True, 'viewer')}"
        elif build(False, "viewer") != (OLD_EMPTY_NOTE, "interest") or build(False, "audio") != (OLD_EMPTY_NOTE, "interest"):
            problem = "teks tanpa heatmap berubah"
        original_heat = analyze_mod.compute_audio_energy_heatmap
        for label, fake_heat, want, banned in (
                ("akustik", [{"start_time": i * 0.15, "end_time": (i + 1) * 0.15, "value": (i % 10) / 10} for i in range(100)],
                 ("audio_energy(0-1)", "NOT viewer interest", "start|end[|energy]"), ("audience_interest", "Prioritise high-interest")),
                ("akustik kosong", [], (OLD_EMPTY_NOTE, "start|end[|interest]"), ("audio_energy",))):
            if problem:
                break
            analyze_mod.compute_audio_energy_heatmap = lambda *a, _h=fake_heat, **kw: list(_h)
            original = patch_gemini(analyze_mod, "scored")
            try:
                read_sse_events(client, base)
                prompt = FakeGeminiClient.prompts[-1] if FakeGeminiClient.prompts else ""
            finally:
                restore_gemini(analyze_mod, original)
                analyze_mod.compute_audio_energy_heatmap = original_heat
            if not prompt:
                problem = f"{label}: prompt tidak tertangkap"
            elif any(w not in prompt for w in want) or any(b in prompt for b in banned):
                problem = f"{label}: teks heatmap prompt salah"
        report(name, not problem, problem or "upload akustik = audio_energy + peringatan; YouTube dan kosong = teks lama persis")
    except Exception as e:
        report(name, False, repr(e))


def run_audio_heatmap_check(tone_video: Path, work_dir: Path) -> None:
    """Task #33: compute_audio_energy_heatmap tidak pernah membuat data buatan."""
    name = "heatmap energi audio tanpa data buatan"
    try:
        from backend.video_engine import compute_audio_energy_heatmap
        noaudio, loud, broken = work_dir / "heat_noaudio.mp4", work_dir / "heat_loud.mp4", work_dir / "heat_broken.mp4"
        make_synthetic_video(noaudio, 20, "320x180", audio=False)
        make_synthetic_video(loud, 40, "320x180", audio_filter="volume='if(between(t,20,26),1.0,0.15)':eval=frame")
        broken.write_bytes(b"bukan video")
        problem = ""
        for label, path, dur in (("tanpa audio", noaudio, 20.0), ("file rusak", broken, 20.0),
                                 ("nada rata", tone_video, float(VIDEO_DURATION))):
            if compute_audio_energy_heatmap(path, dur) != []:
                problem = f"{label}: heatmap tidak kosong"
                break
        if not problem:
            heat = compute_audio_energy_heatmap(loud, 40.0)
            if len(heat) != 100:
                problem = f"bagian keras: {len(heat)} titik, seharusnya 100"
            else:
                values = [p["value"] for p in heat]
                inside = sum(values[50:65]) / 15
                outside = (sum(values) - sum(values[50:65])) / 85
                if not inside > outside + 0.5:
                    problem = f"bagian keras tidak menonjol: rata-rata 20-26 s {inside:.2f}, lainnya {outside:.2f}"
        report(name, not problem, problem or "tanpa audio, rusak, nada rata = []; bagian keras 20-26 s berpuncak")
    except Exception as e:
        report(name, False, repr(e))


def run_render_check(client, render_service, is_valid_mp4, exports_dir: Path, video_name: str, use_gpu: bool):
    start, end = RENDER_CLIP
    payload = {
        "video_url": f"/api/video/{video_name}",
        "video_id": Path(video_name).stem,
        "clips": [{
            "title": "Smoke test clip",
            "title_suggestion": "Smoke Test Clip",
            "start_time": start,
            "end_time": end,
            "hook_time": start,
        }],
        "settings": {
            "caption_style": "none",
            "enable_face_tracking": False,
            "hardware_accel": "auto" if use_gpu else "cpu",
        },
    }
    name = "render 1 klip"
    try:
        t0 = time.time()
        resp = client.post("/api/render-batch", json=payload)
        if resp.status_code != 200:
            report(name, False, f"HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        batch_id = resp.json()["batch_id"]
        batch = render_service.RENDER_BATCHES.get(batch_id) or {}
        clip = (batch.get("clips") or [{}])[0]
        if batch.get("overall_status") != "completed" or clip.get("status") != "completed":
            report(name, False, f"status {batch.get('overall_status')}/{clip.get('status')}: {clip.get('error_message')}")
            return batch_id
        out_path = exports_dir / clip["download_url"].split("/")[-1]
        if not out_path.exists():
            report(name, False, f"file tidak ada: {out_path.name}")
            return batch_id
        if not is_valid_mp4(str(out_path)):
            report(name, False, "is_valid_mp4 = False")
            return batch_id
        info = ffprobe_video(out_path)
        expected = end - start
        problems = []
        if (info["width"], info["height"]) != (1080, 1920):
            problems.append(f"resolusi {info['width']}x{info['height']}")
        if abs(info["duration"] - expected) > 1.0:
            problems.append(f"durasi {info['duration']:.2f}s (harap {expected:.1f}s)")
        detail = "; ".join(problems) or f"1080x1920, {info['duration']:.2f}s, {time.time() - t0:.0f}s render, di {exports_dir}"
        report(name, not problems, detail)
        return batch_id
    except Exception as e:
        report(name, False, repr(e))
        return None


def run_cleanup_check(config) -> None:
    """Cek 5: auto-cleanup menghapus cache lama tetapi tidak menyentuh EXPORTS_DIR (TTL maupun kuota).
    Folder backend diganti sementara ke folder sementara agar file asli tidak tersentuh."""
    import backend.services.system_service as system_service

    name = "auto-cleanup tidak menyentuh exports"
    root = Path(tempfile.mkdtemp(prefix="cheatclip_cleanup_"))
    temp, exports, base = root / "temp_clips", root / "exports", root / "backend"
    uploads = temp / "uploads"
    for d in (uploads, exports, base / "temp"):
        d.mkdir(parents=True, exist_ok=True)

    original = (config.TEMP_DIR, config.UPLOADS_DIR, config.EXPORTS_DIR, system_service._base_dir)
    config.TEMP_DIR, config.UPLOADS_DIR, config.EXPORTS_DIR = temp, uploads, exports
    system_service._base_dir = str(base)
    try:
        old = time.time() - 2 * 3600

        def make(path: Path, size: int, mtime=None) -> Path:
            path.write_bytes(b"\0" * size)
            if mtime:
                os.utime(path, (mtime, mtime))
            return path

        # Tahap TTL: file > 1 jam di cache terhapus, di exports tetap ada.
        old_export = make(exports / "clip_1_batch_old.mp4", 100, old)
        old_temp = make(temp / "batch_old_clip_0_raw.mp4", 100, old)
        old_upload = make(uploads / "upload_old.mp4", 100, old)
        old_cache_tmp = make(base / "temp" / "old.tmp", 100, old)
        fresh_temp = make(temp / "fresh.ass", 100)
        system_service.auto_cleanup_expired_files(max_age_seconds=3600, max_storage_bytes=10**9)
        problems = []
        if not old_export.exists():
            problems.append("TTL menghapus MP4 di exports")
        for p in (old_temp, old_upload, old_cache_tmp):
            if p.exists():
                problems.append(f"TTL tidak menghapus cache lama {p.name}")
        if not fresh_temp.exists():
            problems.append("TTL menghapus cache baru")

        # Tahap kuota: exports besar tidak dihitung, jadi cache kecil di bawah kuota tidak dipurge.
        big_export = make(exports / "clip_2_batch_big.mp4", 5000)
        res = system_service.auto_cleanup_expired_files(max_age_seconds=10**9, max_storage_bytes=1000)
        if not big_export.exists() or not old_export.exists():
            problems.append("kuota menghapus MP4 di exports")
        if not fresh_temp.exists():
            problems.append("kuota menghapus cache padahal di bawah kuota")
        if res.get("remaining_storage_bytes") != 100:
            problems.append(f"exports ikut dihitung kuota ({res.get('remaining_storage_bytes')} byte)")
        report(name, not problems, "; ".join(problems) or "cache lama terhapus, exports utuh, kuota hanya cache")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        config.TEMP_DIR, config.UPLOADS_DIR, config.EXPORTS_DIR, system_service._base_dir = original
        shutil.rmtree(root, ignore_errors=True)


def run_admin_check() -> None:
    """Cek 6: guard endpoint admin dan penyimpanan Gemini key di backend.
    `.env` dialihkan ke folder sementara dan variabel env dipulihkan, jadi `.env` asli tidak tersentuh."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.routers.system as system_mod

    name = "admin guard + gemini key backend"
    env_names = ("ADMIN_API_KEY", "CHEAT_CLIP_API_KEY", "GEMINI_API_KEY")
    saved_env = {k: os.environ.get(k) for k in env_names}
    original_path = system_mod.GEMINI_KEY_ENV_PATH
    root = Path(tempfile.mkdtemp(prefix="cheatclip_admin_"))
    env_file = root / ".env"
    env_file.write_bytes(b"FOO=bar\r\n# komentar\r\nGEMINI_API_KEY=old_key_value_123\r\n")
    system_mod.GEMINI_KEY_ENV_PATH = env_file

    app = FastAPI()
    app.include_router(system_mod.router)
    local = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))
    problems = []

    def expect(label, resp, code):
        if resp.status_code != code:
            problems.append(f"{label}: {resp.status_code} (harap {code})")

    try:
        for k in env_names:
            os.environ.pop(k, None)
        fake_key = "AIzaSmokeTestKey_0123456789abcdWXYZ"

        # Tanpa ADMIN_API_KEY: hanya loopback tanpa Origin asing.
        expect("GET key lokal", local.get("/api/settings/gemini-key"), 200)
        expect("GET key dari LAN", remote.get("/api/settings/gemini-key"), 403)
        expect("clear-temp dari LAN", remote.post("/api/clear-temp"), 403)
        expect("auto-cleanup Origin asing",
               local.post("/api/auto-cleanup", headers={"Origin": "https://evil.example"}), 403)
        expect("PUT key Origin asing",
               local.put("/api/settings/gemini-key", json={"api_key": fake_key}, headers={"Origin": "https://evil.example"}), 403)
        expect("update tanpa ADMIN_API_KEY", local.post("/api/system/update"), 403)
        expect("restart tanpa ADMIN_API_KEY", local.post("/api/system/restart"), 403)

        # Simpan key: .env ditulis, baris lain utuh, respons tidak memuat key utuh.
        r = local.put("/api/settings/gemini-key", json={"api_key": fake_key},
                      headers={"Origin": "http://localhost:5173"})
        expect("PUT key lokal", r, 200)
        body = r.text
        if fake_key in body or fake_key in local.get("/api/settings/gemini-key").text:
            problems.append("respons memuat key utuh")
        if r.status_code == 200 and (r.json().get("hint") != "WXYZ" or r.json().get("source") != "file"):
            problems.append(f"status key salah: {r.json()}")
        text = env_file.read_bytes()
        if text != f"FOO=bar\r\n# komentar\r\nGEMINI_API_KEY={fake_key}\r\n".encode():
            problems.append(f".env tidak sesuai: {text!r}")
        if os.environ.get("GEMINI_API_KEY") != fake_key:
            problems.append("key tidak aktif di os.environ")
        expect("PUT key format salah", local.put("/api/settings/gemini-key", json={"api_key": "ada spasi di sini"}), 400)

        # Hapus key: baris lain tetap ada.
        r = local.delete("/api/settings/gemini-key")
        expect("DELETE key", r, 200)
        if env_file.read_bytes() != b"FOO=bar\r\n# komentar\r\n" or os.environ.get("GEMINI_API_KEY"):
            problems.append("DELETE tidak menghapus key dengan rapi")

        # Dengan ADMIN_API_KEY: key wajib, update/restart lolos guard lalu ditolak flag SELF_UPDATE_DISABLED.
        os.environ["ADMIN_API_KEY"] = "smoke-admin-key"
        expect("clear-temp tanpa key admin", local.post("/api/clear-temp"), 401)
        expect("update key salah", local.post("/api/system/update", headers={"X-API-Key": "salah"}), 401)
        r = local.post("/api/system/update", headers={"X-API-Key": "smoke-admin-key"})
        expect("update key benar (diblok flag)", r, 403)
        if r.status_code == 403 and "dinonaktifkan" not in r.text:
            problems.append("update dengan key benar tidak sampai ke flag SELF_UPDATE_DISABLED")
        expect("restart Bearer benar (diblok flag)",
               local.post("/api/system/restart", headers={"Authorization": "Bearer smoke-admin-key"}), 403)

        report(name, not problems, "; ".join(problems) or "LAN/Origin asing ditolak, update/restart butuh key admin, key di .env tanpa bocor")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        system_mod.GEMINI_KEY_ENV_PATH = original_path
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(root, ignore_errors=True)


def run_choices_check(config) -> None:
    """Cek 8 (task #35): pilihan Pakai/Lewati disimpan permanen di EXPORTS_DIR/data/clip_choices.json.
    EXPORTS_DIR dialihkan ke folder sementara, jadi pilihan asli pemilik tidak tersentuh."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.routers.choices as choices_mod
    from backend.services import choices_service

    name = "pilihan klip (#35)"
    saved_env = {k: os.environ.get(k) for k in ("ADMIN_API_KEY", "CHEAT_CLIP_API_KEY")}
    original_exports = config.EXPORTS_DIR
    root = Path(tempfile.mkdtemp(prefix="cheatclip_choices_"))
    config.EXPORTS_DIR = root
    app = FastAPI()
    app.include_router(choices_mod.router)
    local = TestClient(app, client=("127.0.0.1", 50000))
    remote = TestClient(app, client=("192.168.1.50", 50000))
    origin = {"Origin": "http://localhost:5173"}
    problems = []

    def expect(label, resp, code):
        if resp.status_code != code:
            problems.append(f"{label}: {resp.status_code} (harap {code})")
        return resp

    base = {"video_id": "vidA", "video_title": "Video A", "source_type": "youtube", "start_time": 10.0,
            "end_time": 40.5, "clip_title": "Klip 1", "virality_score": 91, "rank": 1, "rank_total": 3,
            "tier": "priority", "needs_context": False, "heatmap_avg": 0.42, "heatmap_source": "youtube_viewers",
            "model": "gemini-mock",
            "scores": {"prompt_match": None, "hook": 92, "retention": 90, "clarity": 88, "emotional_pull": 91,
                       "payoff": 93, "editability": 89}}
    try:
        for k in saved_env:
            os.environ.pop(k, None)
        path = choices_service.choices_file_path()
        if path != root / "data" / "clip_choices.json":
            problems.append(f"lokasi file salah: {path}")

        expect("PUT dari LAN", remote.put("/api/clip-choices", json={**base, "choice": "use"}), 403)
        expect("PUT Origin asing", local.put("/api/clip-choices", json={**base, "choice": "use"},
                                             headers={"Origin": "https://evil.example"}), 403)
        expect("PUT pilihan salah", local.put("/api/clip-choices", json={**base, "choice": "maybe"}), 422)
        expect("PUT end <= start", local.put("/api/clip-choices", json={**base, "choice": "use", "end_time": 10.0}), 422)

        first = expect("PUT use", local.put("/api/clip-choices", json={**base, "choice": "use"}, headers=origin), 200)
        created = first.json().get("record", {}).get("created_at") if first.status_code == 200 else None
        time.sleep(1.1)
        r = expect("PUT skip (timpa)", local.put("/api/clip-choices", json={**base, "choice": "skip",
                                                                              "reason": "  hook lemah  "}), 200)
        expect("PUT klip tanpa skor", local.put("/api/clip-choices", json={
            "video_id": "vidA", "start_time": 50, "end_time": 70, "choice": "use", "scores": None,
            "virality_score": 80}), 200)
        expect("PUT video lain", local.put("/api/clip-choices", json={**base, "video_id": "vidB", "choice": "use"}), 200)

        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("records", [])
        a1 = [x for x in records if x["video_id"] == "vidA" and x["start_time"] == 10.0]
        if data.get("version") != 1 or len(records) != 3 or len(a1) != 1:
            problems.append(f"isi file salah: {len(records)} record, {len(a1)} untuk klip 1")
        elif (a1[0]["choice"] != "skip" or a1[0]["reason"] != "hook lemah" or a1[0]["created_at"] != created
              or a1[0]["updated_at"] == created or a1[0]["scores"]["hook"] != 92 or a1[0]["heatmap_avg"] != 0.42):
            problems.append(f"timpa tidak benar: {a1[0]}")
        if list(path.parent.glob("*.tmp")):
            problems.append("file sementara tertinggal")

        got = expect("GET per video", local.get("/api/clip-choices", params={"video_id": "vidA"}), 200).json()
        if len(got.get("records", [])) != 2:
            problems.append(f"GET vidA: {len(got.get('records', []))} record (harap 2)")
        expect("GET dari LAN", remote.get("/api/clip-choices"), 403)

        exp = expect("ekspor JSON", local.get("/api/clip-choices/export", params={"format": "json"}), 200)
        if exp.status_code == 200 and len(exp.json().get("records", [])) != 3:
            problems.append("ekspor JSON tidak lengkap")
        csv_resp = expect("ekspor CSV", local.get("/api/clip-choices/export", params={"format": "csv"}), 200)
        lines = csv_resp.text.lstrip("﻿").splitlines()
        if len(lines) != 4 or "score_hook" not in lines[0] or "choice" not in lines[0] or "hook lemah" not in csv_resp.text:
            problems.append(f"ekspor CSV salah: {lines[:2]}")

        r = expect("DELETE", local.delete("/api/clip-choices", params={"video_id": "vidA", "start_time": 50,
                                                                        "end_time": 70}), 200)
        if r.status_code == 200 and r.json().get("deleted") is not True:
            problems.append("DELETE tidak menghapus")
        r = local.delete("/api/clip-choices", params={"video_id": "vidA", "start_time": 50, "end_time": 70})
        if r.status_code != 200 or r.json().get("deleted") is not False:
            problems.append("DELETE kedua harus deleted=false")
        if len(json.loads(path.read_text(encoding="utf-8"))["records"]) != 2:
            problems.append("record tersisa setelah DELETE salah")

        # File rusak: dibackup, tidak ditimpa diam-diam, lalu mulai kosong.
        path.write_text("{rusak", encoding="utf-8")
        got = expect("GET file rusak", local.get("/api/clip-choices"), 200).json()
        backups = list(path.parent.glob("clip_choices.corrupt-*.json"))
        if got.get("records") != [] or len(backups) != 1 or backups[0].read_text(encoding="utf-8") != "{rusak":
            problems.append(f"file rusak tidak dibackup dengan benar ({len(backups)} backup)")

        report(name, not problems, "; ".join(problems) or "simpan/timpa/batal/baca/ekspor JSON-CSV, file rusak dibackup, LAN/Origin asing ditolak")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        config.EXPORTS_DIR = original_exports
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v
        shutil.rmtree(root, ignore_errors=True)


def run_guardrail_check() -> None:
    """Fungsi murni backend/utils/clip_guardrails.py dengan kasus buatan (tanpa jaringan, tanpa Gemini)."""
    name = "guardrail output"
    try:
        from backend.utils.clip_guardrails import apply_guardrails

        transcript = [{"start": float(s), "end": float(e), "text": text, "engagement": 0.0} for s, e, text in SRT_LINES]

        def clip(title, s, e, quotes, score=80, hook=None):
            return {"title": title, "start_time": s, "end_time": e, "hook_time": s if hook is None else hook,
                    "virality_score": score, "key_quotes": quotes}

        clips = [
            clip("asli", 5.0, 15.0, ["you can measure attention with data"], score=90),
            clip("karangan", 15.0, 25.0, ["editors secretly hate short clips"], hook=99.0),
            clip("duplikat 80%", 6.0, 16.0, ["Most people think finding viral moments is pure luck"], score=70),
            clip("overlap 50%", 20.0, 30.0, ["Short clips with a strong payoff keep viewers watching"], score=60),
            clip("lewat durasi", 33.0, 55.0, ["That is the whole process from start to finish"], score=50),
            clip("di luar video", 45.0, 60.0, ["Thanks for watching"], score=40),
        ]
        out, summary = apply_guardrails(clips, transcript, 0.0, float(VIDEO_DURATION))
        by_title = {c["title"]: c for c in out}
        problems = []
        if "duplikat 80%" in by_title or summary["merged"] != 1:
            problems.append("overlap 80% tidak digabung")
        if "di luar video" in by_title or summary["dropped_invalid"] != 1:
            problems.append("klip di luar durasi tidak dibuang")
        late = by_title.get("lewat durasi")
        if not late or late["end_time"] != float(VIDEO_DURATION):
            problems.append("end_time tidak dijepit ke durasi")
        fake = by_title.get("karangan")
        if not fake or fake["key_quotes"] == ["editors secretly hate short clips"] or not fake["key_quotes"]:
            problems.append("kutipan karangan tidak diganti")
        elif not any(fake["key_quotes"][0] in text for _, _, text in SRT_LINES):
            problems.append("kutipan pengganti bukan kalimat asli")
        if not fake or fake["hook_time"] != 15.0:
            problems.append("hook di luar klip tidak diperbaiki")
        if by_title.get("asli", {}).get("key_quotes") != ["you can measure attention with data"]:
            problems.append("kutipan asli ikut dibuang")
        flagged = [c for c in out if any("review" in n for n in c["guardrail_notes"])]
        if summary["flagged_overlap"] != 1 or {c["title"] for c in flagged} != {"karangan", "overlap 50%"}:
            problems.append(f"overlap 50% tidak ditandai ({summary})")
        report(name, not problems, "; ".join(problems) or
               f"{summary['clips_in']} klip -> {summary['clips_out']}, 1 digabung, 1 dibuang, 1 dijepit, "
               f"1 kutipan diganti, 1 overlap ditandai")
    except Exception as e:
        report(name, False, repr(e))


def run_subtitle_fix_check(work_dir: Path) -> None:
    """Task #11: kamus koreksi subtitle di generate_ass_file dan validasi RenderSettingsModel (tanpa Whisper)."""
    name = "koreksi subtitle (#11)"
    try:
        from pydantic import ValidationError
        from backend.schemas.render import RenderSettingsModel
        from backend.video_engine import generate_ass_file

        words = [
            {"word": "halo", "start": 0.0, "end": 0.4},
            {"word": "Yutub,", "start": 0.5, "end": 0.9},
            {"word": "eh", "start": 1.0, "end": 1.2},
            {"word": "channel", "start": 1.3, "end": 1.7},
            {"word": "yutub.", "start": 2.5, "end": 2.9},
        ]

        def dialogue_lines(replacements, text_case="uppercase", tag="x") -> list:
            out = work_dir / f"subfix_{tag}.ass"
            generate_ass_file(words=words, style_preset="viral_pop", font_name="Outfit", output_ass_path=str(out),
                              text_case=text_case, duration_seconds=4.0, word_replacements=replacements)
            content = out.read_text(encoding="utf-8")
            return [ln for ln in content.splitlines() if ln.startswith("Dialogue:")], content

        problems = []
        base_lines, base_content = dialogue_lines(None, tag="none")
        for tag, empty in (("empty", []), ("nomatch", [{"from": "tidakada", "to": "X"}])):
            if dialogue_lines(empty, tag=tag)[1] != base_content:
                problems.append(f"kamus {tag} mengubah file .ass")
        settings = RenderSettingsModel(subtitle_replacements=[{"from": "YUTUB", "to": "YouTube"}, {"from": "eh", "to": ""}])
        fixed_lines, fixed_content = dialogue_lines(settings.subtitle_replacements, text_case="none", tag="fix")
        if "YouTube," not in fixed_content or "YouTube." not in fixed_content:
            problems.append("kata tidak diganti atau tanda baca ujung hilang")
        if "utub" in fixed_content.lower().replace("youtube", ""):
            problems.append("kata salah masih ada")
        import re
        spoken = [re.sub(r"\{[^}]*\}", " ", ln.split(",,", 1)[-1]).lower().split() for ln in fixed_lines]
        if any("eh" in toks for toks in spoken):
            problems.append("kata dengan pengganti kosong tidak dihapus")
        upper_content = dialogue_lines(settings.subtitle_replacements, text_case="uppercase", tag="upper")[1]
        if "YOUTUBE," not in upper_content:
            problems.append("text_case uppercase tidak diterapkan ke pengganti")
        rejected = 0
        for bad in ([{"from": "dua kata", "to": "x"}], [{"from": "", "to": "x"}], [{"from": "a" * 41, "to": "x"}],
                    [{"from": "a", "to": "b" * 61}], [{"from": "a", "to": "b"}] * 101):
            try:
                RenderSettingsModel(subtitle_replacements=bad)
            except ValidationError:
                rejected += 1
        if rejected != 5:
            problems.append(f"validasi menolak {rejected}/5 input tidak valid")
        report(name, not problems, "; ".join(problems) or
               "tanpa kamus/kamus kosong identik, ganti kata + tanda baca ujung, hapus kata, uppercase, 5 input tidak valid ditolak")
    except Exception as e:
        report(name, False, repr(e))


def run_subtitle_preview_check(client, config, video_name: str, work_dir: Path) -> None:
    """Task #36a: build_subtitle_events = baris Dialogue render (hash acuan dari kode sebelum #36a), dan endpoint
    POST /api/preview-subtitles pada video sintetis dengan Whisper dipalsukan (cache, kamus, fallback, segmen dihapus)."""
    name = "pratinjau subtitle (#36a)"
    try:
        import hashlib
        import re
        from backend.video_engine import build_subtitle_events, format_ass_timestamp, generate_ass_file
        import backend.services.subtitle_preview_service as preview_svc

        problems = []
        words = [{"word": w, "start": s, "end": e} for w, s, e in [
            ("halo", 0.0, 0.4), ("Yutub,", 0.5, 0.9), ("eh", 1.0, 1.2), ("channel", 1.3, 1.7), ("ini", 1.75, 1.9),
            ("sangat", 1.95, 2.1), ("menarik.", 2.15, 2.4), ("Kenapa?", 3.2, 3.6), ("karena", 3.65, 3.9),
            ("kita", 3.95, 4.1), ("semua", 4.12, 4.3), ("suka", 4.35, 4.6), ("konten", 4.62, 5.0),
            ("panjangbanget123456789", 5.05, 5.6), ("ok", 5.61, 5.62)]]
        cases = (("viral_pop", "uppercase", None),
                 ("clean_minimal", "none", [{"from": "yutub", "to": "YouTube"}, {"from": "eh", "to": ""}]),
                 ("fire_red", "capitalize", None))
        blocks = []
        for i, (style, text_case, reps) in enumerate(cases):
            ass_path = work_dir / f"preview36_{i}.ass"
            generate_ass_file(words=words, style_preset=style, font_name="Outfit", output_ass_path=str(ass_path),
                              text_case=text_case, duration_seconds=6.0, word_replacements=reps)
            lines = [ln for ln in ass_path.read_text(encoding="utf-8").splitlines() if ln.startswith("Dialogue: 0,")]
            blocks.append("\n".join(lines))
            events = build_subtitle_events(words, text_case, reps)
            if len(events) != len(lines):
                problems.append(f"{style}: {len(events)} event vs {len(lines)} baris Dialogue")
                continue
            for ev, ln in zip(events, lines):
                parts = ln.split(",", 3)
                text = re.sub(r"\{[^}]*\}", "", ln.split(",,", 1)[-1].split("}", 1)[-1])
                if (parts[1], parts[2]) != (format_ass_timestamp(ev["start"]), format_ass_timestamp(ev["end"])) \
                        or text.split() != " ".join(ev["words"]).split():
                    problems.append(f"{style}: event tidak sama dengan baris Dialogue ({ln[:60]})")
                    break
        digest = hashlib.sha256("\n----\n".join(blocks).encode()).hexdigest()
        if digest != "c1560aac716f62901fda0306e87ae71de3d36c8db68e3703b5ac14509b60a9fd":
            problems.append(f"baris Dialogue berubah dari acuan sebelum #36a (hash {digest[:12]})")

        calls = []
        fake_words = [{"word": "halo", "start": 0.1, "end": 0.5}, {"word": "yutub", "start": 0.6, "end": 1.0},
                      {"word": "semua.", "start": 1.1, "end": 1.6}]

        def fake_transcribe(path, fallback, start, end, language=None):
            calls.append(path)
            if path:
                return [] if start >= 20 else [dict(w) for w in fake_words]
            return [{"word": "dari", "start": 0.0, "end": 0.5}, {"word": "transkrip", "start": 0.5, "end": 1.0}] if fallback else []

        original = preview_svc.transcribe_clip_words
        preview_svc.transcribe_clip_words = fake_transcribe
        preview_svc._WORDS_CACHE.clear()
        try:
            body = {"video_url": f"/api/video/{video_name}", "video_id": Path(video_name).stem, "start_time": 5.0,
                    "end_time": 15.0, "text_case": "uppercase", "subtitle_replacements": [{"from": "yutub", "to": "YouTube"}],
                    "transcript": [{"start": 20.0, "end": 25.0, "text": "dari transkrip"}]}
            r1 = client.post("/api/preview-subtitles", json=body)
            d1 = r1.json() if r1.status_code == 200 else {}
            if r1.status_code != 200 or d1.get("source") != "whisper" or d1.get("cached"):
                problems.append(f"panggilan pertama: HTTP {r1.status_code}, {str(d1)[:120]}")
            elif d1["events"] != build_subtitle_events(fake_words, "uppercase", [{"from": "yutub", "to": "YouTube"}]):
                problems.append("event endpoint tidak sama dengan build_subtitle_events")
            elif "YOUTUBE" not in " ".join(" ".join(e["words"]) for e in d1["events"]):
                problems.append("kamus #11 tidak diterapkan")
            r2 = client.post("/api/preview-subtitles", json={**body, "text_case": "lowercase"})
            d2 = r2.json() if r2.status_code == 200 else {}
            if r2.status_code != 200 or not d2.get("cached") or len(calls) != 1:
                problems.append(f"cache tidak kena (HTTP {r2.status_code}, transcribe dipanggil {len(calls)}x)")
            elif "youtube" not in " ".join(" ".join(e["words"]) for e in d2["events"]):
                problems.append("text_case lowercase tidak diterapkan dari cache")
            r5 = client.post("/api/preview-subtitles", json={**body, "force": True})
            d5 = r5.json() if r5.status_code == 200 else {}
            if r5.status_code != 200 or d5.get("cached") or len(calls) != 2:
                problems.append(f"force tidak menjalankan Whisper ulang (HTTP {r5.status_code}, transcribe dipanggil {len(calls)}x)")
            r3 = client.post("/api/preview-subtitles", json={**body, "start_time": 20.0, "end_time": 30.0})
            d3 = r3.json() if r3.status_code == 200 else {}
            if r3.status_code != 200 or d3.get("source") != "transcript" or not d3.get("events"):
                problems.append(f"fallback transkrip: HTTP {r3.status_code}, {str(d3)[:120]}")
            r4 = client.post("/api/preview-subtitles", json={**body, "start_time": 9.0, "end_time": 9.0})
            if r4.status_code != 422:
                problems.append(f"rentang kosong tidak ditolak (HTTP {r4.status_code})")
        finally:
            preview_svc.transcribe_clip_words = original
            preview_svc._WORDS_CACHE.clear()
        leftover = [p.name for p in Path(config.TEMP_DIR).glob("preview_*")]
        if leftover:
            problems.append(f"segmen pratinjau tertinggal: {leftover}")
        report(name, not problems, "; ".join(problems) or
               "event = baris Dialogue di 3 gaya, hash acuan sama, endpoint whisper/cache/text_case/force/fallback transkrip/422, segmen dihapus")
    except Exception as e:
        report(name, False, repr(e))


def run_subtitle_edit_check(client, render_service, video_name: str) -> None:
    """Task #36b: render memakai kata pratinjau (subtitle_words) tanpa Whisper, mode separate/merged/retry,
    potongan manual (group), list kosong, masukan tidak valid, dan pratinjau dari kata suntingan."""
    name = "subtitle suntingan dipakai render (#36b)"
    try:
        import re
        from backend.video_engine import build_subtitle_events

        problems = []

        def ts(value: str) -> float:
            h, m, s = value.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)

        def dialogue_rows(ass_text: str):
            rows = []
            for ln in ass_text.splitlines():
                if not ln.startswith("Dialogue: 0,") or "SubStyle" not in ln:
                    continue
                parts = ln.split(",", 3)
                text = re.sub(r"\{[^}]*\}", "", ln.split(",,", 1)[-1].split("}", 1)[-1])
                rows.append((ts(parts[1]), ts(parts[2]), " ".join(text.split())))
            return rows

        def event_rows(events, shift=0.0):
            return [(ev["start"] + shift, ev["end"] + shift, " ".join(ev["words"])) for ev in events]

        def same_rows(got, want) -> bool:
            return len(got) == len(want) and all(
                g[2] == w[2] and abs(g[0] - w[0]) <= 0.02 and abs(g[1] - w[1]) <= 0.02 for g, w in zip(got, want))

        reps = [{"from": "yutub", "to": "YouTube"}]
        edited = [{"word": w, "start": s, "end": e, "group": g} for w, s, e, g in [
            ("halo", 0.2, 0.5, 0), ("yutub", 0.6, 0.9, 0), ("ini", 1.0, 1.2, 1), ("suntingan", 1.25, 1.7, 1),
            ("satu", 1.75, 1.9, 1), ("dua", 1.95, 2.1, 1), ("baris.", 2.15, 2.5, 2)]]
        whisper_words = [{"word": w, "start": s, "end": e} for w, s, e in [
            ("dari", 0.1, 0.4), ("whisper", 0.5, 0.9), ("palsu", 1.0, 1.4)]]

        captured = []
        calls = []
        real_generate = render_service.generate_ass_file

        def wrap_generate(**kwargs):
            real_generate(**kwargs)
            with open(kwargs["output_ass_path"], encoding="utf-8") as f:
                captured.append(f.read())

        def fake_transcribe(path, fallback, start, end, language=None):
            calls.append(start)
            return [dict(w) for w in whisper_words]

        def stop_render(*args, **kwargs):
            raise RuntimeError("smoke36b: encode dilewati")

        originals = (render_service.generate_ass_file, render_service.transcribe_clip_words, render_service.render_clip_to_mp4)
        render_service.generate_ass_file = wrap_generate
        render_service.transcribe_clip_words = fake_transcribe
        render_service.render_clip_to_mp4 = stop_render
        batch_ids = []
        settings = {"caption_style": "viral_pop", "text_case": "uppercase", "subtitle_replacements": reps,
                    "title_position": "none", "enable_face_tracking": False, "hardware_accel": "cpu"}
        base = {"video_url": f"/api/video/{video_name}", "video_id": Path(video_name).stem}

        def render(clips, extra=None):
            captured.clear()
            calls.clear()
            r = client.post("/api/render-batch", json={**base, "clips": clips, "settings": {**settings, **(extra or {})}})
            if r.status_code != 200:
                raise RuntimeError(f"render-batch HTTP {r.status_code}: {r.text[:120]}")
            batch_ids.append(r.json()["batch_id"])
            return render_service.RENDER_BATCHES.get(batch_ids[-1]) or {}

        try:
            # Pratinjau dari kata suntingan: tanpa unduh/Whisper, source edited, group dipatuhi
            body = {**base, "start_time": 5.0, "end_time": 15.0, "text_case": "uppercase", "subtitle_replacements": reps}
            rp = client.post("/api/preview-subtitles", json={**body, "words": edited})
            dp = rp.json() if rp.status_code == 200 else {}
            preview_events = dp.get("events") or []
            lines = []
            for ev in preview_events:
                if not lines or lines[-1] != ev["words"]:
                    lines.append(ev["words"])
            if rp.status_code != 200 or dp.get("source") != "edited":
                problems.append(f"pratinjau suntingan: HTTP {rp.status_code}, {str(dp)[:120]}")
            elif lines != [["HALO", "YOUTUBE"], ["INI", "SUNTINGAN", "SATU", "DUA"], ["BARIS."]]:
                problems.append(f"potongan tidak mengikuti group: {lines}")
            bad = client.post("/api/preview-subtitles", json={**body, "words": [{"word": "x", "start": 2.0, "end": 1.0}]})
            if bad.status_code != 422:
                problems.append(f"kata suntingan tidak valid tidak ditolak (HTTP {bad.status_code})")

            clip = {"title": "Smoke 36b", "start_time": 5.0, "end_time": 15.0}
            # 1. Separate dengan kata suntingan: Whisper tidak dipanggil, Dialogue = event pratinjau
            render([{**clip, "subtitle_words": edited}])
            if calls:
                problems.append(f"separate: Whisper tetap dipanggil {len(calls)}x")
            elif len(captured) != 1 or not same_rows(dialogue_rows(captured[0]), event_rows(preview_events)):
                problems.append("separate: baris Dialogue tidak sama dengan event pratinjau")
            # 2. Retry batch memakai kata yang sama
            r = client.post(f"/api/render-batch/{batch_ids[-1]}/retry", json={"clip_indices": [0]})
            if r.status_code != 200 or calls or len(captured) != 2 or captured[1] != captured[0]:
                problems.append(f"retry: HTTP {r.status_code}, Whisper {len(calls)}x, .ass {len(captured)}")
            # 3. Tanpa kata pratinjau: Whisper tetap dipakai seperti sebelumnya
            render([clip])
            if len(calls) != 1:
                problems.append(f"tanpa pratinjau: Whisper dipanggil {len(calls)}x (harap 1)")
            # 4. List kosong: tanpa subtitle, tanpa Whisper
            render([{**clip, "subtitle_words": []}])
            if calls or len(captured) != 1 or dialogue_rows(captured[0]):
                problems.append("subtitle_words [] tidak menghasilkan video tanpa subtitle")
            # 5. Tidak valid: klip gagal dengan pesan jelas, tanpa Whisper
            batch = render([{**clip, "subtitle_words": [{"word": "x", "start": 1.0, "end": 0.5}]}])
            err = ((batch.get("clips") or [{}])[0].get("error_message") or "")
            if calls or "tidak valid" not in err:
                problems.append(f"subtitle_words tidak valid: Whisper {len(calls)}x, pesan '{err[:80]}'")
            # 6. Merged: segmen 1 disunting (group), segmen 2 Whisper; kata digeser 4 s
            seg1 = [w for w in edited if w["end"] <= 2.2]  # baris 0 dan 1
            render([{**clip, "start_time": 2.0, "end_time": 6.0, "subtitle_words": seg1},
                    {**clip, "start_time": 10.0, "end_time": 14.0}], {"render_mode": "merged"})
            want = event_rows(build_subtitle_events(seg1, "uppercase", reps)) + \
                event_rows(build_subtitle_events(whisper_words, "uppercase", reps), 4.0)
            if len(calls) != 1 or calls[0] != 10.0:
                problems.append(f"merged: Whisper dipanggil untuk {calls} (harap hanya segmen 2)")
            elif len(captured) != 1 or not same_rows(dialogue_rows(captured[0]), want):
                problems.append("merged: baris Dialogue tidak sama dengan event per segmen yang digeser")
        finally:
            (render_service.generate_ass_file, render_service.transcribe_clip_words,
             render_service.render_clip_to_mp4) = originals
            for bid in batch_ids:
                for p in Path(render_service.TEMP_DIR).glob(f"*{bid}*"):
                    p.unlink(missing_ok=True)
                render_service.RENDER_BATCHES.pop(bid, None)
                render_service.BATCH_REQUESTS.pop(bid, None)
        report(name, not problems, "; ".join(problems) or
               "pratinjau suntingan (group, 422), separate/retry tanpa Whisper dan Dialogue = pratinjau, "
               "tanpa pratinjau tetap Whisper, [] tanpa subtitle, tidak valid gagal jelas, merged per segmen")
    except Exception as e:
        report(name, False, repr(e))


def cleanup(paths: list, batch_id, temp_dir: Path, exports_dir: Path) -> None:
    targets = list(paths)
    if batch_id:
        targets += [p for p in temp_dir.glob(f"*{batch_id}*")]
        targets += [p for p in exports_dir.glob(f"*{batch_id}*")]
    for p in targets:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink()
        except Exception as e:
            print(f"  peringatan: gagal menghapus {p}: {e}")


def run_whisper_model_name_check() -> None:
    """Task #38: pemilihan nama model Whisper dari env tanpa memuat model."""
    name = "nama model Whisper dari env (#38)"
    saved = os.environ.get("CHEAT_CLIP_WHISPER_MODEL")
    problems = []
    try:
        from backend import video_engine as ve
        loaded_before = ve._WHISPER_MODEL
        cases = (("", ve.WHISPER_DEFAULT_MODEL), ("  ", ve.WHISPER_DEFAULT_MODEL), ("small", "small"),
                 (" Medium.EN ", "medium.en"), ("large-v3", "large-v3"), ("gpt-4", "base"), ("base;rm", "base"))
        for value, want in cases:
            os.environ["CHEAT_CLIP_WHISPER_MODEL"] = value
            got = ve.resolve_whisper_model_name()
            if got != want:
                problems.append(f"{value!r} -> {got!r}, harusnya {want!r}")
        os.environ.pop("CHEAT_CLIP_WHISPER_MODEL", None)
        if ve.resolve_whisper_model_name() != ve.WHISPER_DEFAULT_MODEL:
            problems.append("env tidak ada tidak memberi default")
        if ve.resolve_whisper_model_name("small") != "small":
            problems.append("argumen value diabaikan")
        if ve.WHISPER_DEFAULT_MODEL not in ve.WHISPER_KNOWN_MODELS or ve.WHISPER_DEFAULT_MODEL.endswith(".en"):
            problems.append(f"default {ve.WHISPER_DEFAULT_MODEL!r} bukan model multibahasa yang dikenal")
        if ve._WHISPER_MODEL is not loaded_before:
            problems.append("model Whisper ikut dimuat")
        report(name, not problems, "; ".join(problems) or f"kosong = {ve.WHISPER_DEFAULT_MODEL}, valid dipakai, tidak dikenal = base, model tidak dimuat")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        if saved is None:
            os.environ.pop("CHEAT_CLIP_WHISPER_MODEL", None)
        else:
            os.environ["CHEAT_CLIP_WHISPER_MODEL"] = saved


def run_audio_language_check(client, analyze_mod, render_service, video_name: str, video_file: Path) -> None:
    """Task #39: bahasa audio diteruskan ke Whisper (analisis, pratinjau, render separate/merged/retry), Otomatis identik
    dengan sebelum #39, kode tidak dikenal 422. Whisper selalu dipalsukan, model asli tidak dimuat."""
    name = "bahasa audio Whisper (#39)"
    problems = []
    try:
        from backend import video_engine as ve
        from backend.services import subtitle_preview_service as preview_svc

        # 1. Argumen transcribe di video_engine (model palsu)
        seen = []

        class FakeModel:
            def transcribe(self, path, **kwargs):
                seen.append(kwargs)
                return {"segments": [{"text": "halo", "start": 0.0, "end": 1.0,
                                      "words": [{"word": "halo", "start": 0.1, "end": 0.5}]}]}

        old_prompt = "Transkrip video percakapan dalam Bahasa Indonesia atau English."
        want_auto_full = {"word_timestamps": True, "fp16": False, "verbose": False, "initial_prompt": old_prompt}
        want_auto_clip = {"word_timestamps": True, "fp16": False}
        original_get = ve.get_whisper_model
        ve.get_whisper_model = lambda: FakeModel()
        try:
            for lang, want_full, want_clip in (
                    (None, want_auto_full, want_auto_clip), ("auto", want_auto_full, want_auto_clip),
                    ("en", {"word_timestamps": True, "fp16": False, "verbose": False, "language": "en"},
                     {"word_timestamps": True, "fp16": False, "language": "en"})):
                seen.clear()
                ve.transcribe_local_video_file(video_file, language=lang)
                ve.transcribe_clip_words(str(video_file), None, 0.0, 5.0, language=lang)
                if seen != [want_full, want_clip]:
                    problems.append(f"argumen transcribe {lang!r}: {seen}")
            seen.clear()
            ve.transcribe_local_video_file(video_file)
            ve.transcribe_clip_words(str(video_file), None, 0.0, 5.0)
            if seen != [want_auto_full, want_auto_clip]:
                problems.append(f"tanpa argumen bahasa tidak identik dengan sebelum #39: {seen}")
            try:
                ve.transcribe_clip_words(str(video_file), None, 0.0, 5.0, language="xx")
                problems.append("kode 'xx' tidak ditolak video_engine")
            except ValueError:
                pass
        finally:
            ve.get_whisper_model = original_get

        # 2. Kode tidak dikenal ditolak 422 di ketiga endpoint
        base = {"video_url": f"/api/video/{video_name}", "video_id": Path(video_name).stem}
        bad = {
            "/api/analyze": {"url": video_name, "api_key": "mock", "audio_language": "xx"},
            "/api/render-batch": {**base, "clips": [{"start_time": 5.0, "end_time": 15.0}],
                                  "settings": {"audio_language": "xx"}},
            "/api/preview-subtitles": {**base, "start_time": 5.0, "end_time": 15.0, "audio_language": "xx"},
        }
        for path, body in bad.items():
            r = client.post(path, json=body)
            if r.status_code != 422:
                problems.append(f"{path} audio_language 'xx': HTTP {r.status_code} (harap 422)")

        # 3. Analisis upload tanpa subtitle manual: bahasa diteruskan ke transcribe_local_video_file
        full_calls = []

        def fake_full(path, progress_callback=None, language=None):
            full_calls.append(language)
            return [{"text": f"kalimat uji nomor {i}.", "start": float(i * 3), "duration": 2.5} for i in range(15)]

        original_full = analyze_mod.transcribe_local_video_file
        analyze_mod.transcribe_local_video_file = fake_full
        try:
            for lang in (None, "id"):
                body = {"url": video_name, "duration": "15s", "api_key": "mock"}
                if lang:
                    body["audio_language"] = lang
                events = read_sse_events(client, body)
                if not any(e.get("done") for e in events):
                    errs = [e.get("error") for e in events if e.get("error")]
                    problems.append(f"analisis {lang!r} tidak selesai: {errs[:1]}")
            if full_calls != [None, "id"]:
                problems.append(f"analisis: bahasa ke Whisper {full_calls} (harap [None, 'id'])")
        finally:
            analyze_mod.transcribe_local_video_file = original_full

        # 4. Pratinjau: bahasa diteruskan dan ikut kunci cache
        preview_calls = []

        def fake_clip(path, fallback, start, end, language=None):
            preview_calls.append(language)
            return [{"word": "halo", "start": 0.1, "end": 0.5}] if path else []

        original_clip = preview_svc.transcribe_clip_words
        preview_svc.transcribe_clip_words = fake_clip
        preview_svc._WORDS_CACHE.clear()
        try:
            body = {**base, "start_time": 5.0, "end_time": 15.0}
            results = [client.post("/api/preview-subtitles", json={**body, **extra})
                       for extra in ({}, {"audio_language": "en"}, {"audio_language": "id"},
                                     {"audio_language": "en"}, {"audio_language": "auto"})]
            cached = [r.json().get("cached") if r.status_code == 200 else f"HTTP {r.status_code}" for r in results]
            if preview_calls != [None, "en", "id"] or cached != [False, False, False, True, True]:
                problems.append(f"pratinjau: Whisper {preview_calls}, cached {cached}")
        finally:
            preview_svc.transcribe_clip_words = original_clip
            preview_svc._WORDS_CACHE.clear()

        # 5. Render separate, retry, merged: settings.audio_language sampai ke transcribe_clip_words
        render_calls = []

        def fake_render_clip(path, fallback, start, end, language=None):
            render_calls.append(language)
            return [{"word": "halo", "start": 0.1, "end": 0.5}]

        def stop_render(*args, **kwargs):
            raise RuntimeError("smoke39: encode dilewati")

        originals = (render_service.transcribe_clip_words, render_service.render_clip_to_mp4)
        render_service.transcribe_clip_words = fake_render_clip
        render_service.render_clip_to_mp4 = stop_render
        batch_ids = []
        settings = {"caption_style": "viral_pop", "title_position": "none", "enable_face_tracking": False,
                    "hardware_accel": "cpu"}
        clip = {"title": "Smoke 39", "start_time": 5.0, "end_time": 15.0}
        try:
            merged_clips = [{**clip, "start_time": 2.0, "end_time": 6.0}, {**clip, "start_time": 10.0, "end_time": 14.0}]
            for label, clips, extra, want in (
                    ("separate otomatis", [clip], {}, [None]),
                    ("separate en", [clip], {"audio_language": "en"}, ["en"]),
                    ("merged id", merged_clips, {"audio_language": "id", "render_mode": "merged"}, ["id", "id"])):
                render_calls.clear()
                r = client.post("/api/render-batch", json={**base, "clips": clips, "settings": {**settings, **extra}})
                if r.status_code != 200:
                    problems.append(f"{label}: render-batch HTTP {r.status_code}")
                    continue
                batch_ids.append(r.json()["batch_id"])
                if render_calls != want:
                    problems.append(f"{label}: bahasa ke Whisper {render_calls} (harap {want})")
                if label == "separate en":
                    render_calls.clear()
                    rr = client.post(f"/api/render-batch/{batch_ids[-1]}/retry", json={"clip_indices": [0]})
                    if rr.status_code != 200 or render_calls != ["en"]:
                        problems.append(f"retry: HTTP {rr.status_code}, bahasa ke Whisper {render_calls}")
        finally:
            render_service.transcribe_clip_words, render_service.render_clip_to_mp4 = originals
            for bid in batch_ids:
                for p in Path(render_service.TEMP_DIR).glob(f"*{bid}*"):
                    p.unlink(missing_ok=True)
                render_service.RENDER_BATCHES.pop(bid, None)
                render_service.BATCH_REQUESTS.pop(bid, None)

        report(name, not problems, "; ".join(problems) or
               "Otomatis = argumen transcribe sama dengan sebelum #39 (initial_prompt tetap), bahasa dipilih = language "
               "tanpa initial_prompt, diteruskan di analisis/pratinjau/separate/retry/merged, cache pratinjau per bahasa, 'xx' = 422")
    except Exception as e:
        report(name, False, repr(e))


def run_yt_whisper_language_check(analyze_mod, client, audio_file: Path) -> None:
    """Task #40: analisis URL YouTube tanpa caption jatuh ke Whisper dan meneruskan bahasa audio. Metadata, caption,
    unduhan audio, dan Whisper dipalsukan di analyze_mod (tanpa jaringan); Gemini palsu 429 menghentikan alur setelah transkrip."""
    name = "fallback Whisper YouTube meneruskan bahasa (#40)"
    calls = []

    def fake_metadata(url, proxy=None, cookies=None):
        return {"title": "Smoke 40", "channel": "Smoke", "duration": float(VIDEO_DURATION), "heatmap": [],
                "is_live": False, "live_status": "not_live"}

    def fake_transcript(video_id, proxy=None, on_progress=None, cookies=None):
        raise RuntimeError("smoke40: caption tidak tersedia")

    def fake_audio(video_id, output_dir=None, proxy=None, cookies=None, on_progress=None):
        return str(audio_file)

    def fake_whisper(path, progress_callback=None, language=None):
        calls.append(language)
        return [{"text": f"kalimat uji nomor {i}.", "start": float(i * 3), "duration": 2.5} for i in range(10)]

    names = ("fetch_video_metadata", "fetch_transcript", "download_youtube_audio_file", "transcribe_local_video_file")
    originals = {n: getattr(analyze_mod, n) for n in names}
    for n, fake in zip(names, (fake_metadata, fake_transcript, fake_audio, fake_whisper)):
        setattr(analyze_mod, n, fake)
    gemini = patch_gemini(analyze_mod, "rate_limit")
    problems = []
    try:
        for lang in (None, "en"):
            body = {"url": "https://www.youtube.com/watch?v=smk40aaaaaa", "duration": "15s", "api_key": "smoke-fake-key"}
            if lang:
                body["audio_language"] = lang
            events = read_sse_events(client, body)
            if not any("Whisper" in str(e.get("stage", "")) for e in events):
                errs = [e.get("error") for e in events if e.get("error")]
                problems.append(f"{lang!r}: jalur Whisper tidak dilalui ({errs[:1]})")
        if calls != [None, "en"]:
            problems.append(f"bahasa ke Whisper {calls} (harap [None, 'en'])")
        report(name, not problems, "; ".join(problems) or "tanpa bahasa = None, audio_language 'en' = 'en' di fallback Whisper")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        for n, fn in originals.items():
            setattr(analyze_mod, n, fn)
        restore_gemini(analyze_mod, gemini)


def run_posting_kit_check(client, analyze_mod, render_service, video_name: str, srt: str) -> None:
    """Task #22: posting kit per klip. Encode dipalsukan (salin segmen mentah), kata subtitle dari request
    (tanpa Whisper), kit ditulis ke EXPORTS_DIR sementara milik smoke test (dialihkan di main)."""
    name = "posting kit per klip (#22)"
    import zipfile
    from backend.services import posting_kit
    from backend.video_engine import build_subtitle_events

    problems = []
    batch_ids = []
    originals = (render_service.render_clip_to_mp4, render_service.transcribe_clip_words, render_service.write_clip_kit)

    def fake_render(video_path=None, output_mp4_path=None, **kwargs):
        shutil.copy2(video_path, output_mp4_path)

    def no_whisper(*args, **kwargs):
        raise RuntimeError("smoke22: Whisper tidak boleh dipanggil")

    def broken_kit(**kwargs):
        raise OSError("smoke22: disk penuh")

    def srt_cues(text: str):
        cues = []
        for block in text.strip().split("\n\n"):
            lines = block.splitlines()
            a, b = lines[1].split(" --> ")
            cues.append((a, b, " ".join(lines[2:])))
        return cues

    reps = [{"from": "yutub", "to": "YouTube"}]
    words = [{"word": w, "start": st, "end": en, "group": g} for w, st, en, g in [
        ("Halo", 0.2, 0.5, 0), ("yutub", 0.6, 0.9, 0), ("ini", 1.0, 1.2, 1), ("kit", 1.25, 1.7, 1), ("posting.", 1.8, 2.3, 2)]]
    scores = {"prompt_match": 80, "hook": 90, "retention": 70, "clarity": 75, "emotional_pull": 60, "payoff": 85,
              "editability": 70}
    long_caption = ("Kenapa editor profesional selalu memotong jeda di awal klip? " * 12).strip() + " #Editing #Shorts"
    clip_a = {"title": "Smoke 22: judul/klip?", "title_suggestion": "Smoke 22 Kit", "start_time": 5.0, "end_time": 15.0,
              "hook_time": 6.0, "virality_score": 79, "score_label": "fair", "scores": scores,
              "score_reason": "Alasan uji.", "needs_context": False, "key_quotes": ["halo youtube"],
              "transcript": "halo youtube ini kit posting", "caption_suggestion": long_caption,
              "hashtag_suggestion": "#Editing #ClipTips #Podcast #Viral #Creator #Growth #Tips", "subtitle_words": words}
    clip_b = {"title": "Smoke 22 tanpa skor", "start_time": 20.0, "end_time": 26.0}
    kit_meta = {"source_title": "Video Uji", "channel": "Kanal Uji", "model": "gemini-smoke", "prompt_version": "abc123",
                "custom_prompt": "fokus editing"}
    settings = {"caption_style": "viral_pop", "text_case": "uppercase", "subtitle_replacements": reps,
                "title_position": "none", "enable_face_tracking": False, "hardware_accel": "cpu"}
    base = {"video_url": f"/api/video/{video_name}", "video_id": Path(video_name).stem}

    def render(clips, extra_settings=None, meta=None):
        body = {**base, "clips": clips, "settings": {**settings, **(extra_settings or {})}}
        if meta:
            body["kit_meta"] = meta
        r = client.post("/api/render-batch", json=body)
        if r.status_code != 200:
            raise RuntimeError(f"render-batch HTTP {r.status_code}: {r.text[:120]}")
        batch_ids.append(r.json()["batch_id"])
        return render_service.RENDER_BATCHES.get(batch_ids[-1]) or {}

    try:
        render_service.render_clip_to_mp4 = fake_render
        render_service.transcribe_clip_words = no_whisper

        # 1. Klip lengkap: skor, caption panjang, kata suntingan + kamus, kit_meta
        batch = render([clip_a], meta=kit_meta)
        st = (batch.get("clips") or [{}])[0]
        kit_dir = Path(st.get("kit_dir") or "")
        if st.get("status") != "completed" or not kit_dir.is_dir():
            raise RuntimeError(f"klip A {st.get('status')}: {st.get('error_message') or st.get('kit_error')}")
        if kit_dir.parent != posting_kit.kit_batch_dir(batch_ids[-1]) or not kit_dir.name.startswith("01_"):
            problems.append(f"lokasi kit {kit_dir}")
        if any(ch in kit_dir.name for ch in ":/?"):
            problems.append(f"nama folder tidak aman: {kit_dir.name}")
        if batch.get("kit_dir") != str(kit_dir.parent):
            problems.append("kit_dir batch tidak diisi")
        want_files = {"video.mp4", "subtitles.srt", "metadata.json", "caption_tiktok.txt", "caption_reels.txt",
                      "caption_shorts.txt", "caption_x.txt"}
        got_files = {p.name for p in kit_dir.iterdir()}
        if got_files != want_files:
            problems.append(f"isi kit {sorted(got_files)}")
        if (kit_dir / "video.mp4").read_bytes() != Path(st["output_path"]).read_bytes():
            problems.append("video.mp4 berbeda dari MP4 hasil render")
        # SRT = potongan karaoke video (event per kata digabung per potongan), huruf asli
        chunks = []
        for ev in build_subtitle_events(words, "uppercase", reps):
            if chunks and chunks[-1][0] == ev["indices"]:
                chunks[-1][2] = ev["end"]
            else:
                chunks.append([ev["indices"], ev["start"], ev["end"], " ".join(ev["words"])])
        cues = srt_cues((kit_dir / "subtitles.srt").read_text(encoding="utf-8"))
        if [c[2].upper() for c in cues] != [c[3] for c in chunks]:
            problems.append(f"teks SRT {[c[2] for c in cues]} != baris video {[c[3] for c in chunks]}")
        elif [(c[0], c[1]) for c in cues] != [(posting_kit._fmt_srt_time(c[1]), posting_kit._fmt_srt_time(c[2])) for c in chunks]:
            problems.append("waktu SRT tidak sama dengan potongan karaoke")
        elif cues[0][2] != "Halo YouTube":
            problems.append(f"SRT tidak memakai huruf asli/kamus: {cues[0][2]!r}")
        meta = json.loads((kit_dir / "metadata.json").read_text(encoding="utf-8"))
        checks = {
            "scores": meta["scoring"]["scores"] == scores and meta["scoring"]["virality_score"] == 79,
            "analysis": meta["analysis"] == {"model": "gemini-smoke", "prompt_version": "abc123", "custom_prompt": "fokus editing"},
            "clip": (meta["clip"]["start_time"], meta["clip"]["end_time"], meta["clip"]["number"]) == (5.0, 15.0, 1),
            "source": meta["source"]["channel"] == "Kanal Uji" and meta["source"]["url"] is None,
            "files": set(meta["files"]) == want_files and meta["render"]["subtitle_cues"] == len(cues),
        }
        problems += [f"metadata {k} salah" for k, ok in checks.items() if not ok]
        for platform, rule in posting_kit.PLATFORM_RULES.items():
            text = (kit_dir / rule["file"]).read_text(encoding="utf-8").strip()
            body_text = text.split("\n\n", 1)[1] if platform == "shorts" else text
            n_tags = len([t for t in body_text.split() if t.startswith("#")])
            if len(body_text) > rule["max_chars"] or n_tags > rule["max_hashtags"] or "Source: Kanal Uji" not in text:
                problems.append(f"caption {platform}: {len(body_text)} karakter, {n_tags} hashtag")
            if platform == "shorts" and len(text.split("\n", 1)[0]) > rule["title_max_chars"]:
                problems.append("judul shorts terlalu panjang")
        # ZIP: MP4 seperti sebelumnya + file kit tanpa video.mp4
        with zipfile.ZipFile(Path(render_service.TEMP_DIR) / f"cheat_clip_pro_{batch_ids[-1]}.zip") as zf:
            names = zf.namelist()
        kit_names = sorted(n for n in names if n.startswith("kits/"))
        if len([n for n in names if n.endswith(".mp4")]) != 1 or any(n.endswith("video.mp4") for n in names) \
                or kit_names != sorted(f"kits/{kit_dir.name}/{f}" for f in want_files - {"video.mp4"}):
            problems.append(f"isi ZIP {names}")
        # 2. Retry menulis ulang kit
        (kit_dir / "caption_x.txt").unlink()
        r = client.post(f"/api/render-batch/{batch_ids[-1]}/retry", json={"clip_indices": [0]})
        if r.status_code != 200 or not (kit_dir / "caption_x.txt").exists():
            problems.append(f"retry tidak menulis ulang kit (HTTP {r.status_code})")

        # 3. Klip tanpa skor/caption, tanpa kit_meta, subtitle mati: kit tetap ada tanpa SRT
        batch = render([clip_b], {"caption_style": "none"})
        st = (batch.get("clips") or [{}])[0]
        kit_b = Path(st.get("kit_dir") or "")
        if st.get("status") != "completed" or not kit_b.is_dir():
            problems.append(f"klip B {st.get('status')}: {st.get('kit_error')}")
        else:
            meta_b = json.loads((kit_b / "metadata.json").read_text(encoding="utf-8"))
            if (kit_b / "subtitles.srt").exists() or meta_b["scoring"]["scores"] is not None \
                    or meta_b["analysis"]["model"] is not None:
                problems.append("klip B: SRT ada atau field tidak null")
            if "Smoke 22 tanpa skor" not in (kit_b / "caption_tiktok.txt").read_text(encoding="utf-8"):
                problems.append("klip B: caption kosong (judul tidak dipakai)")

        # 4. Kit gagal ditulis: klip tetap completed, kit_error terisi
        render_service.write_clip_kit = broken_kit
        batch = render([clip_b], {"caption_style": "none"})
        render_service.write_clip_kit = originals[2]
        st = (batch.get("clips") or [{}])[0]
        if st.get("status") != "completed" or "disk penuh" not in (st.get("kit_error") or ""):
            problems.append(f"kit gagal: status {st.get('status')}, kit_error {st.get('kit_error')!r}")

        # 5. Unit: kredit dengan URL publik, X dipotong tanpa membuang kredit/hashtag
        credit = posting_kit.credit_line("Kanal", "Judul", "https://www.youtube.com/watch?v=abc")
        caps = posting_kit.build_platform_captions(clip_a, "Judul", credit)
        if credit != "Source: Kanal https://www.youtube.com/watch?v=abc" or len(caps["x"].strip()) > 280 \
                or credit not in caps["x"] or "#editing" not in caps["x"]:
            problems.append(f"caption X/kredit: {caps['x']!r}")
        if posting_kit.credit_line("Kanal", None, "/api/video/upload_x.mp4") != "Source: Kanal":
            problems.append("kredit upload memuat path lokal")
        # Upload dimuat dari riwayat: frontend mengirim URL watch buatan; channel placeholder bukan kredit
        if posting_kit.public_source_url("https://www.youtube.com/watch?v=upload_x", "upload_x") is not None \
                or posting_kit.public_source_url("https://www.youtube.com/watch?v=abc", "abc") is None \
                or posting_kit.credit_line("Local Upload", "upload_x", None) != "" \
                or posting_kit.credit_line("", "Judul Video", None) != "Source: Judul Video":
            problems.append("URL/kredit sumber upload tidak disaring")

        # 6. prompt_version di respons analisis (mock dan jalur Gemini)
        base_an = {"url": video_name, "duration": "15s", "subtitles": srt, "subtitles_filename": "smoke.srt"}
        mock_done = [e for e in read_sse_events(client, {**base_an, "api_key": "mock"}) if e.get("done")]
        gem = patch_gemini(analyze_mod, "scored")
        try:
            real_done = [e for e in read_sse_events(client, {**base_an, "api_key": "smoke-fake-key"}) if e.get("done")]
        finally:
            restore_gemini(analyze_mod, gem)
        pv = analyze_mod.PROMPT_VERSION
        if not pv or not mock_done or not real_done or mock_done[-1]["result"].get("prompt_version") != pv \
                or real_done[-1]["result"].get("prompt_version") != pv:
            problems.append(f"prompt_version tidak ada di respons analisis ({pv!r})")
    except Exception as e:
        problems.append(repr(e))
    finally:
        (render_service.render_clip_to_mp4, render_service.transcribe_clip_words, render_service.write_clip_kit) = originals
        for bid in batch_ids:
            for p in list(Path(render_service.TEMP_DIR).glob(f"*{bid}*")) + list(Path(render_service.EXPORTS_DIR).glob(f"*{bid}*")):
                p.unlink(missing_ok=True)
            render_service.RENDER_BATCHES.pop(bid, None)
            render_service.BATCH_REQUESTS.pop(bid, None)
    report(name, not problems, "; ".join(problems) or
           "folder kit 7 file, video.mp4 = MP4 render, SRT = baris karaoke (huruf asli, kamus), metadata, batas caption, "
           "ZIP tanpa MP4 ganda, retry menulis ulang, tanpa skor/kit_meta/subtitle, kit gagal = klip tetap selesai, "
           "prompt_version di respons mock dan Gemini")


def run_yt_hd_cache_check(work_dir: Path) -> None:
    """Task #28: cache stream HD YouTube tanpa jaringan (yt-dlp dipalsukan): ID video, saklar, coba ulang,
    batas ukuran, tinggi < 720 ditolak, satu unduhan untuk dua permintaan bersamaan, cache dipakai ulang
    lewat jalur potong lokal, dan file cache tidak terdeteksi sebagai sumber lokal."""
    import threading
    name = "cache HD YouTube (#28)"
    problems = []
    from backend import video_engine as ve
    vid = "smk28_test1"
    url = f"https://www.youtube.com/watch?v={vid}"
    cache = ve.yt_hd_cache_path(vid)
    saved_env = {k: os.environ.get(k) for k in ("CHEAT_CLIP_YT_HD_CACHE", "CHEAT_CLIP_YT_HD_CACHE_MAX_GB")}
    originals = (ve._yt_hd_cache_extract, ve._yt_hd_cache_download, ve.get_effective_cookies_path, ve.get_yt_dlp_base_cmd)
    calls = {"extract": 0, "download": 0}

    class OldMethodReached(Exception):
        pass

    def set_env(key, value):
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    def clear_cache_files():
        for p in cache.parent.glob(f"{vid}*") if cache.parent.exists() else []:
            p.unlink(missing_ok=True)

    try:
        hd_src, low_src = work_dir / "yt28_hd.mp4", work_dir / "yt28_low.mp4"
        make_synthetic_video(hd_src, duration=12, size="1280x720")
        make_synthetic_video(low_src, duration=12, size="640x360")

        # 1. ID video dari berbagai bentuk URL; selain YouTube = None
        ids = {
            "https://www.youtube.com/watch?v=aqz-KE-bpKQ&t=30s": "aqz-KE-bpKQ", "https://youtu.be/aqz-KE-bpKQ?si=x": "aqz-KE-bpKQ",
            "https://www.youtube.com/shorts/aqz-KE-bpKQ": "aqz-KE-bpKQ", "aqz-KE-bpKQ": "aqz-KE-bpKQ",
            "/api/video/upload_abc.mp4": None, "https://drive.google.com/file/d/abc/view": None, "": None,
        }
        for u, want in ids.items():
            if ve.extract_youtube_video_id(u) != want:
                problems.append(f"ID {u!r} -> {ve.extract_youtube_video_id(u)!r} (harap {want!r})")
        if cache.parent.name != ve.YT_HD_CACHE_SUBDIR or cache.parent.parent != Path(ve.TEMP_DIR):
            problems.append(f"cache tidak di TEMP_DIR/{ve.YT_HD_CACHE_SUBDIR}: {cache}")

        plan = {"format_id": "137+140", "height": 1080, "vcodec": "avc1.640028", "size": 50 * 1024 ** 2, "duration": 12.0}
        state = {"plans": [], "src": hd_src, "sleep": 0.0}

        def fake_extract(base_cmd, u, info_path, timeout):
            calls["extract"] += 1
            info_path.write_text("{}", encoding="utf-8")
            p = state["plans"].pop(0) if state["plans"] else plan
            return (p, "") if p else (None, "format HD tidak tersedia (tinggi 360)")

        def fake_download(base_cmd, info_path, format_id, out_path, timeout):
            calls["download"] += 1
            time.sleep(state["sleep"])
            shutil.copy2(state["src"], out_path)
            return ""

        def reset(**kw):
            clear_cache_files()
            calls.update(extract=0, download=0)
            state.update({"plans": [], "src": hd_src, "sleep": 0.0, **kw})

        ve._yt_hd_cache_extract, ve._yt_hd_cache_download = fake_extract, fake_download
        # 1b. Pemecah tantangan JS (yt-dlp-ejs) hanya untuk cache HD; pemanggil lain = --no-js-runtimes (perilaku sebelum #28)
        default_cmd = ve.get_yt_dlp_base_cmd(include_cookies=False)
        hd_cmd = ve.get_yt_dlp_base_cmd(include_cookies=False, solve_js_challenges=True)
        if "--no-js-runtimes" not in default_cmd or "--js-runtimes" in default_cmd:
            problems.append(f"base cmd default masih menyalakan runtime JS: {default_cmd}")
        if "--no-js-runtimes" in hd_cmd or (shutil.which("node") or shutil.which("deno")) and "--js-runtimes" not in hd_cmd:
            problems.append(f"base cmd cache HD tanpa runtime JS: {hd_cmd}")
        base_calls = []
        ve.get_effective_cookies_path = lambda: None
        ve.get_yt_dlp_base_cmd = lambda include_cookies=True, cookies_path=None, solve_js_challenges=False: (
            base_calls.append(solve_js_challenges) or ["yt-dlp-palsu"])
        set_env("CHEAT_CLIP_YT_HD_CACHE", None)
        set_env("CHEAT_CLIP_YT_HD_CACHE_MAX_GB", None)

        # 2. Saklar mati: helper tidak memanggil yt-dlp
        reset()
        for off in ("0", "false", "OFF"):
            os.environ["CHEAT_CLIP_YT_HD_CACHE"] = off
            if ve.get_youtube_hd_cache(url) is not None or calls["extract"]:
                problems.append(f"saklar {off!r} tidak mematikan cache")
        set_env("CHEAT_CLIP_YT_HD_CACHE", None)

        # 3. HD tidak tersedia dua kali: coba ulang sekali lalu None
        reset(plans=[None, None])
        if ve.get_youtube_hd_cache(url) is not None or calls != {"extract": 2, "download": 0}:
            problems.append(f"HD tidak tersedia: {calls}")
        # 4. Pertama 360p saja, percobaan ulang HD: tetap dapat cache
        reset(plans=[None, plan])
        got = ve.get_youtube_hd_cache(url)
        if got != cache or calls != {"extract": 2, "download": 1} or not cache.exists():
            problems.append(f"coba ulang: {got}, {calls}")
        if not base_calls or not all(base_calls):
            problems.append(f"helper cache tidak menyalakan solve_js_challenges: {base_calls}")
        # 5. Dipakai ulang tanpa ekstraksi/unduh
        calls.update(extract=0, download=0)
        if ve.get_youtube_hd_cache(url) != cache or calls != {"extract": 0, "download": 0}:
            problems.append(f"pakai ulang: {calls}")
        # 6. Batas ukuran
        reset(plans=[{**plan, "size": 3 * 1024 ** 3}])
        if ve.get_youtube_hd_cache(url) is not None or calls["download"]:
            problems.append(f"batas ukuran 2 GB tidak dihormati: {calls}")
        os.environ["CHEAT_CLIP_YT_HD_CACHE_MAX_GB"] = "0.01"
        reset()
        if ve.get_youtube_hd_cache(url) is not None or calls["download"]:
            problems.append("CHEAT_CLIP_YT_HD_CACHE_MAX_GB diabaikan")
        set_env("CHEAT_CLIP_YT_HD_CACHE_MAX_GB", None)
        # 7. Hasil unduhan di bawah 720p ditolak, sisa file sementara dibersihkan
        reset(src=low_src)
        leftovers = None
        if ve.get_youtube_hd_cache(url) is None:
            leftovers = [p.name for p in cache.parent.glob(f"{vid}*")]
        if leftovers is None or leftovers:
            problems.append(f"unduhan 360p diterima atau sisa file: {leftovers}")
        # 8. Dua permintaan bersamaan = satu unduhan
        reset(sleep=1.0)
        outs = []
        threads = [threading.Thread(target=lambda: outs.append(ve.get_youtube_hd_cache(url))) for _ in range(2)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        if calls["download"] != 1 or outs != [cache, cache]:
            problems.append(f"bersamaan: {calls['download']} unduhan, hasil {outs}")

        # 9. download_clip_segment memotong dari cache lewat jalur lokal (tanpa metode lama)
        def old_method(*a, **k):
            raise OldMethodReached()

        ve.get_yt_dlp_base_cmd = old_method
        ve._yt_hd_cache_extract = lambda *a, **k: (_ for _ in ()).throw(OldMethodReached())
        seg_name = f"smoke28_{uuid.uuid4().hex[:6]}.mp4"
        try:
            seg = Path(ve.download_clip_segment(url, 2.0, 6.0, seg_name))
            info = ffprobe_video(seg)
            if info.get("height") != 720 or abs(float(info.get("duration") or 0) - 4.0) > 0.5:
                problems.append(f"segmen dari cache: {info}")
            seg.unlink(missing_ok=True)
        except OldMethodReached:
            problems.append("segmen memakai metode lama padahal cache valid")
        # 10. Saklar mati: metode lama dipakai, dan file cache tidak dianggap sumber lokal (ID polos)
        os.environ["CHEAT_CLIP_YT_HD_CACHE"] = "0"
        for src in (url, vid):
            try:
                ve.download_clip_segment(src, 2.0, 6.0, seg_name)
                problems.append(f"{src!r}: metode lama tidak dipanggil (cache terdeteksi sebagai sumber lokal?)")
            except OldMethodReached:
                pass
        (Path(ve.TEMP_DIR) / seg_name).unlink(missing_ok=True)
        # 11. Format: 1080p maks, 720p min, H.264 diutamakan
        f = ve.YT_HD_CACHE_FORMAT
        if not (f.startswith("bv*[height<=1080][height>=720][vcodec^=avc1]") and all("[height>=720]" in alt for alt in f.split("/"))):
            problems.append(f"format: {f}")

        report(name, not problems, "; ".join(problems) or
               "ID dari URL, runtime JS hanya untuk cache (default --no-js-runtimes), saklar 0 mematikan, HD tidak tersedia = coba ulang lalu metode lama, batas ukuran, <720p ditolak, "
               "2 permintaan = 1 unduhan, cache dipotong lokal tanpa metode lama, cache tidak terdeteksi sebagai sumber lokal")
    except Exception as e:
        report(name, False, repr(e))
    finally:
        ve._yt_hd_cache_extract, ve._yt_hd_cache_download, ve.get_effective_cookies_path, ve.get_yt_dlp_base_cmd = originals
        for k, v in saved_env.items():
            set_env(k, v)
        clear_cache_files()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Cheat Clip PRO")
    parser.add_argument("--keep", action="store_true", help="Jangan hapus video sintetis dan hasil render")
    parser.add_argument("--gpu", action="store_true", help="Render dengan hardware_accel=auto (default: cpu)")
    args = parser.parse_args()

    print("Menyiapkan backend (impor modul, deteksi FFmpeg dan encoder)...", flush=True)
    try:
        import backend.config as config  # efek samping: PATH FFmpeg, folder kerja, uji encoder
    except Exception as e:
        print(f"[FAIL] impor backend.config: {e!r}")
        return 1

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("[FAIL] FFmpeg/ffprobe tidak ditemukan di PATH. Pasang dengan: winget install Gyan.FFmpeg")
        return 1

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.routers.analyze as analyze_mod
    from backend.routers.render import router as render_router
    from backend.services import render_service

    app = FastAPI()
    app.include_router(analyze_mod.router)
    app.include_router(render_router)
    client = TestClient(app)

    work_dir = Path(tempfile.mkdtemp(prefix="cheatclip_smoke_"))
    video_name = f"upload_smoke_{uuid.uuid4().hex[:8]}.mp4"
    video_path = config.UPLOADS_DIR / video_name
    batch_id = None
    # Task #22: semua posting kit dari smoke test ditulis ke folder sementara, bukan ~/CheatClip/kits
    from backend.services import posting_kit
    original_kit_root = posting_kit.EXPORTS_DIR
    posting_kit.EXPORTS_DIR = work_dir / "exports"
    try:
        try:
            make_synthetic_video(work_dir / video_name)
            config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work_dir / video_name, video_path)
            report("video sintetis", True, f"{VIDEO_DURATION}s 1280x720 -> {video_path.name}")
        except Exception as e:
            report("video sintetis", False, repr(e))
            return 1

        run_analyze_checks(client, analyze_mod, video_name, build_srt())
        run_fallback_overlap_check(client, analyze_mod, config.UPLOADS_DIR, work_dir)
        run_audio_heatmap_check(work_dir / video_name, work_dir)
        run_score_check(client, analyze_mod, video_name, build_srt())
        run_heatmap_prompt_check(client, analyze_mod, video_name, build_srt())
        batch_id = run_render_check(
            client, render_service, config.is_valid_mp4, config.EXPORTS_DIR, video_name, args.gpu
        )
        run_cleanup_check(config)
        run_admin_check()
        run_choices_check(config)
        run_guardrail_check()
        run_subtitle_fix_check(work_dir)
        run_subtitle_preview_check(client, config, video_name, work_dir)
        run_subtitle_edit_check(client, render_service, video_name)
        run_whisper_model_name_check()
        run_audio_language_check(client, analyze_mod, render_service, video_name, work_dir / video_name)
        run_yt_hd_cache_check(work_dir)
        run_yt_whisper_language_check(analyze_mod, client, work_dir / video_name)
        run_posting_kit_check(client, analyze_mod, render_service, video_name, build_srt())
    finally:
        posting_kit.EXPORTS_DIR = original_kit_root
        if args.keep:
            print(f"--keep: file disimpan ({video_path}, batch {batch_id})")
        else:
            cleanup([work_dir, video_path], batch_id, config.TEMP_DIR, config.EXPORTS_DIR)

    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} cek lulus.")
    if failed:
        print("Gagal: " + ", ".join(failed))
        return 1
    print("SMOKE TEST LULUS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
