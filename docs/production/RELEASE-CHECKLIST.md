# Selectu5 production release checklist

This checklist starts incomplete. An unchecked item is not evidence of a failed implementation.
Codex must attach evidence before it marks an item complete.
Record `blocked` or `not_run` when a check cannot finish.

## Catalog-only candidate

- [x] Record candidate commit, package version, Python version, and supported root types. Evidence: `docs/production/ACCEPTANCE.md` (S `7db6c62951b552d15fa13cc09e1f083f073ca92a`, 0.2.3, Python 3.12, local Linux/Windows roots; UNC excluded).
- [x] Confirm matching code, manifest, and self catalog versions. Evidence: harness source inspection pass.
- [x] Confirm that shipped code keeps the installer gate disabled. Evidence: `INSTALL_ENABLED = False`.
- [x] Confirm all unqualified skill entries remain list-only. Evidence: harness list-only pass.
- [x] Attach verified historical Linux and Windows CI for `e86b2d7`. Evidence: ACCEPTANCE and evidence.json. Require successful checks for the final follow-up commit before merge.
- [x] Check offline listing, inventory, permissions cards, and update notices. Evidence: repository suite + local CLI checks.
- [x] Check unavailable catalog fallback and invalid catalog refusal. Evidence: repository suite.
- [x] Check that installation refusal fetches no artifact. Evidence: repository suite disabled-gate tests.
- [x] Record the selected license. Mike selected Apache-2.0 on 2026-10-10. `LICENSE` and `NOTICE` accompany the package. Distribution scope remains pending.
- [ ] Record branch controls and required checks, or mark configuration pending. Status: blocked — current/proposed recorded in ACCEPTANCE; protection unavailable/read-only with current plan/token.
- [x] Prepare changelog, limitations, and release notes. Evidence: `CHANGELOG.md`, `docs/production/RELEASE-NOTES-CATALOG-ONLY.md`.

## Artifact identity and transport

- [x] Record approved owner/repository and source commit S. Evidence: ACCEPTANCE Stage 2.
- [x] Record package version, access, core requirement, and reviewed permissions. Evidence: ACCEPTANCE Stage 2.
- [ ] Record exact URL and observed redirects from the production fetch path. Status: blocked — URL recorded; production fetch returned HTTP 404 before redirect/archive qualification.
- [ ] Preserve the exact downloaded ZIP and its SHA-256 digest D.
- [ ] Record archive size and package root.
- [ ] Validate archive structure and manifest identity. Status: blocked for downloaded artifact; source manifest inspected only.
- [x] Inspect package content and dependencies without executing installed code. Evidence: source inspection at S (no credential filenames/executables; stdlib only).
- [ ] Confirm a second retrieval produces D, or report unstable bytes.
- [ ] Confirm current transport can retrieve the artifact without new credential handling. Status: blocked — private repo artifact returns HTTP 404 to production fetcher.
- [ ] Record subsequent catalog commit C separately from S.
- [ ] Confirm the catalog records S, D, and the correct package root.

Private API access does not qualify the installer's unauthenticated artifact transport.
A transport blocker prevents installer release. It does not prevent a catalog-only candidate.

## Isolated qualification

- [x] Record disposable roots and all function overrides. Evidence: `scripts/qualify.py` and harness output.
- [x] Test qualification-harness plan construction from the canonical validated destination. Evidence: harness `canonical plan destination` pass under a raw `/./` skills path.
- [x] Record every harness override. Evidence: `scripts/qualify.py` records gate injection, synthetic fetcher, trusted-catalog injection, and supplied dummy-core version.
- [x] Test synthetic no-op with no fetch and no mutation, update identity, and preserved backup contents. Evidence: harness checks pass locally; both CI jobs now run the harness.
- [ ] Test actual fresh installation with a canonical plan and exact version. Status: blocked — synthetic fresh install passed; actual artifact transport blocked.
- [ ] Test matching-provenance no-op and differing-provenance refusal.
- [ ] Test actual update between two qualified versions, or mark it incomplete. Status: incomplete — synthetic update passed only.
- [ ] Test backup preservation and interrupted self-update.
- [ ] Test process death before and after each directory move.
- [ ] Test interrupted recovery, repeat recovery, and a subsequent update.
- [ ] Test invalid published identity without false terminal recovery.
- [ ] Test wrong digest, invalid manifest, unsafe archive, and incompatible core refusal.
- [ ] Test untrusted catalog refusal and lock contention.
- [ ] Test native Windows root, target, staging, recovery, inventory, and backup boundaries.
- [ ] Preserve raw ZIP names in the negative Windows archive fixture.
- [ ] Test 150 transactions and restart recovery with bounded terminal history.
- [ ] Test pending journal limits and legacy terminal journal migration.
- [ ] Test actual slow-body and delayed-header transport deadlines.
- [x] Confirm dummy core and credential sentinel hashes remain unchanged. Evidence: harness sentinel check pass.
- [ ] Confirm core inventory reads only public manifests.
- [x] Qualify native UNC roots, or exclude them from production support. Evidence: UNC excluded in release notes/acceptance until native pilot.

Synthetic checks cannot satisfy an actual artifact checkbox.
The test override does not establish host consent or production authorization.

## Operator readiness

- [x] Document ambiguous recovery and preservation of active content, journals, and backups. Evidence: ACCEPTANCE operator readiness.
- [x] Document backup retention and review before manual removal. Evidence: ACCEPTANCE operator readiness.
- [x] Document catalog withdrawal without deletion of installed content. Evidence: ACCEPTANCE operator readiness.
- [x] Document security reporting and version withdrawal procedures. Evidence: ACCEPTANCE operator readiness.
- [x] Prepare exact release, catalog, visibility, and gate actions with separate review points. Evidence: ACCEPTANCE proposed operator actions.
- [x] Prepare a return path for each proposed production action. Evidence: ACCEPTANCE proposed operator actions.
- [x] Record remaining permissions and decisions with their responsible actor. Evidence: ACCEPTANCE remaining decisions and checklist review table.
- [x] Complete `ACCEPTANCE.md` and `evidence.json` without invented results. Evidence: this checklist, `docs/production/ACCEPTANCE.md`, `docs/production/evidence.json`.

## Review decisions

| Decision | Actor | Required evidence | Initial state |
|---|---|---|---|
| License | Mike | Apache-2.0. See `LICENSE` and `NOTICE`. | Selected on 2026-10-10. Distribution scope remains pending. |
| Repository controls | Maintainer | Current settings and exact required check/review settings | Pending verification |
| Catalog-only publication | Mike | Candidate CI, license, release notes, supported platforms | Not approved by this goal |
| Pilot artifact/catalog | Mike | S, D, C, permissions, transport and isolated test results | Pending |
| Installer enablement | Mike | Completed qualification and resolved release blockers | Not approved |
| Public visibility | Mike | Reviewed license, package, and repository contents | Not approved |

Publishing a catalog-only release does not authorize installer enablement.
A successful merge does not authorize package execution or deployment.

## Follow-up merge checks

- [x] Compare every backup file, directory, and mode with the pre-update snapshot.
- [x] Add regressions for payload corruption, an extra directory, and POSIX permission changes.
- [x] Record synthetic overrides only on the operations that use them.
- [x] Separate selected pilot S from the qualification checkout in CI.
- [x] Retain runner-generated qualification JSON and Markdown for 14 days.
- [ ] Confirm successful Linux and Windows checks for the final follow-up commit before merge.

The retained runner evidence identifies the checkout that produced each result.
Historical evidence in this repository does not claim results for a future commit.

## Fixed-asset transport (Stage 2)

- [x] Design catalog `distribution` fields and bind them into the canonical plan. Evidence: `docs/production/FIXED-ASSET-DESIGN.md`.
- [x] Add deterministic packaging with explicit inventory and rebuild verification. Evidence: `scripts/package.py`, `docs/production/package-inventory.json`.
- [x] Propose package inventory and distribution/license decision record. Evidence: `docs/production/PACKAGE-INVENTORY.md`, `docs/production/DISTRIBUTION-DECISION.md`.
- [x] Test changed asset locators, digests, plans, redirects, and malformed distribution entries locally. Evidence: `tests/test_fixed_assets.py`.
- [ ] Record Mike's distribution repository, package contents, license, audience, and publication authority.
- [ ] Prepare the exact pilot asset (S, D, package root) and later catalog commit C for Mike's review.
- [ ] Complete actual artifact qualification on Linux and Windows (Stage 3).

## PR #3 audit fixes

- [x] Reject source symlinks/junctions/reparse points and verify containment before reading package files (external-sentinel regression test).
- [x] Build release evidence from two independent clean exports with recorded S and build-tool versions; working-tree builds labeled development evidence.
- [x] Reject malformed asset URLs (controls, encoded traversal, invalid ports, wrong types) before URL normalization.
- [x] Enforce distribution records on skill entries only.
- [x] Reject duplicate/colliding inventory paths and validate the finished ZIP with the installer archive validator.
- [ ] Linux and Windows CI for the final PR #3 head (now including the new regression tests).
