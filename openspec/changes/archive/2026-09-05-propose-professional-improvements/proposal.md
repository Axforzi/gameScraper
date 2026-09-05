# Proposal: Professional Improvements

## Intent

gameScraper is a functional prototype — Flask + Scrapy + Crochet monolith scraping game deals from Steam, EGS, and GOG. It works, but it has critical security holes (XSS via innerHTML, no CSRF), a blocking `while+sleep` loop that can freeze the web server, synchronous HTTP inside Scrapy spiders, zero tests, zero error handling, and broken package layout (`sys.path` hacks). This change transforms it into a maintainable, deployable, production-grade project.

## Scope

### In Scope
- Security fixes: XSS sanitization, CSRF tokens, input validation
- Stability fixes: async timeout/cancellation for spider triggers, proper error handling
- Architecture: eliminate `sys.path` hacks via proper package structure, deduplicate TriggerGame/TriggerOffers
- Config management: extract hardcoded country/locale/currency to environment/config
- Testing baseline: pytest setup, unit tests for triggers/routes/spiders, CI-ready
- Dead code removal: juegospider.py
- Dependency cleanup: separate dev/prod requirements

### Out of Scope
- Full rewrite or new framework migration
- New scraping targets beyond current Steam/EGS/GOG
- UI redesign or new frontend features
- Monitoring/observability stack (Prometheus, Sentry, etc.)
- Containerization beyond what Render needs

## Capabilities

### New Capabilities
- `security-hardening`: XSS sanitization, CSRF protection, input validation on all user-facing surfaces
- `async-spider-management`: Non-blocking spider triggers with timeout, cancellation, and error propagation
- `package-layout`: Proper Python package structure eliminating sys.path hacks
- `testing-baseline`: pytest framework, unit tests, coverage reporting
- `config-management`: Environment-based configuration for country/locale/currency and secrets

### Modified Capabilities
None — this project has no existing specs in `openspec/specs/`.

## Approach

**Tier 1 — Security + Stability** (first, blocks everything else):
- Sanitize all innerHTML writes in `src/static/js/ofertas.js` using `textContent` or a sanitizer
- Add `flask-wtf` CSRF to all POST forms
- Replace `while+sleep` in `src/triggers.py` with `crochet.wait_for()` or threading.Event with timeout
- Replace `requests.get()` in `steamScrape/spiders/offers_steam.py` with Scrapy's async download

**Tier 2 — Architecture** (after Tier 1 stabilizes):
- Flatten `sys.path` hacks: make `src/` and `steamScrape/` proper packages with `__init__.py`, add to `pyproject.toml` or `setup.py`
- Merge duplicated TriggerGame/TriggerOffers into a single `TriggerRunner` class with config
- Delete dead `steamScrape/spiders/juegospider.py`
- Extract hardcoded VE/es-ES/USD to `config.yaml` or env vars

**Tier 3 — Quality**:
- Add `pytest`, `pytest-cov`, `ruff` to dev deps
- Write tests for: trigger timeout, route responses, spider parse methods
- Add `ruff` lint config, `mypy` basic checks

**Tier 4 — Professional**:
- Split `requirements.txt` → `requirements.txt` (prod) + `requirements-dev.txt`
- Add CI workflow (GitHub Actions: lint + test on push/PR)
- Minimal README update with setup/run/test instructions

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/triggers.py` | Modified | Replace blocking loop, merge duplicated classes |
| `src/static/js/ofertas.js` | Modified | XSS sanitization |
| `src/routes/index.py` | Modified | Add CSRF, error handling |
| `src/templates/*.html` | Modified | CSRF token fields in forms |
| `steamScrape/spiders/offers_steam.py` | Modified | Replace sync requests with async |
| `steamScrape/spiders/juegospider.py` | Removed | Dead code |
| `main.py` | Modified | Remove sys.path hack |
| `requirements.txt` | Modified | Split prod/dev, trim pinned deps |
| `pyproject.toml` | New | Package metadata, tool config |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scrapy sites change HTML structure, breaking spiders | High | Add defensive parsing with fallbacks; test with cached HTML fixtures |
| Crochet/Reactor interaction breaks under async refactor | Medium | Test with integration tests before deploy; keep Crochet as bridge |
| Render deployment constraints differ from local | Low | Keep Waitress WSGI; test Dockerfile if used |
| CSRF breaks existing form submissions | Low | Add token to all forms in one pass; test each endpoint |

## Rollback Plan

Each tier is independently revertible via git revert. Tier 1 changes are isolated to 4 files. If a tier breaks deploy, revert that tier's commits only — lower tiers are unaffected. No database migrations involved.

## Dependencies

- `flask-wtf` for CSRF (add to requirements)
- `bleach` or `nh3` for HTML sanitization (evaluate — may use DOMPurify JS-side instead)
- pytest + ruff + mypy added to dev dependencies

## Success Criteria

- [ ] Zero innerHTML writes with unsanitized user data
- [ ] CSRF token present on all POST forms
- [ ] Spider triggers timeout after configurable limit (default 60s) instead of blocking forever
- [ ] `sys.path` hacks removed; imports work via package installation
- [ ] `ruff check` passes with zero warnings
- [ ] `pytest` runs with >0% coverage (baseline established)
- [ ] Dead code (juegospider.py) deleted
