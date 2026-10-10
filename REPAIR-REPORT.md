# Selectu5 remaining audit repairs — version 0.2.3

## Release decision

The installer remains disabled. All bundled skill entries remain list-only.
This repair addresses findings N01–N06 from the production audit.
The source baseline is commit `1b9c340c191704b60d0e7dfa88a1eac025fd4f5b`.
The historical version 0.2.2 packet remains in `AUDIT-PACKET.md`.

## Changes and evidence

| Finding | Change | Regression evidence |
|---|---|---|
| N01: Incorrect terminal recovery | Mark rollback recovered only after validated restoration or removal of a failed new install. Preserve ambiguous published content and its backup. | Corrupt provenance after publication during a new install and an update. Both cases retain a pending journal and refuse automatic recovery. Existing successful rollback tests still pass. |
| N02: Completed records block installation | Count only pending journals toward the 100-record and 1 MiB limits. Archive terminal records on the next recovery call. Retain the latest 100 terminal records. Preserve package backups. | Complete 150 installs, restart recovery in another process, and complete another update. Migrate 101 legacy terminal records. Refuse 101 pending records without removal. |
| N03: Windows path boundaries | Preserve drive and UNC anchors. Reject symlinks, junctions, and other Windows reparse points. Compare protected paths with platform case rules. | Model drive and UNC component walks. Windows CI runs native junction checks from a nonroot working directory for roots, targets, inventory, staging, recovery, and backups. |
| N04: Core read limits | Read only public core manifests. Do not read core provenance, including reserved aliases and the configured core path. | Instrument file reads for three reserved core names. Refuse any provenance read for a configured core folder. |
| N05: Windows ZIP fixture | Preserve a raw backslash in the ZIP fixture. Assert the raw member name before validation. | The original negative archive test now checks the intended archive bytes on Windows. The archive policy remains strict. |
| N06: Download deadline | Run URL transport in a separate process. Terminate and collect that process after a 60-second total deadline. Preserve byte limits, transport errors, and redirect checks. | A local HTTP server sends a slow response body or delays headers. Both actual transport tests stop at a reduced test deadline. File URL tests check success, overflow, and missing files. |

## Validation

Local environment: Linux, Python 3.12.14.
Command: `python3 -m unittest discover -s tests -v`.
The suite contains 62 tests. Linux skips only the native Windows junction test.
GitHub CI runs the same suite on Linux and Windows with Python 3.12.
The pull request checks provide the authoritative CI result for the submitted commit.

Additional checks: Python compilation, offline catalog listing, version output, and Git whitespace validation.
No test enables the shipped installer or executes an installed package.
The slow transport tests use a local HTTP server. Production artifact transport still requires approved HTTPS endpoints.

## Limits and operator instructions

An invalid published identity can require manual recovery. Selectu5 preserves the journal, active content, and available backup.
This repair does not delete unknown active content automatically.

1. Stop installation attempts when recovery reports an ambiguous state.
2. Preserve the pending journal and all associated package folders.
3. Compare the active manifest and provenance with the journal identities.
4. Restore a validated old backup only after an operator reviews the recorded state.
5. Run recovery again after the operator resolves the active path.

History retention removes only validated terminal journal records beyond the latest 100 records.
Package backups remain available. Operators must review backups before manual removal.
More than 1,000 current journal files or history files requires manual review.
The process deadline includes transport and output collection. Process startup can add platform scheduling time.
The timeout implementation requires permission to create a Python subprocess.

These tests cover process interruption and ordinary filesystem failures.
They do not prove power-loss durability or resistance to a hostile concurrent filesystem writer.
UNC anchor traversal has a model test. A native network-share pilot remains a separate release check.

## Next steps toward production

1. Review this pull request and require successful Linux and Windows checks before merge.
2. Keep `INSTALL_ENABLED = False` in the catalog-only release.
3. Select a license before public distribution.
4. Configure required branch checks and review controls before production changes.
5. Review the exact source commit, ZIP bytes, package root, manifest, and permissions for one pilot artifact.
6. Record its SHA-256 digest and immutable source commit in a subsequent reviewed catalog update.
7. Test actual HTTPS retrieval, installation, update, interruption, and recovery in disposable Linux and Windows roots.
8. Check the configured core and credential sentinels after each pilot operation.
9. Review native network-share behavior if the production release supports UNC roots.
10. Obtain Mike's release decision before enabling the installer or changing repository visibility.

Use a distinct package version for different artifact bytes.
Do not invent a companion artifact digest or reuse an earlier version for changed bytes.
The catalog cannot contain a digest of its own future archive. Record the artifact digest in a subsequent catalog commit.
Companion packaging and service behavior require their own review.

## Glossary

- Terminal journal: A validated journal with stage `done` or `recovered`.
- Pending journal: A validated journal with another accepted stage.
- Provenance: The installed identity record in `.selectu5-meta.json`.
- Reparse point: A Windows filesystem object that can redirect path operations.
- UNC anchor: The server and share at the start of a Windows network path.

This report uses STE100-based technical English. It is not a certified ASD dictionary check.
