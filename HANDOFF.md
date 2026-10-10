# Selectu5 handoff

## Current state

PR #2 (production qualification) is merged. Merge commit on `main`: `3e0f488e60bfe085630f74eca2435e09ee666dba`.
Tested PR #2 head: `7593c76e45b40f127c360eb297090d03f80791be`. All four PR/push CI jobs passed; each platform ran 66 tests with one platform-specific skip.
The shipped installer remains disabled (`INSTALL_ENABLED = False`). All bundled skill artifacts remain list-only.
Synthetic installation qualification passes. Actual artifact qualification remains blocked: the generated `/archive/<commit>.zip` path cannot retrieve from the private repository, and generated source archives do not guarantee permanent ZIP bytes.
Supported first environment: Python 3.12 on Linux and Windows, local filesystem destinations only. macOS, network shares, and other Python versions are separate qualification work.
Current work (Stage 1–2 of the production plan): fixed-asset transport and packaging, with installation still disabled. See `docs/production/FIXED-ASSET-DESIGN.md`, `docs/production/PACKAGE-INVENTORY.md`, and `docs/production/DISTRIBUTION-DECISION.md`.

## Task

Use `docs/production/CODEX-GOAL.md` as the Codex `/goal` prompt.
Use `docs/production/RELEASE-CHECKLIST.md` for acceptance evidence.
Use `docs/production/evidence-template.json` to create the observed evidence record.
Read `REPAIR-REPORT.md` for repairs N01–N06 and the remaining release limitations.

## Remaining work

1. Mike records the distribution and license decision (`docs/production/DISTRIBUTION-DECISION.md`).
2. Prepare the exact pilot asset (S, D, package root) and the later catalog commit C for Mike's review.
3. Run actual artifact qualification (retrieval, fresh install, no-op, update, recovery, concurrency) on Linux and Windows.
4. Qualify host consent and one catalog entry (Stage 4).
5. Prepare the final production candidate and release packet (Stage 5).

Private repository access does not establish artifact access through the current installer.
No private-token delivery is planned. Publication, visibility change, and installer enablement remain Mike's separate decisions.

## Decisions

Mike must select the license before public distribution.
Repository controls need current verification and an exact configuration proposal.
Installer enablement, public release, and visibility changes remain separate decisions.
This handoff does not authorize them.

## Continuity record

- PR #2 merged: merge commit `3e0f488e60bfe085630f74eca2435e09ee666dba`; tested head `7593c76e45b40f127c360eb297090d03f80791be`; all four CI jobs passed (66 tests per platform, one platform-specific skip each).
- Historical qualification evidence stays historical: `docs/production/ACCEPTANCE.md` and `docs/production/evidence.json` describe the PR #2 candidate, not the current installer code.
- Historical artifact S: `7db6c62951b552d15fa13cc09e1f083f073ca92a`; digest D and catalog C remain unqualified.
- Current branch: `codex/selectu5-fixed-asset-transport` (Stage 1–2: fixed-asset design, deterministic packaging, catalog/plan binding, transport support; gate disabled).
- Remaining blockers: distribution/license decision, actual artifact qualification, repository controls verification, final release review.
- Next action: Mike reviews the fixed-asset PR and records the distribution decision; then prepare the exact pilot asset for qualification.

Publication, visibility, and installer enablement remain separate decisions.
Update this record before another pause. Preserve the tested identities and unresolved blockers.
