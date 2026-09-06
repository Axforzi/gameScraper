# Package Layout Specification

## Purpose

Turn the flat monolith into a proper installable Python package, eliminating every `sys.path` hack while preserving the Render deployment flow.

## Requirements

### Requirement: REQ-PKG-1 — Imports resolve via package installation

The system MUST make `src/` and `steamScrape/` importable packages (with `__init__.py`) and MUST remove every `sys.path` manipulation from `main.py`, `src/triggers.py`, and `src/app.py`.

#### Scenario: Fresh environment imports

- GIVEN a fresh venv with the package installed via pip
- WHEN the application entry point starts
- THEN all src and steamScrape imports resolve without sys.path edits

#### Scenario: No path hacks remain

- GIVEN a search across the codebase
- WHEN looking for `sys.path`
- THEN no application-code matches are found

### Requirement: REQ-PKG-2 — pyproject.toml package metadata

The system MUST declare package metadata, dependencies, and tool configuration (ruff, mypy, pytest) in `pyproject.toml` or an equivalent.

#### Scenario: Editable install works

- GIVEN pyproject.toml declaring src and steamScrape packages
- WHEN a developer runs `pip install -e .`
- THEN both packages import from anywhere in the repo

### Requirement: REQ-PKG-3 — Remove dead code

The system MUST delete `steamScrape/spiders/juegospider.py` and MUST remove unused imports found during the restructure (e.g., `CrawlerProcess` in `triggers.py`).

#### Scenario: Dead spider absent

- GIVEN the restructured package
- WHEN the project tree is inspected
- THEN `juegospider.py` does not exist
- AND nothing references it

### Requirement: REQ-PKG-4 — Separate dev and prod dependencies

The system MUST split dependencies into production (`requirements.txt`) and development (`requirements-dev.txt`); dev-only tools (pytest, pytest-cov, ruff, mypy, ipython) MUST NOT appear in production requirements.

#### Scenario: Production install is lean

- GIVEN a fresh production install from `requirements.txt`
- WHEN the installed packages are listed
- THEN no test or lint tooling is present

### Requirement: REQ-PKG-5 — README with setup/run/test instructions

The system MUST update the README with minimal setup, run, and test instructions reflecting the new package layout.

#### Scenario: Onboarding steps work

- GIVEN a developer follows the README
- WHEN they execute the install, run, and test commands
- THEN each command succeeds without undocumented steps

## Technical Notes

- Tier 2 (packaging, dead code) plus Tier 4 (dependency split, README); each tier's commits stay isolated for independent revert.
- Keep Waitress WSGI; the Render start command MUST keep resolving a valid entry point after the restructure.
- Scrapy `scrapy.cfg` and settings discovery MUST keep working with spiders inside an installed package.
- No new scraping targets, no framework migration, no containerization.