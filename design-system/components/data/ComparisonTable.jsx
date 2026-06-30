import React from 'react';

/**
 * ComparisonTable — a two-column framing table (e.g. bull case vs bear case),
 * each column headed with a tinted label and a list of points. Also works as a
 * generic data table when passed `columns` + `rows`.
 */
export function ComparisonTable({ left, right, columns, rows, style, ...rest }) {
  // Two-column "framework" mode
  if (left && right) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)', ...style }} {...rest}>
        {[left, right].map((col, i) => (
          <div
            key={i}
            style={{
              background: 'var(--surface-card)',
              border: '1px solid var(--border-hairline)',
              boxShadow: 'var(--ring-inset)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-6)',
              borderTop: `3px solid ${i === 0 ? 'var(--data-positive)' : 'var(--data-negative)'}`,
            }}
          >
            <div
              style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                color: i === 0 ? 'var(--data-positive)' : 'var(--data-negative)',
                marginBottom: 'var(--space-4)',
              }}
            >
              {col.title}
            </div>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {col.points.map((p, j) => (
                <li key={j} style={{ display: 'flex', gap: 'var(--space-3)', fontFamily: 'var(--font-body)', fontSize: 'var(--text-lg)', color: 'var(--text-body)', lineHeight: 'var(--leading-snug)' }}>
                  <span style={{ color: i === 0 ? 'var(--data-positive)' : 'var(--data-negative)', flex: 'none' }}>{i === 0 ? '+' : '–'}</span>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  // Generic table mode
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-body)', ...style }} {...rest}>
      <thead>
        <tr>
          {columns.map((c, i) => (
            <th
              key={i}
              style={{
                textAlign: i === 0 ? 'left' : 'right',
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--text-muted)',
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '2px solid var(--border-strong)',
              }}
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, ri) => (
          <tr key={ri}>
            {row.map((cell, ci) => (
              <td
                key={ci}
                style={{
                  textAlign: ci === 0 ? 'left' : 'right',
                  fontFamily: ci === 0 ? 'var(--font-body)' : 'var(--font-mono)',
                  fontSize: 'var(--text-lg)',
                  fontWeight: ci === 0 ? 500 : 600,
                  color: ci === 0 ? 'var(--text-primary)' : 'var(--text-body)',
                  padding: 'var(--space-4)',
                  borderBottom: '1px solid var(--border-hairline)',
                }}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
