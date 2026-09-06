# gameScraper

A Flask app that scrapes game prices and deals from Steam, GOG, and Epic Games
Store using Scrapy, compares them, and displays the results on a single page.

Live site: <https://gamescraper.onrender.com>

## Features

- Search a game name and compare prices across Steam, GOG, and Epic Games Store
- Browse current deals from each store's offers page
- Server-side sanitization with `nh3` plus client-side `textContent` rendering
- CSRF protection on all POST endpoints
- Timeout-bounded crawling with graceful cancellation (no orphaned spiders)

## Requirements

- Python 3.10+ (CI validates 3.11, 3.12, and 3.13)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate

# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes production + pytest, ruff, mypy, ipython)
pip install -r requirements-dev.txt

# Editable install so `src` and `steamScrape` resolve as packages
pip install -e .
```

## Configuration

Configuration is read from environment variables (see `src/config.py`).
Defaults match the app's original hardcoded values, so a bare deploy works
out of the box — except `SECRET_KEY`, which is **required in production**.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Flask session/CSRF signing key. **Required** unless `DEBUG=1`. Never commit it. |
| `COUNTRY` | `VE` | Country code used in store URLs and API calls |
| `LOCALE` | `es-ES` | Locale used in store URLs and API calls |
| `CURRENCY` | `USD` | Currency code shown in scraped prices |
| `GOG_COUNTRY` | `US` | Per-store override for GOG URLs |
| `GOG_LOCALE` | `en-US` | Per-store override for GOG URLs |
| `GOG_CURRENCY` | `USD` | Per-store override for GOG prices |
| `HOST` | `0.0.0.0` | Waitress bind host |
| `PORT` | `5000` | Waitress bind port |
| `DEBUG` | off | Enable dev mode (`DEBUG=1`). Never enable in production. |
| `SPIDER_TIMEOUT` | `60` | Seconds a crawl may run before it is cancelled (seconds) |
| `DOWNLOAD_DELAY` | `1` | Scrapy per-request delay (seconds) |

Example for local development:

```bash
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DEBUG=1
```

## Run

```bash
python main.py
```

Serves the app with Waitress on `http://0.0.0.0:5000` (or `HOST`/`PORT`).

## Test and quality gates

```bash
pytest --cov=src --cov=steamScrape   # full suite with coverage report
ruff check .                          # lint — zero warnings expected
mypy src steamScrape                  # type check (non-strict)
```

Tests run against cached HTML/JSON fixtures — no live store access, so the
suite is deterministic and safe offline.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs lint + tests on every push and
pull request to `main`, across Python 3.11/3.12/3.13, with pip caching and
concurrency cancellation. No secrets are used in the workflow.

## Architecture

```
Browser ──> Flask (Waitress) ──> TriggerRunner (crochet bridge) ──> Scrapy spiders
                 │                                                     │
                 └─────────────── JSON payload (sanitized) ◄───────────┘
```

- **Flask app** (`src/app.py` factory, `src/routes/index.py`): serves the pages
  and JSON endpoints; validates input, sanitizes payloads, maps crawl errors to
  HTTP responses (400/502/504).
- **TriggerRunner** (`src/triggers.py`): runs the Scrapy crawlers inside the
  Twisted reactor via crochet, merges per-store items, enforces the timeout,
  and cancels cleanly on abort.
- **Spiders** (`steamScrape/spiders/`): six Scrapy spiders — one per store for
  game search, one per store for deals — all configured from `Settings`.
- **Config** (`src/config.py`): immutable `Settings` dataclass built from
  environment variables, used by the app, the spiders, and the entry point.

## Project structure

```
gameScraper/
├── main.py                 # entry point: Waitress serve(create_app(), ...)
├── pyproject.toml          # package metadata + ruff/mypy/pytest config
├── requirements.txt        # production dependencies
├── requirements-dev.txt    # production + dev tooling
├── src/                    # Flask app package
│   ├── app.py              # create_app() factory + CSRF
│   ├── config.py           # Settings (env-backed)
│   ├── triggers.py         # TriggerRunner (crochet bridge)
│   ├── routes/index.py     # endpoints, validation, error mapping
│   └── static/ templates/  # assets and HTML templates
├── steamScrape/            # Scrapy project package
│   ├── settings.py         # Scrapy settings (DOWNLOAD_DELAY from env)
│   └── spiders/            # six store spiders
└── tests/                  # pytest suite + cached HTML/JSON fixtures
```

## Deployment

On Render (or any WSGI host), the start command is `python main.py`. Set
`SECRET_KEY` in the platform's environment settings before deploying —
the app refuses to start without it outside debug mode.