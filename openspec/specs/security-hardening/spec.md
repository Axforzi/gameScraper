# Security Hardening Specification

## Purpose

Eliminate XSS, CSRF, and input-validation vulnerabilities on all user-facing surfaces of the Flask frontend without changing the route set or UI behavior.

## Requirements

### Requirement: REQ-SEC-1 — Sanitize all client-side DOM writes

The system MUST NOT insert unsanitized spider or server data into the DOM via `innerHTML` or equivalent sinks in `src/static/js/ofertas.js`; every dynamic write MUST use `textContent` or an explicit sanitizer, and server-side sanitization MUST back any value echoed into templates.

#### Scenario: Malicious title rendered as text

- GIVEN a spider result whose game title contains `<script>alert(1)</script>`
- WHEN `ofertas.js` renders the deal card
- THEN the title appears as literal text
- AND no script element is injected or executed

#### Scenario: Sanitizer used for structured markup

- GIVEN a value that must preserve formatting
- WHEN it is rendered into an offer card
- THEN it passes through an explicit sanitizer before insertion
- AND the output contains no script, event-handler, or `javascript:` attributes

### Requirement: REQ-SEC-2 — CSRF protection on all POST forms

The system MUST enable CSRF protection (flask-wtf `CSRFProtect`) app-wide and MUST include a valid CSRF token on every POST form; any POST without a valid token MUST be rejected before the spider trigger starts.

#### Scenario: Valid form submission

- GIVEN a user loads a page containing a POST form
- WHEN the form is submitted with its CSRF token
- THEN the request is processed normally

#### Scenario: Missing or invalid token

- GIVEN a POST request without a CSRF token or with a stale one
- WHEN it reaches the server
- THEN the server rejects it with HTTP 400
- AND no spider trigger is launched

### Requirement: REQ-SEC-3 — Validate game-link input on routes

The system MUST validate the `game-link` form field before it reaches any spider: it is a **game search term** (passed to the trigger as the `juego=` parameter), not a store URL, so it MUST be non-empty, length-bounded (≤200 characters), and conform to the allowlist pattern `^[A-Za-z0-9 \-\&'.,:!()+]+$`; validation failures MUST return HTTP 400 with a user-facing message.

#### Scenario: Valid game search term accepted

- GIVEN a well-formed game search term (e.g. a game title or keyword) under 200 characters
- WHEN the form is submitted
- THEN validation passes
- AND the search term is passed to the spider trigger as the `juego=` parameter

#### Scenario: Empty or malformed input rejected

- GIVEN an empty `game-link` or one containing characters outside the allowlist (including a literal URL containing `/`, which is rejected by design)
- WHEN the form is submitted
- THEN the server responds HTTP 400 with an error message
- AND no spider is launched

## Technical Notes

- Tier 1; changes isolated to `src/static/js/ofertas.js`, `src/routes/index.py`, `src/templates/*.html`, and dependencies (flask-wtf). Isolated commits keep Tier 1 independently revertible.
- Defense in depth: client-side `textContent`/sanitizer in `ofertas.js` AND server-side sanitization of values echoed into templates. The server-side sanitizer (nh3 text cleaning plus an http(s) URI allowlist) is implemented inline in `src/routes/index.py` per the design's file matrix (design §8); there is no standalone `src/security.py` module.
- CSRF MUST be enabled in one pass so no POST endpoint stays unprotected; add tokens to all forms in the same change to avoid breaking existing submissions.
- Keep Waitress WSGI for Render. No UI redesign, no new frontend framework, no new scraping targets.