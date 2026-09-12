# Web UI Specification

## Purpose

Replace the Bootstrap + icon-CDN frontend with a zero-build token/component system, fixing cover-fallback, divide-by-zero, a11y, responsive, and 504 gaps while preserving REQ-SEC-1..3 and HTTP envelopes (proposal §Scope/§Approach/§Success Criteria).

## Requirements

### Requirement: REQ-UI-1 — Design token system

The system MUST define `:root` tokens — surfaces `#0f1117`/`#171a23`/`#1e2330`, accent `#00C89C`, store colors (Steam `#66c0f4`, GOG `#a55eea`, Epic white-on-dark), radius/space/shadow, tabular-nums — and components MUST reference tokens only, dark default (proposal §Approach-A).

#### Scenario: Token baseline

- GIVEN tokens stylesheet loaded
- THEN `:root` holds the tokens; components use `var(--*)` only

### Requirement: REQ-UI-2 — Component layer

Components MUST exist: store-badge, price-card, offer-card, skeleton, empty/error-state, toast, sticky-header, two-column footer. Price-card MUST show original struck → final + `-XX%` chip only when `precio > 0` AND `descuento` present (`descuento` = FINAL price, `None` = not on sale).

#### Scenario: Discounted card

- GIVEN `precio` 15, `descuento` 7.5
- THEN struck 15, final 7.5, chip `-50%`

#### Scenario: No percentage

- GIVEN `descuento` `None` or `precio` 0
- THEN single price, no chip, no strike, no `Infinity`

### Requirement: REQ-UI-3 — Template structure

Templates MUST keep `meta[name="csrf-token"]`, hidden `input[name="csrf_token"]`, and `input[name="game-link"]` unchanged; include inline SVGs, focus-visible styles, `<noscript>`; `ofertas.html` MUST have one `<h1>` and one section per store with its "view more" link; the form MUST post to `/juego` without JS; partials MUST be sticky header + two-column footer.

#### Scenario: Index contract

- GIVEN `GET /`
- THEN csrf meta, `game-link`, hidden csrf input present; form posts to `/juego`

#### Scenario: Offers page

- GIVEN `GET /ofertas`
- THEN one `<h1>`, three store sections, `<noscript>` present

### Requirement: REQ-UI-4 — Accessibility

Pages MUST be `lang="es"` with one `<h1>` in main; covers/logos MUST have `alt`; icon-only buttons and the panel MUST be named via `aria-label`/`aria-labelledby`; `:focus-visible` MUST show an outline.

#### Scenario: Language and heading

- GIVEN any rendered page
- THEN `lang="es"` and exactly one `<h1>` in main

#### Scenario: Keyboard and AT

- GIVEN nav, icon buttons, results panel
- THEN each has an accessible name and visible focus outline

### Requirement: REQ-UI-5 — Client-side behaviors

~80-line vanilla JS MUST keep current behaviors: panel opens on submit, closes via button/ESC/backdrop; `getGame`/`getOfertas` POST with `X-CSRFToken` meta header and 65 s `AbortController`; per-store loading/error; 504 partials render available stores or graceful error; empty/failed covers use a local placeholder (never `src=""`); dynamic writes `textContent`-only (REQ-SEC-1).

#### Scenario: Search flow

- GIVEN a submitted term
- WHEN the panel opens
- THEN `POST /juego` sends meta token with 65 s abort; skeleton while loading

#### Scenario: Partial 504

- GIVEN a 504 with partial store data
- THEN available stores render with an error toast

#### Scenario: Failure and covers

- GIVEN a failing store or empty `img`
- THEN only that section errors; placeholder used, never `src=""`

### Requirement: REQ-UI-6 — Responsive layout

Styles MUST be mobile-first, stepping at 576/768/992 px; a 360 px viewport MUST be usable without horizontal overflow.

#### Scenario: Phone and desktop

- GIVEN a 360 px viewport
- THEN no horizontal scroll, tappable controls; ≥ 992 px uses multi-column layout

### Requirement: REQ-UI-7 — Additive currency contract

`POST /juego` and `POST /ofertas` 200 envelopes MUST add top-level `currency` from `Settings.currency` (default `USD`); non-200 MUST omit it; existing fields/shapes untouched. Price labels MAY use the envelope currency instead of hardcoded `$`.

#### Scenario: 200 envelope

- GIVEN a successful POST
- THEN JSON has `"currency": "USD"` and unchanged `steam`/`gog`/`egs`/`errors`

#### Scenario: Error envelope

- GIVEN a rejected POST
- THEN JSON has `error` and no `currency`

### Requirement: REQ-UI-8 — Dependency and junk removal

Pages MUST have zero Bootstrap/FA/Material references, zero `console.log`, zero deprecated `align`; icons MUST be inline SVGs.

#### Scenario: No CDN and no junk

- GIVEN `GET /` and `GET /ofertas`
- THEN no jsdelivr/bootstrapcdn/googleapis/cdnjs URLs, FA/Material classes, `console.log`, or `align=`

### Requirement: REQ-UI-9 — Security contract preservation

The rewrite MUST NOT weaken REQ-SEC-1..3: csrf meta/input and `game-link` survive with identical names; client writes remain `textContent`-only; nh3 sanitization and route validation untouched.

#### Scenario: Contract and sinks

- GIVEN rewritten templates and JS
- THEN meta–input–`game-link` names persist; no `innerHTML`/`insertAdjacentHTML` with dynamic data

### Requirement: REQ-UI-10 — Offline regression tests

The suite MUST stay green (REQ-TST baseline) and add fixture-driven offline tests: served `/` + `/ofertas` assert csrf meta/input + `game-link` and zero CDN URLs; price-math units cover normal, `None`, and zero `precio`.

#### Scenario: HTML contract offline

- GIVEN the app client with local fixtures
- WHEN `GET /` and `GET /ofertas`
- THEN csrf/game-link contract holds; no CDN URLs

#### Scenario: Price math

- GIVEN `(15, 7.5)`, `(15, None)`, `(0, ...)`
- THEN percentages are `50`, none, none — no division by zero

## Technical Notes

- New capability; sdd-archive promotes it to `openspec/specs/web-ui/spec.md`. REQ-SEC-1..3 preserved verbatim.
- Traceability: REQ-UI-1..8 ↔ §Scope; REQ-UI-7 ↔ §Approach-A; REQ-UI-10 ↔ §Success Criteria/§Risks.
- File impact: templates/partials; tokens.css+app.css replace index/ofertas/responsive.css; ofertas.js + inline script; routes/index.py additive; tests fixtures/conftest.
- Deferred to design: stylesheet split, currency plumbing, placeholder asset, price-label format.