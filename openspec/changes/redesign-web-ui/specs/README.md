# Redesign Web UI — Change Specs

This change introduces one NEW capability: `web-ui`. No existing capability is modified — REQ-SEC-1..3 (security-hardening) are preserved verbatim as an implementation-only change (proposal §Capabilities). sdd-archive promotes `specs/web-ui/spec.md` to `openspec/specs/web-ui/spec.md` after verification.

## Capability Overview

| Capability | Requirements | Full spec |
|------------|--------------|-----------|
| web-ui | REQ-UI-1..10 | `specs/web-ui/spec.md` |

## ADDED Requirements by Capability

### web-ui

- REQ-UI-1 — Design token system
- REQ-UI-2 — Component layer
- REQ-UI-3 — Template structure
- REQ-UI-4 — Accessibility
- REQ-UI-5 — Client-side behaviors
- REQ-UI-6 — Responsive layout
- REQ-UI-7 — Additive currency contract
- REQ-UI-8 — Dependency and junk removal
- REQ-UI-9 — Security contract preservation
- REQ-UI-10 — Offline regression tests

## Revertibility

Single `git revert` of the UI commits restores the previous templates/static; backend routes and data shapes are untouched (proposal §Rollback Plan). Template + JS are coupled and MUST be reverted together, never as partial slices.