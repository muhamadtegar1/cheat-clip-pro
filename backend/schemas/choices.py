from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

# Task #35: pilihan pemilik per klip (Pakai/Lewati), disimpan permanen untuk kalibrasi skor (#2, #3).

ClipChoiceValue = Literal["use", "skip"]


class ClipChoiceRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=300)
    video_title: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=2000)
    source_type: Optional[str] = Field(None, max_length=20)
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., ge=0)
    clip_title: Optional[str] = Field(None, max_length=500)
    choice: ClipChoiceValue
    reason: Optional[str] = Field(None, max_length=300)
    scores: Optional[Dict[str, Optional[float]]] = None
    virality_score: Optional[float] = None
    rank: Optional[int] = Field(None, ge=1)
    rank_total: Optional[int] = Field(None, ge=1)
    tier: Optional[Literal["priority", "backup"]] = None
    needs_context: Optional[bool] = None
    heatmap_avg: Optional[float] = None
    heatmap_source: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=200)


class ClipChoiceRecord(ClipChoiceRequest):
    created_at: str
    updated_at: str
