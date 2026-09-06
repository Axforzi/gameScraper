# Project: gameScraper

## Overview

gameScraper is a three-store game deal price-comparison web app. It scrapes deals from Steam, EGS (Epic Games Store), and GOG: a Flask frontend lets a user submit a game title (or scrape current offers), and Scrapy spiders (bridged into the Flask process via Crochet over Twisted) fetch and merge per-store results. Originally a functional prototype, it was hardened through the `propose-professional-improvements` change into a maintainable, deployable, tested codebase.

## Tech Stack

- **Language**: Python 3 (CI matrix 3.11–3.13)
- **Web framework**: Flask 3.1 + Jinja2 templates
- **Scraping**: Scrapy 2.12 spiders (async download pipeline)
- **Async bridge**: Crochet + Twisted reactor over Waitress WSGI
- **Security**: flask-wtf CSRF, nh3 server-side sanitization, `textContent` client-side writes
- **Config**: `src/config.py` `Settings` frozen dataclass read from environment variables

## Layout (flat)

- `src/` — Flask application (`app.py`, `config.py`, `triggers.py`, `routes/`, `static/`, `templates/`)
- `steamScrape/` — Scrapy project (`settings.py`, `spiders/`)
- `tests/` — pytest suite with cached HTML/JSON fixtures (no live network)
- `main.py` — entry point: Waitress `serve(create_app(), ...)`
- `pyproject.toml` — package metadata + ruff/mypy/pytest tool config
- `requirements.txt` (prod) / `requirements-dev.txt` (adds pytest, ruff, mypy, python-dotenv, ipython)
- `.github/workflows/ci.yml` — lint + test jobs on push/PR, matrix 3.11–3.13

Both `src/` and `steamScrape/` are installable packages (`pip install -e .`); absolute imports throughout, no `sys.path` hacks.

## Quality Gates

- **Tests**: pytest 55/55 passing
- **Coverage**: 89% (`src/` + `steamScrape/`)
- **Lint**: `ruff check .` clean (zero warnings)
- **Types**: `mypy src steamScrape` clean (non-strict)

## Configuration

Default values (unchanged when unset):

| Var | Default | Used by |
|-----|---------|---------|
| `COUNTRY` / `LOCALE` / `CURRENCY` | `VE` / `es-ES` / `USD` | Steam/EGS store URLs + headers |
| `GOG_COUNTRY` / `GOG_LOCALE` / `GOG_CURRENCY` | `US` / `en-US` / `USD` | GOG catalog URLs |
| `SECRET_KEY` | required (fail-fast unless DEBUG) | Flask sessions + CSRF signing |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | Waitress bind |
| `DEBUG` | off | dev server |
| `SPIDER_TIMEOUT` | `60` | TriggerRunner trigger timeout |
| `DOWNLOAD_DELAY` | `1` | Scrapy setting |

## Open Concerns

1. **cp314 wheel gap** — the pinned direct deps (lxml 5.4.0, cryptography 44.0.3, Twisted 24.11.0, Scrapy 2.12.0) lack cp314 wheels, so Python 3.14 cannot install them locally. Use Python ≤3.13 locally (the CI matrix is 3.11–3.13). Verification was run on an unpinned loose venv.
2. **python-dotenv declared but not loaded** — `python-dotenv` is in `requirements-dev.txt` but never imported, so `.env` support is inert. SUGGESTION to resolve: either call `load_dotenv()` in `main.py` guarded to dev, or drop the dependency.
