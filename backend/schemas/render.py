from typing import Annotated, List, Optional, Dict, Any
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _check_audio_language(value: Optional[str]) -> Optional[str]:
    """Task #39: kode bahasa audio Whisper; None/"auto" = Otomatis, kode di luar daftar = 422."""
    if value is None:
        return None
    from backend.video_engine import normalize_audio_language  # impor lambat: video_engine punya efek samping
    return normalize_audio_language(value)


# Task #39: bahasa audio untuk Whisper (None = Otomatis), dipakai AnalyzeRequest, RenderSettingsModel, PreviewSubtitlesRequest
AudioLanguage = Annotated[Optional[str], AfterValidator(_check_audio_language)]

# Task #11: satu pasangan kamus koreksi subtitle ("salah" -> "benar"), "from" satu kata tanpa spasi
class SubtitleReplacement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(..., alias="from", min_length=1, max_length=40, pattern=r"^\S+$")
    to: str = Field("", max_length=60)

class RenderSettingsModel(BaseModel):
    aspect_ratio: str = "9:16"
    background_style: str = "black"
    enable_face_tracking: bool = True
    streamer_preset: str = "none"
    facecam_position: Optional[str] = "auto"
    title_text: Optional[str] = None
    title_prefix: Optional[str] = ""
    title_suffix: Optional[str] = ""
    file_name_prefix: Optional[str] = ""
    file_name_suffix: Optional[str] = ""
    title_position: str = "auto"
    title_duration: Optional[str] = "entire"
    subtitles_enabled: Optional[bool] = True
    caption_style: str = "viral_pop"
    caption_font: str = "Outfit"
    title_font: Optional[str] = "Outfit"
    font_size: str = "medium"
    title_font_size: Optional[str] = "medium"
    font_size_px: Optional[int] = None
    title_font_size_px: Optional[int] = None
    text_case: str = "uppercase"
    title_text_case: Optional[str] = "uppercase"
    title_y_percent: Optional[float] = None
    subtitle_y_percent: Optional[float] = None
    subtitle_position_mode: Optional[str] = "bottom"
    subtitle_center_y_percent: Optional[float] = 50.0
    # Task #11: kamus koreksi kata subtitle, berlaku untuk semua klip dalam render
    subtitle_replacements: Optional[List[SubtitleReplacement]] = Field(None, max_length=100)
    # Task #39: bahasa audio untuk Whisper subtitle per kata (None = Otomatis)
    audio_language: AudioLanguage = None
    # Background Music
    bgm_enabled: Optional[bool] = False
    bgm_file_path: Optional[str] = None
    bgm_volume: Optional[float] = 25.0
    bgm_start_offset: Optional[float] = 0.0
    # Hook SFX
    hook_sfx_enabled: Optional[bool] = False
    hook_sfx_file_path: Optional[str] = None
    hook_sfx_volume: Optional[float] = 100.0
    # Raw Audio / Voice Boost
    original_audio_volume: Optional[float] = 100.0
    # Watermark
    watermark_enabled: Optional[bool] = False
    watermark_type: Optional[str] = "image"
    watermark_file_path: Optional[str] = None
    watermark_text: Optional[str] = None
    watermark_size: Optional[float] = 20.0
    watermark_opacity: Optional[float] = 80.0
    watermark_x: Optional[float] = 90.0
    watermark_y: Optional[float] = 8.0
    hardware_accel: Optional[str] = "auto"
    # Multi-Segment Merged Highlight Video
    render_mode: Optional[str] = "separate"  # "separate" | "merged"
    compilation_title: Optional[str] = None

# Task #22: data hasil analisis untuk metadata posting kit (semua opsional, request lama tetap valid)
class KitMeta(BaseModel):
    source_title: Optional[str] = None
    channel: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    custom_prompt: Optional[str] = None

class RenderBatchRequest(BaseModel):
    video_url: str
    video_id: str
    clips: List[Dict[str, Any]]
    settings: RenderSettingsModel
    transcript: Optional[List[Dict[str, Any]]] = None
    cookies: Optional[str] = None
    kit_meta: Optional[KitMeta] = None

# Task #36a: subtitle asli (Whisper) untuk pratinjau Clip Studio sebelum render
class PreviewSubtitlesRequest(BaseModel):
    video_url: Optional[str] = None
    video_id: str = Field(..., min_length=1, max_length=300)
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)
    transcript: Optional[List[Dict[str, Any]]] = None
    cookies: Optional[str] = None
    subtitle_replacements: Optional[List[SubtitleReplacement]] = Field(None, max_length=100)
    text_case: str = "uppercase"
    # True = lewati cache dan jalankan Whisper lagi (tombol "Buat ulang")
    force: bool = False
    # Task #36b: kata hasil suntingan (waktu relatif awal klip, "group" = baris). Diisi = tanpa unduh/Whisper
    words: Optional[List[Dict[str, Any]]] = Field(None, max_length=3000)
    # Task #39: bahasa audio untuk Whisper (None = Otomatis), ikut kunci cache kata
    audio_language: AudioLanguage = None

class RetryBatchRequest(BaseModel):
    clip_indices: Optional[List[int]] = None
    cookies: Optional[str] = None
