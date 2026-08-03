---
name: arena-ui-ux-review
description: UX/UI design and accessibility audit for Agent Arena webapp https://agent-arena-blond.vercel.app. Uses Vercel web design guidelines, checks token system (cards, btn, code panes), responsive layout, empty states, loading skeletons, keyboard nav, color contrast. Use when user asks improve UI, review UX, check accessibility, polish frontend, design audit, or live site looks broken. Triggers: review UI, UX audit, design polish, accessibility, frontend critique.
---

# Arena UI/UX Review

Specialized frontend reviewer for arena-work/frontend deployed at https://agent-arena-blond.vercel.app

Current stack: Vite + React 18 + Tailwind + shadcn-ish tokens (Geist font, CSS vars --bg --surface --accent #0070F3), Zustand auth, react-router-dom 7.

## When to Use

- "Review my webapp", "UI looks off", "improve UX"
- Home shows "Format library 0" / "Loading formats…" stuck
- LiveBattle dual panes jank, event stream overflow
- DesignOptions / DesignMockup pages need direction

## Audit Framework

Based on Vercel Web Interface Guidelines + custom arena heuristics.

### Step 1 - Automated UI Scan

Run `scripts/ui_scan.py`:

- Parses `src/pages/*.tsx` for:
  - Missing loading skeleton vs raw text "Loading…" (Home, Leaderboard)
  - Hardcoded values: 25 formats, 47s avg battle — should be live or hidden
  - Tailwind color contrast: text-muted on bg-soft passes WCAG?
  - Accessibility: buttons missing aria-label (SiteHeader mobile ☰), inputs missing label linkage
  - Responsive: grid-cols-12 without sm breakpoints, card overflow on mobile
  - Navigation: 404 route minimal, no error boundary
- Checks design tokens in `index.css`: --code-bg #0A0A0A dark vs light, --accent #0070F3 hover states
- Outputs `reports/ui.json`

### Step 2 - Vercel Design Guidelines Checklist

**Layout & Visual Hierarchy**

- [ ] 12-col grid used consistently? Home uses col-span-12 lg:col-span-7/5 correct but pb-12 border separation?
- [ ] Max width 1360px px-6 py-8 — sufficient gutters mobile?
- [ ] Card hierarchy: card p-5 vs card overflow-hidden — consistent border-radius 12px
- [ ] LiveBattle: CodePane header vs raw div — duplicate border treatment?

**Typography**

- [ ] Geist 400/500/600/700 loaded, but h1 tracking -0.03em — needs Instrument Serif for display? Currently all Geist.
- [ ] Mono tokens: Geist Mono vs JetBrains — line numbers 11px muted correct
- [ ] Text sizes: 11px meta too small for WCAG? Should be >=12px or 0.75rem min

**Interaction**

- [ ] Buttons: btn / btn-primary / btn-ghost — focus-visible outline 2px accent correct, but disabled opacity 0.5 pointer-events:none hides reason
- [ ] Selects: class "select" — custom or native? Check cross-browser
- [ ] SSE streaming: blinking cursor animation blink 1s steps(1) — subtle?

**Empty & Loading**

- [ ] Home: "Loading formats…" → skeleton grid needed (FormatCard placeholder)
- [ ] Leaderboard: empty "No rankings yet — run a battle" — good but needs CTA
- [ ] History: localStorage fallback silently fails — needs user feedback
- [ ] NewBattle: no validation for empty providers list

**Accessibility**

- [ ] Header nav links have .active class but no aria-current
- [ ] Mobile menu button "☰" no aria-label (has but generic)
- [ ] CodePane pre break-all truncates but screen reader?
- [ ] Contrast: --fg-muted #71717A on #FFFFFF fails AA? Check ratio

**Performance & Polish**

- [ ] Live site shows "0 engines" — engines Set from formats.engine filter Boolean, if formats [] then 0 — should hide or skeleton
- [ ] Host free models pill FREE with success dot — semantic?
- [ ] Backend URL slice(0,32)… odd UX — use hostname only
- [ ] Artifacts event stream max-h-[160px] overflow-auto — should virtualize

### Step 3 - Live Webapp Verification

Use Playwright tool (or firecrawl scrape) to screenshot https://agent-arena-blond.vercel.app:

- Check hero: "Models fight. You watch code." — line break intentional?
- Check FormatCard: large={i<2} causes first 2 large — layout shifts if 0 formats
- Check responsive 375px vs 1360px

Script `scripts/screenshot_live.py` (optional) can use playwright to capture.

### Step 4 - Generate Polished Fixes

Produce `reports/ui-improvements.md` with sections:

#### Immediate (visual bugs causing "0" display)

- Fix Home: replace hardcoded {formats.length || 25} with real loading + fallback; show skeleton
- Fix engines: const enginesCount = new Set(formats.map(f=>f.engine)).size — guard empty
- Fix api.ts BASE: ensure VITE_MODAL_URL env set in vercel, else graceful error UI not empty

#### Design System Polish (Vercel guidelines)

- Introduce page-level ErrorBoundary
- Add FormatCard skeleton loader
- Replace 11px meta with 12px + uppercase tracking for readability
- Improve CodePane: line numbers 80 slice truncates silently → show "+59 lines hidden"
- Add link styles, hover states for table rows (already hover:bg-soft/60 good)

#### Accessibility Uplift

- Add aria-current="page" to nav active
- Add labels to NewBattle selects, link via htmlFor
- Increase contrast mutants
- Ensure keyboard live battle stop/save reachable

#### Distinctive Touch (not templated)

- Suggest: duel visualization line (build→break→judge) use accent trail, not plain h-px
- Hero: tiny token stream animation behind card? Keep minimal
- Code pane: theme-aware code-bg stays dark in light mode — intentional, good (code storytelling) but add toggle

## Resources

- `references/design-tokens.md` — extracted tokens from index.css + tailwind.config
- `references/vacui-checklist.md` — Vercel UI guidelines condensed for arena
- `references/competitors.md` — lmsys, vercel ai playground patterns
- `assets/mockups/` — optional before/after wireframes

## Scripts

- `scripts/ui_scan.py` — grep + AST for UI anti-patterns
- `scripts/check_contrast.py` — computes contrast ratios from CSS vars
- `scripts/gen_report.py` → `reports/ui-polish.html` visual report

## Validation

- `cd frontend && pnpm run lint && pnpm run check && pnpm run build`
- Open `reports/ui-polish.html` in browser, verify before/after
- Lighthouse check: devtools perf, a11y

## Example

User: "Review https://agent-arena-blond.vercel.app UI"
→ Scrape live, run ui_scan.py, check design tokens, produce checklist with severity, propose fix for "Format library 0" bug, suggest skeleton loaders, a11y fixes, write report, optionally run dev server and screenshot.
