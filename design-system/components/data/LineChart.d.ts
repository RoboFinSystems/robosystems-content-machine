import * as React from 'react';

/** Single series: an ordered map of axis label -> number. */
export type LineSeries = Record<string, number>;

export interface LineChartProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Single series as an ordered map `{ FY2022: 1017375000, ... }`, or multi-series
   * `{ series: { "Gross margin": { ... }, "Net margin": { ... } } }`.
   */
  data: LineSeries | { series: Record<string, LineSeries> };
  /** Multi-series: the series name to draw in the accent (others are muted). */
  highlight?: string;
  /** Formats the current (last lead-series) value tag. Default: identity. */
  format?: (value: number) => React.ReactNode;
  /** Chart height in px. Default 260. */
  height?: number;
}

/**
 * Time-series trend chart. Use for trajectories where the shape over time is the
 * point (revenue, margins, price); use BarChart to compare discrete periods.
 */
export declare function LineChart(props: LineChartProps): JSX.Element;
