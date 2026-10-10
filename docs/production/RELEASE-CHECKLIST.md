# Selectu5 production release checklist

This checklist starts incomplete. An unchecked item is not evidence of a failed implementation.
Codex must attach evidence before it marks an item complete.
Record `blocked` or `not_run` when a check cannot finish.

## Catalog-only candidate

- [ ] Record candidate commit, package version, Python version, and supported root types.
- [ ] Confirm matching code, manifest, and self catalog versions.
- [ ] Confirm that shipped code keeps the installer gate disabled.
- [ ] Confirm all unqualified skill entries remain list-only.
- [ ] Attach successful Linux and Windows CI for the candidate.
- [ ] Check offline listing, inventory, permissions cards, and update notices.
- [ ] Check unavailable catalog fallback and invalid catalog refusal.
- [ ] Check that installation refusal fetches no artifact.
- [ ] Record a selected license, or mark public distribution blocked.
- [ ] Record branch controls and required checks, or mark configuration pending.
- [ ] Prepare changelog, limitations, and release notes.

## Artifact identity and transport

- [ ] Record approved owner/repository and source commit S.
- [ ] Record package version, access, core requirement, and reviewed permissions.
- [ ] Record exact URL and observed redirects from the production fetch path.
- [ ] Preserve the exact downloaded ZIP and its SHA-256 digest D.
- [ ] Record archive size and package root.
- [ ] Validate archive structure and manifest identity.
- [ ] Inspect package content and dependencies without executing installed code.
- [ ] Confirm a second retrieval produces D, or report unstable bytes.
- [ ] Confirm current transport can retrieve the artifact without new credential handling.
- [ ] Record subsequent catalog commit C separately from S.
- [ ] Confirm the catalog records S, D, and the correct package root.

Private API access does not qualify the installer's unauthenticated artifact transport.
A transport blocker prevents installer release. It does not prevent a catalog-only candidate.

## Isolated qualification

- [ ] Record disposable roots and all function overrides.
- [ ] Test actual fresh installation with a canonical plan and exact version.
- [ ] Test matching-provenance no-op and differing-provenance refusal.
- [ ] Test actual update between two qualified versions, or mark it incomplete.
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
- [ ] Confirm dummy core and credential sentinel hashes remain unchanged.
- [ ] Confirm core inventory reads only public manifests.
- [ ] Qualify native UNC roots, or exclude them from production support.

Synthetic checks cannot satisfy an actual artifact checkbox.
The test override does not establish host consent or production authorization.

## Operator readiness

- [ ] Document ambiguous recovery and preservation of active content, journals, and backups.
- [ ] Document backup retention and review before manual removal.
- [ ] Document catalog withdrawal without deletion of installed content.
- [ ] Document security reporting and version withdrawal procedures.
- [ ] Prepare exact release, catalog, visibility, and gate actions with separate review points.
- [ ] Prepare a return path for each proposed production action.
- [ ] Record remaining permissions and decisions with their responsible actor.
- [ ] Complete `ACCEPTANCE.md` and `evidence.json` without invented results.

## Review decisions

| Decision | Actor | Required evidence | Initial state |
|---|---|---|---|
| License | Mike | Proposed license and distribution scope | Pending |
| Repository controls | Maintainer | Current settings and exact required check/review settings | Pending verification |
| Catalog-only publication | Mike | Candidate CI, license, release notes, supported platforms | Not approved by this goal |
| Pilot artifact/catalog | Mike | S, D, C, permissions, transport and isolated test results | Pending |
| Installer enablement | Mike | Completed qualification and resolved release blockers | Not approved |
| Public visibility | Mike | Reviewed license, package, and repository contents | Not approved |

Publishing a catalog-only release does not authorize installer enablement.
A successful merge does not authorize package execution or deployment.
