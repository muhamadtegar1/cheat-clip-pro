"""Task #36a: subtitle asli (Whisper per kata) untuk pratinjau Clip Studio sebelum render.

Memakai jalur yang sama dengan render: normalisasi URL sumber, download_clip_segment, transcribe_clip_words,
lalu build_subtitle_events (pemotongan yang juga dipakai generate_ass_file), sehingga pratinjau sama dengan video.
Kata mentah di-cache di memori per (video, rentang klip); kamus koreksi (#11) dan text_case diterapkan tiap
permintaan tanpa Whisper ulang. Whisper/FFmpeg memakai _RENDER_SEMAPHORE agar tidak berjalan bersamaan dengan render.
"""
import asyncio
import os
import time
import uuid
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from backend.config import TEMP_DIR, download_clip_segment, is_valid_mp4, logger, transcribe_clip_words
from backend.schemas.render import PreviewSubtitlesRequest
from backend.services.render_service import _RENDER_SEMAPHORE, resolve_source_url
from backend.video_engine import build_subtitle_events

PREVIEW_CACHE_MAX = 50
# kunci: (video_id, start, end) -> {"words": [...], "source": "whisper" | "transcript" | "none"}
_WORDS_CACHE: "OrderedDict[Tuple[str, float, float], Dict[str, Any]]" = OrderedDict()


def _cache_key(video_id: str, start_time: float, end_time: float) -> Tuple[str, float, float]:
    return (video_id, round(float(start_time), 3), round(float(end_time), 3))


def _cache_put(key: Tuple[str, float, float], entry: Dict[str, Any]) -> None:
    _WORDS_CACHE[key] = entry
    _WORDS_CACHE.move_to_end(key)
    while len(_WORDS_CACHE) > PREVIEW_CACHE_MAX:
        _WORDS_CACHE.popitem(last=False)


def _transcribe_segment(raw_path: str, transcript: Optional[List[Dict[str, Any]]],
                        start_time: float, end_time: float) -> Tuple[List[Dict[str, Any]], str]:
    """Sama dengan transcribe_clip_words di render, tetapi mencatat sumber kata (Whisper atau transkrip)."""
    words = transcribe_clip_words(raw_path, None, start_time, end_time)
    if words:
        return words, "whisper"
    # Path kosong: Whisper dilewati, langsung fallback transkrip seperti di render
    words = transcribe_clip_words("", transcript, start_time, end_time) if transcript else []
    return words, ("transcript" if words else "none")


async def _load_words(req: PreviewSubtitlesRequest) -> Tuple[Dict[str, Any], bool]:
    key = _cache_key(req.video_id, req.start_time, req.end_time)
    cached = _WORDS_CACHE.get(key)
    if cached is not None:
        _WORDS_CACHE.move_to_end(key)
        return cached, True

    async with _RENDER_SEMAPHORE:
        cached = _WORDS_CACHE.get(key)
        if cached is not None:
            return cached, True

        target_url = resolve_source_url(req.video_url, req.video_id)
        seg_filename = f"preview_{uuid.uuid4().hex[:10]}_raw.mp4"
        raw_path = None
        try:
            raw_path = await asyncio.to_thread(
                download_clip_segment, target_url, req.start_time, req.end_time, seg_filename, req.cookies
            )
            if not raw_path or not os.path.exists(raw_path) or not is_valid_mp4(raw_path):
                raise RuntimeError("Segmen klip gagal diunduh atau rusak")
            words, source = await asyncio.to_thread(
                _transcribe_segment, raw_path, req.transcript, req.start_time, req.end_time
            )
        finally:
            for path in {raw_path, str(TEMP_DIR / seg_filename)}:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as e:
                        logger.warning(f"[Subtitle Preview] Gagal menghapus segmen {path}: {e}")

        entry = {"words": words, "source": source}
        _cache_put(key, entry)
        return entry, False


async def preview_subtitles(req: PreviewSubtitlesRequest) -> Dict[str, Any]:
    if req.end_time <= req.start_time:
        raise ValueError("end_time harus lebih besar dari start_time")
    t0 = time.time()
    entry, cached = await _load_words(req)
    events = build_subtitle_events(entry["words"], req.text_case or "uppercase", req.subtitle_replacements)
    return {
        "video_id": req.video_id,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "source": entry["source"],
        "cached": cached,
        "elapsed_seconds": round(time.time() - t0, 2),
        "words": entry["words"],
        "events": events,
    }
