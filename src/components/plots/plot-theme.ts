// Shared Observable Plot styling, kept in sync with tailwind.config.mjs
// (colors.paper / colors.ink / colors.accent) and the site's type system.
// Plot renders plain SVG, so these are applied through `style` and mark
// channel colors rather than CSS classes.

export const COLORS = {
  paper: '#faf9f6',
  ink: '#1a1a1a',
  inkMuted: 'rgb(26 26 26 / 0.55)',
  inkFaint: 'rgb(26 26 26 / 0.12)',
  accent: '#003366',
  accentMuted: 'rgb(0 51 102 / 0.35)',
  hub: '#8a1f1f'
} as const;

export const FONT_MONO = '"JetBrains Mono", "Fira Code", ui-monospace, monospace';
export const FONT_SERIF = 'Georgia, "Computer Modern Serif", ui-serif, serif';

/** Base options merged into every Plot.plot() call on this site. */
export const baseStyle = {
  background: 'transparent',
  color: COLORS.ink,
  fontFamily: FONT_MONO,
  fontSize: '12px'
} as const;

export const gridStyle = {
  stroke: COLORS.inkFaint,
  strokeDasharray: '0'
} as const;

/**
 * Renders a plot into `container`, sized to the container's current width,
 * and re-renders on viewport resize so the figure stays readable at any
 * breakpoint without ever exceeding it (no page-level horizontal overflow).
 *
 * `make(width)` must return a freshly built Plot SVG/HTML element — Plot
 * figures aren't resizable in place, so each resize discards and rebuilds.
 */
export function renderResponsive(container: HTMLElement, make: (width: number) => SVGElement | HTMLElement): void {
  let frame: number | null = null;

  const paint = () => {
    const width = Math.max(container.clientWidth, 220);
    container.replaceChildren(make(width));
  };

  paint();

  const observer = new ResizeObserver(() => {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(paint);
  });
  observer.observe(container);
}

/** Truncates a label to a maximum character length with a word-aware ellipsis. */
export function truncate(label: string, max = 30): string {
  if (label.length <= max) return label;
  const cut = label.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return `${cut.slice(0, lastSpace > 10 ? lastSpace : max)}…`;
}

const SUBSCRIPT_DIGITS: Record<string, string> = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
};

/** Renders e.g. Nk(5) as "N₅" for axis and figure labels. */
export function subscript(n: number): string {
  return String(n)
    .split('')
    .map((c) => SUBSCRIPT_DIGITS[c] ?? c)
    .join('');
}
