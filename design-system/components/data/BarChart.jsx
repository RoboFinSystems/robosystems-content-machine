import React from 'react';

/**
 * BarChart — a horizontal-label / vertical-bar chart for trend data
 * (label → number). The highlighted bar uses the accent; the rest are muted.
 * Values are display-formatted via the `format` prop.
 */
export function BarChart({ data, highlight, format = (v) => v, height = 260, style, ...rest }) {
  const entries = Array.isArray(data) ? data : Object.entries(data);
  const max = Math.max(...entries.map(([, v]) => Number(v)));
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 'var(--space-4)',
        height,
        ...style,
      }}
      {...rest}
    >
      {entries.map(([label, value]) => {
        const isHi = label === highlight;
        const pct = max > 0 ? (Number(value) / max) * 100 : 0;
        return (
          <div key={label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end', gap: 'var(--space-3)' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: isHi ? 'var(--accent)' : 'var(--text-body)',
              }}
            >
              {format(value)}
            </span>
            <div
              style={{
                width: '100%',
                height: `${pct}%`,
                minHeight: 4,
                borderRadius: 'var(--radius-sm) var(--radius-sm) 2px 2px',
                background: isHi ? 'var(--accent)' : 'var(--ink-700)',
                boxShadow: isHi ? 'var(--glow-accent)' : 'none',
                transition: 'height var(--dur-reveal) var(--ease-out)',
              }}
            />
            <span
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-sm)',
                color: isHi ? 'var(--text-primary)' : 'var(--text-muted)',
                fontWeight: isHi ? 600 : 400,
              }}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
