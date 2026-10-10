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

1. Review public repository contents and history. Mike selected public source with fixed release assets and authorized the visibility change.
2. Prepare the exact pilot asset (S, D, package root) and the later catalog commit C for Mike's review.
3. Run actual artifact qualification (retrieval, fresh install, no-op, update, recovery, concurrency) on Linux and Windows.
4. Qualify host consent and one catalog entry (Stage 4).
5. Prepare the final production candidate and release packet (Stage 5).

Private repository access does not establish artifact access through the current installer.
No private-token delivery is planned. Mike authorized public repository visibility on 2026-10-10.
The connected GitHub tools cannot change visibility. A repository administrator must perform that step after the public-content review.
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
- Next action: Review the public repository contents and history, then prepare the exact pilot asset for qualification.

Public repository visibility is authorized. Exact asset publication and installer enablement remain pending.
Update this record before another pause. Preserve the tested identities and unresolved blockers.

## 2026-10-10 — Stage 3 actual-artifact qualification started

The v0.2.4 catalog-only prerelease is live at
`https://github.com/terramike/xrpl-selectu5/releases/tag/v0.2.4` (repository is
public; asset verified: 31,064 bytes, SHA-256
`98ccb8d50f2a66c105a0efa39aa337f234d11b135245ce5b0054156e74b3f5a2`).
`scripts/qualify_artifact.py` retrieves that asset through the production
fetcher and exercises fresh installation, no-op, rejected requests, and lock
contention in a disposable root. Linux evidence is recorded in
`docs/production/STAGE3-RESULTS.md` and `stage3-evidence.json`; CI runs the
same harness on Linux and Windows.

Still open in Stage 3: an actual update (needs a second distinct reviewed
artifact), an actual-artifact interruption run, and the Windows actual run.
No catalog commit C exists yet, no entry is installable from the shipped
client, and `INSTALL_ENABLED = False` remains the shipped gate.

The 0.2.5 prerelease was published by the release-automation workflows
(prep run 38038529791, digest approved, publish run verified) with release
immutability enabled. Actual update qualification now passes on Linux:
fresh 0.2.4 install -> production-fetcher update to 0.2.5 -> preserved
backup and zero-fetch no-op (`STAGE3-UPDATE-RESULTS.md`). Remaining Stage 3
items: the actual-artifact interruption run and the Windows actual run.
