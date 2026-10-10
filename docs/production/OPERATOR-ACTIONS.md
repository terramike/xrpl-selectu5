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

Return path: delete the release (with release immutability enabled,
deleting a published release may be restricted — withdraw the catalog
entry first, then delete the tag). Installed packages and backups are
never touched by release deletion.

## Withdraw a catalog entry

Operator: maintainer, via a registry pull request.

Set the entry back to list-only (clear `artifact_sha256`, `package_root`,
and `distribution`; keep identification fields). Merging the change makes
the entry non-installable in future catalogs and stops update offers.
Installed packages and their backups are preserved by design; nothing is
deleted from a user's skills folder.

Return path: restore the recorded S/D/root/distribution fields in a
follow-up pull request.

## Manual recovery of an interrupted install

Operator: the user, or Alfred with the user's approval, on that machine.

Run any Selectu5 command against the same skills folder. Recovery runs
before new work under the process lock: it restores the previous active
package from its backup, or finishes from preserved package content, and
only then continues. If content is ambiguous, preserve the staging,
recovery, and backup folders untouched and inspect them before any
deletion.

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
