# Design: Professional Improvements — gameScraper

## 1. Architecture Overview

Target layout (flat, both packages at repo root — zero directory moves):

```
gameScraper/
├── pyproject.toml            # metadata, packages, ruff/mypy/pytest config
├── main.py                   # entry: Waitress serve(create_app(), cfg.host, cfg.port)
├── requirements.txt          # prod (trimmed direct deps)
├── requirements-dev.txt      # -r requirements.txt + pytest, ruff, mypy, dotenv, ipython
├── scrapy.cfg                # unchanged — steamScrape.settings still resolves
├── src/                      # NEW __init__.py
│   ├── app.py                # create_app() factory + CSRFProtect
│   ├── config.py             # NEW Settings dataclass
│   ├── triggers.py           # TriggerRunner (merges TriggerGame/TriggerOffers)
│   ├── routes/__init__.py    # NEW
│   ├── routes/index.py       # validation + error mapping
│   ├── static/  templates/
├── steamScrape/              # packed as-is; spiders/ minus juegospider.py
└── tests/                    # Tier 3
```

Imports normalized to absolute (`from src.app import create_app`, `from src.triggers import TriggerRunner`, `from steamScrape.spiders.offers_steam import OffersSteamSpider`); all resolve via `pip install -e .`. `sys.path` removed from `main.py`, `src/triggers.py`; `src/app.py` keeps `Flask(__name__)` (static/templates ship via `[tool.setuptools.package-data]`).

## 2. TriggerRunner

One class parameterized by spider list, optional search term, config — replaces both classes, response shapes unchanged (`{steam:…, gog:…, egs:…}`).

**State machine** per run: `PENDING → RUNNING → COMPLETED | PARTIAL | TIMEOUT | FAILED`

- `COMPLETED`: all spiders finished with items or explicit `{store: None}` (legit no-match).
- `PARTIAL`: some spiders failed — their error logged, successful stores' results preserved (REQ-ASM-3).
- `TIMEOUT`: `EventualResult.wait(timeout)` raised `crochet.TimeoutError` → cancel → route returns 504 + partial payload.
- `FAILED`: exception before/at scheduling → route returns 502.

**Per-crawler signals** replace global `dispatcher.connect` (cross-talk/leak fix): `runner.create_crawler(spider_cls)` → connect `item_scraped`/`spider_closed` on `crawler.signals`, `d.addErrback(...)`. Completion count = `len(self.spiders)` (kills the `count == 3` magic number). State resets in `run()` — instance is per-request (existing pattern kept).

```python
class TriggerRunner:
    def __init__(self, spiders: list[type[scrapy.Spider]],
                 term: str | None = None,
                 timeout: float = 60.0) -> None: ...
    def run(self) -> dict                      # blocks ≤ timeout; returns merged items + meta
    def cancel(self) -> None                   # reactor entry: crawl_runner.stop()
    @property
    def state(self) -> str: ...                # COMPLETED|PARTIAL|TIMEOUT|FAILED
    @property
    def errors(self) -> list[tuple[str, str]]: ...  # (spider_name, reason)
```

### Decision: Timeout primitive — crochet `EventualResult.wait(timeout=)` vs `threading.Event`

| Option | Tradeoff | Decision |
|---|---|---|
| `@crochet.wait_for(timeout=N)` decorator | Timeout fixed at decoration; can't be per-run configurable (REQ-CFG-4) | Rejected |
| `EventualResult.wait(timeout=…)` (wait_for mechanism, call-time arg) | Same crochet primitive, timeout passed per run from config; raises `crochet.TimeoutError` | **Chosen** |
| `threading.Event` + `time.sleep` loop | Hand-rolled reimplementation of the current bug; no reactor access for cancellation; manual error plumbing | Rejected |

The Flask thread parks on the crochet wait primitive (GIL released, no busy loop); the Twisted reactor and other Waitress workers stay responsive. Cancellation (REQ-ASM-2): on `TimeoutError` the thread calls `self.cancel()` (second `@run_in_reactor` entry) → `EventualResult.cancel()` attempt + `crawl_runner.stop()` (stops all tracked crawlers, fires when ended) → no orphaned crawler keeps the reactor busy. Logs `spider_timeout spider=<names> timeout=<s>`.

## 3. Crochet Bridge — timeout/cancellation flow

Module-level `crochet.setup()` + singleton `crawl_runner = CrawlerRunner(get_project_settings())` stay (CrawlerRunner is the documented hub for tracked, stoppable crawls inside an existing reactor).

```
Flask thread (Waitress worker)          Twisted reactor thread
─────────────────────────               ──────────────────────
POST /juego|/ofertas
  CSRF check │ validation │ 400
  runner = TriggerRunner(spiders, term, cfg.spider_timeout)
  runner.run()
    ├─ EventualResult = _schedule(term)  ──► create_crawler per spider
    │                                        join item_scraped/spider_closed
    │                                        crawl_runner.crawl(crawler)
    │                                        return EventualResult
    │
    ├─ eventual.wait(timeout)  ◄──parked──  crawls run; items merged via signals
    │     ├─ done ─► COMPLETED/PARTIAL ─► 200 json (+errors meta)
    │     └─ crochet.TimeoutError
    │           └─ cancel()  ──► EventualResult.cancel(); crawl_runner.stop()
    │                state=TIMEOUT ─► log ─► 504 + partial payload
    └─ other exception ─► FAILED ─► 502 + error payload
```

Route error mapping: `crochet.TimeoutError`→504, spider/trigger exception→502, `CSRFError`→400 (flask-wtf default), validation→400.

## 4. Security Hardening

### Decision: Sanitizer — client `textContent` + server `nh3`

| Option | Tradeoff | Decision |
|---|---|---|
| DOMPurify (JS) | Client-only; can't back template echoes; new JS dep for content we render as text | Rejected |
| bleach (Python) | Deprecated/unmaintained (upstream recommends nh3) | Rejected |
| nh3 (Python, server-side) + `textContent` client-side | Rust-backed, maintained; sanitizes JSON before it leaves the server; all sinks use textContent | **Chosen** |

- `ofertas.js` and `index.html` inline script: **zero innerHTML writes with data** — `textContent` for names/descriptions/percentages (discount span built via `createElement`/`textContent`). Defense-in-depth: `src/security.py` sanitizes `nombre`/`descripcion` strings with nh3 in every response payload; `link`/`img` URI-validated to `http(s)://` only (blocks `javascript:` in `a.href`/`img.src`).
- **CSRF** (REQ-SEC-2): `CSRFProtect.init_app(app)` in factory; `base.html` gets `<meta name="csrf-token" content="{{ csrf_token() }}">`; `ofertas.js` and the inline `getGame` fetch send `X-CSRFToken`; index form gets a hidden `csrf_token` input (non-JS fallback). One pass, all POST surfaces, default 400 rejection before any spider starts.
- **Validation** (REQ-SEC-3): `game-link` is a *search term* (passed as `juego=`, not a URL). Rules: strip → non-empty, ≤200 chars, allowlist `[A-Za-z0-9 \-\&'.,:!()+]`, no control/HTML chars. Failure → 400 + message, no spider launched.

## 5. Config Design

`src/config.py` — frozen dataclass `Settings.from_env()` reading `os.environ` once, defaults identical to today's values:

| Var | Default | Used by |
|---|---|---|
| `COUNTRY` / `LOCALE` / `CURRENCY` | `VE` / `es-ES` / `USD` | offers_egs, epicgames URLs + `/es-ES/p/` link, steam `Accept-Language` |
| `GOG_COUNTRY` / `GOG_LOCALE` / `GOG_CURRENCY` | `US` / `en-US` / `USD` | gog, offers_gog — per-store override so a bare deploy keeps today's GOG behavior |
| `SECRET_KEY` | required in prod | Flask sessions + CSRF signing; startup aborts with clear error if unset and not DEBUG |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | Waitress bind |
| `DEBUG` | off | dev server; debug never on in prod |
| `SPIDER_TIMEOUT` | `60` | TriggerRunner timeout (REQ-CFG-4) |
| `DOWNLOAD_DELAY` | `1` | Scrapy settings (read via env in `settings.py`) |

`.env` (python-dotenv) dev-only; secrets never logged; entry `main.py` binds from config.

## 6. Testing Design

```
tests/
├── conftest.py             # app+client fixture, crochet single-reactor setup, fixture readers
├── fixtures/html|json/     # captured store HTML/JSON (steam offer page, GOG catalog, EGS graphql)
├── test_triggers.py        # REQ-TST-2: mocked spiders → completion, timeout abort, cancel leaves no
│                           #   running crawler, partial-failure preserves successes, state machine
├── test_routes.py          # REQ-TST-3: GET 200; POST w/o CSRF token → 400, no trigger (assert
│                           #   TriggerRunner.run not called); bad game-link → 400; success → 200
├── test_spiders.py         # REQ-TST-4: parse methods fed HtmlResponse/TextResponse from fixtures;
│                           #   price cleaning, name matching, roman-numeral conversion, malformed
│                           #   input logged not fatal; offers_steam has no requests/session import
└── test_config.py          # REQ-CFG: defaults == today's values; env override; SECRET_KEY fail-fast
```

Crochet constraint: single `crochet.setup()` per process (module import does it); trigger tests monkeypatch `CrawlerRunner` with deterministic fake crawlers, tiny timeout (≈1s), never live sites.

## 7. Dependency / CI Design

- `requirements.txt`: trimmed to direct prod deps (`Flask`, `flask-wtf`, `Scrapy`, `crochet`, `Twisted`, `waitress`, `nh3`, `beautifulsoup4`, `lxml`, `roman`, `cryptography`, `pyOpenSSL`, `service-identity`) — **drops `requests`** (REQ-ASM-4 removes last use) and **`ipython`** (dev tool). Transitives resolve via pip.
- `requirements-dev.txt`: `-r requirements.txt` + `pytest`, `pytest-cov`, `ruff`, `mypy`, `python-dotenv`, `ipython`.
- `.github/workflows/ci.yml` (push + PR to default branch, no secrets): job `lint` → `pip install -r requirements-dev.txt` → `ruff check .` → `mypy src steamScrape` (non-strict); job `test` → `pip install -e .` + dev deps → `pytest --cov=src --cov=steamScrape`. concurrency cancel-in-progress, pip cache.

## 8. File-by-File Change Map

| Tier | File | Action | Description |
|---|---|---|---|
| 1 | `src/triggers.py` | Modify | Timeout/cancel/error machinery in both existing classes (shared helper) |
| 1 | `src/static/js/ofertas.js` | Modify | All `innerHTML`→`textContent`; `X-CSRFToken` header on fetch |
| 1 | `src/templates/base.html` | Modify | CSRF meta tag |
| 1 | `src/templates/index.html` | Modify | Hidden csrf input; fetch header; modal writes → textContent |
| 1 | `src/templates/ofertas.html` | Modify | Adapt template for textContent-only fills |
| 1 | `src/routes/index.py` | Modify | Validation (REQ-SEC-3), error→HTTP mapping, CSRF-safe responses |
| 1 | `src/app.py` | Modify | `create_app()` factory, `CSRFProtect.init_app`, CSRFError handler |
| 1 | `steamScrape/spiders/offers_steam.py` | Modify | `requests.get`→follow-up `scrapy.Request` for `game_header_image_full`; drop `requests`/`Session` |
| 1 | `requirements.txt` | Modify | +`flask-wtf`, +`nh3` |
| 2 | `src/__init__.py`, `src/routes/__init__.py` | Create | Package markers |
| 2 | `src/config.py` | Create | `Settings` dataclass (env vars, defaults) |
| 2 | `src/triggers.py` | Modify | `TriggerRunner` merge; drop `CrawlerProcess` import; `len(spiders)` count |
| 2 | `src/routes/index.py` | Modify | Call `TriggerRunner` |
| 2 | `main.py` | Modify | Remove `sys.path`; Waitress bind from config; remove `debug=True` |
| 2 | `steamScrape/spiders/juegospider.py` | Delete | Dead code (REQ-PKG-3) |
| 2 | `steamScrape/settings.py` | Modify | `DOWNLOAD_DELAY` from env |
| 2 | `steamScrape/spiders/{steam,epicgames,gog,offers_egs,offers_gog}.py` | Modify | Config vars in URLs/headers |
| 2 | `pyproject.toml` | Create | Packages `["src","src.routes","steamScrape","steamScrape.spiders"]`, package-data (static/templates), ruff/mypy/pytest config |
| 2 | `.gitignore` | Modify | venv, .env, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, coverage |
| 3 | `tests/…` (conftest, fixtures, 4 test files) | Create | §6 |
| 4 | `requirements.txt` + `requirements-dev.txt` | Modify/Create | Split (REQ-PKG-4) |
| 4 | `.github/workflows/ci.yml` | Create | §7 |
| 4 | `README.md` | Modify | Setup/run/test instructions (REQ-PKG-5) |

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED tests |
|---|---|---|---|
| Documentation-like paths | N/A — README updates are informational; nothing executable | — | — |
| Git repo selection / Commit state / Push state / PR commands | N/A — no git/VCS/PR automation in app or CI | — | — |
| Process integration (Twisted reactor inside Flask; crawls spawned in reactor) | **Applicable** | Blocking HTTP inside reactor is the threat (REQ-ASM-4); orphaned crawlers on timeout (REQ-ASM-2) | `test_spiders` asserts no `requests` import + parse runs offline; `test_triggers` timeout test asserts `crawl_runner.stop()` invoked and no crawler remains running |

## Migration / Rollout

No data migration. Tiers are independently revertible (git revert per tier). Render: same `main.py` entry; new required env `SECRET_KEY` documented in README before deploy. One behavior caveat: `/ofertas` fetch now requires CSRF header — deployed atomically with template change (same pass).

## Open Questions

- None blocking. (Note: REQ-SEC-3 wording says "store URLs" but the field is a search term — design validates a search-term allowlist; if the field later becomes a URL input, swap in a URL validator.)