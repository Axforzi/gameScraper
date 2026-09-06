# Propose Professional Improvements — Change Specs

This change introduces five NEW capabilities. The project has zero existing specs in `openspec/specs/`, so every capability below is a complete new spec (no MODIFIED/REMOVED/RENAMED requirements exist for this change). sdd-archive promotes these specs to `openspec/specs/{capability}/spec.md` after verification.

## Capability Overview

| Capability | Tier | Requirements | Full spec |
|------------|------|--------------|-----------|
| security-hardening | 1 | REQ-SEC-1..3 | `specs/security-hardening/spec.md` |
| async-spider-management | 1–2 | REQ-ASM-1..5 | `specs/async-spider-management/spec.md` |
| config-management | 2 | REQ-CFG-1..4 | `specs/config-management/spec.md` |
| package-layout | 2, 4 | REQ-PKG-1..5 | `specs/package-layout/spec.md` |
| testing-baseline | 3, 4 | REQ-TST-1..7 | `specs/testing-baseline/spec.md` |

## ADDED Requirements by Capability

### security-hardening (Tier 1)

- REQ-SEC-1 — Sanitize all client-side DOM writes
- REQ-SEC-2 — CSRF protection on all POST forms
- REQ-SEC-3 — Validate game-link input on routes

### async-spider-management (Tiers 1–2)

- REQ-ASM-1 — Non-blocking trigger with timeout
- REQ-ASM-2 — Cancellation of in-flight crawls
- REQ-ASM-3 — Error propagation and logging
- REQ-ASM-4 — Async downloads inside spiders
- REQ-ASM-5 — Single TriggerRunner class

### config-management (Tier 2)

- REQ-CFG-1 — Country/locale/currency via environment
- REQ-CFG-2 — Secrets from environment
- REQ-CFG-3 — Deployment knobs via environment
- REQ-CFG-4 — Tunables via configuration

### package-layout (Tiers 2 and 4)

- REQ-PKG-1 — Imports resolve via package installation
- REQ-PKG-2 — pyproject.toml package metadata
- REQ-PKG-3 — Remove dead code
- REQ-PKG-4 — Separate dev and prod dependencies
- REQ-PKG-5 — README with setup/run/test instructions

### testing-baseline (Tiers 3 and 4)

- REQ-TST-1 — pytest suite runs
- REQ-TST-2 — Trigger timeout unit tests
- REQ-TST-3 — Route tests
- REQ-TST-4 — Spider parse tests
- REQ-TST-5 — Coverage reporting
- REQ-TST-6 — Lint and type checks
- REQ-TST-7 — CI runs on push and PR

## Revertibility

Each tier is independently revertible via git revert: Tier 1 = security-hardening + REQ-ASM-1..4; Tier 2 = config-management, package-layout REQ-PKG-1..3, and REQ-ASM-5; Tier 3 = testing-baseline REQ-TST-1..6; Tier 4 = package-layout REQ-PKG-4..5 and REQ-TST-7. No database migrations are involved.