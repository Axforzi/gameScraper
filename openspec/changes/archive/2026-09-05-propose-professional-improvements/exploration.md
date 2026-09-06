# Exploration: propose-professional-improvements

## Current State

gameScraper is a 686-line Python monolith that scrapes game prices from Steam, GOG, and Epic Games Store. Flask serves a frontend; Scrapy spiders do the heavy lifting, bridged by Crochet (Twisted reactor). The app is deployed to Render. There are zero tests, zero quality tools, zero CI/CD, and significant architectural debt that would prevent any professional team from maintaining this reliably.

## Affected Areas

- `src/triggers.py` — Core concurrency bridge; duplicated classes, blocking sleep loop, hardcoded magic numbers
- `src/routes/index.py` — No input validation, no error handling, no rate limiting
- `src/app.py` — Unused import, sys.path manipulation
- `main.py` — Redundant sys.path hack
- `steamScrape/spiders/*.py` — 6 spiders with heavy duplication, inconsistent error handling, mixed languages
- `steamScrape/spiders/steam.py` / `gog.py` / `epicgames.py` — Shared regex/roman numeral logic copy-pasted
- `steamScrape/spiders/offers_steam.py` — Makes synchronous HTTP requests INSIDE a Scrapy spider (requests + BeautifulSoup), completely defeating async
- `steamScrape/settings.py` — Hardcoded user agent, commented-out Selenium config, no env-based config
- `requirements.txt` — 65 pinned deps, includes ipython (dev tool), no dependency groups
- `.gitignore` — Only ignores `env`, missing `.venv`, `__pycache__`, `.env`, etc.

## Analysis by Area

### 1. Architecture (Severity: HIGH)

**Current**: Flat monolith. Flask app in `src/`, Scrapy in `steamScrape/`, connected by a module-level global `crawl_runner` and two nearly identical classes (`TriggerGame`/`TriggerOffers`) in `triggers.py`. No package structure, no separation of concerns.

**Issues**:
- `sys.path` hacks in both `main.py` and `triggers.py` to resolve imports — indicates broken package layout
- No application factory pattern (`create_app()`) — the Flask app is a module-level singleton
- Spiders are coupled to the web layer through `TriggerGame`/`TriggerOffers` (they import specific spider classes directly)
- No service layer — routes directly instantiate triggers and block
- `JuegoSpider` in `juegospider.py` is dead code (never imported anywhere)

### 2. Code Quality (Severity: HIGH)

**Duplication**:
- `TriggerGame` and `TriggerOffers` are 90% identical — same `__init__`, `crawler_result`, `finished_scrape`, `scrape_with_crochet` pattern. Only differ in whether `juego` is passed.
- Price cleaning logic (`replace('$', '').strip().split()[0]`) is copy-pasted across `steam.py`, `gog.py`, `epicgames.py`
- Roman numeral conversion logic is identical in `gog.py` and `epicgames.py`
- The entire offers rendering in `ofertas.js` is 3x copy-pasted blocks (steam/egs/gog)
- The modal rendering in `index.html` JS is 3x copy-pasted for each store

**Naming**: Mix of Spanish and English (`juego`, `nombre`, `precio`, `descuento` in items; English everywhere else). Inconsistent variable naming (`steamEventual`, `egsEventual`, `modiNombre`).

**Dead code**: `juegospider.py` is never used. `CrawlerProcess` is imported but never used in `triggers.py`. `prefix` is imported but unused in `app.py`. Multiple unused imports.

### 3. Security (Severity: HIGH)

- **No input validation**: `request.form.get('game-link')` is passed directly to Scrapy spiders without sanitization. The regex in spiders (`re.findall(r'[a-zA-Z0-9]+', juego)`) is the only defense.
- **No CSRF protection**: Flask app has no CSRF tokens on POST forms
- **XSS risk**: `innerHTML` is used extensively in frontend JS with unsanitized data (`clone.querySelector('.titulo').innerHTML = data.steam.nombre`)
- **Synchronous requests inside spider**: `offers_steam.py` makes raw `requests.get()` calls inside a Scrapy spider, creating a blocking call in the reactor
- **Hardcoded user agent**: Spoofs Chrome browser in `settings.py`
- **No secrets management**: No `.env` support, no environment variable handling at all

### 4. Error Handling (Severity: HIGH)

- **No try/except anywhere in the Python codebase**: Zero exception handling in spiders, routes, or triggers
- **Silent failures**: Spiders yield `{'steam': None}` when parsing fails, but no logging
- **Potential crashes**: `float(game['precio'].replace('$', ''))` will crash if `precio` is `None` or has unexpected format
- **No HTTP error responses**: Routes return 200 even when scraping fails
- **Blocking while loop**: `while self.scrape_completed is False: time.sleep(2)` — no timeout, can block forever
- **Hardcoded magic number**: `if self.count == 3` assumes exactly 3 spiders always

### 5. Configuration (Severity: MEDIUM)

- No config file or env var support
- Hardcoded URLs, country codes (`VE`), locale (`es-ES`), and currency (`USD`) in spider URLs
- `DOWNLOAD_DELAY = 1` hardcoded in `settings.py`
- Waitress host/port hardcoded in `app.py`
- Debug mode hardcoded in `main.py` (`app.run(debug=True)`)

### 6. Testing Surface (Severity: CRITICAL)

**Current state**: Zero tests. No test files, no test runner config, no pytest, no unittest, no coverage.

**What's needed**:
- Unit tests for price cleaning/normalization logic (high value, easy to test)
- Unit tests for the regex-based name matching in spiders
- Integration tests for Flask routes (at minimum, route existence and response codes)
- Mock-based tests for spider parsing (Scrapy's `Response` can be mocked)
- The `TriggerGame`/`TriggerOffers` classes need tests but are currently untestable due to global state and `time.sleep`
- Frontend JS is untestable without browser testing framework (Playwright/Puppeteer)

### 7. Documentation (Severity: MEDIUM)

- README is in Spanish, 10 lines, describes it as "a test to learn Scrapy with Flask"
- No API documentation for the POST endpoints
- No docstrings on any Python function or class
- No inline comments explaining business logic (only Scrapy boilerplate comments)
- No setup/installation instructions beyond the Render URL

### 8. Dependencies (Severity: MEDIUM)

- **65 pinned packages**: Many are transitive dependencies that shouldn't be pinned directly
- **Dev dependency mixed in**: `ipython==9.2.0` is a development tool in production requirements
- **No dependency groups**: No separation between production, dev, and test dependencies
- **`roman==5.0`**: Only used for converting arabic numerals to roman numerals in game names — very niche
- **`requests` AND `Scrapy`**: Two HTTP clients — `requests` is only used for the blocking calls in `offers_steam.py`
- **No lock file mechanism**: Just a flat requirements.txt

## Prioritized Recommendations

### P0 — Must fix before anything else

1. **Add exception handling**: Every spider parse method and every route needs try/except with logging. The current code will crash silently on any unexpected page structure change.
2. **Input validation on routes**: Validate and sanitize the `game-link` form field before passing to spiders.
3. **Add timeout to TriggerGame/TriggerOffers**: The `while` loop can block indefinitely.

### P1 — Critical for maintainability

4. **Deduplicate TriggerGame/TriggerOffers**: Extract a single `TriggerCrawler` class parameterized by spider list and optional search term.
5. **Extract shared spider logic**: Create a base spider class or utility module for price cleaning, roman numeral conversion, and name matching.
6. **Remove synchronous requests from offers_steam.py**: Use Scrapy's built-in request mechanism instead of `requests.get()`.
7. **Remove dead code**: Delete `juegospider.py`, unused imports.

### P2 — Needed for professional quality

8. **Establish test baseline**: Start with unit tests for price normalization and name matching (pure functions, high value). Add pytest + coverage.
9. **Fix sys.path hacks**: Restructure as a proper Python package with `pyproject.toml`.
10. **Add environment configuration**: Use `python-dotenv` or similar for config.
11. **Add linter/formatter**: ruff or flake8 + black.
12. **Fix .gitignore**: Add standard Python ignores.
13. **Add CSRF protection**: Flask-WTF or manual token.

### P3 — Nice to have

14. **Add API docs**: OpenAPI/Swagger for the two endpoints.
15. **Frontend refactoring**: Extract repeated JS into functions.
16. **Dependency cleanup**: Separate dev/prod deps, remove ipython from prod.
17. **CI/CD pipeline**: GitHub Actions with lint + test + coverage gates.

## Risks

- **Spiders depend on live sites**: Testing spiders requires either mocking HTTP responses or accepting flaky tests against real sites
- **Render deployment**: Any structural changes need to preserve the Render deployment flow
- **Spanish/English inconsistency**: Standardizing language is a cultural decision, not just technical
- **Scrapy+Crochet+Flask integration**: The bridge is fragile; changing concurrency model risks breaking the whole flow

## Key Learnings

1. The codebase is 686 lines of Python with zero tests, zero error handling, and zero configuration management.
2. The most dangerous code is the `while self.scrape_completed is False: time.sleep(2)` loop in triggers.py — it can block the web server indefinitely.
3. `offers_steam.py` makes synchronous HTTP requests inside a Scrapy spider using the `requests` library, completely defeating the async architecture.
4. TriggerGame and TriggerOffers are 90% duplicated code with only one parameter differing.
5. Frontend JavaScript uses innerHTML with unsanitized server data, creating XSS vulnerability surface.

## Ready for Proposal

Yes. The exploration identified concrete, actionable improvements across 8 areas with clear priority ordering. The P0 items (error handling, input validation, timeout) are safety-critical. The P1 items (deduplication, dead code removal, async fix) are the biggest bang-for-buck quality improvements. The P2 items (testing, packaging, config) establish the foundation for sustainable development.
