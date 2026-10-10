# Selectu5 production acceptance report

Date: 2026-10-09 (America/Los_Angeles).
Repository: `terramike/xrpl-selectu5` (private).
Qualification branch: `codex/selectu5-production-qualification`.
Baseline main / artifact source commit S: `7db6c62951b552d15fa13cc09e1f083f073ca92a`.
Repair baseline referenced by the goal: PR #1 head `98e12c4e9c70f236e2122b17fb93fd0ac71338ca`, merge `22528a2967133c78c59f7455188b8e5f1165fc0c`.
Package version: `0.2.3`.
Shipped installer: **disabled** (`INSTALL_ENABLED = False`).

This report separates source inspection, synthetic checks, actual artifact checks, and live operations. It does not approve publication, installer enablement, or visibility change.

## Current baseline reconciliation (2026-10-10)

PR #2 is merged into `main` at `3e0f488e60bfe085630f74eca2435e09ee666dba`; tested PR head `7593c76e45b40f127c360eb297090d03f80791be`. All four PR/push CI jobs passed; each platform ran 66 tests with one platform-specific skip. The stage reports below remain the historical PR #2 qualification record and do not describe the current installer code. Current work is Stage 1-2 of the production plan (fixed-asset transport) on `codex/selectu5-fixed-asset-transport`; see `docs/production/FIXED-ASSET-DESIGN.md` and `docs/production/DISTRIBUTION-DECISION.md`.

## Stage 1 — catalog-only candidate

Status: All four CI jobs passed for PR head `e86b2d707a3df75e76ecdba9bb9cfb620e5b2d3d`. Both platforms also ran the harness. The final follow-up commit requires its own successful checks before merge.

Evidence:
- Code, SKILL.md manifest, and self catalog entry all report `0.2.3`.
- `INSTALL_ENABLED = False` verified in `scripts/selectu5.py`.
- Bundled skill entries remain list-only where artifact facts are incomplete: `xrpl-view-export`, `xrpl-community-shows`, and `xrpl-selectu5` lack a complete reviewed commit + artifact SHA-256 + package-root set.
- Local Linux run: `python3 -m unittest discover -s tests` = 62 tests, OK, 1 skipped (native Windows junction test). Local Python: 3.12.
- Independent CI verification for `e86b2d7`: Linux passed 61 tests with one Windows-only skip. Windows passed 62 tests without skips. Both harness runs completed 10 checks and correctly reported the artifact blocker.
- Offline listing, permissions cards, inventory, and update notices are covered by the repository suite and local CLI checks.
- GitHub workflow uses `actions/checkout@v4` and `actions/setup-python@v5` with Python 3.12 on Linux and Windows. The project has no third-party Python dependencies; imports are standard library only. GitHub's official Python workflow documentation still uses these action majors in its examples.
- `CHANGELOG.md` and `docs/production/RELEASE-NOTES-CATALOG-ONLY.md` added. UNC/network-share roots are excluded from production support until a native UNC pilot passes.

Repository controls:
- Current: repo is private; default branch is `main`. Branch-protection read returned GitHub HTTP 403: “Upgrade to GitHub Pro or make this repository public to enable this feature.” Actions run list returned HTTP 403: “Resource not accessible by personal access token.”
- Proposed exact settings when available: protect `main`; require status checks `linux` and `windows`; require pull-request review (1 approval); dismiss stale approvals; require conversation resolution; block force pushes and branch deletion.
- Missing permission/limitation: this token cannot read Actions runs, and branch protection is unavailable for this private repo on the current plan. Do not claim repository controls are configured.

License choices for Mike (no recommendation inferred):
- MIT: permissive reuse with attribution.
- Apache-2.0: permissive reuse with attribution and express patent grant.
- GPL-3.0: copyleft distribution terms.
- Proprietary / all rights reserved: no open-source reuse grant.
Public distribution remains blocked until Mike selects the license and scope.

## Stage 2 — exact artifact

Pilot artifact: Selectu5 itself (`xrpl-selectu5`, version `0.2.3`, access `read`, core requirement from manifest).
Source commit S: `7db6c62951b552d15fa13cc09e1f083f073ca92a`.
Production request URL: `https://github.com/terramike/xrpl-selectu5/archive/7db6c62951b552d15fa13cc09e1f083f073ca92a.zip`.
Production fetcher: `selectu5.fetch_distribution`.

Result: **blocked**. The production fetcher returned `OSError: HTTP Error 404: Not Found`. The repository is private and the current installer transport has no private-artifact authentication. An authenticated GitHub API read would not prove installer retrieval, so it was not used as a substitute.

Because transport did not retrieve the pilot:
- Observed redirects, archive bytes, SHA-256 D, package root from downloaded bytes, second-fetch digest, and catalog commit C are **not qualified**.
- No catalog update was made. The self entry remains list-only.
- Source inspection at S found no credential/secret filenames, no shell/batch/PowerShell/executable files, and Python imports limited to the standard library in the baseline tree.
- Installed package code was not executed during artifact qualification.

Blocker classification: transport blocker for artifact pilot and installer release. It does not block catalog-only review.

## Stage 3 — qualification harness

Harness: `scripts/qualify.py`, separate from the production CLI.
It creates its own disposable root, refuses to use shipped defaults for installation, records every override (install gate injection, synthetic fetcher, trusted-catalog injection, and supplied core version), and never changes shipped `INSTALL_ENABLED`. Plans are built only from `validate_destination()` canonical destinations, including under a raw skills path containing `/./`. The harness is now wired into both Linux and Windows CI jobs.

Observed local harness result (`/tmp/selectu5-qual-evidence.json` during the run):
- Source versions and gate: pass.
- Unqualified entries list-only: pass.
- Repository test suite: pass (62 tests, 1 skipped on Linux).
- Canonical plan destination under a `/./` raw path: pass.
- Synthetic fresh install via `cmd_install`: pass (one synthetic fetch).
- Synthetic matching-provenance no-op: pass (zero fetches; disposable skills tree unchanged).
- Synthetic update with backup preservation: pass (active identity is 1.0.1 with the v2 digest; backup manifest/provenance remain 1.0.0 with the v1 digest).
- Dummy core binding: `SELECTU5_CORE_DIR` points at the dummy core; the supplied core version is read from its manifest by the harness. Sentinel hashes are checked after each operation; dummy-core manifest reads during an operation are distinguished from credential-sentinel reads, which must be zero.
- Actual production fetch: blocked (HTTP 404 above).

Synthetic checks cannot satisfy actual artifact checkboxes. Actual update qualification remains incomplete until two artifacts are retrievable through the production transport. The repository suite retains process-death, repeat-recovery, invalid-provenance, lock, wrong-digest, unsafe-archive, invalid-manifest, core-incompatibility, transport-deadline, 150-transaction history, and Windows-boundary tests; Windows-native assertions require exact-commit Windows CI.

## Stage 4 — operator readiness

Manual recovery for ambiguous published identity:
1. Stop further install attempts for that entry.
2. Preserve the pending journal, active package folder, staging leftovers, and all backups exactly as found.
3. Compare active `SKILL.md` and `.selectu5-meta.json` with the journal's old/new version, commit, and artifact digest.
4. Restore only a validated old backup after operator review; do not delete unknown active content automatically.
5. Rerun recovery only after the active path is resolved, then record the outcome.

Backup retention:
- Package backups are not deleted by catalog changes or terminal-journal history retention.
- Operators review backups before any manual removal. More than 1,000 current/history journal files requires manual review.

Withdrawal:
- To withdraw an entry, make it list-only in a reviewed catalog commit (remove artifact facts / mark non-installable by policy).
- Withdrawal preserves installed packages and backups. It does not delete active content.

Security reporting:
- Report suspected catalog, archive, or installer issues privately to Mike/terramike before public disclosure.
- If a version is suspect, withdraw its catalog artifact facts first, preserve evidence, then decide on version withdrawal and user notice.

Proposed operator actions and return paths (each needs Mike's separate approval):
1. Catalog-only publication: publish the reviewed 0.2.3 catalog-only note/package while gate stays disabled. Return path: withdraw the release/note and revert the catalog commit.
2. Repository controls: apply the proposed `main` protection when the plan supports it. Return path: restore prior branch settings recorded before change.
3. Pilot artifact/catalog: after transport design is reviewed, record S, D, and package root in catalog commit C. Return path: revert C to make the entry list-only; installed packages/backups remain.
4. Installer enablement: change `INSTALL_ENABLED` only in a separate reviewed release after qualification blockers close. Return path: disable the gate in a follow-up release and withdraw artifact facts.
5. Public visibility: change repo visibility only after license and package review. Return path: set repo private again; note that public exposure cannot be fully undone.

## Readiness summary

- Catalog-only release: **ready for review**. CI for `e86b2d7` is independently verified. The follow-up changes require successful checks before merge.
- Artifact pilot: **blocked** by private-artifact production transport (HTTP 404); no S/D/C qualification claimed.
- Installer enablement: **not approved** and remains disabled.
- Public visibility: **not approved**.

Remaining decisions for Mike: license; repository-control plan/permissions; catalog-only publication; pilot artifact after transport review; installer enablement; public visibility.

## Final harness follow-up

The harness compares every backup file, directory, and mode with the pre-update snapshot.
Regression tests reject corrupted payload bytes, an extra backup directory, and a POSIX permission change.
Linux completed 66 local tests with one native Windows skip during this follow-up.
The Windows suite skips the POSIX mode test. It runs the native Windows junction test.

Each check records only its own test overrides. The actual fetch check has no synthetic overrides.
The workflow fixes pilot source S separately from the checked-out qualification commit.
Each platform retains its qualification JSON and Markdown for 14 days, including failure output when available.
The runner-generated files identify the tested checkout. They establish the final follow-up result after CI finishes.

Verified historical checks for `e86b2d7`:
- Linux: https://github.com/terramike/xrpl-selectu5/actions/runs/38031784905/job/114154075930
- Windows: https://github.com/terramike/xrpl-selectu5/actions/runs/38031784905/job/114154075633

These changes do not qualify private artifact retrieval or enable installation.

## Stage 3 addendum — actual-artifact qualification (2026-10-10)

The v0.2.4 fixed release asset is published (public catalog-only prerelease)
and `scripts/qualify_artifact.py` now qualifies the **actual artifact**: the
production fetcher retrieves the live release asset (redirect chain recorded),
and fresh installation, same-version no-op, rejected requests, and lock
contention run against those exact bytes in a disposable root. Linux evidence:
`docs/production/STAGE3-RESULTS.md` and `stage3-evidence.json`. CI runs the
same harness on Linux and Windows.

Stage 3 update leg **closed on Linux**: the actual 0.2.4 -> 0.2.5 update between
published release assets passes through the production fetcher
(`docs/production/STAGE3-UPDATE-RESULTS.md`), including post-update no-op
and preserved 0.2.4 backup. Stage 3 remains partial only for the Windows actual run (CI on the
qualification branch). The actual-artifact interruption run also passes on
Linux: a real update killed at the publish move recovered to 0.2.4 and then
completed to 0.2.5 (`STAGE3-INTERRUPT-RESULTS.md`). No catalog
commit C exists, no entry is installable from the shipped client, and
`INSTALL_ENABLED = False` remains the shipped gate.
