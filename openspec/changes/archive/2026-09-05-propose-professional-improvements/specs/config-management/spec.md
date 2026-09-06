# Configuration Management Specification

## Purpose

Replace hardcoded country/locale/currency, secrets, and deployment knobs with environment-based configuration, keeping default behavior identical when variables are unset.

## Requirements

### Requirement: REQ-CFG-1 — Country/locale/currency via environment

The system MUST source country (`VE`), locale (`es-ES`), and currency (`USD`) from environment variables or a config file, with today's values as defaults so current behavior is unchanged when unset.

#### Scenario: Defaults preserve current behavior

- GIVEN no config variables set
- WHEN the app starts
- THEN country=VE, locale=es-ES, currency=USD are used

#### Scenario: Override via environment

- GIVEN COUNTRY=US, LOCALE=en-US, CURRENCY=EUR are exported
- WHEN a spider builds its store URLs
- THEN the overridden values appear in the requests

### Requirement: REQ-CFG-2 — Secrets from environment

The system MUST load the Flask `SECRET_KEY` (and any other secrets) from the environment and MUST fail fast at startup when a required secret is missing in production.

#### Scenario: Missing secret fails fast

- GIVEN production mode
- WHEN `SECRET_KEY` is not set
- THEN startup aborts with a clear error message

#### Scenario: Secret loaded successfully

- GIVEN `SECRET_KEY` is set in the environment
- WHEN the app initializes
- THEN sessions and CSRF signing use that key

### Requirement: REQ-CFG-3 — Deployment knobs via environment

The system MUST read Waitress host/port and debug mode from the environment; debug MUST default to off and MUST NOT be enabled in production.

#### Scenario: Waitress binds configured values

- GIVEN `HOST` and `PORT` are set
- WHEN Waitress starts
- THEN it binds to those values

#### Scenario: Debug off by default

- GIVEN no `DEBUG` variable
- WHEN the app starts
- THEN debug mode is disabled

### Requirement: REQ-CFG-4 — Tunables via configuration

The system SHOULD expose spider settings (`DOWNLOAD_DELAY`) and the spider-trigger timeout (default 60s) through the same configuration mechanism.

#### Scenario: Timeout override honored

- GIVEN `SPIDER_TIMEOUT=10` is set
- WHEN a trigger runs
- THEN the trigger aborts after 10 seconds (per REQ-ASM-1)

## Technical Notes

- Tier 2; values extracted: VE/es-ES/USD, SECRET_KEY, Waitress host/port, debug mode, DOWNLOAD_DELAY, spider timeout.
- `.env` support (python-dotenv) is dev-only; secrets MUST never be logged or committed.
- Defaults MUST equal today's hardcoded values so a bare deploy behaves exactly like the current app on Render.
- Env vars only — no config service, no monitoring stack, no containerization changes.