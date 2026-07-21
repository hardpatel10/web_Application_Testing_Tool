/**
 * Chart color palette for the Intelligence Dashboard.
 *
 * This app forces dark mode unconditionally (see `components/theme-provider.tsx`),
 * so only the dark-surface steps of the dataviz reference palette are used here
 * -- no light-mode variants, no `prefers-color-scheme` branching. Values are the
 * validated dark-mode categorical/status steps (CVD ΔE and contrast checked via
 * the dataviz skill's `validate_palette.js`, not eyeballed).
 */

/** Fixed hue order -- never cycled, never reassigned by rank (see dataviz skill). */
export const CATEGORICAL: readonly string[] = [
  "#3987e5", // blue
  "#008300", // green
  "#d55181", // magenta
  "#c98500", // yellow
  "#199e70", // aqua
  "#d95926", // orange
  "#9085e9", // violet
  "#e66767", // red
];

/** Reserved status colors -- never reused for a categorical series. */
export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
} as const;

/** Finding severity -> a fixed status color. Info is a neutral, non-risk tone, not part of the status set. */
export const SEVERITY_COLOR: Record<string, string> = {
  critical: STATUS.critical,
  high: STATUS.serious,
  medium: STATUS.warning,
  low: STATUS.good,
  info: "#898781",
};

export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;

/** Chart chrome, matching this app's existing dark theme tokens (not the dataviz reference hexes). */
export const CHART_CHROME = {
  grid: "hsl(var(--border))",
  axis: "hsl(var(--muted-foreground))",
  tooltipBg: "hsl(var(--popover))",
  tooltipBorder: "hsl(var(--border))",
  text: "hsl(var(--foreground))",
  mutedText: "hsl(var(--muted-foreground))",
};

export function categoricalColor(index: number): string {
  return CATEGORICAL[index % CATEGORICAL.length];
}
