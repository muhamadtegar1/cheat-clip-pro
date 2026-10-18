import { useCallback, useEffect, useMemo, useState } from 'react';
import type { AnalyzeResponse, ClipChoice, ClipChoiceRecord, HeatmapPoint, ViralClip } from '../types';
import { clipKey, hasClipScores, type ClipTier } from './clipScores';

// Task #35: pilihan Pakai/Lewati pemilik per klip, disimpan permanen di backend (/api/clip-choices).

export type ClipChoiceStatus = 'saving' | 'saved' | 'error';

/** Rata-rata heatmap di rentang klip, ditimbang lama tumpang tindih tiap titik; null bila tidak ada data. */
export const heatmapAverage = (heatmap: HeatmapPoint[] | undefined, start: number, end: number): number | null => {
  let weighted = 0;
  let total = 0;
  for (const p of heatmap || []) {
    const overlap = Math.min(end, p.end_time) - Math.max(start, p.start_time);
    if (overlap > 0 && Number.isFinite(p.value)) {
      weighted += p.value * overlap;
      total += overlap;
    }
  }
  return total > 0 ? Math.round((weighted / total) * 10000) / 10000 : null;
};

/** Sumber heatmap: penonton YouTube untuk jalur YouTube, energi audio (#33) untuk upload/Drive. */
export const heatmapSource = (result: AnalyzeResponse): string | null => {
  if (!result.heatmap || result.heatmap.length === 0) return null;
  if (result.source_type === 'upload' || result.source_type === 'gdrive') return 'audio_energy';
  return 'youtube_viewers';
};

/** Peringkat skor dalam hasil analisis (1 = tertinggi, skor sama berbagi peringkat). */
export const computeClipRanks = (clips: ViralClip[] | undefined): Map<string, number> => {
  const ranks = new Map<string, number>();
  const list = clips || [];
  for (const clip of list) {
    ranks.set(clipKey(clip), 1 + list.filter((c) => c.virality_score > clip.virality_score).length);
  }
  return ranks;
};

const buildRecord = (
  result: AnalyzeResponse,
  clip: ViralClip,
  choice: ClipChoice,
  reason: string | null,
  rank: number | undefined,
  tier: ClipTier | undefined,
): ClipChoiceRecord => ({
  video_id: result.video_id,
  video_title: result.title || null,
  video_url: result.video_url || null,
  source_type: result.source_type || null,
  start_time: clip.start_time,
  end_time: clip.end_time,
  clip_title: clip.title || null,
  choice,
  reason: reason && reason.trim() ? reason.trim().slice(0, 300) : null,
  scores: hasClipScores(clip) ? clip.scores : null,
  virality_score: clip.virality_score,
  rank: rank ?? null,
  rank_total: result.clips.length || null,
  tier: tier ?? null,
  needs_context: clip.needs_context ?? null,
  heatmap_avg: heatmapAverage(result.heatmap, clip.start_time, clip.end_time),
  heatmap_source: heatmapSource(result),
  model: result.model || null,
});

export const useClipChoices = (result: AnalyzeResponse | null, tiers: Map<string, ClipTier>) => {
  const videoId = result?.video_id;
  // Pilihan disimpan bersama video_id-nya agar hasil video lain tidak memakai pilihan lama.
  const [store, setStore] = useState<{ videoId?: string; records: Record<string, ClipChoiceRecord> }>({ records: {} });
  const [statuses, setStatuses] = useState<Record<string, ClipChoiceStatus>>({});
  const ranks = useMemo(() => computeClipRanks(result?.clips), [result?.clips]);

  useEffect(() => {
    if (!videoId) return;
    let cancelled = false;
    fetch(`/api/clip-choices?video_id=${encodeURIComponent(videoId)}`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: { records?: ClipChoiceRecord[] }) => {
        if (cancelled) return;
        const records: Record<string, ClipChoiceRecord> = {};
        for (const rec of data.records || []) records[clipKey(rec)] = rec;
        setStore({ videoId, records });
      })
      .catch((err) => {
        if (!cancelled) console.warn('[Clip Choices] Gagal memuat pilihan:', err);
      });
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  const records = store.videoId === videoId ? store.records : {};

  const setStatus = (key: string, status: ClipChoiceStatus) => setStatuses((prev) => ({ ...prev, [key]: status }));

  const save = useCallback(
    async (clip: ViralClip, choice: ClipChoice, reason: string | null) => {
      if (!result) return;
      const key = clipKey(clip);
      setStatus(key, 'saving');
      try {
        const res = await fetch('/api/clip-choices', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(buildRecord(result, clip, choice, reason, ranks.get(key), tiers.get(key))),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: { record: ClipChoiceRecord } = await res.json();
        setStore((prev) => ({
          videoId: result.video_id,
          records: { ...(prev.videoId === result.video_id ? prev.records : {}), [key]: data.record },
        }));
        setStatus(key, 'saved');
      } catch (err) {
        console.warn('[Clip Choices] Gagal menyimpan pilihan:', err);
        setStatus(key, 'error');
      }
    },
    [result, ranks, tiers],
  );

  const clear = useCallback(
    async (clip: ViralClip) => {
      if (!result) return;
      const key = clipKey(clip);
      setStatus(key, 'saving');
      try {
        const params = new URLSearchParams({
          video_id: result.video_id,
          start_time: String(clip.start_time),
          end_time: String(clip.end_time),
        });
        const res = await fetch(`/api/clip-choices?${params.toString()}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setStore((prev) => {
          const next = { ...(prev.videoId === result.video_id ? prev.records : {}) };
          delete next[key];
          return { videoId: result.video_id, records: next };
        });
        setStatus(key, 'saved');
      } catch (err) {
        console.warn('[Clip Choices] Gagal membatalkan pilihan:', err);
        setStatus(key, 'error');
      }
    },
    [result],
  );

  return { records, statuses, save, clear };
};

/** Unduh semua pilihan (JSON/CSV) dari backend; false bila gagal. */
export const downloadClipChoicesExport = async (format: 'json' | 'csv'): Promise<boolean> => {
  try {
    const res = await fetch(`/api/clip-choices/export?format=${format}`);
    if (!res.ok) return false;
    const blob = await res.blob();
    const match = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') || '');
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = match ? match[1] : `clip_choices.${format}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return true;
  } catch {
    return false;
  }
};
