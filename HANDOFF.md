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

1. Review the exact pilot package in `docs/production/PILOT-RELEASE.md`. Public visibility is verified.
2. Prepare the exact pilot asset (S, D, package root) and the later catalog commit C for Mike's review.
3. Run actual artifact qualification (retrieval, fresh install, no-op, update, recovery, concurrency) on Linux and Windows.
4. Qualify host consent and one catalog entry (Stage 4).
5. Prepare the final production candidate and release packet (Stage 5).

Private repository access does not establish artifact access through the current installer.
No private-token delivery is planned. Mike authorized public repository visibility on 2026-10-10.
Mike changed repository visibility. Public visibility was verified on 2026-10-10.
Exact release asset publication and installer enablement still need review.

## Decisions

Mike selected Apache-2.0 on 2026-10-10. The repository and package inventory include `LICENSE` and `NOTICE`.
Repository controls need current verification and an exact configuration proposal.
Mike selected public source with fixed release assets from `terramike/xrpl-selectu5` on 2026-10-10.
Installer enablement and exact release asset publication remain pending.

## Continuity record

- PR #2 merged: merge commit `3e0f488e60bfe085630f74eca2435e09ee666dba`; tested head `7593c76e45b40f127c360eb297090d03f80791be`; all four CI jobs passed (66 tests per platform, one platform-specific skip each).
- Historical qualification evidence stays historical: `docs/production/ACCEPTANCE.md` and `docs/production/evidence.json` describe the PR #2 candidate, not the current installer code.
- Historical artifact S: `7db6c62951b552d15fa13cc09e1f083f073ca92a`; digest D and catalog C remain unqualified.
- Current branch: `codex/selectu5-fixed-asset-transport`, PR #3. Initial head `925c8e3097d6` passed all four CI jobs (73 tests/platform). Audit fixes followed before merge: source symlink/reparse refusal with containment, clean-export rebuild evidence, malformed asset-URL rejection, skill-only distribution, duplicate/colliding inventory refusal, and finished-ZIP validation. Final head and CI are recorded in PR #3.
- Remaining blockers: public-content review and package approval, actual artifact qualification, repository controls verification, final release review.
- Next action: review the exact pilot release packet, publish the approved asset through the repository operator, and complete actual qualification.

Public repository visibility is authorized. Exact asset publication and installer enablement remain pending.
Update this record before another pause. Preserve the tested identities and unresolved blockers.

## Stage 3 preparation

PR #3 merged at `8092edd2d765ec6d940a42756be190a21f27d566`. Its tested head `5e157df7062e0528f04add18d4bc4f0cf2586b2e` passed all four CI jobs.
Local verification: 78 tests, one native Windows skip, no failures.
The reproducible 0.2.4 pilot ZIP and catalog preview are documented in `docs/production/PILOT-RELEASE.md`.
Actual fixed-asset retrieval, installation, update, and host consent qualification remain incomplete.
