# Selectu5 audit packet

Date: 2026-10-09 (America/Los_Angeles).
Purpose: give the next auditor everything needed to review the current Selectu5 candidate, including what is still open.

## Audit target

- Repository: `terramike/xrpl-selectu5` (private; verified `private: true`).
- Branch: `fix/selectu5-install-boundaries-r2`.
- Candidate commit: `39fead3f365efd6b06b13cdfe25e4a9ee763a4b3`.
- Base/main commit: `5bcbd9a7c72f280f2939e39a06d9749d3a2139f2`.
- Previous reviewed commits: `bb1072536906c93b4d98ff6c36ca0749ef368a7f` (v0.2.0 audit), `084594f7fe4ed746845ce5da4bf0f357755660f8` (round 1), `849095c57ea16dd140567436f66ace00daf8ce78` (round 2).
- Package version: `0.2.2`.
- Installer gate in shipped code: `INSTALL_ENABLED = False`.
- Deployment status: not merged as a release, not deployed, not public.

The core XRPL Muse implementation is unchanged by this repair. Community Shows is owned outside this Selectu5 audit (Codex/owner lane); this packet asks for no Community Shows changes.

## Files to audit

- `scripts/selectu5.py` — client, catalog validation, inventory, install engine, recovery.
- `tests/test_selectu5.py` — repository test suite.
- `registry/registry.json` — bundled catalog (`selectu5-registry/1`).
- `SKILL.md` — skill frontmatter and operating rules.
- `SPEC.md` — STE100-style specification.
- `README.md` — user-facing overview/status.
- `.github/workflows/tests.yml` — Linux and Windows CI definitions.
- `REPAIR-REPORT.md` — Alfred's round-3 status report.
- `AUDIT-PACKET.md` — this packet.

## Safety boundary to verify

- The shipped command must keep real installation disabled. Tests may inject the gate and fixture fetchers only inside test processes; shipped defaults must not.
- A plan digest proves content consistency, not human consent. The host must obtain the user's word for the exact plan. `--yes` and `--plan` are arguments, not proof of approval.
- Only the bundled reviewed catalog may authorize installs. Remote or environment-selected catalogs are browse-only.
- An installable entry requires an exact approved GitHub owner/repository pair, a full 40-char commit, a reviewed artifact SHA-256, and an explicit package root. Incomplete entries stay list-only.
- Selectu5 never proposes, never signs, and never touches policy, seed, wallet, or core files. The only permitted core read is the core skill's public manifest version for compatibility.

## Currently installable entries

None.

Every bundled skill entry currently lacks at least a reviewed `artifact_sha256` or `package_root`. Community Shows is pinned to commit `d0457fd53e1695a1b464bccc5391369eb7d5f7c3` in the catalog, but its digest/root are null, so it remains list-only. Artifact facts must be supplied and reviewed by Mike or the owning maintainer before any entry becomes installable.

## Install and recovery protocol under audit

1. `cmd_install()` prints the permissions card and canonical plan.
2. A real install requires `--yes <exact version>` and `--plan <digest>`; mismatches refuse before fetch.
3. The engine verifies artifact digest, validates archive structure from `ZipInfo.orig_filename`, enforces byte/time limits, strictly validates the manifest, and checks core compatibility.
4. The engine validates the supplied root and target, acquires the OS process lock, and only then runs recovery.
5. Journals record intent before directory moves: `prepared -> old-moved -> published -> done` (or `recovered`). Journals carry old/new version, commit, and artifact identity.
6. Recovery validates the whole pending journal set before mutation, decides by validated package identity, restores old content when publication did not safely complete, recognizes completed publication only after identity/provenance validation, and tolerates its own interruption.
7. Post-publication verification or journal failure runs the rollback protocol: move new content aside, restore the old backup, and mark the transaction recovered.

## Local evidence supplied

Commands run by Alfred on Linux:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile scripts/selectu5.py tests/test_selectu5.py
python3 scripts/selectu5.py version
```

Latest local result before this packet: **51 tests, OK, 0 skipped**. `version` prints `xrpl-selectu5 0.2.2`. `INSTALL_ENABLED = False` was verified in `scripts/selectu5.py`.

Test coverage includes: command-path install through the same orchestration the CLI calls, missing-plan refusal before fetch, wrong digest refusal, missing manifest access refusal, OS-lock contention, corrupt-journal refusal before mutation, symlinked staging/core-overlap refusal, raw ZIP name validation, extraction deadline enforcement, semantic-version ordering, provenance identity binding and summary suppression, backup collision refusal, interrupted self-update restore, actual process termination after the first directory move, actual process termination after the second directory move, and termination during recovery followed by successful repeat recovery.

## Auditor reproduction commands

From a checkout of the candidate commit:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/selectu5.py tests/test_selectu5.py
python3 scripts/selectu5.py --offline list
python3 scripts/selectu5.py version
grep -n "INSTALL_ENABLED" scripts/selectu5.py
```

Please run negative probes with dummy packages and temporary roots only. Do not use real skills folders, credentials, policy files, wallets, or production services.

## Status map for the auditor

Alfred's current claim is “repaired in code, pending independent audit,” not release approval.

- F01 destination boundaries: repaired in code for tested supplied-root, internal-path, target, and core-overlap cases.
- F02 approval/artifact binding: mechanism repaired; release integration pending because no entry is installable.
- F03 recoverable updates: repaired in code with actual process-termination tests at both directory moves and during recovery.
- F04 resource limits: byte limits and extraction deadline repaired; download deadline is enforced around reads, but one blocking socket read is bounded by socket timeout rather than an ideal hard wall-clock deadline.
- F05 strict manifests: repaired on the installation path.
- F06 Community Shows fixture/distribution: outside Alfred's Selectu5 scope; artifact facts pending from the owner/Mike.
- F07 core compatibility: repaired for `>=MAJOR.MINOR.PATCH`; equal-base prerelease is refused.
- F08 catalog validation/display: repaired for tested metadata/control cases.
- F09 inventory boundaries: repaired for tested root, symlink, backup, and duplicate-field cases.
- F10 version/provenance reporting: repaired for the defined grammar and tested provenance cases.
- F11 catalog availability/inventory independence: repaired; `installed` needs no registry and `--offline` is explicit.
- F12 documentation consistency: repaired in the candidate docs; auditor should verify no stale claims remain.
- F13 release evidence: partial. Linux local tests pass. Windows CI for the exact candidate commit still needs green evidence. License and branch protection remain maintainer decisions.

Round-2 repair items: R01 closed; R02 repaired in code; R03 repaired; R04 mechanism repaired but live private retrieval unverified; R05 repaired for tested probes; R06 repaired pending Windows CI; R07 repaired for tested cases; R08 improved, auditor should judge sufficiency; R09 repaired; R10 repaired with the socket-read caveat above.

## What is still open

1. **Windows CI evidence:** `.github/workflows/tests.yml` defines Linux and Windows jobs. Alfred's automation token cannot read GitHub Actions runs (HTTP 403 observed earlier), so this packet does not claim a green Windows result. The auditor or Mike must confirm both jobs for commit `39fead3f365efd6b06b13cdfe25e4a9ee763a4b3`.
2. **No installable artifact facts:** no bundled entry has a complete reviewed commit + artifact digest + package root set. Any future entry needs separately reviewed facts before installability.
3. **Live distribution retrieval unverified:** tests use fixture fetchers and dummy packages. No real private GitHub archive was downloaded through the enabled path.
4. **Power-loss durability:** journals use atomic replacement and fsync where supported, but two renames are not one atomic transaction. Process-death recovery is tested; power-loss is not claimed beyond platform support.
5. **Hostile writer assumption:** the skills root assumes no hostile concurrent writer. Pre-existing symlink/journal cases are refused, but filesystem-control attackers remain outside the supported model.
6. **Download deadline caveat:** elapsed-time checks surround chunk reads. A single blocking read is bounded by the transport socket timeout, not a mathematically hard total deadline.
7. **Platforms:** Linux is locally tested. Windows requires the exact-commit CI result. macOS is not claimed.
8. **Maintainer decisions:** license selection, branch protection/required checks, release merge, public launch, and any installer-gate change all require Mike's separate word.
9. **Public-launch checks not done here:** legal/trademark and handle/domain checks for the Selectu5 name remain Mike's public-launch work, not part of this code audit.
10. **Gate remains closed:** passing this audit does not itself authorize flipping `INSTALL_ENABLED`. Re-enablement needs Mike's explicit approval after the final review.

## Questions for the auditor

1. Does every interruption point in the journal protocol preserve or restore an identifiable active version?
2. Can recovery be interrupted at any point and safely repeated?
3. Are staging, recovery, lock, target, and inventory paths all validated before use?
4. Do raw ZIP member names remain safe under Windows normalization?
5. Can provenance ever describe another package and still yield a current result?
6. Are deadlines and byte limits enforced on the actual command path?
7. Do docs, registry permissions, and code describe the same reads, writes, version, and gate state?
8. Is the evidence sufficient to close A28 on the exact candidate commit?

## Required audit output

Please return: audited commit, platform/runtime versions, commands actually executed, test counts (passed/failed/skipped/warnings), CI job links/results for the exact commit, finding-by-finding status for F01–F13 and R01–R10, acceptance status for A01–A30, any new findings with reproduction steps, and a clear statement whether the installer gate may be considered for re-enablement or must remain closed.
