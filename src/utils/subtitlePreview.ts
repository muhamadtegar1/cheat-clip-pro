import type {
  AudioLanguage,
  CaptionStyle,
  SubtitlePreviewEvent,
  SubtitlePreviewResponse,
  SubtitleReplacement,
  SubtitleWord,
  TextCaseOption,
  TranscriptLine,
} from '../types';

// Task #36a: subtitle asli (Whisper) untuk pratinjau Clip Studio, pemotongan sama dengan render server.

// Task #39: pilihan bahasa audio Whisper (urutan dropdown), sama dengan WHISPER_AUDIO_LANGUAGES di backend
export const AUDIO_LANGUAGE_OPTIONS: AudioLanguage[] = ['auto', 'en', 'id', 'ms', 'es', 'pt', 'fr', 'de', 'ar', 'hi', 'ja', 'ko'];
export const AUDIO_LANGUAGE_STORAGE_KEY = 'cheat_clip_audio_language';
export const parseAudioLanguage = (value: string | null | undefined): AudioLanguage =>
  AUDIO_LANGUAGE_OPTIONS.find(code => code === value) ?? 'auto';
/** Task #40: storage diblokir (mode privat, kebijakan browser) = Otomatis, bukan galat yang menjatuhkan App. */
export const readStoredAudioLanguage = (): AudioLanguage => {
  try {
    return parseAudioLanguage(localStorage.getItem(AUDIO_LANGUAGE_STORAGE_KEY));
  } catch {
    return 'auto';
  }
};
/** Task #40: gagal simpan diabaikan; pilihan tetap berlaku sampai halaman dimuat ulang. */
export const storeAudioLanguage = (value: AudioLanguage): void => {
  try {
    localStorage.setItem(AUDIO_LANGUAGE_STORAGE_KEY, value);
  } catch {
    // storage diblokir atau penuh
  }
};
/** Kode untuk backend: 'auto' tidak dikirim, jadi request mode Otomatis sama dengan sebelum #39. */
export const audioLanguageParam = (value?: AudioLanguage): string | undefined =>
  value && value !== 'auto' ? value : undefined;
/** Task #39: kunci pratinjau per klip dan bahasa, agar kata dari bahasa lain tidak dipakai render. */
export const subtitlePreviewKey = (startTime: number, endTime: number, language: AudioLanguage): string =>
  `${startTime}_${endTime}_${language}`;

export interface SubtitlePreviewRequest {
  videoUrl: string;
  videoId: string;
  startTime: number;
  endTime: number;
  transcript?: TranscriptLine[];
  cookies?: string;
  replacements: SubtitleReplacement[];
  audioLanguage?: AudioLanguage; // Task #39
  textCase: TextCaseOption;
  /** Lewati cache backend dan jalankan Whisper lagi (tombol "Buat ulang") */
  force?: boolean;
  /** Task #36b: kata yang sudah ada (hasil Whisper atau suntingan); diisi = backend tanpa unduh/Whisper */
  words?: SubtitleWord[];
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
      force: req.force || undefined,
      words: req.words,
      audio_language: audioLanguageParam(req.audioLanguage),
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

// Task #36b: sunting subtitle per baris. Baris = potongan dari build_subtitle_events (event.indices),
// hasil suntingan = daftar kata dengan group per baris yang dipakai pratinjau dan render.

export interface SubtitleLine {
  /** Kata mentah baris ini (sebelum kamus/kapitalisasi) */
  words: SubtitleWord[];
  /** Teks yang tampil di video (sesudah kamus/kapitalisasi) */
  display: string;
  /** Indeks kata respons (event.indices) untuk mencocokkan baris dengan event aktif */
  key?: string;
  /** Awal baris (detik relatif klip) */
  start?: number;
}

/** Batas karakter potongan otomatis di backend; baris suntingan yang lebih panjang bisa terpotong di tepi video. */
export const SUBTITLE_LINE_MAX_CHARS = 22;

/** Task #40: batas panjang satu kata, sama dengan SUBTITLE_WORD_MAX_CHARS di render_service (backend menolak dengan 422). */
export const SUBTITLE_WORD_MAX_CHARS = 60;
/** Kata pertama di teks yang melebihi SUBTITLE_WORD_MAX_CHARS, atau null. */
export const findTooLongWord = (text: string): string | null =>
  text.trim().split(/\s+/).find(word => word.length > SUBTITLE_WORD_MAX_CHARS) ?? null;

export const subtitleLineText = (line: SubtitleLine): string => line.words.map(w => w.word).join(' ');

/** Baris dari respons pratinjau; kata yang dibuang kamus/pembersih tidak masuk baris mana pun. */
export const linesFromPreview = (words: SubtitleWord[], events: SubtitlePreviewEvent[]): SubtitleLine[] => {
  const lines: SubtitleLine[] = [];
  let lastKey = '';
  events.forEach(ev => {
    const key = ev.indices.join(',');
    if (key === lastKey) return;
    lastKey = key;
    lines.push({ words: ev.indices.map(i => words[i]).filter(Boolean), display: ev.words.join(' '), key, start: ev.start });
  });
  return lines.filter(line => line.words.length > 0);
};

/** Daftar kata ber-group (satu group per baris) untuk dikirim ke pratinjau dan render. */
export const linesToWords = (lines: SubtitleLine[]): SubtitleWord[] =>
  lines.flatMap((line, group) => line.words.map(w => ({ word: w.word, start: w.start, end: w.end, group })));

const roundTime = (t: number) => Math.round(t * 1000) / 1000;

/**
 * Ketik ulang satu baris. Jumlah kata sama: waktu tiap kata dipertahankan. Berbeda: rentang baris
 * (awal kata pertama s.d. akhir kata terakhir) dibagi rata. Teks kosong = baris dihapus (null).
 */
export const retypeLine = (line: SubtitleLine, text: string): SubtitleLine | null => {
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  if (tokens.length === 0 || line.words.length === 0) return null;
  if (tokens.length === line.words.length) {
    return { ...line, words: line.words.map((w, i) => ({ ...w, word: tokens[i] })) };
  }
  const start = line.words[0].start;
  const end = Math.max(start, line.words[line.words.length - 1].end);
  const step = (end - start) / tokens.length;
  return {
    ...line,
    words: tokens.map((word, i) => ({ word, start: roundTime(start + i * step), end: roundTime(start + (i + 1) * step) })),
  };
};

/** Jumlah kata sebelum kursor di teks input; dipakai menentukan titik pecah (kata yang terpotong kursor ikut bagian pertama). */
export const wordsBeforeCursor = (text: string, cursor: number): number =>
  text.slice(0, Math.max(0, cursor)).trim().split(/\s+/).filter(Boolean).length;

/** Pecah baris di batas kata ke-k; k di luar 1..n-1 = dipecah di tengah. Baris satu kata tidak bisa dipecah. */
export const splitLine = (line: SubtitleLine, k: number): SubtitleLine[] => {
  const n = line.words.length;
  if (n < 2) return [line];
  const at = k >= 1 && k <= n - 1 ? k : Math.ceil(n / 2);
  return [
    { words: line.words.slice(0, at), display: '' },
    { words: line.words.slice(at), display: '' },
  ];
};

export const mergeLines = (a: SubtitleLine, b: SubtitleLine): SubtitleLine => ({ words: [...a.words, ...b.words], display: '' });
