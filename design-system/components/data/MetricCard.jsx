import React from 'react';

const TONE_FG = {
  positive: 'var(--data-positive)',
  negative: 'var(--data-negative)',
  neutral: 'var(--text-primary)',
  warning: 'var(--data-warning)',
  accent: 'var(--accent)',
};

/**
 * MetricCard — one figure in a metric_cards grid: a label, a big value, and
 * an optional change line. Highlight the card that carries the story.
 */
export function MetricCard({ label, value, change, changeTone = 'positive', highlight = false, style, ...rest }) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        border: `1px solid ${highlight ? 'var(--accent)' : 'var(--border-hairline)'}`,
        boxShadow: highlight ? 'var(--ring-accent), var(--shadow-card)' : 'var(--ring-inset)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
        ...style,
      }}
      {...rest}
    >
      <span
        style={{
          fontFamily: 'var(--font-body)',
          fontSize: 'var(--text-sm)',
          color: 'var(--text-muted)',
          fontWeight: 500,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: 'var(--text-4xl)',
          lineHeight: 1,
          color: highlight ? 'var(--accent)' : 'var(--text-primary)',
          letterSpacing: 'var(--tracking-display)',
        }}
      >
        {value}
      </span>
      {change != null && (
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--text-sm)',
            color: TONE_FG[changeTone] || TONE_FG.neutral,
            fontWeight: 500,
          }}
        >
          {change}
        </span>
      )}
    </div>
  );
}
