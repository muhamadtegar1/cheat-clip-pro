"""Guardrail output analisis AI (task #12).

Fungsi murni tanpa I/O dan tanpa Gemini. Dipanggil `analyze_video` setelah klip diparse, sebelum `ViralClip` dibuat:
- timestamp dijepit ke rentang pencarian, klip yang jadi terlalu pendek dibuang, hook di luar klip diperbaiki;
- kutipan dicocokkan ke transkrip di sekitar klip, yang tidak ada dibuang, klip tanpa kutipan diisi kalimat asli;
- klip dengan overlap > MERGE_OVERLAP digabung (skor tertinggi dipertahankan), REVIEW_OVERLAP-MERGE_OVERLAP ditandai.
"""

import difflib
import re
from typing import Dict, List, Optional, Tuple

QUOTE_MATCH = 0.85      # rasio kemiripan minimum (sama dengan penilai golden fixtures)
QUOTE_WINDOW = 5.0      # detik toleransi di luar rentang klip saat mencari kutipan
MIN_CLIP_SECONDS = 5.0  # klip lebih pendek dari ini setelah dijepit dibuang
MERGE_OVERLAP = 0.70    # overlap > 70% dari klip yang lebih pendek: digabung
REVIEW_OVERLAP = 0.40   # overlap 40-70%: dipertahankan, ditandai di guardrail_notes
FILL_MAX_CHARS = 200    # panjang maksimum kalimat pengganti kutipan


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\[[^\]]*\]", " ", text)          # [Music], [Tertawa]
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def quote_fragments(quote: str) -> List[str]:
    """Kutipan bersambung ("...", "…") dipecah per potongan; potongan < 3 kata diabaikan bila ada yang lebih panjang."""
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


def lines_in(transcript: List[dict], start: float, end: float, pad: float = 0.0) -> List[dict]:
    return [l for l in transcript
            if float(l.get("end", 0.0)) >= start - pad and float(l.get("start", 0.0)) <= end + pad]


def quote_is_grounded(quote: str, transcript: List[dict], start: float, end: float) -> bool:
    frags = quote_fragments(quote)
    if not frags:
        return False
    hay = normalize_text(" ".join(str(l.get("text", "")) for l in lines_in(transcript, start, end, QUOTE_WINDOW)))
    return all(text_contains(hay, f) for f in frags)


def fill_quote(transcript: List[dict], start: float, end: float) -> Optional[str]:
    """Kalimat asli pengganti: baris di dalam klip dengan engagement tertinggi, lalu yang terpanjang."""
    candidates = [l for l in lines_in(transcript, start, end)
                  if float(l.get("start", 0.0)) >= start - 0.5 and float(l.get("end", 0.0)) <= end + 0.5
                  and len(normalize_text(str(l.get("text", ""))).split()) >= 3]
    if not candidates:
        candidates = [l for l in lines_in(transcript, start, end) if normalize_text(str(l.get("text", "")))]
    if not candidates:
        return None
    best = max(candidates, key=lambda l: (float(l.get("engagement") or 0.0), len(str(l.get("text", "")))))
    text = " ".join(str(best.get("text", "")).split())
    return text[:FILL_MAX_CHARS].rstrip() if text else None


def _as_float(value) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def apply_guardrails(clips: List[dict], transcript: List[dict], start_bound: float,
                     end_bound: float) -> Tuple[List[dict], Dict[str, int]]:
    """Kembalikan (klip yang lolos, ringkasan). Klip masukan tidak diubah; setiap klip keluaran punya `guardrail_notes`."""
    summary = {"clips_in": len(clips), "dropped_invalid": 0, "merged": 0, "flagged_overlap": 0,
               "quotes_dropped": 0, "quotes_filled": 0, "hook_fixed": 0, "clamped": 0}

    # 1. Timestamp
    valid: List[dict] = []
    for raw in clips:
        clip = dict(raw)
        clip["guardrail_notes"] = list(raw.get("guardrail_notes") or [])
        s, e = _as_float(clip.get("start_time")), _as_float(clip.get("end_time"))
        if s is None or e is None:
            summary["dropped_invalid"] += 1
            continue
        if s > e:
            s, e = e, s
        cs, ce = max(start_bound, s), min(end_bound, e)
        if ce - cs < MIN_CLIP_SECONDS:
            summary["dropped_invalid"] += 1
            continue
        if (cs, ce) != (s, e):
            summary["clamped"] += 1
            clip["guardrail_notes"].append(f"timestamp adjusted from {s:.1f}-{e:.1f}s to {cs:.1f}-{ce:.1f}s")
        clip["start_time"], clip["end_time"] = cs, ce
        hook = _as_float(clip.get("hook_time"))
        if hook is None or not (cs <= hook <= ce):
            clip["hook_time"] = cs
            if hook is not None:
                summary["hook_fixed"] += 1
        else:
            clip["hook_time"] = hook
        valid.append(clip)

    # 2. Kutipan
    for clip in valid:
        s, e = clip["start_time"], clip["end_time"]
        kept = []
        for q in clip.get("key_quotes") or []:
            if isinstance(q, str) and quote_is_grounded(q, transcript, s, e):
                kept.append(q)
            else:
                summary["quotes_dropped"] += 1
        if not kept:
            filled = fill_quote(transcript, s, e)
            if filled:
                kept = [filled]
                summary["quotes_filled"] += 1
                clip["guardrail_notes"].append("key quote replaced with verbatim transcript line")
        clip["key_quotes"] = kept

    # 3. Overlap: skor tertinggi diproses dulu, urutan asli dipertahankan di hasil
    order = sorted(range(len(valid)), key=lambda i: -(_as_float(valid[i].get("virality_score")) or 0.0))
    kept_idx: List[int] = []
    for i in order:
        a = valid[i]
        merged_into = None
        for j in kept_idx:
            b = valid[j]
            shorter = max(0.001, min(a["end_time"] - a["start_time"], b["end_time"] - b["start_time"]))
            share = overlap(a["start_time"], a["end_time"], b["start_time"], b["end_time"]) / shorter
            if share > MERGE_OVERLAP:
                merged_into = j
                break
        if merged_into is not None:
            summary["merged"] += 1
            b = valid[merged_into]
            b["guardrail_notes"].append(
                f"merged overlapping clip '{str(a.get('title', ''))[:60]}' ({a['start_time']:.1f}-{a['end_time']:.1f}s)")
            continue
        kept_idx.append(i)
    result = [valid[i] for i in sorted(kept_idx)]
    for x in range(len(result)):
        for y in range(x + 1, len(result)):
            a, b = result[x], result[y]
            shorter = max(0.001, min(a["end_time"] - a["start_time"], b["end_time"] - b["start_time"]))
            share = overlap(a["start_time"], a["end_time"], b["start_time"], b["end_time"]) / shorter
            if share >= REVIEW_OVERLAP:
                summary["flagged_overlap"] += 1
                pct = round(share * 100)
                a["guardrail_notes"].append(f"overlaps {pct}% with clip '{str(b.get('title', ''))[:60]}' (review)")
                b["guardrail_notes"].append(f"overlaps {pct}% with clip '{str(a.get('title', ''))[:60]}' (review)")

    summary["clips_out"] = len(result)
    return result, summary
