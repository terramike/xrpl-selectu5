# Selectu5 audit repair — status report

Date: 2026-10-09 (America/Los_Angeles).
Branch: `fix/selectu5-install-boundaries`.
Audited commit: `bb1072536906c93b4d98ff6c36ca0749ef368a7f` (v0.2.0).
Audit: `Selectu5-Audit-and-Alfred-Instructions-STE100.md` (Mike, 2026-10-09).

Real installation remains DISABLED (`INSTALL_ENABLED = False`) until
Mike reviews this report and the remaining maintainer decisions land.
The core XRPL Muse implementation is unchanged by this repair.

## Finding status

| Finding | Status | Evidence |
| --- | --- | --- |
| F01 destination escape / core overwrite | Closed in code | Strict ID rules, reserved core IDs, `validate_destination` (canonical root, symlink, case collision). Tests A01, A02. Install engine calls it under the lock. |
| F02 approval does not bind package | Closed in code | Canonical plan + SHA-256 plan digest shown before approval; `--plan` mismatch refused; 40-char commit pins only; approved GitHub owner pairs; `archive` overrides banned from catalogs; digest verify before extraction. Tests A06, A07, A09. |
| F03 failed update loses active install | Closed in code | Same-filesystem staging, unique backup names, transaction record before first rename, restore on final-rename failure, recovery pass before new mutations, exclusive lock. Tests A17, A18, A19, A29. |
| F04 resource limits | Closed in code | Chunk-bounded reads (registry 1 MiB, download 25 MiB, deadline), archive metadata limits, counted decompression. Tests A10, A11, A12. |
| F05 manifest access may be absent | Closed in code | Strict frontmatter grammar, duplicates rejected, name/version/access required. Test A13. |
| F06 Community Shows seed.json rejected | Companion ready | Branch `fix/selectu5-fixture-rename` in terramike/xrpl-community-shows at `433f7538f18e`: `access` frontmatter added, fixture renamed to `data/shows-fixture.json`, v0.2.2. Needs Mike's review and merge before Selectu5 pins it. Credential-name rejection retained. Test A15/A16. |
| F07 core compatibility ignored | Closed in code | `>=MAJOR.MINOR.PATCH` only; absent/unknown/old core refuses. Test A14. |
| F08 registry validation and display | Closed in code | Whole-catalog validation, duplicate/unknown rejection, control-character rejection and escaping. Tests A01, A05, A25. |
| F09 inventory trusts backups/symlinks | Closed in code | `.bak-` and dot folders excluded, symlink manifests rejected, bounded metadata reads. Test A20. |
| F10 update check misreports versions | Closed in code | Semantic ordering; newer and unknown states reported plainly. Test A21. |
| F11 inventory depends on registry | Closed in code | `installed` runs with no catalog; fallback prints source, catalog date, and a stale warning. Tests A23, A24. Tests: `test_A23_installed_without_registry`, `test_remote_registry_fallback`. |
| F12 documents disagree | Closed in docs | SKILL/SPEC/README now separate transaction access from install side effects, state the host approval boundary, and describe snapshot freshness. Test A30 is this review. |
| F13 release and test controls | Partial | CI workflow added (Linux + Windows jobs). The token in this environment cannot read Actions runs (HTTP 403), so a green remote run is not yet evidenced. License not selected: maintainer decision required. Branch protection: maintainer decision required. |

## Acceptance mapping

Executed in tests: A01, A02, A05, A06, A07, A09, A10 (download limit
logic via `read_limited`; registry limit unit path), A11, A12, A13,
A14, A15, A16, A17, A18, A19, A20, A21, A23, A24, A25 (validation
rejection), A26 (core and showcase stay notices), A27 (dry runs change
nothing; install fixtures assert no target on refusal), A29.
Source-inspected or environment-limited: A03 (destination checks are
unit-tested; no hostile concurrent writer is assumed — see limits),
A04 (backup names come from the validated ID plus a transaction ID,
never manifest text), A08 (redirect handler refuses non-https;
catalogs cannot carry overrides), A22 (provenance needs a reviewed
artifact digest in the catalog; the comparison logic ships with the
metadata record but no live entry carries a digest yet), A28 (CI
defined for Linux and Windows; remote run unverified from here),
A30 (documentation sync in this branch).

## Commands run

- `python3 -m unittest discover -s tests` — 37 tests, OK (3 install
  fixtures skipped while the gate is shut; they return with the
  re-enable review).
- Offline dummy installs through the test transport with fixture
  archives only. No real package script ran. No live GitHub archive
  was downloaded through the installer.

## Limits that remain true

- Two renames are not one atomic transaction; the transaction record
  is the recovery mechanism. Recovery is tested for the recorded
  intermediate states, not for power loss mid-write on every platform.
- A canonical path check does not stop a hostile writer that already
  controls the skills root. Supported use assumes no hostile
  concurrent writer in that directory.
- A plan digest proves consistency, not human consent. The host must
  enforce the user's approval before a real install call.
- Supported systems: Linux (tested locally) and Windows (CI defined,
  run unverified from this environment). macOS is not claimed.

## Maintainer decisions still needed

1. Review and merge the Community Shows companion branch, then let
   Selectu5 pin its reviewed commit and artifact digest.
2. Choose a license before any public distribution.
3. Enable branch protection and required checks on `main`.
4. Decide the fixed release artifact format (preferred over a
   regenerated repository ZIP) so artifact digests stay stable.
5. Say the word to re-enable real installation after reviewing this
   report; the gate does not open on its own.
