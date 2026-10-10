# Selectu5 audit repair — round 2 status report

Date: 2026-10-09 (America/Los_Angeles).
Branch: `fix/selectu5-install-boundaries-r2`.
Base commit: `5bcbd9a7c72f280f2939e39a06d9749d3a2139f2` (current private main).
Review input: `Selectu5-Repair-Review-and-Alfred-Instructions-STE100.md`.

Real installation remains DISABLED in the shipped command (`INSTALL_ENABLED = False`). Tests exercise the enabled path only by injecting the gate and a fixture fetcher into the same `cmd_install()` orchestration function the CLI calls. The core XRPL Muse implementation is unchanged.

## What round 2 changed

- `cmd_install()` now has one installation path. The legacy `fetch_archive()`, `install_root()`, `extractall()`, permissive manifest acceptance, and same-name backup deletion are removed.
- A real install requires `--yes <exact version>` and `--plan <digest>`. Missing or mismatched plan approval is refused before any fetch. Dry-run examples print both arguments.
- Installs require the locally reviewed bundled catalog. Remote and environment-selected catalogs are browse-only.
- Entries without an immutable 40-char commit, reviewed artifact SHA-256, and package root are list-only.
- Distribution retrieval uses exact approved owner/repository pairs, approved HTTPS redirect hosts, bounded reads, and a deadline.
- Recovery and installation run under an OS process lock acquired before recovery. Lock files are rendezvous points; process death releases the OS lock.
- Journals use random transaction IDs, root-relative backup names, strict schema validation, atomic replacement, and fsync where the platform supports it. Corrupt or ambiguous records stop mutation.
- Root validation checks supplied path components before canonicalization and refuses core/credential roots, symlink targets, and case collisions.
- Archive validation covers original member names, directory entries, file/directory collisions, unsupported member types, Windows reserved/ADS-style names, credential filenames, aggregate expanded bytes during extraction, and an extraction deadline.
- Semantic versions sort releases after prereleases and compare numeric prerelease identifiers numerically. An equal-base prerelease core does not satisfy a release requirement.
- Installed provenance (`.selectu5-meta.json`) is read back bounded and validated. Same-version digest or commit differences report as provenance differences, never as silently current.
- Package version is consistently `0.2.2` in the skill manifest, client, tests, and Selectu5 registry entry.

## Finding status

| Finding | Round-2 status | Evidence |
| --- | --- | --- |
| F01 | Repaired in code | Strict IDs, reserved core IDs, supplied-root component checks, engine-boundary validation. |
| F02 | Repaired in code | Required plan digest, exact repo pairs, trusted local catalog, immutable commits, artifact digest verification. |
| F03 | Repaired in code | OS lock before recovery, random tx IDs, validated journals, unique backups, rename refusal on existing destinations, restore-on-failure. Process-death lock/recovery test included. |
| F04 | Repaired in code | Bounded catalog/distribution reads, aggregate extraction counter, extraction deadline. |
| F05 | Repaired in code | Strict manifest parser is the install path; missing or duplicate safety fields fail. |
| F06 | Out of Alfred scope | Community Shows is owned by Codex. Selectu5 only lists facts Mike supplies; no Alfred-owned fixture/artifact work remains in this chat. The entry stays list-only until Mike supplies reviewed artifact facts. |
| F07 | Repaired in code | Same install path checks core compatibility; equal-base prerelease cores are refused. |
| F08 | Repaired in code | Catalog metadata is validated and escaped; invalid catalog data is distinguished from transport unavailability. |
| F09 | Repaired in code | Inventory rejects backup/symlink cases and requires valid manifest identity for a known version. |
| F10 | Repaired in code | Semantic ordering and provenance-difference reporting are implemented and tested. |
| F11 | Repaired in code | `installed` needs no registry; explicit `--offline` uses only the bundled catalog. |
| F12 | Repaired in docs | SKILL.md, SPEC.md, README, registry card, and report describe the same gated behavior and version. |
| F13 | Partial | Linux tests pass locally. Windows CI must pass on the exact pushed commit before this can close. License and branch protection remain maintainer decisions. |

## Acceptance evidence

Executed locally on Linux:

- `python3 -m unittest discover -s tests` — 44 tests, OK, 0 skipped.
- Command-path tests cover missing plan before fetch, successful dummy install, wrong digest, missing manifest access, core prerelease refusal, lock contention, corrupt journal refusal, symlinked root refusal, portable archive rejection, provenance difference reporting, default catalog fallback, backup collision, interrupted self-update restore, and a terminated lock-holder process followed by recovery and installation.

Environment-limited:

- Windows behavior is covered by portable unit assertions and the CI workflow definition. A green Windows job for the exact final commit is still required evidence; this environment's token cannot read Actions runs (HTTP 403).

## Community Shows

Community Shows is owned by Codex, not by this Selectu5 repair. The catalog may list it from facts Mike supplies. Alfred does not prepare its fixed distribution artifact from this chat. Until Mike supplies a reviewed commit, artifact digest, and package root, the entry remains list-only.

## Remaining limits

- Two renames are not one atomic transaction; validated journals are the recovery mechanism. Process-death recovery is tested. Power-loss durability is limited to the documented fsync/replace protocol and is not claimed beyond platform support.
- The skills root assumes no hostile concurrent writer. Pre-existing symlink and journal attacks are refused, but a hostile writer with filesystem control remains outside the supported model.
- A plan digest proves content consistency, not human consent. The host must enforce the user's approval before a real install call.
- Supported claim after this round: Linux tested locally. Windows requires the exact-commit CI result. macOS is not claimed.

## Maintainer decisions still needed

1. Choose a license before any public distribution.
2. Enable branch protection and required checks on `main`.
3. Review the final commit and Windows CI evidence.
4. Say the word before the installer gate changes. The gate does not open on its own.
