import type {
  CaptionStyle,
  SubtitlePreviewEvent,
  SubtitlePreviewResponse,
  SubtitleReplacement,
  TextCaseOption,
  TranscriptLine,
} from '../types';

// Task #36a: subtitle asli (Whisper) untuk pratinjau Clip Studio, pemotongan sama dengan render server.

export interface SubtitlePreviewRequest {
  videoUrl: string;
  videoId: string;
  startTime: number;
  endTime: number;
  transcript?: TranscriptLine[];
  cookies?: string;
  replacements: SubtitleReplacement[];
  textCase: TextCaseOption;
}

/** Warna kata aktif per gaya, sama dengan highlight_color di generate_ass_file (backend/video_engine.py). */
export const SUBTITLE_HIGHLIGHT_COLORS: Record<CaptionStyle, string> = {
  viral_pop: '#FFE600',
  beast_punch: '#00FF66',
  cyber_violet: '#D946EF',
  fire_red: '#FF2E2E',
  electric_cyan: '#00F0FF',
  golden_aura: '#FFB800',
  clean_minimal: '#E0E0E0',
  none: '#E0E0E0',
};

/** Tanda tangan parameter yang memengaruhi event (kamus + kapitalisasi), untuk tahu kapan perlu dihitung ulang. */
export const subtitlePreviewSignature = (replacements: SubtitleReplacement[], textCase: TextCaseOption): string =>
  JSON.stringify({ r: replacements, c: textCase });

export const fetchSubtitlePreview = async (req: SubtitlePreviewRequest): Promise<SubtitlePreviewResponse> => {
  const res = await fetch('/api/preview-subtitles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_url: req.videoUrl || undefined,
      video_id: req.videoId,
      start_time: req.startTime,
      end_time: req.endTime,
      transcript: req.transcript && req.transcript.length > 0 ? req.transcript : undefined,
      cookies: req.cookies || undefined,
      subtitle_replacements: req.replacements.length > 0 ? req.replacements : undefined,
      text_case: req.textCase,
    }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && typeof data.detail === 'string') detail = data.detail;
    } catch {
      // respons bukan JSON
    }
    throw new Error(detail);
  }
  return res.json();
};

/** Indeks event yang tampil pada detik relatif klip, -1 bila tidak ada (jeda tanpa subtitle). */
export const findActiveSubtitleEvent = (events: SubtitlePreviewEvent[], relTime: number): number => {
  for (let i = 0; i < events.length; i++) {
    if (relTime >= events[i].start && relTime < events[i].end) return i;
  }
  return -1;
};

/** Kelompokkan event karaoke menjadi potongan (baris subtitle) untuk daftar teks; event berturut-turut dengan kata sama = satu potongan. */
export const groupSubtitleChunks = (events: SubtitlePreviewEvent[]): Array<{ start: number; end: number; text: string; firstEvent: number; lastEvent: number }> => {
  const chunks: Array<{ start: number; end: number; text: string; firstEvent: number; lastEvent: number }> = [];
  events.forEach((ev, i) => {
    const text = ev.words.join(' ');
    const last = chunks[chunks.length - 1];
    if (last && last.text === text && ev.active > events[i - 1].active) {
      last.end = ev.end;
      last.lastEvent = i;
    } else {
      chunks.push({ start: ev.start, end: ev.end, text, firstEvent: i, lastEvent: i });
    }
  });
  return chunks;
};
