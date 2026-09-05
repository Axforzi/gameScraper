# Tasks: Professional Improvements

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,100–1,300 (T1≈300, T2≈350, T3≈400, T4≈200) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 4 PRs, one per tier: PR1 (T1) → PR2 (T2) → PR3 (T3) → PR4 (T4) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Work Units

| Unit | PR | Focused test command | Runtime harness | Rollback |
|------|----|----------------------|-----------------|----------|
| 1 T1 security+stability | PR1 | `pytest tests/test_routes.py tests/test_triggers.py` (T3) | `python main.py` + curl no-token POST → 400 | revert T1 commits |
| 2 T2 arch+config | PR2 | `pip install -e .`; import `src.triggers.TriggerRunner` | boot `main.py`; no `sys.path` in src/main | revert T2 commits |
| 3 T3 tests+gates | PR3 | `pytest --cov=src --cov=steamScrape`; `ruff check .` | `pytest` from root (fixtures only, no live sites) | revert T3 commits |
| 4 T4 deps+CI+README | PR4 | `pip install -r requirements.txt` shows no dev tooling | GitHub Actions push/PR | revert T4 commits |

## Phase 1 — Tier 1: Security + Stability

- [x] 1.1 (T1) **Deps**, REQ-SEC-1/2 §7 — `requirements.txt` += `flask-wtf`, `nh3`. Accept: pip resolves. Commit: `build(deps): add flask-wtf and nh3`
- [x] 1.2 (T1) **Timeout/cancel**, REQ-ASM-1/2/3 §2/3 — `src/triggers.py`: shared helper; `wait(timeout)`, `cancel()`→`crawl_runner.stop()`, per-crawler signals, 5 states, errors list. Accept: timeout abort, no orphan. Commit: `fix(triggers): bound runs with crochet timeout`. Deps: 1.1
- [x] 1.3 (T1) **Validation + error mapping**, REQ-SEC-3/ASM-3 §3/4 — `src/routes/index.py`: allowlist game-link; TimeoutError→504, exception→502. Accept: bad input 400, timeout 504. Commit: `fix(routes): validate game-link and map trigger errors`. Deps: 1.2
- [x] 1.4 (T1) **Server sanitizer**, REQ-SEC-1 §4 — sanitizer inline in `src/routes/index.py` (nh3 + URI allowlist); `src/security.py` module not in file matrix (design §file-matrix). Accept: script stripped, `javascript:` blocked. Commit: `feat(security): sanitize deal payloads with nh3`. Deps: 1.1
- [x] 1.5 (T1) **Client sanitization**, REQ-SEC-1 §4 — `src/static/js/ofertas.js`, `templates/index.html`: no `innerHTML` with data. `templates/ofertas.html` reviewed: static placeholder content only, no data sinks → no edit. Accept: script title as text. Commit: `fix(security): replace innerHTML writes with textContent`
- [x] 1.6 (T1) **CSRF all POSTs**, REQ-SEC-2 §4 — `src/app.py` (CSRFProtect, 400 handler; module-level `app` kept — factory needs main.py wiring, Tier 2), `base.html` meta, `index.html` hidden input, fetch header. Accept: no-token POST → 400, no trigger. Commit: `feat(security): enable CSRF on all POST surfaces`. Deps: 1.1
- [x] 1.7 (T1) **Async offers_steam**, REQ-ASM-4 §4/8 — `steamScrape/spiders/offers_steam.py`: `scrapy.Request` follow-up; drop `requests`/`Session`. Accept: no `requests` import. Commit: `fix(spiders): use scrapy.Request instead of requests.get`

## Phase 2 — Tier 2: Architecture + Config

- [x] 2.1 (T2) **Package markers**, REQ-PKG-1 §1 — create `src/__init__.py`, `src/routes/__init__.py`. Accept: `import src.routes`. Commit: `refactor(packaging): add package markers`
- [x] 2.2 (T2) **Settings**, REQ-CFG-1..4 §5 — new `src/config.py`: `Settings.from_env()`, defaults VE/es-ES/USD, SECRET_KEY fail-fast. Accept: unset env = today's values. Commit: `feat(config): add environment-based Settings`. Deps: 2.1
- [x] 2.3 (T2) **Config wiring**, REQ-CFG-1/3/4, PKG-1 §5/8 — `main.py` (drop sys.path/debug, Waitress from config), `steamScrape/settings.py` (DOWNLOAD_DELAY), 5 spiders URLs from Settings. Accept: no sys.path in src/main; overrides reach requests. Commit: `refactor(config): wire Settings through entrypoint and spiders`. Deps: 2.2
- [x] 2.4 (T2) **TriggerRunner merge**, REQ-ASM-5 §2 — `src/triggers.py`: `TriggerRunner(spiders, term, timeout)`, `len(spiders)`, drop `CrawlerProcess`; `src/routes/index.py` calls it. Accept: response shapes unchanged. Commit: `refactor(triggers): merge TriggerGame/TriggerOffers`. Deps: 2.2, 1.2
- [x] 2.5 (T2) **Dead code**, REQ-PKG-3 §8 — delete `steamScrape/spiders/juegospider.py`; extend `.gitignore`. Accept: absent, unreferenced. Commit: `chore(spiders): remove dead juegospider`
- [x] 2.6 (T2) **pyproject.toml**, REQ-PKG-2 §1/7 — create: packages src(+routes)+steamScrape(+spiders), package-data, ruff/mypy/pytest config. Accept: `pip install -e .` imports work. Commit: `build(packaging): add pyproject with tool config`. Deps: 2.1

## Phase 3 — Tier 3: Testing Baseline

- [x] 3.1 (T3) **Scaffolding**, REQ-TST-1 §6 — `tests/conftest.py` (app/client fixture, crochet setup, fixture readers) + `tests/fixtures/html|json/`. Accept: `pytest` exits 0. Commit: `test: add pytest scaffolding and cached fixtures`. Deps: 2.6
- [x] 3.2 (T3) **Trigger tests**, REQ-TST-2 §6 — `tests/test_triggers.py`: mocked spiders; timeout abort asserts `crawl_runner.stop()`; partial keeps successes; state machine. Commit: `test(triggers): cover timeout, cancel, partial failure`. Deps: 3.1, 2.4
- [x] 3.3 (T3) **Route tests**, REQ-TST-3 §6 — `tests/test_routes.py`: GET 200; no-CSRF POST → 400, run not called; bad input → 400; success → 200. Commit: `test(routes): cover CSRF, validation, error mapping`. Deps: 3.1
- [x] 3.4 (T3) **Spider parse tests**, REQ-TST-4 §6 — `tests/test_spiders.py`: fixture-driven parse; price/name/roman; malformed logged; `offers_steam` no `requests` import. Commit: `test(spiders): cover parse methods against fixtures`. Deps: 3.1
- [x] 3.5 (T3) **Config tests**, REQ-CFG §6 — `tests/test_config.py`: defaults, override, SECRET_KEY fail-fast. Commit: `test(config): cover defaults and fail-fast`. Deps: 3.1, 2.2
- [x] 3.6 (T3) **Quality gates**, REQ-TST-5/6 §7 — `pytest --cov` >0; `ruff check .` zero; `mypy src steamScrape` clean; fix violations. Commit: `chore(quality): satisfy coverage, ruff, mypy gates`. Deps: 3.2–3.5

## Phase 4 — Tier 4: Professional

- [x] 4.1 (T4) **Dependency split**, REQ-PKG-4 §7 — trim `requirements.txt` (drop requests, ipython); new `requirements-dev.txt` (−r + pytest, pytest-cov, ruff, mypy, python-dotenv, ipython). Accept: prod install lean. Commit: `3de5927 build(deps): split prod and dev requirements`. Deps: 1.1
- [x] 4.2 (T4) **CI workflow**, REQ-TST-7 §7 — new `.github/workflows/ci.yml`: lint + test jobs on push/PR; no secrets; pip cache. Commit: `1b599d8 ci: add lint and test workflow`. Deps: 4.1
- [x] 4.3 (T4) **README**, REQ-PKG-5 §8 — update `README.md`: setup/run/test incl. `SECRET_KEY`. Commit: `91ab388 docs: document setup, run, and test steps`. Deps: 4.1