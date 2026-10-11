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

The actual-artifact interruption run also passes on Linux: a real
0.2.4 -> 0.2.5 update was SIGKILLed at the publish move, the next operation
restored 0.2.4 from its backup and then completed the 0.2.5 install
(`STAGE3-INTERRUPT-RESULTS.md`). Only the Windows actual run remains in
Stage 3, via the qualification branch CI.

Stage 3 closed 2026-10-10: CI on PR #5 head `393cc564` passed all four
jobs (linux and windows, push and pull_request), including the
actual-artifact, update, and interruption harnesses on Windows. The
Windows failures found and fixed on the way: backslash snapshot keys,
two vacuous checks (wrong-digest and lock) rebuilt on their own
destinations, and proc.kill() for cross-platform termination.

## Qualification evidence follow-up

Head `d1b276b87bffee1c4f5a9a01501e6c5f44941247` included current main and passed all four CI jobs.
A subsequent audit found that actual update qualification checked backup metadata without complete backup contents.
The follow-up compares exactly one backup against the complete original tree, including directories, bytes, and file modes.
It checks active package bytes and complete provenance after update and interrupted-update recovery.
No-op checks now include empty directories and modes.
Corruption, extra-backup, extra-directory, permission, and embedded-child syntax regressions cover these checks.
CI retains Stage 3 evidence for Linux and Windows and records each checkout's qualification and installer identities.
Use the final follow-up head's CI artifacts for acceptance. Earlier results remain historical evidence.
The shipped installer remains disabled. Host consent, credential-read evidence, catalog authority, and release enablement still need review.

## 2026-10-10 — Stage 4 review package prepared

Current state: public repository (Apache-2.0) with v0.2.4 and v0.2.5
prereleases published and independently digest-verified; Stage 3 actual
Linux qualification is complete including interruption recovery; release
immutability is enabled; `main` branch protection is applied and verified
(required linux+windows checks, one approval, no force pushes or branch
deletion, admins not enforced).

Stage 4 package (`docs/production/OPERATOR-ACTIONS.md`, refreshed
`evidence.json`, acceptance addendum) is proposed in this pull request.
Catalog C for the qualified 0.2.5 entry is proposed separately in PR #9
(commit `1519904c932d2e3893b14d19d997b0e7b1d02d6e`); merging it does not
enable installation. Remaining decisions: merge PR #5 and confirm the
Windows actual run, merge PR #9, and any installer enablement as its own
separate decision. `INSTALL_ENABLED = False` remains the shipped gate.

## Stage 3 final-head evidence reconciliation

PR #5 head `e84f3f07f8648fea26d264bc488d4ef57ca9fff6` passed all four Linux and Windows push and pull-request jobs.
The push checkout was that head. The pull-request checkout was `6f6dda89816f5e7326d32a9d3cda98809b687c96`.
Actual retrieval, fresh installation, update, interruption recovery, and no-op passed on both platforms.
The follow-up checks complete backup contents and active package bytes. CI retains Stage 3 evidence for both platforms.

CI: https://github.com/terramike/xrpl-selectu5/actions/runs/38042700935 and https://github.com/terramike/xrpl-selectu5/actions/runs/38042702810.
Earlier head results remain historical evidence. Stage 3 has passed; PR #5 still requires review and merge.
Review host consent, catalog authority, and credential-read evidence before a separate installer enablement decision.
Unchanged sentinel hashes do not establish zero reads. The shipped installer remains disabled.

## Independent change audit and shared instructions

Audit baseline: main `eb4c56ca94a53347e1579e44cf287459ca7f3e27`, PR #11 `0bfb00a04b0161fd823775e1ffde3ec4254dbfc4`, PR #12 `83d4452959ab9a2a60c21263aff2aa028ed1c852`.
Read `docs/agent-team/README.md` for the current audit, repair tasks, Codex goal, evidence, and historical instructions.
Local Linux suite: 87 tests, zero failures, one skip. Both audited PR heads have four successful CI jobs.
The audit reproduced invalid recovery evidence, a printed command without `--offline`, and incomplete bootstrap acceptance and artifact retention.
The bootstrap installs a disabled 0.2.5 predecessor. Qualification of later manual external-client update hops remains separate.
This instruction upload does not approve enablement, publication, or real user installation.
The current shared goal preserves those limits and requires findings A01 through A04 to close before acceptance.
