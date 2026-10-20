from typing import List, Optional, Union
from pydantic import BaseModel, Field

from backend.schemas.render import AudioLanguage

class ClipScores(BaseModel):
    """Skor 7 dimensi per klip (task #1), 0-100. prompt_match None bila pengguna tidak memberi fokus pencarian."""
    prompt_match: Optional[int] = None
    hook: Optional[int] = None
    retention: Optional[int] = None
    clarity: Optional[int] = None
    emotional_pull: Optional[int] = None
    payoff: Optional[int] = None
    editability: Optional[int] = None

class ViralClip(BaseModel):
    title: str = Field(description="Catchy clip title, max 8 words. MUST NEVER use first-person pronouns ('I', 'me', 'my', 'saya', 'aku'). Attribute to the speaker/host by name, role, or use objective framing.")
    start_time: float = Field(description="Clip start in seconds, aligned to a sentence boundary")
    end_time: float = Field(description="Clip end in seconds, aligned to a sentence boundary")
    hook_time: float = Field(description="Absolute timestamp in seconds from video start where the potential hook occurs inside this clip range (must be >= start_time and <= end_time)")
    virality_score: int = Field(description="Overall score 0-100. When `scores` is present it is the rounded mean of the available dimension scores, computed by the backend")
    key_quotes: List[str] = Field(description="1-2 key quotes from the clip")
    transcript: str = Field(description="Spoken text of the clip")
    title_suggestion: str = Field(default="", description="Catchy alternative title suggestion. MUST NEVER use first-person pronouns ('I', 'me', 'my'). Attribute to speaker or objective topic.")
    caption_suggestion: str = Field(default="", description="Engaging social media caption suggestion attributing quotes or insights to the speaker.")
    hashtag_suggestion: str = Field(default="", description="Relevant hashtags suggestion (e.g. #hashtag1 #hashtag2)")
    guardrail_notes: List[str] = Field(default_factory=list, description="Post-processing notes from output guardrails (timestamp adjusted, quote replaced, overlap merged or flagged for review)")
    scores: Optional[ClipScores] = Field(default=None, description="7 dimension scores 0-100 (task #1); None for clips without AI scoring (heatmap fallback, old results)")
    score_reason: Optional[str] = Field(default=None, description="1-2 sentence reason for the scores, referring to the transcript")
    needs_context: Optional[bool] = Field(default=None, description="True when the clip needs context from outside its time range")
    score_label: Optional[str] = Field(default=None, description="'strong' (>= 80), 'fair' (60-79) or 'weak' (< 60), from virality_score; None without scores")

class ViralClipGemini(BaseModel):
    title: str = Field(description="Catchy clip title, max 8 words, in the EXACT SAME LANGUAGE as the video transcript (STRICT ZERO-TRANSLATION RULE: English is English, Indonesian is Indonesian, Spanish is Spanish). NEVER use first-person pronouns ('I', 'me', 'my', 'myself', 'aku', 'saya'). Attribute to the person speaking by name, host/guest title, or use third-person objective framing so it does not look like the user's opinion.")
    start_time: float = Field(description="Clip start in seconds, aligned to a sentence boundary")
    end_time: float = Field(description="Clip end in seconds, aligned to a sentence boundary")
    hook_time: float = Field(description="Absolute timestamp in seconds from video start where the potential hook occurs inside this clip range (must be >= start_time and <= end_time)")
    score_prompt_match: int = Field(description="0-100: how well this clip answers the USER SEARCH FOCUS. Use 0 when no search focus was given (it is then ignored)")
    score_hook: int = Field(description="0-100: how strongly the first 3 seconds stop the scroll (question, bold claim, surprise, conflict) using only what is actually said in the clip")
    score_retention: int = Field(description="0-100: how likely viewers keep watching to the end (momentum, tension, no dead air or rambling)")
    score_clarity: int = Field(description="0-100: how understandable the clip is on its own for a stranger who has not seen the full video")
    score_emotional_pull: int = Field(description="0-100: emotional intensity (humor, surprise, inspiration, tension, relatability)")
    score_payoff: int = Field(description="0-100: how satisfying the ending is (punchline, answer, lesson, resolution) instead of stopping mid-thought")
    score_editability: int = Field(description="0-100: how easy it is to cut cleanly (clean sentence boundaries, few filler words, works as a vertical clip)")
    score_reason: str = Field(description="1-2 sentences in the video's spoken language explaining the scores, quoting a short phrase or naming the second from the transcript. Never claim the clip will surely or definitely go viral")
    needs_context: bool = Field(description="true if the clip refers to something explained outside its time range and a viewer would need that context")
    key_quotes: List[str] = Field(description="1-2 verbatim quotes directly spoken in the clip, in the original language of the video without translation")
    title_suggestion: str = Field(default="", description="Catchy alternative title suggestion in the EXACT SAME LANGUAGE as the video transcript (DO NOT translate). STRICT RULE: NEVER use first-person ('I', 'me', 'my', 'saya', 'aku'). Attribute to the speaker/host/guest by name or topic.")
    caption_suggestion: str = Field(default="", description="Engaging social media caption suggestion written in the EXACT SAME LANGUAGE as the video transcript (DO NOT translate to any other language), attributing insights or story to the speaker.")
    hashtag_suggestion: str = Field(default="", description="Relevant hashtags suggestion in the SAME LANGUAGE as the video transcript (e.g. #hashtag1 #hashtag2)")

class VideoAnalysis(BaseModel):
    summary: str = Field(description="1-2 sentence video summary in the EXACT SAME LANGUAGE as the video transcript (STRICT ZERO-TRANSLATION RULE: English stays English, Indonesian stays Indonesian, Spanish stays Spanish), followed by 2-4 relevant hashtags")
    clips: List[ViralClipGemini] = Field(description="List of viral clip candidates, strongest first")

class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    duration: str = Field("30s", description="Target clip duration: '15s', '30s', '60s', or 'auto'")
    api_key: Optional[str] = Field(None, description="Optional custom Gemini API key provided by the user")
    model: Optional[str] = Field("gemini-2.5-flash", description="Preferred Gemini model name")
    custom_prompt: Optional[str] = Field(None, description="Optional custom focus prompt for clips search")
    range_start: Optional[float] = Field(None, description="Search range start in seconds")
    range_end: Optional[float] = Field(None, description="Search range end in seconds")
    subtitles: Optional[str] = Field(None, description="Optional manual subtitles text (SRT or TXT)")
    subtitles_filename: Optional[str] = Field(None, description="Optional manual subtitles filename")
    target_clip_count: Optional[Union[int, str]] = Field(None, description="Optional target number of clips or 'auto'")
    proxy: Optional[str] = Field(None, description="Optional custom proxy URL")
    cookies: Optional[str] = Field(None, description="Optional user YouTube cookies from browser LocalStorage")
    audio_language: AudioLanguage = Field(None, description="Task #39: Whisper audio language code (None/'auto' = detect)")

class HeatmapPoint(BaseModel):
    start_time: float
    end_time: float
    value: float

class TranscriptLine(BaseModel):
    start: float
    end: float
    text: str
    engagement: Optional[float] = None

class AnalyzeResponse(BaseModel):
    video_id: str
    title: str
    channel: Optional[str] = None
    duration: float
    heatmap: List[HeatmapPoint]
    summary: str
    clips: List[ViralClip]
    transcript: Optional[List[TranscriptLine]] = None
    model: Optional[str] = None
    video_url: Optional[str] = None
    source_type: Optional[str] = "youtube"
    prompt_version: Optional[str] = Field(None, description="Task #22: hash pendek kode prompt analisis (metadata posting kit)")
