import type { ClipScores, ViralClip } from '../types';

// Task #1b: helper skor klip (label prioritas relatif per hasil analisis), dipisah dari komponen agar fast refresh tetap jalan.

export type ClipTier = 'priority' | 'backup';

export const SCORE_DIMENSIONS: (keyof ClipScores)[] = [
  'prompt_match', 'hook', 'retention', 'clarity', 'emotional_pull', 'payoff', 'editability',
];

const PRIORITY_SHARE = 0.3;

export const clipKey = (clip: Pick<ViralClip, 'start_time' | 'end_time'>) => `${clip.start_time}_${clip.end_time}`;

export const hasClipScores = (clip: ViralClip): boolean =>
  !!clip.scores && SCORE_DIMENSIONS.some((d) => d !== 'prompt_match' && typeof clip.scores?.[d] === 'number');

/**
 * Label relatif dari semua klip bertanda skor di satu hasil analisis: sekitar 30% teratas (dibulatkan ke atas,
 * minimal 1, skor sama dengan batas ikut) = priority, sisanya backup. Skor Gemini menggelembung (#1), jadi
 * ambang absolut tidak bermakna; label ini urutan prioritas, bukan vonis kualitas.
 */
export const computeClipTiers = (clips: ViralClip[] | undefined): Map<string, ClipTier> => {
  const tiers = new Map<string, ClipTier>();
  const scored = (clips || []).filter(hasClipScores);
  if (scored.length === 0) return tiers;
  const sorted = [...scored].sort((a, b) => b.virality_score - a.virality_score);
  const count = Math.max(1, Math.ceil(sorted.length * PRIORITY_SHARE));
  const cutoff = sorted[count - 1].virality_score;
  for (const clip of scored) {
    tiers.set(clipKey(clip), clip.virality_score >= cutoff ? 'priority' : 'backup');
  }
  return tiers;
};
