import React from 'react';
import type { ClipScores, ViralClip } from '../types';
import { useLanguage } from '../locales';
import { SCORE_DIMENSIONS, hasClipScores, type ClipTier } from '../utils/clipScores';

// Task #1b: tampilan skor 7 dimensi (#1) dan label prioritas relatif per hasil analisis.

const pillBase: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
  fontSize: '0.65rem',
  fontWeight: 'bold',
  padding: '0.15rem 0.45rem',
  borderRadius: '4px',
  whiteSpace: 'nowrap',
};

export const ClipTierBadges: React.FC<{ tier?: ClipTier; needsContext?: boolean | null }> = ({ tier, needsContext }) => {
  const { t } = useLanguage();
  if (!tier && !needsContext) return null;
  return (
    <>
      {tier && (
        <div
          title={t.results.scoreTierTooltip}
          style={{
            ...pillBase,
            color: tier === 'priority' ? 'var(--accent)' : 'var(--text-secondary)',
            background: tier === 'priority' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(148, 163, 184, 0.10)',
            border: `1px solid ${tier === 'priority' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(148, 163, 184, 0.3)'}`,
          }}
        >
          {tier === 'priority' ? t.results.scoreTierPriority : t.results.scoreTierBackup}
        </div>
      )}
      {needsContext && (
        <div
          title={t.results.needsContextTooltip}
          style={{
            ...pillBase,
            color: '#f59e0b',
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
          }}
        >
          {t.results.needsContextBadge}
        </div>
      )}
    </>
  );
};

export const ClipScorePanel: React.FC<{ clip: ViralClip }> = ({ clip }) => {
  const { t } = useLanguage();
  if (!hasClipScores(clip)) return null;
  const labels: Record<keyof ClipScores, string> = t.results.scoreDimensions;
  const rows = SCORE_DIMENSIONS.filter((d) => typeof clip.scores?.[d] === 'number');

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        margin: '0.5rem 0',
        padding: '0.6rem 0.75rem',
        borderRadius: '8px',
        background: 'rgba(139, 92, 246, 0.05)',
        border: '1px solid var(--border-color)',
      }}
    >
      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.4rem', letterSpacing: '0.03em' }}>
        {t.results.scorePanelTitle}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '0.3rem 0.9rem' }}>
        {rows.map((d) => {
          const value = Math.max(0, Math.min(100, clip.scores![d] as number));
          return (
            <div key={d} style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: '0.15rem 0.4rem', fontSize: '0.7rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{labels[d]}</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{value}</span>
              <div style={{ gridColumn: '1 / -1', height: '4px', borderRadius: '2px', background: 'var(--border-color)', overflow: 'hidden' }}>
                <div style={{ width: `${value}%`, height: '100%', background: 'var(--primary)' }} />
              </div>
            </div>
          );
        })}
      </div>
      {clip.score_reason && (
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{t.results.scoreReasonLabel}</span>{' '}
          {clip.score_reason}
        </div>
      )}
    </div>
  );
};
