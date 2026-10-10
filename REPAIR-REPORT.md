# Selectu5 audit repair — round 3 status report

Date: 2026-10-09 (America/Los_Angeles).
Branch: `fix/selectu5-install-boundaries-r2`.
Reviewed round-2 commit: `849095c57ea16dd140567436f66ace00daf8ce78`.
Package version: 0.2.2.
Installer gate in shipped code: `INSTALL_ENABLED = False`.

This report does not authorize gate enablement, merge, deployment, or publication. The core XRPL Muse implementation is unchanged. Community Shows is owned outside this Selectu5 repair; Alfred did not modify that repo.

## Round-3 repairs

- Transaction journals now record intended state before each directory move: `prepared`, `old-moved`, `published`, then `done` or `recovered`.
- Journals record old and new version, commit, and artifact identity. Recovery validates every pending record before mutation and resolves state by validated package identity, not directory existence alone.
- Recovery is repeatable after its own interruption. Post-publication verification or journal failure follows a rollback protocol that restores the old active package and marks the transaction recovered.
- Internal staging, recovery, and lock paths are validated as plain directories/files before use. A pre-existing staging symlink refuses before external writes.
- Configured core overlap is refused in both directions.
- Inventory validates supplied roots, rejects duplicate identity fields, and reads bounded, identity-bound provenance.
- Archive validation uses `ZipInfo.orig_filename`, so raw backslash names stay rejected under Windows normalization.
- Extraction enforces the deadline during and after member extraction. Download checks enforce elapsed time around chunk reads; one blocking socket read can still be bounded by its socket timeout rather than an ideal hard wall-clock guarantee.
- Supported version grammar is SemVer core plus prerelease, without build metadata and without leading zeroes.
- Provenance differences suppress the “everything current” summary.
- README, script docstring, SKILL.md, SPEC.md, and the Selectu5 registry card now describe version 0.2.2 and the actual reads/writes.

## Finding map

Original findings: F01 partial-to-repaired in code pending final audit; F02 mechanism repaired, release integration pending because no bundled entry is installable; F03 repaired in code with actual process-termination tests; F04 repaired with the stated socket-read limit; F05 repaired; F06 outside Alfred scope (Codex/owner supplies artifact facts); F07 repaired; F08 repaired for tested cases; F09 repaired for tested inventory boundaries; F10 repaired for tested provenance/version states; F11 repaired; F12 repaired in docs; F13 partial because Windows CI and maintainer decisions remain.

Repair findings: R01 closed; R02 repaired in code with process-death evidence; R03 repaired with whole-set journal validation and bounded strict JSON; R04 mechanism repaired, live private retrieval unverified; R05 repaired for staging/core/inventory probes; R06 repaired pending Windows CI; R07 repaired for identity-bound provenance and summary logic; R08 improved with actual termination, recovery interruption, post-publication failure, and command-path tests; R09 repaired in docs; R10 repaired with the stated transport limit.

Acceptance map: A01 closed for tested cases; A02 repaired pending final audit; A03 repaired for supplied/internal/inventory roots; A04 closed; A05 closed for tested cases; A06 closed for CLI binding (host consent remains separate); A07 mechanism closed, release facts pending; A08 partial (no live private artifact retrieval); A09 closed; A10 partial for deadline evidence; A11 repaired with extraction deadline tests; A12 repaired pending Windows CI; A13 closed; A14 closed; A15 pending outside Alfred scope; A16 partial-to-tested through engine/command path; A17 repaired with rollback protocol; A18 repaired with actual process termination after each move; A19 closed for tested lock exclusion; A20 repaired for tested boundaries; A21 repaired for the defined grammar; A22 repaired for tested provenance cases; A23 closed; A24 closed; A25 closed; A26 closed; A27 partial (ordinary commands are read-only in tests); A28 open until Linux and Windows CI pass on the final commit; A29 repaired with interrupted self-update evidence; A30 repaired in docs.

## Evidence

Local Linux evidence after round 3:

- `python3 -m unittest discover -s tests` — 51 tests, OK, 0 skipped.
- Actual process-termination tests terminate an update after the first directory move and after the second directory move, then recover and continue.
- A separate child process is terminated during recovery restoration; a second recovery completes.
- Injected post-publication journal failure restores the old active version; a later valid update succeeds.
- Command-path tests cover plan-before-fetch, digest failure, missing access, staging symlink refusal, core overlap refusal, raw ZIP names, extraction deadline, provenance identity, and current-summary suppression.

Environment-limited evidence:

- Windows CI must pass on the exact final commit before A28 can close. This environment's token cannot read GitHub Actions runs (HTTP 403 previously observed), so no remote result is claimed here.
- No live private distribution retrieval was performed.
- No bundled catalog entry is currently installable: each lacks at least a reviewed artifact digest or package root.

## Durability and limits

The protocol distinguishes process death from power loss. Journals use atomic replacement and fsync where supported, but two directory renames are not one atomic transaction. Recovery uses validated journal and package identity. The supported model still assumes no hostile concurrent writer inside the skills root.

## Maintainer decisions remaining

1. Review the final commit and both CI jobs.
2. Supply reviewed artifact facts before any entry becomes installable.
3. Choose a license before public distribution.
4. Enable branch protection and required checks on `main`.
5. Separately approve any installer gate change after final review.
