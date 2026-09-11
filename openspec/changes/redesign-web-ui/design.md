# Design: Web UI Redesign

## Technical Approach

Zero-build vanilla rewrite (REQ-UI-1..10): `tokens.css` + component CSS replace Bootstrap and both icon CDNs; one ~80-line defer script replaces the inline script + `ofertas.js`; the Bootstrap modal becomes an in-page results panel; covers fall back to a local SVG placeholder; an additive `currency` key is threaded via `app.config`, never a second `Settings` read. Envelopes, CSRF, REQ-SEC-1..3 stay locked.

## Decisions

### D1 — Stylesheet split: tokens.css + app.css

| Option | Tradeoff | Decision |
|---|---|---|
| Single `app.css` | One request; tokens untestable; light theme = whole-file audit | Rejected |
| `tokens.css` + `app.css` | Two requests; token isolation; REQ-UI-1 testable; palette swap edits one file | **Chosen** |
| Keep `responsive.css` | Third request; keeps ≤991px-only fragment | Rejected — 576/768/992 queries fold into `app.css` |

### D2 — Currency plumbing (REQ-UI-7): Settings → app.config → routes

| Option | Tradeoff | Decision |
|---|---|---|
| Import `Settings` in routes, `from_env()` | Re-derives env, ignoring the instance injected by `create_app(settings)` in `conftest.py` | Rejected |
| `app.py` sets `app.config["CURRENCY"]`; `_payload_with_errors()` adds `"currency"` | Mirrors `SPIDER_TIMEOUT` pattern; runs only on 200 paths of both routes → 400/502/504 omit the key | **Chosen** |

### D3 — Placeholder asset (REQ-UI-5): static file

| Option | Tradeoff | Decision |
|---|---|---|
| Inline SVG data URI | Bloat in JS; unusable at server render time | Rejected |
| `src/static/img/placeholder.svg` | Jinja renders it as `img src` before JS runs (JS-off safe); cacheable; `viewBox="0 0 460 215"` | **Chosen** |

Cover `<img>` carries `data-placeholder="{{ url_for('static', filename='img/placeholder.svg') }}"`; JS fallback reads `dataset.placeholder`. `alt` = "Portada de {nombre}".

### D4 — Price label format (REQ-UI-2/7)

`formatPrice(price, currency)` → `"7.50 USD"` (`toFixed(2)` + ISO code). Intl/es-ES comma rejected — no payoff; tests never assert price strings (verified). Chip `Math.round(100 - final*100/precio)` only when `precio > 0` AND `descuento` present; else single price, no strike, no `Infinity`.

### D5 — Component naming: flat semantic, no BEM

`store-badge`, `badge-steam|gog|egs`, `price-card`, `offer-card`, `skeleton`, `empty-state`, `error-state`, `toast`, `sticky-header`, `footer-2col`, `store-section`, `offer-grid`, `store-view`, `results-panel`, `cover-img`, `view-more`. State via `.is-open`/`.is-visible`/`.is-hidden`.

### D6 — Template structure

- `base.html`: `<html lang="es">`; head = charset, viewport, csrf meta, favicon, `tokens.css`, `app.css`, `{% block title %}` (head block kept). Body = header include, `<main>`, footer include, `.toast`, then `<script src="…/js/app.js" defer></script>` (no scripts block).
- `index.html`: `<form id="game-form" action="/juego" method="post">` (JS-off 405 fix), hidden csrf input, `#game`, `#search-submit` with inline search SVG; panel `#results-panel` (role="dialog", aria-modal, aria-labelledby) + `#panel-backdrop` + `#panel-close`; three `[data-store]` sections; `<template id="game-panel-template">`.
- `ofertas.html`: one `<h1>`, three `<section class="store-section" data-store="…">` each with h2 + `.offer-grid` + `.view-more` (URLs unchanged); `<template id="offer-card-template">`; `<noscript>` both pages.
- SVGs: inline per usage (≈6 small icons), not a `<defs>` sprite — ~1 KB, no id-collision ceremony.

### D7 — JS architecture

Single `src/static/js/app.js`, plain `<script defer>` (no module: one file, no imports). Feature-detected init. DOM contract: `meta[name="csrf-token"]`, `#game-form`, `#game`, `#search-submit`, `#results-panel` (+`.is-open`), `#panel-close`, `#panel-backdrop`, `[data-store]`, `.store-view`/`.offer-grid`, `.skeleton`, `#toast` (+`.is-visible`), `.error-state`, `.empty-state`, `img.cover-img[data-placeholder]`, `#offer-card-template`, `#game-panel-template`, `.view-more`.

Flow: submit → `preventDefault` → panel `.is-open` + skeletons → `POST` with `X-CSRFToken` + `AbortController(65000)` → 504 with store data → render available + error toast (fixes discarded partials); 400/502 → `.error-state` per store; 200 → render (textContent/createElement only, REQ-SEC-1). Close: button/ESC/backdrop → remove `.is-open`, restore focus to `#game`. Covers: `error` event or empty payload `src` → `dataset.placeholder`, never `""`.

### D8 — Test plan mapping (REQ-UI-10)

- **Add** `tests/test_web_ui.py` — offline HTML contract: csrf meta + hidden input + `game-link`; form `action="/juego" method="post"`; `lang="es"`; one `<h1>` on `/ofertas`; `<noscript>`; zero CDN URLs/`console.log`/`align=`; only `tokens.css`+`app.css` linked.
- **Add** `tests/test_price_math.py` — pure-Python mirror of the JS formula (no JS runtime in pytest; documented mirror): `(15, 7.5)→50`, `(15, None)→None`, `(0, x)→None`.
- **Append** 3 tests to `test_routes.py` (200 includes `currency`; 400 and 502 omit). All 13 existing route tests untouched — the new key cannot break them.
- **Untouched**: `test_config.py`, `test_spiders.py`, `test_triggers.py`.

## Data Flow

```
submit (app.js, X-CSRFToken, 65 s abort) ──► POST /juego|/ofertas ──► TriggerRunner ──► spiders
  200 {steam,gog,egs,[errors],currency} ──► renderStore() per store
  504 {stores…, error} ──► render available + toast       400/502 {error} ──► .error-state
```

## Interfaces / Contracts

- **Envelope**: 200 adds top-level `"currency"`; non-200 omits; `steam`/`gog`/`egs`/`errors` unchanged.
- **tokens.css**: `:root` only — `--color-surface-0/-1/-2` (#0f1117/#171a23/#1e2330), `--color-accent` (#00C89C), `--color-steam` (#66c0f4), `--color-gog` (#a55eea), `--color-egs`, `--color-text`, `--color-muted`, `--color-border`, `--radius-sm/-md/-lg`, `--space-xs/sm/md/lg`, `--shadow-1/-2`, `--font-sans`; `tabular-nums` on prices. Components use `var(--*)` only (REQ-UI-1).
- **app.js**: `discountPercent(precio, descuento) → int|null`, `formatPrice(n, currency) → str`, `openPanel()/closePanel()`, `renderStore(el, data)`, `showToast(msg)`, `fetchWithAbort(url, formData)`.

## File Changes

| File | Action | Description |
|---|---|---|
| `src/static/css/tokens.css` | Create | `:root` tokens, reset, base typography, `:focus-visible` |
| `src/static/css/app.css` | Create | Components, layout, `.is-*` states, breakpoints |
| `src/static/js/app.js` | Create | ~80-line defer script (D7) |
| `src/static/img/placeholder.svg` | Create | 460×215 cover placeholder |
| `src/templates/base.html` | Rewrite | D6 structure; app.js; toast; drops CDNs |
| `src/templates/index.html` | Rewrite | Form + results panel replacing modal |
| `src/templates/ofertas.html` | Rewrite | One h1, 3 store sections, offer-card template |
| `src/templates/partials/header.html` | Rewrite | Sticky semantic nav, inline brand SVG |
| `src/templates/partials/footer.html` | Rewrite | `.footer-2col`, inline social SVGs |
| `src/routes/index.py` | Modify | `_payload_with_errors()` adds `"currency"` (one line) |
| `src/app.py` | Modify | `app.config["CURRENCY"] = settings.currency` (one line) |
| `src/static/css/index.css` | Delete | Replaced |
| `src/static/css/ofertas.css` | Delete | Replaced |
| `src/static/css/responsive.css` | Delete | Folded into app.css |
| `src/static/js/ofertas.js` | Delete | Merged into app.js |
| `tests/test_web_ui.py` | Create | HTML contract (D8) |
| `tests/test_price_math.py` | Create | Price-math mirror (D8) |
| `tests/test_routes.py` | Modify | Append 3 currency tests only |

Kept: `src/static/img/{steam,gog,egs}.png`, `background.jpg`, `comparacion.svg`, `favicon.ico`.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | Price math normal/None/zero | `test_price_math.py` mirror of `discountPercent` |
| Integration | Currency envelope | new `test_routes.py` cases |
| Integration | HTML contract + junk-free + a11y | `test_web_ui.py` GET `/` + `/ofertas` |

## Threat Matrix

N/A — no OS-routing/shell/subprocess/VCS/process-integration boundary. HTTP routes and the Crochet reactor integration untouched; spiders not modified.

## Migration / Rollout

No migration or flags. Atomic push (template+JS coupled); rollback = single `git revert` (§Rollback Plan).

## Open Questions

None — all spec-deferred items resolved in D1–D8.