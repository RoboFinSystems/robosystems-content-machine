import React from 'react';
import { BrandMark } from './BrandMark.jsx';

/**
 * SourceFooter — the slide's bottom rule: a source-attribution line on the
 * left, the RoboSystems lockup on the right, divided from the content by a
 * hairline. Every research slide carries one.
 */
export function SourceFooter({ source, brand = true, brandLabel = 'RoboSystems', style, ...rest }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 'var(--space-4)',
        borderTop: '1px solid var(--border-hairline)',
        paddingTop: 'var(--space-4)',
        ...style,
      }}
      {...rest}
    >
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-xs)',
          color: 'var(--text-faint)',
          letterSpacing: 'var(--tracking-mono)',
        }}
      >
        {source}
      </span>
      {brand && (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--text-muted)' }}>
          <BrandMark size={18} />
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: 'var(--text-xs)',
              letterSpacing: '0.04em',
            }}
          >
            {brandLabel}
          </span>
        </span>
      )}
    </div>
  );
}
