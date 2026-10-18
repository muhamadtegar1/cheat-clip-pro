import React, { useState } from 'react';
import type { ClipChoice, ClipChoiceRecord } from '../types';
import { useLanguage } from '../locales';
import type { ClipChoiceStatus } from '../utils/clipChoices';

// Task #35: tombol Pakai/Lewati + alasan singkat opsional di kartu klip.

interface Props {
  record?: ClipChoiceRecord;
  status?: ClipChoiceStatus;
  onChoose: (choice: ClipChoice, reason: string | null) => void;
  onClear: () => void;
}

const buttonBase: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
  fontSize: '0.72rem',
  fontWeight: 700,
  padding: '0.25rem 0.6rem',
  borderRadius: '6px',
  cursor: 'pointer',
  background: 'rgba(255, 255, 255, 0.04)',
  border: '1px solid var(--border-color)',
  color: 'var(--text-secondary)',
};

const activeStyle: Record<ClipChoice, React.CSSProperties> = {
  use: { color: 'var(--accent)', background: 'rgba(16, 185, 129, 0.14)', border: '1px solid rgba(16, 185, 129, 0.5)' },
  skip: { color: '#f87171', background: 'rgba(248, 113, 113, 0.12)', border: '1px solid rgba(248, 113, 113, 0.45)' },
};

export const ClipChoiceControls: React.FC<Props> = ({ record, status, onChoose, onClear }) => {
  const { t } = useLanguage();
  const current = record?.choice;
  // Draf alasan diikat ke record tersimpan; berganti otomatis saat record dari backend berubah.
  const [draft, setDraft] = useState<{ source?: string; text: string }>({ text: '' });
  const savedReason = record?.reason || '';
  const sourceKey = `${record?.updated_at || ''}|${savedReason}`;
  const reasonText = draft.source === sourceKey ? draft.text : savedReason;

  const handleChoice = (choice: ClipChoice) => {
    if (current === choice) onClear();
    else onChoose(choice, reasonText || null);
  };

  const commitReason = () => {
    if (!current) return;
    if (reasonText.trim() === savedReason.trim()) return;
    onChoose(current, reasonText.trim() || null);
  };

  const statusText =
    status === 'saving' ? t.results.choiceSaving : status === 'error' ? t.results.choiceSaveError : status === 'saved' && current ? t.results.choiceSaved : '';

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.4rem', margin: '0.4rem 0' }}
    >
      <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)' }}>{t.results.choiceLabel}</span>
      {(['use', 'skip'] as ClipChoice[]).map((choice) => (
        <button
          key={choice}
          type="button"
          title={current === choice ? t.results.choiceClearTooltip : t.results.choiceTooltip}
          disabled={status === 'saving'}
          onClick={() => handleChoice(choice)}
          style={{ ...buttonBase, ...(current === choice ? activeStyle[choice] : {}), opacity: status === 'saving' ? 0.6 : 1 }}
        >
          {choice === 'use' ? t.results.choiceUse : t.results.choiceSkip}
        </button>
      ))}
      {current && (
        <input
          type="text"
          value={reasonText}
          maxLength={300}
          placeholder={t.results.choiceReasonPlaceholder}
          onChange={(e) => setDraft({ source: sourceKey, text: e.target.value })}
          onBlur={commitReason}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur();
          }}
          style={{
            flex: '1 1 180px',
            minWidth: '140px',
            fontSize: '0.72rem',
            padding: '0.25rem 0.5rem',
            borderRadius: '6px',
            border: '1px solid var(--border-color)',
            background: 'rgba(255, 255, 255, 0.03)',
            color: 'var(--text-primary)',
          }}
        />
      )}
      {statusText && (
        <span style={{ fontSize: '0.68rem', color: status === 'error' ? '#f87171' : 'var(--text-muted)' }}>{statusText}</span>
      )}
    </div>
  );
};
