import React from 'react';

const TONES = {
  positive: { fg: 'var(--data-positive)', glow: '0 0 90px -20px rgba(49,196,141,0.5)' },
  negative: { fg: 'var(--data-negative)', glow: '0 0 90px -20px rgba(249,128,128,0.5)' },
  neutral: { fg: 'var(--accent)', glow: 'var(--glow-accent)' },
  warning: { fg: 'var(--data-warning)', glow: '0 0 90px -20px rgba(255,138,76,0.5)' },
};

/**
 * Callout — one enormous number that tells the story (e.g. "44%"), with a
 * label above and a context line below. The single-figure slide kind.
 */
export function Callout({ value, label, context, tone = 'neutral', align = 'center', style, ...rest }) {
  const t = TONES[tone] || TONES.neutral;
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: align === 'center' ? 'center' : 'flex-start',
        textAlign: align,
        gap: 'var(--space-5)',
        ...style,
      }}
      {...rest}
    >
      {label && (
        <span
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: 'var(--text-xl)',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            maxWidth: '26ch',
          }}
        >
          {label}
        </span>
      )}
      <span
        style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 900,
          fontSize: 'var(--text-7xl)',
          lineHeight: 0.9,
          letterSpacing: '-0.03em',
          color: t.fg,
          textShadow: t.glow,
        }}
      >
        {value}
      </span>
      {context && (
        <span
          style={{
            fontFamily: 'var(--font-body)',
            fontSize: 'var(--text-xl)',
            lineHeight: 'var(--leading-snug)',
            color: 'var(--text-body)',
            maxWidth: '34ch',
          }}
        >
          {context}
        </span>
      )}
    </div>
  );
}
