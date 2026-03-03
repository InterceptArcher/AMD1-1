# Hero Visual Refinement Design

**Date**: 2026-03-03
**Goal**: Elevate the hero & first impression to clean premium SaaS quality (Stripe/Linear level)
**Approach**: Refinement pass — purely visual changes, no structural modifications
**Files affected**: `globals.css`, `page.tsx`, new `useCountUp.ts` hook

---

## 1. Typography Polish

- Headline `tracking-[-0.03em]` for tighter display text
- Font fallback chain: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Subheadline opacity `text-white/65` (from `/70`) for better hierarchy

## 2. Animated Stat Counters

- `useCountUp(target, duration, delay)` hook using `requestAnimationFrame`
- Ease-out curve, 1.5s duration
- Stagger: 0ms, 200ms, 400ms for the three stats
- Suffix support (for the `%` character)

## 3. Spring-Eased Entry Animations

- Replace `ease-out` with `cubic-bezier(0.16, 1, 0.3, 1)` (spring approximation)
- Apply to: `fadeInUp`, `fadeInLeft`, `fadeInRight`, `fadeInScale`
- Slight overshoot gives natural, premium feel

## 4. Form Card Gradient Border

- `conic-gradient` rotating border on `.amd-card-premium`
- Cyan highlight rotates around perimeter over 20s
- `opacity: 0.6` — visible but not distracting
- Implemented via `::before` pseudo-element with `@keyframes rotate`

## 5. Ambient Background Motion

- Three glow divs get CSS animations:
  - Primary (top-right): 20s drift, 40px range
  - Secondary (bottom-left): 25s drift, 30px range
  - Accent (center): 18s drift, 20px range
- Different speeds prevent synchronized movement
- Respects `prefers-reduced-motion`

## 6. Micro-Interactions

- **Stats hover**: `text-shadow: 0 0 20px rgba(0,200,170,0.3)` + `scale(1.08)`, spring transition
- **Trust indicators**: Each staggers 100ms after previous (currently simultaneous)
- **Badge shimmer**: Single-pass gradient sweep on load (not infinite)
- **Form card float**: `translateY(-1px)` on hover

---

## Non-Goals

- No new dependencies (pure CSS + vanilla React hooks)
- No structural component changes
- No accessibility changes (separate effort)
- No wizard/loading/results page changes
