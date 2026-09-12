# Archive Report: redesign-web-ui

## Change Summary

**Change**: redesign-web-ui
**Project**: gameScraper
**Archived**: 2026-09-11
**Artifact store**: openspec
**Branch at close**: `main` (local, ahead of `origin/main` by 9 commits)

Replaced gameScraper's Bootstrap + dual-icon-CDN frontend with a zero-build vanilla CSS design-token system and component layer (`tokens.css` + `app.css`, ~198-line `app.js`, inline SVGs), fixed 5 UI bugs (cover fallback, divide-by-zero, ≤576px overflow, a11y gaps, 504 partials), and added an additive `currency` key to 200 envelopes — while preserving REQ-SEC-1..3, the CSRF meta/input contract, and backend route shapes untouched. Introduced one NEW capability: `web-ui` (REQ-UI-1..10).

## Final State (at close)

Final-state facts are ranked per the Archive Final-State Authority: explicit final-state facts from the orchestrator launch prompt and the persisted task artifact outrank intermediate snapshots (`apply-progress`, `verify-report`).

- **Verify disposition**: the verify attempt was settled as **passed** in the native runtime ledger (`gentle-ai sdd-attempt settle` state: complete; objective verify-t0-t16 closed). `verify-report.md` records verdict **PASS WITH WARNINGS** (10/10 requirements, 17/17 scenarios, 0 CRITICAL, 0 blockers) — consistent, non-blocking.
- **Final suite state**: **73 passed, 4 warnings in 0.31s**. The 4 warnings are a pre-existing `DeprecationWarning: isSet()` from `crochet/_eventloop.py`, NOT caused by this change. (verify-report already stated 73/73; the launch-prompt fact confirms the warnings are pre-existing.)
- **Static checks**: `ruff check .` all checks passed; `mypy src steamScrape` success on 18 source files.
- **Tasks**: 17/17 marked `[x]` in `tasks.md` (T0–T16). Task Completion Gate passed — no unchecked implementation tasks remain; no stale-checkbox reconciliation was needed.
- **Commits**: 4 apply commits on top of the redesign scope — `ad87a72` (currency), `605c32e` (static assets), `f04445f` (atomic template+JS rewrite), `072edc0` (offline tests); SDD artifacts committed in `271c77f` (docs). Task 5.1 (T16) is the verify-only sweep, no commit.
- **Working tree**: clean at close except `.atl/` (skill registry cache, intentionally untracked — untouched by this phase). The archive operation itself (promoted spec, README index update, folder move, this report) is left uncommitted by design — commit staging is orchestrated separately.

## Artifacts Read (traceability)

Openspec files read during this archive phase:

- `openspec/changes/redesign-web-ui/proposal.md`
- `openspec/changes/redesign-web-ui/specs/web-ui/spec.md`
- `openspec/changes/redesign-web-ui/design.md`
- `openspec/changes/redesign-web-ui/tasks.md`
- `openspec/changes/redesign-web-ui/verify-report.md`
- `openspec/config.yaml` (rules.archive: "Warn before merging destructive deltas" — no destructive delta, no warning required)

Shared skills loaded: `sdd-archive/SKILL.md` (paths-injected), `skills/_shared/sdd-phase-common.md`, `skills/_shared/openspec-convention.md`.

## Delta Spec Promotion

The `web-ui` main spec did not exist → the delta spec IS the full spec. It was promoted via mechanical shell copy (`cp` to temp in target dir → `diff -r` readback → `mv`), byte-identical: sha256 `d14786872b97e3f6867191142fc0123bd25395dd5c5bbdae01fab3c0b34c81d7` matches the archived delta. File mode aligned to `644` after the copy (mktemp default `600`); content untouched.

| Capability | Promoted spec | Corrections applied |
|------------|---------------|---------------------|
| web-ui | `openspec/specs/web-ui/spec.md` | none (byte-identical) |

`openspec/specs/README.md` capability index updated with the `web-ui` row.

### No Wording Reconciliation Required

The three verify-report WARNINGs are drift from descriptive (non-contractual) figures, not spec inaccuracies — the promoted spec stands byte-identical:

1. **app.js at 198 lines vs "~80-line" (REQ-UI-5, design D7, task 2.4)**: REQ-UI-5's MUST applies to behaviors (panel open/close, CSRF header, 65 s abort, per-store states, 504 partials, cover fallback, textContent-only) — all implemented and evidenced; the line-count figure is descriptive. No spec wording depends on the count.
2. **`.is-hidden` listed in D5/task 2.2 but unused**: the design naming list, not a spec requirement; hiding uses the native `hidden` attribute plus the `[hidden] { display: none !important }` token rule. No spec requirement references `.is-hidden`.
3. **Header brand as `img` referencing the kept `comparacion.svg` vs "inline brand SVG" (task 3.4 wording)**: REQ-UI-4 (logos MUST have `alt`) is met (`alt="Logotipo de gameScraper"`), and REQ-UI-8's inline-SVG requirement applies to icons (search/close/social — all inline), not the brand logo. design.md's "Kept" list explicitly retains `comparacion.svg`.

Per the prior archive convention (`openspec/specs/README.md` "Wording Reconciliation Applied at Archive"), wording reconciliation is applied only when the spec text is inaccurate; here the promoted spec is accurate as written.

## Archive Move

The change folder was moved to `openspec/changes/archive/2026-09-11-redesign-web-ui/` via mechanical `git mv` (all 7 files tracked), snapshot-guarded. The verbatim `diff -r` readback (pre-move recursive snapshot vs archived tree) is recorded in the phase result; empty diff = byte-identity preserved. `.gentle-ai-instance` (dispatcher instance marker) moved along with the change folder.

Verify checklist at close:

- [x] Main specs updated correctly (`openspec/specs/web-ui/spec.md` — new capability, byte-identical promotion)
- [x] Change folder moved to archive (`openspec/changes/archive/2026-09-11-redesign-web-ui/`)
- [x] Archive contains all artifacts (proposal, specs/README + specs/web-ui/spec.md, design, tasks, verify-report, .gentle-ai-instance)
- [x] Archived `tasks.md` has no unchecked implementation tasks (17/17 `[x]`)
- [x] Active changes directory no longer has this change (only `archive/` remains)
- [x] Verbatim `diff -r` readback output included in the phase result and empty (no differences) — both for spec sync and archive move

## Archive Intent

Standard (non-partial). No intentional-with-warnings override was required; the 3 verification warnings are non-CRITICAL, non-blocking drift from descriptive text, documented above and in `verify-report.md` (WARNING-1..3). No open concerns are carried forward to `openspec/project.md` (verify-report SUGGESTION: "none material"; the deviations are cosmetic).