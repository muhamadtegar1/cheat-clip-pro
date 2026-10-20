export interface HeatmapPoint {
  start_time: number;
  end_time: number;
  value: number;
}

export interface TranscriptLine {
  start: number;
  end: number;
  text: string;
  engagement?: number;
}

// Task #1: skor 7 dimensi 0-100 dari backend; prompt_match null tanpa fokus pencarian
export interface ClipScores {
  prompt_match?: number | null;
  hook?: number | null;
  retention?: number | null;
  clarity?: number | null;
  emotional_pull?: number | null;
  payoff?: number | null;
  editability?: number | null;
}

export interface ViralClip {
  title: string;
  start_time: number;
  end_time: number;
  hook_time?: number;
  virality_score: number;
  key_quotes: string[];
  transcript: string;
  title_suggestion?: string;
  caption_suggestion?: string;
  hashtag_suggestion?: string;
  // Task #1 (ditampilkan #1b); null/tidak ada untuk analisis lama dan klip fallback heatmap
  scores?: ClipScores | null;
  score_reason?: string | null;
  needs_context?: boolean | null;
  score_label?: 'strong' | 'fair' | 'weak' | null;
  // Task #36b: kata subtitle dari pratinjau Clip Studio; ada = render tidak menjalankan Whisper
  subtitle_words?: SubtitleWord[];
}

// Task #35: pilihan pemilik per klip, disimpan permanen di backend (EXPORTS_DIR/data/clip_choices.json)
export type ClipChoice = 'use' | 'skip';

export interface ClipChoiceRecord {
  video_id: string;
  video_title?: string | null;
  video_url?: string | null;
  source_type?: string | null;
  start_time: number;
  end_time: number;
  clip_title?: string | null;
  choice: ClipChoice;
  reason?: string | null;
  scores?: ClipScores | null;
  virality_score?: number | null;
  rank?: number | null;
  rank_total?: number | null;
  tier?: 'priority' | 'backup' | null;
  needs_context?: boolean | null;
  heatmap_avg?: number | null;
  heatmap_source?: string | null;
  model?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AnalyzeResponse {
  video_id: string;
  title: string;
  duration: number;
  heatmap: HeatmapPoint[];
  summary: string;
  clips: ViralClip[];
  transcript?: TranscriptLine[];
  model?: string;
  video_url?: string;
  source_type?: 'youtube' | 'upload' | 'gdrive';
}

export type AspectRatioOption = '9:16' | '1:1' | '4:3' | '16:9' | '16:9_landscape';
export type BackgroundStyle = 'black' | 'blurred';
export type CaptionStyle = 
  | 'viral_pop' 
  | 'beast_punch' 
  | 'cyber_violet' 
  | 'fire_red' 
  | 'electric_cyan' 
  | 'golden_aura' 
  | 'clean_minimal' 
  | 'none';
export type CaptionFont = 
  | 'Outfit' 
  | 'Montserrat' 
  | 'Inter' 
  | 'Impact' 
  | 'Bebas Neue' 
  | 'Anton' 
  | 'Poppins' 
  | 'Arial Black'
  | (string & {});
export type TitlePosition = 'auto' | 'safe_zone' | 'middle' | 'none';
export type TitleDurationOption = 'entire' | '5s' | '10s';
export type SubtitlePositionMode = 'bottom' | 'center';
export type StreamerPreset = 'none' | 'split_top_cam' | 'pip_corner';
export type FacecamPosition = 'auto' | 'bottom_right' | 'top_right' | 'bottom_left' | 'top_left' | 'center' | 'left' | 'right';
export type FontSizeOption = 'small' | 'medium' | 'big' | 'custom';
export type TextCaseOption = 'uppercase' | 'capitalize' | 'lowercase';
export type HardwareAccelOption = 'auto' | 'nvenc' | 'amf' | 'qsv' | 'cpu' | 'browser_wasm';
// Task #39: bahasa audio untuk Whisper ('auto' = tebak sendiri), sama dengan WHISPER_AUDIO_LANGUAGES di backend
export type AudioLanguage = 'auto' | 'en' | 'id' | 'ms' | 'es' | 'pt' | 'fr' | 'de' | 'ar' | 'hi' | 'ja' | 'ko';

export interface FontItem {
  name: string;
  is_custom: boolean;
  filename?: string | null;
  url?: string | null;
}

export interface HardwareAccelInfo {
  status: string;
  active_default: string;
  recommended: string;
  support: {
    nvenc: boolean;
    amf: boolean;
    qsv: boolean;
    cpu: boolean;
    recommended: string;
  };
  options: Array<{
    id: HardwareAccelOption;
    label: string;
    sub: string;
    available: boolean;
  }>;
}

// Task #11: satu pasangan kamus koreksi subtitle ("salah" -> "benar")
export interface SubtitleReplacement {
  from: string;
  to: string;
}

// Task #36a: subtitle asli untuk pratinjau Clip Studio (POST /api/preview-subtitles), waktu relatif awal klip
export interface SubtitlePreviewEvent {
  start: number;
  end: number;
  words: string[];
  active: number;
  /** Task #36b: indeks kata masukan (response.words) dalam potongan ini */
  indices: number[];
}

/** Task #36b: kata subtitle, waktu relatif awal klip; group = baris hasil suntingan */
export interface SubtitleWord {
  word: string;
  start: number;
  end: number;
  group?: number;
}

export interface SubtitlePreviewResponse {
  video_id: string;
  start_time: number;
  end_time: number;
  source: 'whisper' | 'transcript' | 'none' | 'edited';
  cached: boolean;
  elapsed_seconds: number;
  words: SubtitleWord[];
  events: SubtitlePreviewEvent[];
}

export interface RenderSettings {
  renderEngine?: 'server' | 'client';
  aspectRatio: AspectRatioOption;
  backgroundStyle: BackgroundStyle;
  enableFaceTracking: boolean;
  streamerPreset: StreamerPreset;
  facecamPosition?: FacecamPosition;
  titleText?: string;
  titlePrefix?: string;
  titleSuffix?: string;
  fileNamePrefix?: string;
  fileNameSuffix?: string;
  titlePosition: TitlePosition;
  titleDuration?: TitleDurationOption;
  titleFont?: CaptionFont;
  titleFontSize?: FontSizeOption;
  titleFontSizePx?: number;
  titleTextCase?: TextCaseOption;
  subtitlesEnabled?: boolean;
  captionStyle: CaptionStyle;
  captionFont: CaptionFont;
  fontSize: FontSizeOption;
  fontSizePx?: number;
  textCase: TextCaseOption;
  titleYPercent?: number;
  subtitleYPercent?: number;
  subtitlePositionMode?: SubtitlePositionMode;
  subtitleCenterYPercent?: number;
  subtitleReplacements?: SubtitleReplacement[];
  audioLanguage?: AudioLanguage; // Task #39
  selectedClips: ViralClip[];
  // Background Music
  bgmEnabled?: boolean;
  bgmFilePath?: string;
  bgmFileName?: string;
  bgmVolume?: number; // 0 to 100%
  bgmStartOffset?: number; // seconds from start of audio track
  // Hook SFX
  hookSfxEnabled?: boolean;
  hookSfxFilePath?: string;
  hookSfxFileName?: string;
  hookSfxVolume?: number; // 0 to 150%
  // Raw Audio / Voice Boost
  originalAudioVolume?: number; // 0 to 200%
  // Watermark
  watermarkEnabled?: boolean;
  watermarkType?: 'image' | 'text';
  watermarkFilePath?: string;
  watermarkUrl?: string;
  watermarkText?: string;
  watermarkSize?: number; // 5 to 50%
  watermarkOpacity?: number; // 10 to 100%
  watermarkX?: number; // 0 to 100%
  watermarkY?: number; // 0 to 100%
  // Hardware Acceleration / Video Encoder
  hardwareAccel?: HardwareAccelOption;
  // Multi-Segment Merged Highlight Video
  renderMode?: 'separate' | 'merged';
  compilationTitle?: string;
}

export interface RenderClipStatus {
  clip_index: number;
  title: string;
  base_title?: string;
  status: 'pending' | 'downloading' | 'transcribing' | 'tracking' | 'rendering' | 'completed' | 'error';
  progress_percent: number;
  download_url?: string;
  error_message?: string;
  error?: string;
}

export interface BatchRenderProgress {
  batch_id: string;
  total_clips: number;
  current_clip_index: number;
  overall_status: 'running' | 'completed' | 'error';
  zip_url?: string;
  error_message?: string;
  warning_message?: string;
  clips: RenderClipStatus[];
}
