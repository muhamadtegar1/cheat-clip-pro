from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from backend.routers.system import verify_admin_access
from backend.schemas.choices import ClipChoiceRequest
from backend.services.choices_service import (
    FILE_VERSION,
    delete_choice,
    export_csv,
    list_choices,
    save_choice,
)

# Task #35: pilihan Pakai/Lewati pemilik per klip, hanya dari komputer ini (guard admin lokal).
router = APIRouter(tags=["Clip Choices"])


@router.get("/api/clip-choices")
def get_clip_choices(video_id: Optional[str] = None, authorized: bool = Depends(verify_admin_access)):
    try:
        return {"records": list_choices(video_id)}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/clip-choices")
def put_clip_choice(payload: ClipChoiceRequest, authorized: bool = Depends(verify_admin_access)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=422, detail="end_time harus lebih besar dari start_time")
    try:
        return {"record": save_choice(payload)}
    except (RuntimeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan pilihan: {e}")


@router.delete("/api/clip-choices")
def delete_clip_choice(
    video_id: str,
    start_time: float,
    end_time: float,
    authorized: bool = Depends(verify_admin_access),
):
    try:
        return {"deleted": delete_choice(video_id, start_time, end_time)}
    except (RuntimeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Gagal membatalkan pilihan: {e}")


@router.get("/api/clip-choices/export")
def export_clip_choices(
    format: Literal["json", "csv"] = Query("json"),
    authorized: bool = Depends(verify_admin_access),
):
    try:
        records = list_choices()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if format == "csv":
        return Response(
            content=export_csv(records),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="clip_choices-{stamp}.csv"'},
        )
    return JSONResponse(
        content={"version": FILE_VERSION, "exported_at": stamp, "records": records},
        headers={"Content-Disposition": f'attachment; filename="clip_choices-{stamp}.json"'},
    )
