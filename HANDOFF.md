# Selectu5 handoff

## Current state

Mike authorized the merge of PR #1 into `main` at `22528a2967133c78c59f7455188b8e5f1165fc0c`.
The package version is 0.2.3. The shipped installer remains disabled.
All bundled skill artifacts remain list-only.
Windows CI passed 62 tests. Linux CI passed 61 tests and skipped one native Windows test.

## Task

Use `docs/production/CODEX-GOAL.md` as the Codex `/goal` prompt.
Use `docs/production/RELEASE-CHECKLIST.md` for acceptance evidence.
Use `docs/production/evidence-template.json` to create the observed evidence record.
Read `REPAIR-REPORT.md` for repairs N01–N06 and the remaining release limitations.

## Remaining work

1. Qualify a catalog-only candidate.
2. Select and inspect one exact artifact.
3. Prove retrieval through the production fetch path.
4. Complete isolated installation, update, and recovery qualification.
5. Prepare release actions and the evidence for Mike's review.

Private repository access does not establish artifact access through the current installer.
The current transport has no private-artifact authentication support.
If actual retrieval cannot finish, record the blocker and complete independent work.

## Decisions

Mike must select the license before public distribution.
Repository controls need current verification and an exact configuration proposal.
Installer enablement, public release, and visibility changes remain separate decisions.
This handoff does not authorize them.

## Continuity record

Codex must update this section before a pause or the end of a session.

- Working branch and candidate commit: `codex/selectu5-production-qualification`, created from current `main` at `7db6c62951b552d15fa13cc09e1f083f073ca92a` (final PR head recorded in the PR).
- Completed stages and evidence paths: Stage 1 catalog-only qualification and Stage 3 synthetic harness complete locally; Stage 2 artifact pilot blocked at production transport; Stage 4 review package drafted in `docs/production/ACCEPTANCE.md` and `docs/production/evidence.json`.
- Commands and latest results: `python3 scripts/qualify.py --source-commit 7db6c62951b552d15fa13cc09e1f083f073ca92a ...` completed with synthetic checks passing and actual production fetch blocked; repository suite locally: 62 tests, OK, 1 skipped on Linux.
- Artifact source S, digest D, and catalog C: S = `7db6c62951b552d15fa13cc09e1f083f073ca92a`; D/C not qualified because `selectu5.fetch_distribution` returned HTTP 404 for the private repo archive.
- Current blockers: Exact-commit Linux/Windows CI confirmation on the PR head; license selection; repository-control plan/token limits; private-artifact transport design; production review.
- Next independent action: Open the qualification PR and confirm Linux/Windows checks on its head; if transport remains blocked, prepare a separate reviewed fixed-asset/authenticated transport design.
- Next decision needed from Mike: Review the concrete package in `docs/production/ACCEPTANCE.md`; license and release decisions remain separate.

Keep this record concise. Preserve actual identities, unresolved failures, and the next action.
