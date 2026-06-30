import React from 'react';

const TONES = {
  neutral: { bg: 'rgba(59,122,245,0.14)', fg: 'var(--blue-300)', bd: 'rgba(59,122,245,0.35)' },
  accent: { bg: 'var(--accent)', fg: '#fff', bd: 'transparent' },
  positive: { bg: 'rgba(49,196,141,0.14)', fg: 'var(--data-positive)', bd: 'rgba(49,196,141,0.35)' },
  negative: { bg: 'rgba(249,128,128,0.14)', fg: 'var(--data-negative)', bd: 'rgba(249,128,128,0.35)' },
  warning: { bg: 'rgba(255,138,76,0.14)', fg: 'var(--data-warning)', bd: 'rgba(255,138,76,0.35)' },
  graph: { bg: 'rgba(0,212,170,0.14)', fg: 'var(--teal-graph)', bd: 'rgba(0,212,170,0.4)' },
};

/**
 * Badge — a small uppercase pill for status banners (COVERAGE UPDATE,
 * INITIATING COVERAGE) and inline tags. Solid `accent` or tinted tones.
 */
export function Badge({ children, tone = 'neutral', solid = false, style, ...rest }) {
  const t = solid ? TONES.accent : TONES[tone] || TONES.neutral;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.4em',
        fontFamily: 'var(--font-display)',
        fontWeight: 600,
        fontSize: 'var(--text-2xs)',
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        lineHeight: 1,
        padding: '0.5em 0.85em',
        borderRadius: 'var(--radius-pill)',
        background: t.bg,
        color: t.fg,
        border: `1px solid ${t.bd}`,
        whiteSpace: 'nowrap',
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
