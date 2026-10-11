"""Smoke test satu perintah untuk Cheat Clip PRO (task 17a).

Jalankan dari root repo:
    venv\\Scripts\\python.exe scripts\\smoke_test.py [--keep] [--gpu]

Cek yang dijalankan:
  1. POST /api/analyze dengan key `mock` pada video sintetis + SRT manual (tanpa Whisper).
  2. RATE_LIMIT: klien Gemini palsu selalu melempar 429, endpoint harus mengirim error status 429.
  3. MALFORMED_JSON: klien palsu mengembalikan JSON terpotong, parser toleran harus tetap menghasilkan klip.
  4. POST /api/render-batch untuk 1 klip, output MP4 valid 1080x1920 dengan durasi yang benar.

Skrip tidak mengimpor `backend.main`, jadi daemon auto-cleanup tidak berjalan.
Semua file yang dibuat skrip ini dihapus di akhir (kecuali dengan --keep).
"""

import argparse
import json
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


def build_srt() -> str:
    blocks = []
    for i, (start, end, text) in enumerate(SRT_LINES, 1):
        blocks.append(f"{i}\n{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n{text}")
    return "\n\n".join(blocks) + "\n"


def make_synthetic_video(path: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate=30:duration={VIDEO_DURATION}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={VIDEO_DURATION}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
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
    """Pengganti `genai.Client` untuk skenario error. `mode` = 'rate_limit' atau 'malformed_json'."""

    calls = []

    def __init__(self, mode: str):
        self.mode = mode
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model=None, contents=None, config=None):
        FakeGeminiClient.calls.append(model)
        if self.mode == "rate_limit":
            raise Exception("429 RESOURCE_EXHAUSTED. Quota exceeded for this API key (smoke test).")
        return SimpleNamespace(parsed=None, text=MALFORMED_JSON)


def patch_gemini(analyze_mod, mode: str):
    original = (analyze_mod.genai, analyze_mod.get_flash_models_for_key)
    analyze_mod.genai = SimpleNamespace(Client=lambda *a, **kw: FakeGeminiClient(mode))
    analyze_mod.get_flash_models_for_key = lambda client: []
    FakeGeminiClient.calls = []
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
        detail = "; ".join(problems) or f"1080x1920, {info['duration']:.2f}s, {time.time() - t0:.0f}s render"
        report(name, not problems, detail)
        return batch_id
    except Exception as e:
        report(name, False, repr(e))
        return None


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
        batch_id = run_render_check(
            client, render_service, config.is_valid_mp4, config.EXPORTS_DIR, video_name, args.gpu
        )
    finally:
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
