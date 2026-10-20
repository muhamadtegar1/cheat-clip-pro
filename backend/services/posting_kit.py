"""
Task #22: posting kit per klip. Satu folder siap unggah per klip yang selesai dirender (mode separate):
video.mp4 (hardlink ke MP4 hasil render), subtitles.srt, metadata.json, dan caption per platform.
Caption disusun dari saran Gemini yang sudah ada (tanpa memanggil Gemini lagi).
"""
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import EXPORTS_DIR
from backend.video_engine import build_subtitle_events

KIT_SCHEMA_VERSION = 1
KITS_DIRNAME = "kits"

# Aturan per platform. Nilai awal konservatif: cek ulang terhadap aturan platform terbaru (bisa berubah).
# Nanti bisa ditimpa Campaign Profile (#20).
PLATFORM_RULES: Dict[str, Dict[str, Any]] = {
    "tiktok": {"file": "caption_tiktok.txt", "max_chars": 2200, "max_hashtags": 5},
    "reels": {"file": "caption_reels.txt", "max_chars": 2200, "max_hashtags": 5},
    "shorts": {"file": "caption_shorts.txt", "max_chars": 5000, "max_hashtags": 3, "title_max_chars": 100},
    "x": {"file": "caption_x.txt", "max_chars": 280, "max_hashtags": 2},
}

_UNSAFE_CHARS = re.compile(r'[\\/*?:"<>|\x00-\x1f]')
_HASHTAG = re.compile(r"#(\w+)", re.UNICODE)


def safe_name(text: str, max_len: int = 60) -> str:
    """Nama folder aman untuk Windows: tanpa karakter terlarang, spasi dirapikan, tanpa titik/spasi di ujung."""
    clean = _UNSAFE_CHARS.sub("", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()[:max_len].strip(" .")
    return clean or "clip"


def kit_batch_dir(batch_id: str) -> Path:
    """EXPORTS_DIR/kits/<YYYY-MM-DD>_<batch_id>; tanggal dari epoch di batch_id (batch_<epoch>_<hex>)."""
    match = re.match(r"batch_(\d+)_", batch_id)
    stamp = int(match.group(1)) if match else int(time.time())
    day = datetime.fromtimestamp(stamp).strftime("%Y-%m-%d")
    return EXPORTS_DIR / KITS_DIRNAME / f"{day}_{safe_name(batch_id, 80)}"


def clip_kit_dirname(idx: int, title: str) -> str:
    return f"{idx + 1:02d}_{safe_name(title)}"


def _fmt_srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(words: Optional[List[Dict[str, Any]]], word_replacements: Optional[List[Any]] = None) -> str:
    """
    SRT dari kata yang dipakai render. Baris = potongan karaoke video (build_subtitle_events, kamus #11),
    event per kata aktif digabung per potongan. Huruf asli (bukan text_case video). "" bila tanpa kata.
    """
    if not words:
        return ""
    events = build_subtitle_events(words, text_case="original", word_replacements=word_replacements)
    cues: List[Dict[str, Any]] = []
    for ev in events:
        key = tuple(ev["indices"])
        if cues and cues[-1]["key"] == key:
            cues[-1]["end"] = max(cues[-1]["end"], ev["end"])
            continue
        cues.append({"key": key, "start": ev["start"], "end": ev["end"], "text": " ".join(ev["words"])})
    blocks = [
        f"{i}\n{_fmt_srt_time(c['start'])} --> {_fmt_srt_time(c['end'])}\n{c['text']}"
        for i, c in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _hashtags(*texts: str) -> List[str]:
    seen: List[str] = []
    for text in texts:
        for tag in _HASHTAG.findall(text or ""):
            tag = tag.lower()
            if tag and tag not in seen:
                seen.append(tag)
    return [f"#{t}" for t in seen]


def _truncate(text: str, limit: int) -> str:
    """Potong di batas kata, akhiri dengan elipsis bila dipotong."""
    text = text.strip()
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - 1)]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:-") + "…"


# Nama channel buatan analyze.py untuk sumber lokal/Drive: bukan kredit yang berarti
PLACEHOLDER_CHANNELS = {"local upload", "google drive"}


def public_source_url(source_url: Optional[str], video_id: str = "") -> Optional[str]:
    """URL sumber yang boleh ditulis di kit: hanya http dan bukan video upload/Drive (frontend bisa mengirim
    URL watch YouTube buatan untuk ID upload_/gdrive_ yang dimuat dari riwayat)."""
    url = (source_url or "").strip()
    if not url.startswith("http") or video_id.startswith(("upload_", "gdrive_")):
        return None
    return url


def credit_line(channel: Optional[str], source_title: Optional[str], source_url: Optional[str]) -> str:
    """Baris kredit sumber; URL hanya untuk sumber publik (http). Channel placeholder tidak dipakai."""
    name = (channel or "").strip()
    if name.lower() in PLACEHOLDER_CHANNELS:
        name = ""  # judul upload/Drive biasanya nama file, juga tidak dipakai
    elif not name:
        name = (source_title or "").strip()
    url = (source_url or "").strip() if (source_url or "").startswith("http") else ""
    parts = [p for p in (name, url) if p]
    return f"Source: {' '.join(parts)}" if parts else ""


def build_platform_captions(clip: Dict[str, Any], title: str, credit: str) -> Dict[str, str]:
    """Caption per platform dari caption_suggestion + hashtag_suggestion + judul, mematuhi PLATFORM_RULES."""
    raw_caption = (clip.get("caption_suggestion") or "").strip()
    tags = _hashtags(clip.get("hashtag_suggestion") or "", raw_caption)
    body = re.sub(r"\s+", " ", _HASHTAG.sub("", raw_caption)).strip() or (title or "").strip()
    out: Dict[str, str] = {}
    for platform, rule in PLATFORM_RULES.items():
        limit = rule["max_chars"]
        tag_line = " ".join(tags[: rule["max_hashtags"]])
        # Kredit dan hashtag dipertahankan; badan caption yang dipotong bila perlu
        tail = "\n\n".join(p for p in (credit, tag_line) if p)
        tail = tail[:limit]
        room = limit - len(tail) - (2 if tail else 0)
        text = "\n\n".join(p for p in (_truncate(body, room), tail) if p)
        if platform == "shorts":
            short_title = _truncate(title or body, rule["title_max_chars"])
            text = f"{short_title}\n\n{text}"
        out[platform] = text.strip() + "\n"
    return out


def _link_or_copy(src: Path, dst: Path) -> str:
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def _scores(clip: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scores = clip.get("scores")
    return scores if isinstance(scores, dict) else None


def build_metadata(
    *,
    batch_id: str,
    idx: int,
    clip: Dict[str, Any],
    display_title: str,
    settings: Any,
    video_id: str,
    source_url: Optional[str],
    kit_meta: Optional[Dict[str, Any]],
    files: List[str],
    srt_cues: int,
) -> Dict[str, Any]:
    meta = kit_meta or {}
    start = float(clip.get("start_time", 0.0))
    end = float(clip.get("end_time", start))
    return {
        "schema_version": KIT_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "batch_id": batch_id,
        "source": {
            "video_id": video_id,
            "url": public_source_url(source_url, video_id),
            "title": meta.get("source_title"),
            "channel": meta.get("channel"),
        },
        "clip": {
            "number": idx + 1,
            "start_time": start,
            "end_time": end,
            "duration": round(max(0.0, end - start), 3),
            "title": display_title,
            "hook_time": clip.get("hook_time"),
            "key_quotes": clip.get("key_quotes") or [],
            "transcript": clip.get("transcript"),
            "title_suggestion": clip.get("title_suggestion"),
            "caption_suggestion": clip.get("caption_suggestion"),
            "hashtag_suggestion": clip.get("hashtag_suggestion"),
        },
        "scoring": {
            "virality_score": clip.get("virality_score"),
            "score_label": clip.get("score_label"),
            "scores": _scores(clip),
            "score_reason": clip.get("score_reason"),
            "needs_context": clip.get("needs_context"),
        },
        "analysis": {
            "model": meta.get("model"),
            "prompt_version": meta.get("prompt_version"),
            "custom_prompt": meta.get("custom_prompt"),
        },
        "render": {
            "aspect_ratio": getattr(settings, "aspect_ratio", None),
            "caption_style": getattr(settings, "caption_style", None),
            "text_case": getattr(settings, "text_case", None),
            "audio_language": getattr(settings, "audio_language", None),
            "hardware_accel": getattr(settings, "hardware_accel", None),
            "subtitle_cues": srt_cues,
        },
        "files": files,
    }


def write_clip_kit(
    *,
    batch_id: str,
    idx: int,
    clip: Dict[str, Any],
    display_title: str,
    mp4_path: str,
    words: Optional[List[Dict[str, Any]]],
    settings: Any,
    video_id: str,
    source_url: Optional[str],
    kit_meta: Optional[Dict[str, Any]] = None,
) -> Path:
    """Tulis (atau timpa) folder kit satu klip; mengembalikan path folder. Galat dilempar ke pemanggil."""
    meta = kit_meta or {}
    kit_dir = kit_batch_dir(batch_id) / clip_kit_dirname(idx, display_title)
    kit_dir.mkdir(parents=True, exist_ok=True)
    files: List[str] = []

    _link_or_copy(Path(mp4_path), kit_dir / "video.mp4")
    files.append("video.mp4")

    srt_path = kit_dir / "subtitles.srt"
    srt = build_srt(words, getattr(settings, "subtitle_replacements", None))
    if srt:
        srt_path.write_text(srt, encoding="utf-8")
        files.append("subtitles.srt")
    elif srt_path.exists():
        srt_path.unlink()  # retry tanpa subtitle: jangan sisakan SRT lama

    credit = credit_line(meta.get("channel"), meta.get("source_title"), public_source_url(source_url, video_id))
    for platform, text in build_platform_captions(clip, display_title, credit).items():
        name = PLATFORM_RULES[platform]["file"]
        (kit_dir / name).write_text(text, encoding="utf-8")
        files.append(name)

    files.append("metadata.json")
    metadata = build_metadata(
        batch_id=batch_id, idx=idx, clip=clip, display_title=display_title, settings=settings,
        video_id=video_id, source_url=source_url, kit_meta=meta, files=files,
        srt_cues=srt.count(" --> ") if srt else 0,
    )
    (kit_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return kit_dir
