# Proposal: Web UI Redesign

## Intent

Replace gameScraper's Bootstrap + dual-icon-CDN frontend (templates + static) with a maintainable vanilla CSS design-token system and component layer, fix 5 UI bugs, close a11y/responsive gaps. Backend routes, response shapes, security contract stay locked.

## Motivation

| Pain | Evidence |
|---|---|
| Duplicated store blocks | Markup/JS/CSS copied ×3 (ofertas.css: three ~60-line blocks) |
| Bootstrap fights design | ~80 override lines in index.css; 55 KB bundle used for modal+collapse only |
| Cover fallback dead | `src=""` resolves to page URL; `=== ''` check (index.html:162) never fires |
| Free-game crash | `precio==0` → `Infinity%` discount |
| A11y gaps | `lang="en"` on Spanish UI; no `<h1>` on /ofertas; empty `alt`; `align='center'`; unlabeled icon button; no `<noscript>` (JS-off = forever spinners, form 405s) |
| No phone story | ≤991px only; 360px overflows (`.nombre` 350px, EGS margin) |
| No theme system | Hardcoded hexes; no `prefers-color-scheme` |
| Junk | leftover `console.log`; iOS-broken `background-attachment:fixed`; 504 partials discarded; 6+ hardcoded `$`; 2 icon CDNs |

## Scope

### In Scope
- Atomic rewrite of templates + CSS + JS: `:root` tokens, component layer (store-badge, price-card, offer-card, skeleton, empty/error-state, toast, sticky-header, two-column footer), inline SVGs replacing FA/Material, ~80-line vanilla JS replacing modal+collapse, dark default, mobile-first 576/768/992.
- Fix-in-pass: cover fallback; divide-by-zero guard; ≤576px; `<h1>` + `lang="es"` + aria-labels + focus-visible + `<noscript>`; remove `console.log`; preserve 504 partials (or graceful error); additive `currency` in `/juego` + `/ofertas` 200 responses.
- Security preserved, not weakened: CSRF meta/input, `game-link`, textContent-only writes, nh3 server-side. Tests stay green (55/55).

### Out of Scope
- Backend: spiders, route data shapes, config (locked by tests).
- New features: cart, auth, saved games, persistence.
- Light-theme toggle (YAGNI; tokens make it a future palette swap).

## Capabilities

### New Capabilities
- `web-ui`: design tokens, component system, responsive/a11y behavior, client-side behaviors (cover fallback, price-math guard, 504/error/empty states, noscript), additive currency contract.

### Modified Capabilities
None — REQ-SEC-1..3 preserved verbatim (implementation-only change).

## Approach

**A (selected)**: Drop Bootstrap + both icon CDNs → `:root` tokens + ~400-line component CSS + ~80-line vanilla JS + ~1 KB inline SVGs; zero build step (Termux-friendly). Identity: dark "game-deals console" — space-navy surfaces (#0f1117/#171a23/#1e2330), teal #00C89C single accent, store brand colors on small badges only.
**B (rejected)**: Keep Bootstrap + reskin — retains override fight, 55 KB dead weight. **C (rejected)**: Tailwind/build step — violates zero-build constraint.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/templates/*.html` + `partials/` | Rewritten | New structure; CSRF meta (base.html) + hidden input + `game-link` preserved |
| `src/static/css/{index,ofertas,responsive}.css` | Removed | → tokens.css + app.css |
| `src/static/js/ofertas.js` + inline script | Rewritten | ~80 lines; same behaviors: getGame/getOfertas, loading/error states, 65s abort, partials |
| `src/static/img` | Modified | Badge PNGs + background kept; FA/Material dropped; inline SVGs |
| `src/routes/index.py` | Modified (additive) | Optional top-level `currency` in 200 envelopes only |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Breaking CSRF/meta/input contract | Med | Atomic template+JS rewrite; full suite before/after |
| JS↔DOM class coupling breaks | Med | Templates + JS in same commit; behavioral tests |
| 504 partial data lost in rewrite | Med | Preserve-or-graceful handling is explicit scope |
| Offline tests fail (CDN-dependent) | Low | No CDN deps after rewrite; fixture-based tests |

## Rollback Plan

Single `git revert` of UI commits restores previous templates/static; backend untouched, no data migration. Revert whole change, never partial slices (template+JS coupled).

## Dependencies

None new — drops Bootstrap + 2 icon CDNs; no build tooling.

## Success Criteria

- [ ] 55/55 pytest green; CSRF meta/input + `game-link` contract intact
- [ ] Zero Bootstrap/FA/Material references; zero `console.log`; zero unsafe DOM writes
- [ ] Cover fallback fires; free games show no Infinity%; 360px viewport usable
- [ ] a11y: `lang="es"`, `<h1>` on /ofertas, aria-labels, focus-visible, `<noscript>`
- [ ] `currency` present in 200 responses; 504 partials rendered or graceful
- [ ] No build step; runs offline and on Termux

## Open Questions

None — handoff is decision-complete. (One-stylesheet vs tokens+app split deferred to design phase.)