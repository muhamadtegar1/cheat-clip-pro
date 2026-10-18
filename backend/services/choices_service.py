"""Task #35: penyimpanan permanen pilihan pemilik per klip (Pakai/Lewati).

Satu file JSON di EXPORTS_DIR/data/clip_choices.json (di luar folder cache, tidak pernah disentuh auto-cleanup).
Tulis atomik (file sementara + os.replace) di bawah kunci thread. File yang tidak bisa dibaca dibackup, tidak
ditimpa diam-diam.
"""
import csv
import io
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import backend.config as config
from backend.config import logger
from backend.schemas.choices import ClipChoiceRecord, ClipChoiceRequest

CHOICES_FILENAME = "clip_choices.json"
FILE_VERSION = 1
SCORE_DIMENSIONS = ["prompt_match", "hook", "retention", "clarity", "emotional_pull", "payoff", "editability"]
CSV_COLUMNS = [
    "video_id", "video_title", "video_url", "source_type", "start_time", "end_time", "duration", "clip_title",
    "choice", "reason", "virality_score", "rank", "rank_total", "tier", "needs_context",
    *[f"score_{d}" for d in SCORE_DIMENSIONS],
    "heatmap_avg", "heatmap_source", "model", "created_at", "updated_at",
]

_lock = threading.Lock()


def choices_file_path() -> Path:
    # Dibaca saat dipanggil (bukan saat impor) agar EXPORTS_DIR bisa diarahkan ulang (smoke test).
    return Path(config.EXPORTS_DIR) / "data" / CHOICES_FILENAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _same_clip(record: dict, video_id: str, start_time: float, end_time: float) -> bool:
    return (
        record.get("video_id") == video_id
        and round(float(record.get("start_time", -1)), 3) == round(float(start_time), 3)
        and round(float(record.get("end_time", -1)), 3) == round(float(end_time), 3)
    )


def _load_records(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            raise ValueError("format tidak dikenal (tanpa daftar 'records')")
        return [r for r in records if isinstance(r, dict)]
    except Exception as e:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"clip_choices.corrupt-{stamp}.json")
        try:
            os.replace(path, backup)
            logger.warning(f"[Clip Choices] {path} tidak bisa dibaca ({e}); dipindah ke {backup}, mulai kosong.")
        except OSError as move_err:
            logger.error(f"[Clip Choices] {path} rusak dan gagal dibackup: {move_err}")
            raise RuntimeError("File pilihan klip rusak dan tidak bisa dibackup") from move_err
        return []


def _write_records(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": FILE_VERSION, "records": records}, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def save_choice(req: ClipChoiceRequest) -> dict:
    with _lock:
        path = choices_file_path()
        records = _load_records(path)
        now = _now()
        data = req.model_dump()
        data["reason"] = (data.get("reason") or "").strip() or None
        for i, rec in enumerate(records):
            if _same_clip(rec, req.video_id, req.start_time, req.end_time):
                record = ClipChoiceRecord(**data, created_at=rec.get("created_at") or now, updated_at=now).model_dump()
                records[i] = record
                break
        else:
            record = ClipChoiceRecord(**data, created_at=now, updated_at=now).model_dump()
            records.append(record)
        _write_records(path, records)
        return record


def delete_choice(video_id: str, start_time: float, end_time: float) -> bool:
    with _lock:
        path = choices_file_path()
        records = _load_records(path)
        kept = [r for r in records if not _same_clip(r, video_id, start_time, end_time)]
        if len(kept) == len(records):
            return False
        _write_records(path, kept)
        return True


def list_choices(video_id: Optional[str] = None) -> List[dict]:
    with _lock:
        records = _load_records(choices_file_path())
    if video_id is not None:
        records = [r for r in records if r.get("video_id") == video_id]
    return records


def export_csv(records: List[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for rec in records:
        row = {k: rec.get(k) for k in CSV_COLUMNS}
        scores = rec.get("scores") or {}
        for d in SCORE_DIMENSIONS:
            row[f"score_{d}"] = scores.get(d)
        try:
            row["duration"] = round(float(rec["end_time"]) - float(rec["start_time"]), 3)
        except (KeyError, TypeError, ValueError):
            row["duration"] = None
        writer.writerow(row)
    # BOM agar Excel membuka UTF-8 dengan benar
    return "﻿" + buf.getvalue()
