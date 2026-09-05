# Testing Baseline Specification

## Purpose

Establish a repeatable automated quality gate: pytest suite, coverage reporting, lint, type checks, and CI running lint + tests.

## Requirements

### Requirement: REQ-TST-1 — pytest suite runs

The system MUST provide a pytest setup (pyproject.toml or pytest.ini) that runs all tests with a single `pytest` command from the repo root.

#### Scenario: Full suite executes

- GIVEN dev dependencies installed
- WHEN pytest is run from the repo root
- THEN all tests execute and the run exits 0 on success

### Requirement: REQ-TST-2 — Trigger timeout unit tests

The system MUST unit-test trigger behavior — completion within timeout and abort at the configured timeout — using mocked spiders, never live sites.

#### Scenario: Timeout abort verified

- GIVEN a mocked spider that never completes
- WHEN the trigger runs with a short timeout
- THEN the trigger aborts at the timeout
- AND the error path (REQ-ASM-1/REQ-ASM-2) is exercised

### Requirement: REQ-TST-3 — Route tests

The system MUST test Flask routes with the test client: route existence, CSRF rejection (HTTP 400 without token), validation rejection (HTTP 400 on bad input), and success responses.

#### Scenario: CSRF rejection covered

- GIVEN the Flask test client
- WHEN a POST without a CSRF token hits a form endpoint
- THEN the response is HTTP 400
- AND no spider trigger is launched

### Requirement: REQ-TST-4 — Spider parse tests

The system MUST test spider parse methods against cached or mocked HTML fixtures, covering price cleaning, name matching, and roman-numeral conversion, with malformed input degrading gracefully instead of crashing.

#### Scenario: Price cleaning covered

- GIVEN a cached HTML snippet per store
- WHEN the parse method processes it
- THEN prices normalize to the expected form
- AND malformed prices are logged, not fatal

### Requirement: REQ-TST-5 — Coverage reporting

The system MUST run coverage via pytest-cov and MUST report a coverage percentage; the baseline MUST be above zero.

#### Scenario: Coverage report generated

- GIVEN pytest-cov configured
- WHEN `pytest --cov` runs
- THEN a coverage report is printed
- AND the reported total is greater than zero

### Requirement: REQ-TST-6 — Lint and type checks

The system MUST pass `ruff check` with zero warnings and MUST support basic `mypy` checks without errors at the configured (non-strict) level.

#### Scenario: Lint gate passes

- GIVEN ruff configured in pyproject.toml
- WHEN `ruff check` runs on the codebase
- THEN zero warnings are reported

### Requirement: REQ-TST-7 — CI runs on push and PR

The system MUST add a GitHub Actions workflow that runs lint and tests on push and pull request to the default branch.

#### Scenario: CI green on push

- GIVEN a push to the default branch
- WHEN the workflow runs
- THEN lint and test jobs execute
- AND the workflow is green when both pass

## Technical Notes

- Tier 3 (pytest, coverage, ruff, mypy) plus Tier 4 (CI); CI is its own revertible commit.
- No live-site tests: spider tests use cached HTML fixtures so the suite is deterministic.
- Crochet/reactor constraint: trigger tests MUST run within a single reactor per process; design tests around that.
- CI MUST require no secrets; it runs lint + tests only.