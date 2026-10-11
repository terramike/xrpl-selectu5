# Release automation

Selectu5 releases are published by GitHub Actions so no operator has to
upload release files by hand. Two separate workflows keep approval bound
to the exact bytes.

## Step 1 — Prepare (`.github/workflows/release-prep.yml`)

Run manually with a full source commit `S` and a version. The job:

1. Checks out exactly `S` (plus a second independent export).
2. Runs the repository test suite.
3. Builds the ZIP with `scripts/package.py --verify-rebuild` and records
   the SHA-256 digest `D`.
4. Retains the ZIP, `package-record.json`, and `package-inventory.json`
   as a workflow artifact for review (30 days).

Permissions are `contents: read`. This workflow publishes nothing.

## Step 2 — Approve

A human approves the concrete package: `S`, version, asset name
`xrpl-selectu5-<version>.zip`, and `D`. Approval of tests or code alone
never approves publication.

## Step 3 — Publish (`.github/workflows/release-publish.yml`)

Run manually with the prep run ID and the approved binding. This is the
only release workflow with `contents: write`. The job:

1. Downloads the retained candidate from the prep run — it never rebuilds.
2. Verifies the retained bytes hash to the approved `D` and that the
   shipped installer gate matches the approved source commit `S` (the
   0.2.5-era "still disabled" wording was retired with enablement).
3. Refuses to run if the tag or release already exists; it never
   overwrites an asset (no `--clobber`).
4. Creates a draft release targeted at `S`, attaches the ZIP, the package
   record, and the inventory, confirms the attachment list, and only then
   publishes.
5. Downloads the published asset again and verifies `D` a second time.

Installer enablement is not part of either workflow and stays a separate,
explicit decision.

## Repository setting (operator, one time)

Enable **Settings → Releases → Enable release immutability** before the
next release. Immutability applies only to future releases; the existing
v0.2.4 release is not locked retroactively.

Optionally protect the `release` environment (used by the publish job)
with required reviewers so a second human confirms each publication run.
