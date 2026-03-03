# Hero Visual Refinement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Elevate the hero & first impression to clean premium SaaS quality (Stripe/Linear level) with spring animations, animated stat counters, gradient card border, ambient background motion, and micro-interactions.

**Architecture:** Pure CSS + one small React hook. No new dependencies. All changes are visual-only — no component restructuring, no data flow changes, no accessibility changes.

**Tech Stack:** CSS keyframes, Tailwind utility classes, React `useEffect` + `requestAnimationFrame`

---

### Task 1: Create useCountUp hook

**Files:**
- Create: `frontend/src/hooks/useCountUp.ts`
- Test: `frontend/__tests__/useCountUp.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/__tests__/useCountUp.test.tsx
import { renderHook, act } from '@testing-library/react';
import { useCountUp } from '../src/hooks/useCountUp';

// Mock requestAnimationFrame for deterministic tests
beforeEach(() => {
  jest.useFakeTimers();
  let rafId = 0;
  jest.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
    rafId++;
    setTimeout(() => cb(performance.now()), 16);
    return rafId;
  });
  jest.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
    clearTimeout(id);
  });
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('useCountUp', () => {
  it('starts at 0', () => {
    const { result } = renderHook(() => useCountUp(33, 1500, 0));
    expect(result.current).toBe(0);
  });

  it('reaches target value after duration', () => {
    const { result } = renderHook(() => useCountUp(33, 1500, 0));
    act(() => {
      jest.advanceTimersByTime(2000);
    });
    expect(result.current).toBe(33);
  });

  it('respects delay before starting', () => {
    const { result } = renderHook(() => useCountUp(58, 1500, 500));
    act(() => {
      jest.advanceTimersByTime(400);
    });
    expect(result.current).toBe(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npx jest __tests__/useCountUp.test.tsx --no-cache`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```ts
// frontend/src/hooks/useCountUp.ts
import { useState, useEffect, useRef } from 'react';

export function useCountUp(target: number, duration = 1500, delay = 0): number {
  const [value, setValue] = useState(0);
  const startTimeRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const timeout = setTimeout(() => {
      const animate = (timestamp: number) => {
        if (startTimeRef.current === null) {
          startTimeRef.current = timestamp;
        }
        const elapsed = timestamp - startTimeRef.current;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic: decelerates toward end
        const eased = 1 - Math.pow(1 - progress, 3);
        setValue(Math.round(eased * target));

        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        }
      };
      rafRef.current = requestAnimationFrame(animate);
    }, delay);

    return () => {
      clearTimeout(timeout);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [target, duration, delay]);

  return value;
}
```

**Step 4: Run test to verify it passes**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npx jest __tests__/useCountUp.test.tsx --no-cache`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add frontend/src/hooks/useCountUp.ts frontend/__tests__/useCountUp.test.tsx
git commit -m "feat: add useCountUp hook for animated stat counters"
```

---

### Task 2: Upgrade entry animations to spring easing

**Files:**
- Modify: `frontend/src/app/globals.css` (lines 416-434: the `.animate-fade-in-*` classes)

**Step 1: Write the failing test**

No unit test for CSS — this is a visual-only change. Verify by inspection.

**Step 2: Change animation timing functions to spring approximation**

In `globals.css`, replace the `ease-out` timing on all four entry animation classes with `cubic-bezier(0.16, 1, 0.3, 1)` (spring overshoot). Also increase distance slightly for more drama:

Replace:
```css
.animate-fade-in-up {
  animation: fadeInUp 0.6s ease-out forwards;
  opacity: 0;
}

.animate-fade-in-left {
  animation: fadeInLeft 0.6s ease-out forwards;
  opacity: 0;
}

.animate-fade-in-right {
  animation: fadeInRight 0.6s ease-out forwards;
  opacity: 0;
}

.animate-fade-in-scale {
  animation: fadeInScale 0.5s ease-out forwards;
  opacity: 0;
}
```

With:
```css
.animate-fade-in-up {
  animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.animate-fade-in-left {
  animation: fadeInLeft 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.animate-fade-in-right {
  animation: fadeInRight 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.animate-fade-in-scale {
  animation: fadeInScale 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}
```

Also increase `fadeInUp` translateY from `20px` to `30px`, `fadeInLeft`/`fadeInRight` translateX from `20px` to `30px` — more travel = more dramatic spring settle.

**Step 3: Verify visually**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npm run dev`
Check: Entry animations have a subtle spring overshoot feel.

**Step 4: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat: upgrade entry animations to spring easing"
```

---

### Task 3: Add ambient background glow motion

**Files:**
- Modify: `frontend/src/app/globals.css` (add 3 new keyframes + classes)
- Modify: `frontend/src/app/page.tsx` (lines 152-158: background glow divs)

**Step 1: Add CSS keyframes for ambient drift**

Add to `globals.css` (after the existing `amd-grid-pattern` section, around line 59):

```css
/* Ambient background glow drift */
@keyframes ambientDrift1 {
  0%, 100% { transform: translate(33%, -33%); }
  50% { transform: translate(28%, -28%); }
}

@keyframes ambientDrift2 {
  0%, 100% { transform: translate(-33%, 33%); }
  50% { transform: translate(-28%, 38%); }
}

@keyframes ambientDrift3 {
  0%, 100% { transform: translate(-50%, -50%); opacity: 0.03; }
  50% { transform: translate(-45%, -55%); opacity: 0.05; }
}

.ambient-glow-1 {
  animation: ambientDrift1 20s ease-in-out infinite;
}

.ambient-glow-2 {
  animation: ambientDrift2 25s ease-in-out infinite;
}

.ambient-glow-3 {
  animation: ambientDrift3 18s ease-in-out infinite;
}
```

**Step 2: Apply classes to background divs in page.tsx**

Replace lines 152-158 in `page.tsx`:

From:
```tsx
<div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#00c8aa]/[0.07] rounded-full blur-[150px] translate-x-1/3 -translate-y-1/3" />
<div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[#00c8aa]/[0.04] rounded-full blur-[120px] -translate-x-1/3 translate-y-1/3" />
<div className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-blue-500/[0.03] rounded-full blur-[100px] -translate-x-1/2 -translate-y-1/2" />
```

To:
```tsx
<div className="absolute top-0 right-0 w-[800px] h-[800px] bg-[#00c8aa]/[0.07] rounded-full blur-[150px] ambient-glow-1" />
<div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[#00c8aa]/[0.04] rounded-full blur-[120px] ambient-glow-2" />
<div className="absolute top-1/2 left-1/2 w-[400px] h-[400px] bg-blue-500/[0.03] rounded-full blur-[100px] ambient-glow-3" />
```

Note: The initial translate values are now baked into the keyframes (matching the previous static values as the start/end positions).

**Step 3: Verify visually**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npm run dev`
Check: Background glows drift subtly. Should be barely noticeable but make the page feel alive.

**Step 4: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/app/page.tsx
git commit -m "feat: add ambient drift animation to background glows"
```

---

### Task 4: Add animated gradient border to form card

**Files:**
- Modify: `frontend/src/app/globals.css` (update `.amd-card-premium::before`)

**Step 1: Add rotating gradient keyframe**

Add to `globals.css` after the existing `.amd-card-premium::before` block (replace it):

```css
@keyframes borderRotate {
  from { --border-angle: 0deg; }
  to { --border-angle: 360deg; }
}

.amd-card-premium {
  @apply bg-gradient-to-br from-white/[0.08] to-white/[0.02] border border-white/20 rounded-2xl backdrop-blur-md;
  position: relative;
}

.amd-card-premium::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: conic-gradient(
    from var(--border-angle, 0deg),
    transparent 40%,
    rgba(0, 200, 170, 0.4) 50%,
    transparent 60%
  );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  animation: borderRotate 20s linear infinite;
}
```

Note: `@property --border-angle` is needed for animating CSS custom properties. Add at top of file:

```css
@property --border-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}
```

**Step 2: Verify visually**

Run dev server. The form card border should have a subtle cyan highlight that slowly rotates around the perimeter. If `@property` isn't supported (Firefox), it degrades gracefully to the static gradient.

**Step 3: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "feat: add rotating gradient border to premium card"
```

---

### Task 5: Add stat counter animations + micro-interactions to page.tsx

**Files:**
- Modify: `frontend/src/app/page.tsx` (stats section ~lines 210-223, trust indicators ~226-247, badge ~187-190)

**Step 1: Import and wire useCountUp to stats**

Add import at top of `page.tsx`:
```tsx
import { useCountUp } from '@/hooks/useCountUp';
```

Inside `HomeContent` function body (after the state declarations), add:
```tsx
const statLeaders = useCountUp(33, 1500, 400);
const statChallengers = useCountUp(58, 1500, 600);
const statObservers = useCountUp(9, 1500, 800);
```

**Step 2: Replace hardcoded stat values**

Replace the stats grid (lines ~210-223):

From:
```tsx
<div className="grid grid-cols-3 gap-6 sm:gap-8 animate-fade-in-up stagger-4">
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-[#00c8aa] transition-transform group-hover:scale-105">33%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Leaders</div>
  </div>
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-white transition-transform group-hover:scale-105">58%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Challengers</div>
  </div>
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-white/60 transition-transform group-hover:scale-105">9%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Observers</div>
  </div>
</div>
```

To:
```tsx
<div className="grid grid-cols-3 gap-6 sm:gap-8 animate-fade-in-up stagger-4">
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-[#00c8aa] transition-all duration-300 group-hover:scale-108 group-hover:[text-shadow:0_0_20px_rgba(0,200,170,0.4)]">{statLeaders}%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Leaders</div>
  </div>
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-white transition-all duration-300 group-hover:scale-108 group-hover:[text-shadow:0_0_20px_rgba(0,200,170,0.3)]">{statChallengers}%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Challengers</div>
  </div>
  <div className="amd-stat group cursor-default">
    <div className="text-3xl sm:text-4xl font-bold text-white/60 transition-all duration-300 group-hover:scale-108 group-hover:[text-shadow:0_0_20px_rgba(0,200,170,0.2)]">{statObservers}%</div>
    <div className="text-sm text-white/50 mt-2 font-medium tracking-wide">Observers</div>
  </div>
</div>
```

**Step 3: Stagger trust indicators**

Replace the trust indicators section (lines ~226-247). Add individual stagger classes to each trust item:

From:
```tsx
<div className="mt-10 pt-8 border-t border-white/10 animate-fade-in-up stagger-5">
  <div className="flex flex-wrap items-center gap-6 text-sm text-white/40">
    <div className="flex items-center gap-2">...</div>
    <div className="flex items-center gap-2">...</div>
    <div className="flex items-center gap-2">...</div>
  </div>
</div>
```

To (add individual animation to each child):
```tsx
<div className="mt-10 pt-8 border-t border-white/10">
  <div className="flex flex-wrap items-center gap-6 text-sm text-white/40">
    <div className="flex items-center gap-2 animate-fade-in-up stagger-5">
      ...Personalized to your role...
    </div>
    <div className="flex items-center gap-2 animate-fade-in-up stagger-6">
      ...Industry-specific insights...
    </div>
    <div className="flex items-center gap-2 animate-fade-in-up stagger-7">
      ...Instant PDF download...
    </div>
  </div>
</div>
```

**Step 4: Tighten headline typography**

Replace the h1 (line ~198):

From:
```tsx
<h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.08] mb-6 text-white animate-fade-in-up stagger-2">
```

To:
```tsx
<h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-[1.08] tracking-[-0.03em] mb-6 text-white animate-fade-in-up stagger-2">
```

And the subheadline (line ~205):

From:
```tsx
<p className="text-lg sm:text-xl text-white/70 leading-relaxed mb-10 max-w-lg animate-fade-in-up stagger-3">
```

To:
```tsx
<p className="text-lg sm:text-xl text-white/65 leading-relaxed mb-10 max-w-lg animate-fade-in-up stagger-3">
```

**Step 5: Add badge shimmer**

In `globals.css`, add a single-pass shimmer for the badge:

```css
/* Badge shimmer — single sweep on load */
@keyframes badgeShimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

.amd-badge {
  @apply inline-flex items-center gap-2 px-4 py-2 rounded-full;
  @apply border border-[#00c8aa]/40 bg-[#00c8aa]/10;
  @apply text-sm text-[#00c8aa] font-semibold;
  background-image: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 200, 170, 0.15) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: badgeShimmer 1.5s ease-out 0.5s 1, badge-pulse 2s ease-in-out 2s infinite;
}
```

This plays one shimmer sweep on load (at 0.5s delay), then transitions to the existing soft pulse.

**Step 6: Verify visually**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npm run dev`
Check:
- Stats count up from 0 with stagger
- Stats glow cyan on hover
- Trust indicators appear sequentially
- Headline has tighter tracking
- Badge does a shimmer sweep on load

**Step 7: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/globals.css frontend/src/hooks/useCountUp.ts
git commit -m "feat: add animated stat counters, micro-interactions, and typography polish"
```

---

### Task 6: Add form card hover float effect

**Files:**
- Modify: `frontend/src/app/page.tsx` (the form card wrapper div, line ~252)

**Step 1: Add hover transition to form card wrapper**

Replace line ~252:

From:
```tsx
<div className="amd-card-premium p-8 lg:p-10 amd-glow-intense">
```

To:
```tsx
<div className="amd-card-premium p-8 lg:p-10 amd-glow-intense transition-transform duration-500 ease-out hover:-translate-y-1">
```

**Step 2: Verify visually**

Hover over form card — should float up 4px smoothly.

**Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: add subtle hover float to form card"
```

---

### Task 7: Add scale-108 to Tailwind config

**Files:**
- Modify: `frontend/tailwind.config.ts` or `tailwind.config.js`

**Step 1: Check which config file exists**

Run: `ls /workspaces/AMD1-1_Alpha/frontend/tailwind.config.*`

**Step 2: Add custom scale value**

In the `theme.extend` section, add:
```js
scale: {
  '108': '1.08',
},
```

This enables the `scale-108` class used in Task 5's stat hover effect.

**Step 3: Commit**

```bash
git add frontend/tailwind.config.*
git commit -m "feat: add scale-108 to Tailwind config"
```

---

### Task 8: Run full test suite + visual verification

**Step 1: Run existing tests**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npx jest --no-cache`
Expected: All tests pass (including new useCountUp tests). Note: some pre-existing tests may already be failing per git status — only new failures count.

**Step 2: Run dev server and verify**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npm run dev`

Visual checklist:
- [ ] Background glows drift slowly (20-25s cycle)
- [ ] Hero text slides in with spring overshoot
- [ ] Stats count from 0 to target values
- [ ] Stats glow cyan on hover
- [ ] Form card has rotating gradient border
- [ ] Form card floats up on hover
- [ ] Badge shimmer sweeps once on load
- [ ] Trust indicators appear sequentially
- [ ] Headline tracking is tighter
- [ ] All animations respect prefers-reduced-motion

**Step 3: Build check**

Run: `cd /workspaces/AMD1-1_Alpha/frontend && npm run build`
Expected: Build succeeds with no errors.

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address visual regression from refinement pass"
```
