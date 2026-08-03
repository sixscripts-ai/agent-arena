# Vercel Web UI Guidelines — Condensed for Agent Arena

Source: Vercel Web Interface Guidelines + Geist design system.

## Core Principles

- Content-first, chrome-minimal: border 1px --border, shadow 0 1px 2px.
- Typography: Geist 400-600, mono for code/meta, display serif optional for hero.
- Radius 8px buttons, 12px cards.
- Motion subtle: pulse for live, no heavy animation.

## Checklist

### Layout
- Max width 1360px px-6 consistent SiteHeader + main.
- 12-col grid only when needed, gap-3-8, avoid nested 12.
- Sticky header with backdrop-blur, border-b.

### Components
- btn: h-8 / h-11 variants, 13px semibold, focus-visible 2px accent.
- card: border + shadow, radius 12.
- Empty states: centered, 10px padded, muted text + primary CTA.
- Skeletons: animate-pulse bg-surface2, match real layout.

### Accessibility
- aria-current page on nav active.
- Contrast muted must pass 4.5:1.
- 11px too small — use 12px minimum for body meta, 11 only for fine meta with uppercase tracking.
- Keyboard: all interactive via Tab, focus-visible.

### Performance
- Fonts: preconnect fonts.googleapis.com, fonts.gstatic.com.
- Vite: dynamic import for heavy routes (design/battle).
- No layout shift: skeleton prevents content jump when formats load.

### Distinctiveness (avoid generic shadcn)
- CodePane keeps dark bg even in light — storytelling.
- Phase line: h-px accent trail vs plain border.
- LIVE badge animated dot.
- Backend URL not raw slice, use hostname pill.
- Event stream mono 11px, truncated but expandable on click ideally.

## Arena-Specific UX Issues Seen on Live

- Format library 0: causes grid empty, should show skeleton 6 cards.
- Engines 0: Set from formats.engine — if formats empty shows 0.
- Avg battle 47s median hardcode — replace live metric or remove.
- Host free models FREE pill success color ambiguous — use accent-soft.
