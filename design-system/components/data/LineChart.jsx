import React from 'react';

// Non-lead series cycle through these; the lead series is always the accent.
const MUTED_SERIES = ['var(--accent-graph)', 'var(--text-muted)', 'var(--blue-300)'];

/**
 * LineChart — a time-series trend chart (label → number over an ordered axis).
 * Single series: pass `data` as an ordered map { FY2022: n, ... }. Multi-series:
 * pass { series: { "Gross margin": {...}, "Net margin": {...} } }. The highlighted
 * series (by name, or the first) draws in the accent; the rest are muted. Inline
 * SVG with non-scaling strokes so the line stays crisp at any width. Use this for
 * trajectories where the *shape* over time is the point; use BarChart to compare
 * discrete periods.
 */
export function LineChart({ data, highlight, format = (v) => v, height = 260, style, ...rest }) {
  const isMulti = data && typeof data === 'object' && data.series && typeof data.series === 'object';
  const raw = isMulti
    ? Object.entries(data.series).map(([name, m]) => ({ name, entries: Object.entries(m) }))
    : [{ name: null, entries: Array.isArray(data) ? data : Object.entries(data || {}) }];

  const labels = (raw[0] ? raw[0].entries : []).map(([l]) => l);
  const allValues = raw.flatMap((s) => s.entries.map(([, v]) => Number(v)));
  const yMax = Math.max(...allValues, 0);
  const yMin = Math.min(...allValues, 0);
  const span = yMax - yMin || 1;

  const leadName = highlight != null ? highlight : raw[0] && raw[0].name;
  const series = raw.map((s, i) => ({
    ...s,
    lead: !isMulti || s.name === leadName,
    color: !isMulti || s.name === leadName ? 'var(--accent)' : MUTED_SERIES[i % MUTED_SERIES.length],
  }));

  const n = labels.length;
  const xAt = (i) => (n > 1 ? (i / (n - 1)) * 100 : 50);
  const yAt = (v) => 100 - ((Number(v) - yMin) / span) * 100;
  const lead = series.find((s) => s.lead) || series[0];
  const lastV = lead && lead.entries.length ? Number(lead.entries[lead.entries.length - 1][1]) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', ...style }} {...rest}>
      {isMulti && (
        <div style={{ display: 'flex', gap: 'var(--space-5)', marginBottom: 'var(--space-1)' }}>
          {series.map((s) => (
            <span
              key={s.name}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                fontFamily: 'var(--font-body)',
                fontSize: 'var(--text-sm)',
                color: s.lead ? 'var(--text-primary)' : 'var(--text-muted)',
                fontWeight: s.lead ? 600 : 400,
              }}
            >
              <span style={{ width: 14, height: 3, borderRadius: 2, background: s.color, display: 'inline-block' }} />
              {s.name}
            </span>
          ))}
        </div>
      )}

      <div style={{ position: 'relative', height, width: '100%' }}>
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ position: 'absolute', inset: 0, overflow: 'visible' }}
        >
          <line
            x1="0"
            y1={yAt(yMin)}
            x2="100"
            y2={yAt(yMin)}
            stroke="var(--border-hairline)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
          {series.filter((s) => !s.lead).map((s) => (
            <polyline
              key={s.name}
              points={s.entries.map(([, v], i) => `${xAt(i)},${yAt(v)}`).join(' ')}
              fill="none"
              stroke={s.color}
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {lead && (
            <polyline
              points={lead.entries.map(([, v], i) => `${xAt(i)},${yAt(v)}`).join(' ')}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="3"
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>

        {/* Lead-series point dots, positioned in real px space so they stay round */}
        {lead && lead.entries.map(([label, v], i) => (
          <div
            key={label}
            style={{
              position: 'absolute',
              left: `${xAt(i)}%`,
              top: `${yAt(v)}%`,
              width: 9,
              height: 9,
              marginLeft: -4.5,
              marginTop: -4.5,
              borderRadius: '50%',
              background: 'var(--accent)',
              boxShadow: i === n - 1 ? 'var(--glow-accent)' : 'none',
            }}
          />
        ))}

        {/* Current (last lead) value tag, right-anchored so it never clips */}
        {lead && lead.entries.length > 0 && (
          <span
            style={{
              position: 'absolute',
              right: 0,
              top: `${yAt(lastV)}%`,
              transform: 'translateY(-130%)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              color: 'var(--accent)',
              whiteSpace: 'nowrap',
            }}
          >
            {format(lastV)}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        {labels.map((l) => (
          <span key={l} style={{ fontFamily: 'var(--font-body)', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}
