# Design

## Theme

Human, reassuring healthtech for a claims-decisioning tool. Pure-white canvas, a deep moss-olive brand color carrying the warmth, generous space, and calm typography. Warmth comes from a soft serif and plain language — never from a tinted background, rounded cuteness, or emoji. Restrained color strategy: brand green ≤10% of surface, semantic status colors reserved exclusively for verdicts.

## Color

OKLCH throughout. Body bg is literally pure white — the brand color does the work.

### Neutrals
- `--bg`: `oklch(1 0 0)` — pure white canvas
- `--surface`: `oklch(0.985 0 0)` — panels, raised areas
- `--ink`: `oklch(0.23 0.008 120)` — primary text (≈13:1 on white)
- `--ink-muted`: `oklch(0.45 0.01 120)` — secondary text (≥4.5:1, never lighter for body)
- `--ink-faint`: `oklch(0.60 0.01 120)` — large/non-essential only
- `--border`: `oklch(0.91 0.004 120)` — hairlines
- `--border-strong`: `oklch(0.84 0.005 120)`

### Brand
- `--primary`: `oklch(0.48 0.097 118)` — deep moss-olive; nav, primary actions, links
- `--primary-hover`: `oklch(0.43 0.097 118)`
- `--primary-ink`: `oklch(0.99 0 0)` — text on primary
- `--primary-soft`: `oklch(0.96 0.02 118)` — selected rows, brand tint backgrounds
- `--accent`: `oklch(0.62 0.12 50)` — clay; sparing highlights, focus glow only

### Semantic status (verdicts only — always paired with icon + label)
- approved: `--ok` `oklch(0.55 0.13 150)`, bg `oklch(0.96 0.03 150)`
- partial: `--warn` `oklch(0.64 0.12 75)`, bg `oklch(0.96 0.04 75)`
- rejected: `--bad` `oklch(0.52 0.16 28)`, bg `oklch(0.96 0.04 28)`
- review: `--info` `oklch(0.54 0.12 255)`, bg `oklch(0.96 0.03 255)`

Focus ring: 2px `--accent` at 0.5 alpha, 2px offset. Status never communicated by color alone.

## Typography

Pair on a contrast axis (serif + sans). No Inter/Geist default.
- **Display / headings**: `Fraunces` (optical soft serif) — warmth + character. Weights 400/500/600. `text-wrap: balance` on h1–h3, letter-spacing ≥ -0.02em.
- **Body / UI**: `IBM Plex Sans` — humanist, healthtech-credible, sharp at small sizes. 400/500/600.
- **Numeric / IDs**: `IBM Plex Mono` with `font-variant-numeric: tabular-nums` for amounts and claim IDs.
- Scale (clamp): h1 `clamp(1.75rem, 1.2rem + 2vw, 2.5rem)`; h2 `1.5rem`; h3 `1.2rem`; body `1rem/1.6`; small `0.875rem`. Body measure ≤ 70ch.

## Spacing & Shape

- 4px base scale: 4, 8, 12, 16, 24, 32, 48, 64, 96. Vary spacing for rhythm; let the decision breathe.
- Radius: `--r-sm` 6px, `--r-md` 10px, `--r-lg` 16px. Moderate — not pill-rounded (avoids playful).
- Elevation: subtle layered shadows, low opacity, tinted toward ink not black. The decision card and dropzone get the only real elevation.
- Hairline borders over heavy cards. No identical card grids; no `border-left` accent stripes.

## Components

- **Verdict badge** — 4 states; icon + label + status color + soft bg. The page's loudest element.
- **Confidence meter** — horizontal track with an animated fill; numeric % in mono; low confidence (<0.8) visibly distinct, paired with a "routed for review" note.
- **Money breakdown** — claimed → deductions (co-pay / network discount) → approved, right-aligned tabular figures, the approved figure largest.
- **Live processing stepper** — Reading → Extracting → Checking coverage → Adjudicating → Decided. Sequential reveal mirroring the real pipeline.
- **Upload dropzone** — drag-drop with file chips; segmented toggle to a structured-JSON path.
- **Claims table** — calm rows (not a dense grid), status chip, amounts, drill-in.
- **Audit trail** — expandable ordered list of rules evaluated (from the engine's `audit_trail`).

## Motion

- Durations 150–450ms; easing `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out-expo). No bounce/elastic.
- Stepper items reveal in sequence; the verdict and approved amount animate in last.
- Confidence fill animates from 0 on mount.
- `@media (prefers-reduced-motion: reduce)`: replace all with instant/crossfade.

## Z-index scale
dropdown 10 · sticky 20 · backdrop 30 · modal 40 · toast 50 · tooltip 60. No arbitrary 999.
