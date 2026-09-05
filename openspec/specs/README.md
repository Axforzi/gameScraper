# Promoted Specifications

Source-of-truth specs promoted from archived changes. Once a change is archived, its delta specs are merged here and the change folder moves to `openspec/changes/archive/`.

## Capability Index

| Capability | Spec | Origin |
|------------|------|--------|
| security-hardening | `security-hardening/spec.md` | `propose-professional-improvements` (Tier 1) |
| async-spider-management | `async-spider-management/spec.md` | `propose-professional-improvements` (Tiers 1–2) |
| config-management | `config-management/spec.md` | `propose-professional-improvements` (Tier 2) |
| package-layout | `package-layout/spec.md` | `propose-professional-improvements` (Tiers 2, 4) |
| testing-baseline | `testing-baseline/spec.md` | `propose-professional-improvements` (Tiers 3, 4) |

All five capabilities were introduced as NEW specs by the `propose-professional-improvements` change (the project previously had zero specs in `openspec/specs/`). No MODIFIED/REMOVED/RENAMED requirements exist for this change; each promoted spec is a full capability spec.

## Wording Reconciliation Applied at Archive

- **security-hardening / REQ-SEC-3**: the `game-link` field is a **game search term** (passed as `juego=`), not a store URL. The promoted spec uses search-term wording and documents the allowlist `^[A-Za-z0-9 \-\&'.,:!()+]+$` with max length 200; a literal URL containing `/` is rejected by design.
- **security-hardening**: server-side sanitization (nh3 + URI allowlist) lives inline in `src/routes/index.py` per the design file matrix (§8). There is no standalone `src/security.py` module; the promoted spec does not reference one.
- **config-management / REQ-CFG-1**: confirmed defaults are per-store — Steam/EGS use `VE`/`es-ES`/`USD` and GOG uses `US`/`en-US`/`USD`. Both are reflected in the promoted spec.
