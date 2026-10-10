# Selectu5 0.2.4 pilot release packet

Status: prepared for review. The asset is not published.
Repository public visibility was verified on 2026-10-10.

## Observed baseline

- PR #3 merged at `8092edd2d765ec6d940a42756be190a21f27d566`.
- Tested source S: `5e157df7062e0528f04add18d4bc4f0cf2586b2e`.
- All four final-head CI jobs passed.
- Independent local run: 78 tests, one native Windows test skipped, no failures.
- Version: `0.2.4`. Shipped gate: `INSTALL_ENABLED = False`.
- License: Apache-2.0. The package includes `LICENSE` and `NOTICE`.

## Exact package proposed for publication

| Field | Value |
| --- | --- |
| Asset | `xrpl-selectu5-0.2.4.zip` |
| Source S | `5e157df7062e0528f04add18d4bc4f0cf2586b2e` |
| ZIP SHA-256 D | `98ccb8d50f2a66c105a0efa39aa337f234d11b135245ce5b0054156e74b3f5a2` |
| ZIP size | 31,064 bytes |
| Package root | `xrpl-selectu5-0.2.4` |
| Proposed tag | `v0.2.4`, targeting S |
| Audience | Public catalog-only pilot |
| Proposed repository | `terramike/xrpl-selectu5` |

The package contains eight files. See `pilot/0.2.4-package-record.json` for their complete hashes.
Build exports A and B came from separate GitHub content fetches at S.
Every exported file matched its recorded Git blob hash.
The builder produced identical ZIP bytes from the two exports.
Build environment: Python 3.12.14. This does not prove reproducibility on every runtime.

The ZIP exists in the preparation workspace. It is not committed as a binary in this repository.
The exact reviewed ZIP must be uploaded. Do not regenerate it and retain this digest without comparing the bytes.

## Proposed operator action

1. Obtain Mike's approval for this exact package and catalog-only pilot publication.
2. Verify the ZIP SHA-256 against D.
3. Verify immutable releases are available and enabled.
4. Create a draft release for `v0.2.4` at S.
5. Attach the reviewed ZIP and SHA-256 record.
6. Mark the release as a prerelease.
7. Publish the approved release.
8. Verify public retrieval through the production fetcher.
9. Record the release and asset identifiers, redirects, retrieved bytes, and D.

The connected GitHub tools cannot create releases or upload release assets.
A repository operator must perform the draft, upload, and publication steps.

Do not use GitHub's automatic source ZIP as this artifact.
Do not enable the installer or claim successful installation from publication alone.

## Catalog preview

`pilot/0.2.4-catalog-preview.json` records the proposed locator, S, D, and package root.
It is a proposal in documentation. The shipped catalog remains list-only.
The proposed URL does not exist until the approved asset is published.
Record a reviewed catalog commit C after public retrieval passes.

## Stage 3 Codex goal

```text
Goal: qualify actual Selectu5 release assets on Linux and Windows.

Start from the merged Stage 1–2 implementation.
Read PILOT-RELEASE.md and the exact package record.
Keep the shipped installer disabled.
Keep unqualified shipped catalog entries list-only.

Add qualification inputs for an exact reviewed catalog entry and optional baseline entry.
Remove the harness's dependence on a hard-coded source archive for release-asset tests.
Use the production fetcher for real artifact retrieval.
Record S, D, C, installer I, qualification Q, platform, and every override per operation.
Treat this packet's catalog preview as a proposal until Mike approves it.

When the pilot asset is published, verify its digest before extraction.
Run fresh installation into a disposable skills root with a bound dummy core.
Check manifest identity, installed contents, provenance, and untouched core sentinels.
Check that same-version no-op performs zero fetches and zero tree mutation.
Require zero credential-sentinel reads.

Select a distinct reviewed baseline version before actual update qualification.
Do not fabricate another version by editing the reviewed ZIP.
Verify the new active package and exactly one complete previous backup.
Test locking, process interruption, recovery, and ambiguous-state preservation.
Separate synthetic fault injection from actual artifact evidence.

Add a release qualification mode that fails on any mandatory blocked check.
Retain the existing diagnostic mode for routine CI where unpublished artifacts remain blocked.
Do not let green diagnostic CI imply release qualification passed.

Add meaningful regression tests.
Run Linux and Windows CI for the final submitted head.
Record actual results and blockers in the handoff.
Prepare installer enablement as a separate reviewed change.
Do not publish another asset or enable installation from this goal alone.
```
