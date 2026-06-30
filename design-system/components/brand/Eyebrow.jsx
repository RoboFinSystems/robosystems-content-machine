import React from 'react';

/**
 * Eyebrow — the uppercase Orbitron section label that sits above a slide
 * headline (e.g. "01 / THE PAIN"). Pair an index with a label, or pass children.
 */
export function Eyebrow({ index, label, children, accent = true, style, ...rest }) {
  const content =
    children != null
      ? children
      : [
          index != null && (
            <span key="i" style={{ color: accent ? 'var(--eyebrow-accent)' : 'inherit' }}>
              {String(index).padStart(2, '0')}
            </span>
          ),
          index != null && label && <span key="s" style={{ opacity: 0.5, margin: '0 0.5em' }}>/</span>,
          label && <span key="l">{label}</span>,
        ];

  return (
    <div
      style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 600,
        fontSize: 'var(--text-sm)',
        letterSpacing: 'var(--tracking-eyebrow)',
        textTransform: 'uppercase',
        color: 'var(--eyebrow-color)',
        display: 'flex',
        alignItems: 'center',
        ...style,
      }}
      {...rest}
    >
      {content}
    </div>
  );
}
