# Tasks: Web UI Redesign

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,000–2,300 (Unit 1 ≈ 50, Unit 2 ≈ 620, Unit 3 ≈ 1,250, Unit 4 ≈ 200) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 (currency) → PR2a (tokens+placeholder+app.js) → PR2b (app.css) → PR3 (atomic rewrite, over budget) → PR4 (offline tests) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

**Unit 3 (atomic rewrite) is ~1,250 changed lines and CANNOT be split without breaking atomicity.** Templates, app.js wiring, and the legacy CSS/JS deletes must land in one commit: any intermediate state either runs old `ofertas.js` selectors against the new DOM (broken behaviors) or violates the single-`git revert` rollback plan (proposal §Rollback, design §Migration). Recommended exception: keep unit 3 whole and accept the over-budget diff (`size:exception` or explicit user acceptance) — ~580 of its lines are mechanical dead-file deletes (index/ofertas/responsive.css, ofertas.js) and template rewrites are the real review load. If the user refuses the exception and demands a split, the only safe boundary is per-page: split ofertas.html (a purely static page) from index.html+base.html+app.js wiring — NOT recommended, it leaves partial redesign states and complicates revert. `app.js` is created unreferenced in unit 2 (inert); any selector fixes found during wiring land in unit 3's commit.

### Work Units

| Unit | Tasks | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|-------|------|-----------|----------------------|-----------------|-------------------|
| 0 Baseline gate | 0.1 | Green 60/60 baseline recorded | none | `pytest` | `python main.py` + `curl /` 200 | N/A — gate only |
| 1 Currency plumbing | 1.1–1.3 | Additive `currency` in 200 envelopes only | PR1 (~50) | `pytest tests/test_routes.py` (18 tests) | `python main.py`; CSRF `POST /juego` → body has `"currency":"USD"`; 400/502 omit it | revert PR1 commits |
| 2 Static assets | 2.1–2.4 | tokens+app.css+placeholder+app.js, unreferenced | PR2a (~230): 2.1+2.3+2.4 / PR2b (~400): 2.2 | `ruff check .` (no lint for CSS/JS in repo); file presence | boot app; `GET /static/{tokens.css,app.css,placeholder.svg,app.js}` → 200 | revert PR2 commits |
| 3 Atomic rewrite | 3.1–3.5 | Templates + JS wiring + legacy deletes, one commit | PR3 (~1,250) — over budget | `pytest` full (60 green; csrf/game-link asserts in test_routes.py must still pass) | `python main.py`; manual submit → panel opens, ESC/backdrop close; `/ofertas` shows 3 sections | single `git revert` of PR3 |
| 4 Offline tests | 4.1–4.3 | REQ-UI-10 regression suite | PR4 (~200) | `pytest tests/test_web_ui.py tests/test_price_math.py tests/test_routes.py` | pytest client + cached fixtures, no network | revert PR4 commits |
| 5 Final sweep | 5.1 | REQ-UI-1..10 checklist + junk sweep | none (verify-only, folded into PR4) | `pytest` + grep sweep (see 5.1) | repo-wide grep; manual 360 px viewport check | N/A — no code |

Notes: commits are conventional (orchestrator injects `-c user.name/user.email` per command — see §1.1 example); NEVER add Co-Authored-By. `strict_tdd: false` — no RED-first tasks. Threat matrix N/A (design §Threat Matrix).

## Phase 0 — Baseline Gate

- [x] 0.1 (T0) Run `pytest` from repo root; record exact green count (60/60 expected) in apply notes; abort if not green.

## Phase 1 — Currency Plumbing (additive backend)

- [x] 1.1 (T1) `src/app.py`: add `app.config["CURRENCY"] = settings.currency` beside `SPIDER_TIMEOUT` (D2 — mirrors SPIDER_TIMEOUT pattern; single source, respects `create_app(settings)` injection).
- [x] 1.2 (T2) `src/routes/index.py`: `_payload_with_errors()` adds one line `payload['currency'] = current_app.config["CURRENCY"]` — 200 paths only; 400/502/504 envelopes untouched (REQ-UI-7, D2).
- [x] 1.3 (T3) `tests/test_routes.py`: append 3 tests (D8) — `POST /juego` and `POST /ofertas` 200 include `"currency"=="USD"`; 400 omits it; 502 omits it. Accept: `pytest tests/test_routes.py` green (18). Commit: `feat(routes): add currency to 200 envelopes` — run with identity: `git -c user.name=<id> -c user.email=<email> commit -m "..."`.

## Phase 2 — Static Assets (additive, unreferenced)

- [x] 2.1 (T4) Create `src/static/css/tokens.css`: `:root` only — surfaces `#0f1117`/`#171a23`/`#1e2330`, accent `#00C89C`, store colors steam `#66c0f4` / gog `#a55eea` / egs, text/muted/border, `--radius-sm/md/lg`, `--space-xs/sm/md/lg`, `--shadow-1/2`, `--font-sans`; global reset, base typography, `:focus-visible` outline; no component rules (REQ-UI-1/4, D1/D5).
- [x] 2.2 (T5) Create `src/static/css/app.css`: components only, all styling via `var(--*)` — `store-badge` + `badge-steam|gog|egs`, `price-card` (struck→final + `-XX%` chip, tabular-nums), `offer-card`, `skeleton`, `empty-state`, `error-state`, `toast`, `sticky-header`, `footer-2col`, `store-section`, `offer-grid`, `store-view`, `results-panel`, `cover-img`, `view-more`; `.is-open/.is-visible/.is-hidden`; mobile-first, breakpoints 576/768/992; 360 px usable, no horizontal overflow (REQ-UI-2/6, D5/D6).
- [x] 2.3 (T6) Create `src/static/img/placeholder.svg`: `viewBox="0 0 460 215"`, neutral cover placeholder (REQ-UI-5, D3).
- [x] 2.4 (T7) Create `src/static/js/app.js`: ~80-line plain defer script (no imports) — `discountPercent(precio, descuento)→int|null` (only when `precio>0` AND `descuento` present, `Math.round(100 - final*100/precio)`), `formatPrice(n, c)→"7.50 USD"`, `openPanel()/closePanel()` (button/ESC/backdrop, focus restore), `renderStore()` (per `[data-store]`), `showToast()`, `fetchWithAbort(url, formData)` (`X-CSRFToken` from meta, `AbortController(65000)`); 504 → render available stores + error toast; covers `error`/empty → `dataset.placeholder`, never `src=""`; writes `textContent`/createElement only, no `innerHTML` with data; feature-detected init; DOM contract per D7. Unreferenced until unit 3 wiring. Commit: `feat(ui): add design tokens, component CSS, placeholder, and app.js`.

## Phase 3 — Atomic Template + JS Rewrite (one commit, single revert boundary)

- [x] 3.1 (T8) Rewrite `src/templates/base.html` (D6): `<html lang="es">`; head = charset, viewport, csrf meta (byte-identical `name="csrf-token"`), favicon, `tokens.css` + `app.css` links only, title block; body = `header` include, `<main>{% block content %}`, `footer` include, `.toast`, `<script src="{{ url_for('static', filename='js/app.js') }}" defer>`; zero CDN links (REQ-UI-3/8/9).
- [x] 3.2 (T9) Rewrite `src/templates/index.html` (D6): `<form id="game-form" action="/juego" method="post">` (JS-off fallback), hidden `input[name="csrf_token"]` + `input[name="game-link"]` (names byte-identical, REQ-UI-3/9), `#game`, `#search-submit` with inline search SVG, `#results-panel` (`role="dialog" aria-modal="true" aria-labelledby`), `#panel-backdrop`, `#panel-close` (aria-label), 3 `[data-store]` sections, `<template id="game-panel-template">`, `<noscript>`; drop inline script entirely (its behaviors live in app.js).
- [x] 3.3 (T10) Rewrite `src/templates/ofertas.html` (D6): exactly one `<h1>` in main; 3 `section.store-section[data-store="…"]` each with `<h2>` + `.offer-grid` + `.view-more` (URLs unchanged); `<template id="offer-card-template">`; `<noscript>` (REQ-UI-3/4).
- [x] 3.4 (T11) Rewrite `src/templates/partials/header.html` (sticky semantic `<nav>`, inline brand SVG, aria-labels on icon links) and `src/templates/partials/footer.html` (`.footer-2col`, inline social SVGs, no CDN icons) (REQ-UI-3/4/8, D5/D6).
- [x] 3.5 (T12) Delete `src/static/css/index.css`, `src/static/css/ofertas.css`, `src/static/css/responsive.css`, `src/static/js/ofertas.js` — ONLY in this commit, atomic with 3.1–3.4 (D1/D6; REQ-UI-8). Accept (3.1–3.5): full `pytest` green — csrf meta + `name="game-link"` + hidden-input asserts keep passing; manual submit flow: panel opens, skeleton → results, ESC closes; `/ofertas` renders 3 sections; 360 px no horizontal scroll. Commit: `feat(ui): rewrite templates with token components and app.js` (atomic; fix app.js selector mismatches here, same commit).

## Phase 4 — Offline Regression Tests

- [x] 4.1 (T13) Create `tests/test_web_ui.py` (D8, REQ-UI-10): GET `/` + `/ofertas` via app client assert csrf meta + hidden input + `name="game-link"`; form `action="/juego" method="post"`; `lang="es"`; exactly one `<h1>` in main on `/ofertas`; `<noscript>` present both pages; zero jsdelivr/bootstrapcdn/googleapis/cdnjs URLs, zero `console.log`, zero `align=`; only `tokens.css`+`app.css` linked (REQ-UI-8).
- [x] 4.2 (T14) Create `tests/test_price_math.py` (D8, REQ-UI-10/2): pure-Python mirror of `discountPercent` — `(15, 7.5)→50`, `(15, None)→None`, `(0, anything)→None` (no division by zero); `formatPrice(7.5, "USD")=="7.50 USD"`. Document mirror relationship in docstring.
- [x] 4.3 (T15) Run full `pytest` (60 + 3 route appends + new files), `ruff check .`, `mypy src steamScrape`; record final counts. Commit: `test(ui): cover HTML contract and price math offline`.

## Phase 5 — Final Verification Sweep (no commit)

- [x] 5.1 (T16) Walk REQ-UI-1..10 scenario checklist: `grep -rn` `src/templates src/static` for `jsdelivr|bootstrapcdn|googleapis|cdnjs|fa-|material-icons|console\.log|align=` → zero; covers never `src=""` (placeholder.svg path via `data-placeholder`); `currency` present in 200 responses, absent in non-200; `textContent`-only dynamic writes; suite green; `main.py` boots offline.