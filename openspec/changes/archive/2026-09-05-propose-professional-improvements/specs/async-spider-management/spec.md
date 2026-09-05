# Async Spider Management Specification

## Purpose

Make spider triggers non-blocking, time-bounded, cancellable, and observable so a slow crawl cannot freeze the Flask request thread or fail silently.

## Requirements

### Requirement: REQ-ASM-1 — Non-blocking trigger with timeout

The system MUST NOT block the Flask request thread on a spider run; every trigger MUST complete or abort within a configurable timeout (default 60 seconds); an abort MUST return an HTTP error instead of hanging.

#### Scenario: Crawl completes in time

- GIVEN a spider run that finishes within the timeout
- WHEN a user submits a scrape request
- THEN the response returns the crawl results
- AND the request thread stays responsive during the crawl

#### Scenario: Crawl exceeds the timeout

- GIVEN a spider run that exceeds the configured timeout
- WHEN the trigger awaits completion
- THEN the trigger aborts after the timeout
- AND the route returns an HTTP error (502/504), not a hang

### Requirement: REQ-ASM-2 — Cancellation of in-flight crawls

The system MUST signal cancellation to an in-flight crawl when its trigger times out and MUST NOT leave orphaned threads occupying the reactor.

#### Scenario: Timeout cancels the crawl

- GIVEN a crawl still running at the timeout boundary
- WHEN the trigger aborts
- THEN the crawl is cancelled via the CrawlerRunner API
- AND no orphaned thread keeps the reactor busy afterwards

### Requirement: REQ-ASM-3 — Error propagation and logging

The system MUST surface spider/trigger failures to the HTTP response (5xx) and MUST log every failure with spider name and reason; silent `{store: None}` results MUST NOT be the only failure signal, and one failing store MUST NOT discard successful stores' results.

#### Scenario: Spider failure surfaces to the route

- GIVEN a spider raises or yields nothing due to a page-structure change
- WHEN the crawl finishes
- THEN the failure is logged with spider name and error
- AND the route returns an error response instead of HTTP 200 with empty data

#### Scenario: Partial failure preserves successes

- GIVEN one store's parser fails on unexpected markup
- WHEN other spiders still succeed
- THEN the failed store is reported as failed
- AND the successful stores still return their results

### Requirement: REQ-ASM-4 — Async downloads inside spiders

The system MUST NOT perform synchronous HTTP (`requests.get`) inside any Scrapy spider; all page downloads MUST use Scrapy's async request pipeline.

#### Scenario: offers_steam uses Scrapy requests

- GIVEN `offers_steam.py` previously called `requests.get` inside the spider
- WHEN the spider runs
- THEN offer pages are fetched as Scrapy Requests
- AND no blocking HTTP call executes inside the Twisted reactor

### Requirement: REQ-ASM-5 — Single TriggerRunner class

The system MUST provide one trigger class parameterized by spider list, optional search term, and configuration, replacing `TriggerGame`/`TriggerOffers` without changing observable endpoint behavior.

#### Scenario: Game search uses the runner

- GIVEN the game-search endpoint
- WHEN a search term is submitted
- THEN the runner runs the game spiders with the term
- AND the response shape matches the previous TriggerGame behavior

#### Scenario: Offers scrape uses the runner

- GIVEN the offers endpoint
- WHEN a scrape is requested
- THEN the runner runs the offers spiders without a term
- AND the response shape matches the previous TriggerOffers behavior

## Technical Notes

- Tier 1 (timeout, cancellation, error handling, async downloads) plus Tier 2 (TriggerRunner merge); both touch `src/triggers.py` and `src/routes/index.py` — keep each tier's commits isolated for independent revert.
- MUST stay inside Crochet's reactor model: use `crochet.wait_for(timeout=...)` or a threading.Event bridge; do not add a second reactor or raw threads.
- The `count == 3` magic number MUST be derived from the configured spider list length.
- Timeout default (60s) MUST be configurable — see config-management REQ-CFG-4.
- Keep Waitress WSGI for Render; spiders must be testable with cached HTML fixtures (see testing-baseline).