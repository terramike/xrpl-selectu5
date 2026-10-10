# Operator actions and return paths

Each action lists who runs it and how to undo it. None of these actions
enables the installer; enablement stays a separate, explicit decision.

## Publish a new package version

Operator: repository maintainer (Run-workflow clicks may require the
maintainer; Alfred's automation token cannot dispatch workflows).

1. Run `release-prep` with the exact source commit and version.
2. Review the retained ZIP, inventory, record, and SHA-256 in the run.
3. Approve that exact digest (Mike).
4. Run `release-publish` with the prep run ID and the approved binding.
5. Confirm the workflow's post-publish digest verification passed.

Return path: withdraw the affected catalog entry. Publish corrected bytes
under a new version through the same review process. Preserve the old
release identities for audit. Withdrawal does not change installed
packages or backups.

## Withdraw a catalog entry

Operator: maintainer, via a registry pull request.

Set the entry back to list-only (clear `artifact_sha256`, `package_root`,
and `distribution`; keep identification fields). Merging the change makes
the entry list-only in future reviewed catalogs. Version comparison can
still show an update notice; withdrawal does not suppress that notice.
Installed packages and their backups are preserved by design; nothing is
deleted from a user's skills folder. Existing bundled catalogs retain their
old records until clients receive a reviewed catalog update. A remote
catalog change does not revoke an old client's local installation authority.

Return path: restore the recorded S/D/root/distribution fields in a
follow-up pull request.

## Manual recovery of an interrupted install

Operator: the user, or Alfred with the user's approval, on that machine.

1. Preserve the active package, staging, recovery journals, and backups.
2. Record the skills root and inspect the unresolved transaction.
3. Do not use `list`, `installed`, or `check-updates` as recovery commands.
   These commands do not run transaction recovery.
4. Recovery runs inside `install_package`, under the process lock, before
   a new installation transaction. The shipped CLI cannot reach this step
   while `INSTALL_ENABLED = False`.
5. Keep recovery work in the isolated harness until a real installation
   has its own approval. After enablement, review the exact destination,
   version, and plan before an approved install attempt.
6. If recovery refuses ambiguous content, keep all content and journals.
   Request a reviewed repair procedure before any manual changes.

Return path: the preserved backup (`<id>.bak-*`) is the previous active
package; journals under `.selectu5-recovery` record each step.

## Change repository controls

Operator: maintainer (Settings → Branches, or the GitHub API).

Current `main` protection: required `linux` and `windows` checks (strict),
1 approving review, stale-review dismissal, no force pushes, no branch
deletion, admins not enforced.

Return path: remove or relax the same settings. Record control changes in
the release checklist; code changes never configure repository controls.

## Security reports

Operator: maintainer.

Users report issues privately to the maintainer first. Triage order:
catalog trust or digest failures, destination escapes, credential or core
reads, then general defects. A confirmed high-severity issue withdraws
the affected catalog entry first (see above), then a fixed package ships
through the normal prep/approve/publish flow.
