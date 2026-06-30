import React from 'react';

const SIZES = {
  sm: { padding: '0.5em 0.9em', fontSize: 'var(--text-sm)' },
  md: { padding: '0.7em 1.3em', fontSize: 'var(--text-base)' },
  lg: { padding: '0.9em 1.7em', fontSize: 'var(--text-lg)' },
};

/**
 * Button — the content-system CTA (e.g. "Built with RoboSystems",
 * "robosystems.ai"). Primary (filled blue), secondary (outline), or ghost.
 */
export function Button({ children, variant = 'primary', size = 'md', as = 'button', style, ...rest }) {
  const sz = SIZES[size] || SIZES.md;
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5em',
    fontFamily: 'var(--font-display)',
    fontWeight: 600,
    letterSpacing: '0.02em',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'background var(--dur-fast) var(--ease-standard), border-color var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard)',
    textDecoration: 'none',
    ...sz,
  };
  const variants = {
    primary: { background: 'var(--accent)', color: '#fff' },
    secondary: { background: 'transparent', color: 'var(--text-primary)', borderColor: 'var(--border-strong)' },
    ghost: { background: 'transparent', color: 'var(--accent)' },
  };
  const Tag = as;
  return (
    <Tag style={{ ...base, ...(variants[variant] || variants.primary), ...style }} {...rest}>
      {children}
    </Tag>
  );
}
