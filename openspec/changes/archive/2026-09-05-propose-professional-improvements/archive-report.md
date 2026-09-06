# Archive Report: propose-professional-improvements

## Change Summary

**Change**: propose-professional-improvements
**Project**: gameScraper
**Archived**: 2026-09-05
**Artifact store**: openspec
**Branch at close**: `feat/tier4-professional`

gameScraper was transformed from a functional prototype into a maintainable, deployable, tested project across four chained tiers (security+stability → architecture/config → testing baseline → professional). The change introduced five NEW capabilities (security-hardening, async-spider-management, config-management, package-layout, testing-baseline) — the project previously had zero specs in `openspec/specs/`.

## Final State (at close)

Final-state facts are ranked per the Archive Final-State Authority: the persisted task artifact and the orchestrator's explicit final-state facts outrank intermediate snapshots.

- **Tasks**: 22/22 marked `[x]` in `tasks.md`, each mapping to a commit on `feat/tier4-professional` (chained tier1 → tier2 → tier3 → tier4, all ancestors of the current HEAD). Task Completion Gate passed — no unchecked implementation tasks remain.
- **Verifidation**: `verify-report.md` committed (`2ec7b2f`) and ledger-adjudicated. Verdict **PASS WITH WARNINGS**: 24/24 REQ MET, 34/34 scenarios runtime-covered, pytest 55/55, coverage 89% (535 stmts, 59 miss), `ruff check .` clean, `mypy src steamScrape` clean (18 source files). Evidence revision sha256 `2cd2c9408282a62a2dc9c38b72c7215f6cc8f0b54763fd6c1c926af35d89be25`; expected revision sha256 `340e6fb88986afe07ba30aad0a6c160cc7932aa487ca1ec0c6fd746d256a10e3`.
- **Verification warnings**: 2 WARNING (REQ-SEC-3 terminology reconciliation; loose-venv live-crawl reactor drift) — both non-CRITICAL, no blockers, no CRITICAL findings. 3 SUGGESTION (inert python-dotenv; cp314 wheel gap for pinned deps; optional pytest boot smoke test).
  - The REQ-SEC-3 terminology warning was folded into the promoted spec (see Reconciliations below), closing that warning at archive.
  - The reactor-drift warning is an environment artifact of unpinned deps on Python 3.14; pinned CI (Scrapy 2.12 defaulting to epoll on Linux) is not expected to reproduce it. Confirmed before archive via the loose-venv wire smoke; flagged for a live-crawl smoke on CI.
  - SUGGESTIONs are carried into `openspec/project.md` Open Concerns.

## Artifacts Read (traceability)

Openspec files read during this archive phase:

- `openspec/changes/propose-professional-improvements/proposal.md`
- `openspec/changes/propose-professional-improvements/specs/README.md`
- `openspec/changes/propose-professional-improvements/specs/security-hardening/spec.md`
- `openspec/changes/propose-professional-improvements/specs/async-spider-management/spec.md`
- `openspec/changes/propose-professional-improvements/specs/config-management/spec.md`
- `openspec/changes/propose-professional-improvements/specs/package-layout/spec.md`
- `openspec/changes/propose-professional-improvements/specs/testing-baseline/spec.md`
- `openspec/changes/propose-professional-improvements/design.md`
- `openspec/changes/propose-professional-improvements/tasks.md`
- `openspec/changes/propose-professional-improvements/verify-report.md`

## Delta Spec Promotion

All five delta specs were promoted to `openspec/specs/{capability}/spec.md` (main spec did not exist; delta spec IS the full spec). Mechanical copy first, then required corrections applied as targeted edits.

| Capability | Promoted spec | Corrections applied |
|------------|---------------|---------------------|
| security-hardening | `openspec/specs/security-hardening/spec.md` | REQ-SEC-3 wording + sanitizer location note (below) |
| async-spider-management | `openspec/specs/async-spider-management/spec.md` | none (byte-identical) |
| config-management | `openspec/specs/config-management/spec.md` | REQ-CFG-1 defaults (below) |
| package-layout | `openspec/specs/package-layout/spec.md` | none (byte-identical) |
| testing-baseline | `openspec/specs/testing-baseline/spec.md` | none (byte-identical) |

`openspec/specs/README.md` and `openspec/project.md` were created as the promoted-capability index and project context respectively.

### Reconciliations Applied (required content corrections)

1. **REQ-SEC-3 wording (security-hardening spec)**: the spec consistently said the game-link field accepts a "store URL"; the implementation validates a **game search term** (`juego=` param) against the allowlist regex `^[A-Za-z0-9 \-\&'.,:!()+]+$` with max length 200. A literal URL containing `/` is rejected by design. The promoted security-hardening spec now uses "game search term" wording throughout REQ-SEC-3 and documents both scenarios accordingly.
2. **Sanitizer location (security-hardening spec)**: the nh3 sanitizer lives inline in `src/routes/index.py` per the design file matrix (design §8 / task 1.4 note); the standalone `src/security.py` mention in the proposal's design section was superseded. The promoted spec does not reference `src/security.py` and documents the inline `src/routes/index.py` location.
3. **REQ-CFG-1 defaults (config-management spec)**: both confirmed defaults are stated — Steam/EGS use `VE`/`es-ES`/`USD` and GOG uses `US`/`en-US`/`USD`.

## Archive Move

The change folder was moved to `openspec/changes/archive/2026-09-05-propose-professional-improvements/` via mechanical shell move (`mv` fallback used because the folder mixes tracked and untracked files, so `git mv` on the whole directory fails; snapshot-integrity verified before the fallback). The verbatim `diff -r` readback is recorded in the phase result; empty diff = byte-identity preserved.

## Archive Intent

Standard (non-partial). No intentional-with-warnings override was required; the 2 verification warnings were non-CRITICAL and non-blocking, and the REQ-SEC-3 wording warning was resolved at archive via the promoted-spec reconciliation.

## Open Concerns Carried Forward

Recorded in `openspec/project.md`:
1. **cp314 wheel gap**: pinned deps lack cp314 wheels (lxml 5.4.0, cryptography 44.0.3, Twisted 24.11.0, Scrapy 2.12.0) — use Python ≤3.13 locally; CI matrix is 3.11–3.13.
2. **python-dotenv declared but not loaded**: `.env` support inert — SUGGESTION to call `load_dotenv()` in `main.py` guarded to dev, or drop the dependency.
