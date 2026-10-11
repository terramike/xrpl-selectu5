# Bootstrap and updates — Selectu5 self-install path

Revision 2 (2026-10-10), corrected per the 2026-10-11 change audit
(findings A04). This is the candidate release model for 0.2.6.
It is not enablement approval.

## The constraint

A release package cannot record its own artifact digest: the digest
exists only after the package is built. A client can install only the
versions whose qualified records were bundled **before** that client
was built. Remote catalogs are browse-only and never grant install
authority. An installed client never acquires new install authority on
its own.

## The first hop (qualified)

The candidate 0.2.6 client is an **external client** the user obtains
by downloading the current release ZIP manually. Trust for that first
copy comes from the release process: prep artifact digest approved by
Mike, published asset re-verified after download, release immutability
on.

1. Unzip the release ZIP anywhere **outside** the skills folder.
2. `selectu5.py --offline install xrpl-selectu5` shows the permissions
   card and canonical plan. `--offline` selects the bundled catalog —
   the only install authority.
3. The user gives the word for the exact entry and version in chat
   (consent ceremony); the host then runs with `--yes <version>` and
   `--plan <digest>`.
4. The external client installs **xrpl-selectu5 0.2.5** into the skills
   folder, preserving any replaced version as a backup.

Known limitation: the 0.2.5 artifact predates enablement
(`INSTALL_ENABLED = False` inside it), so the first hop installs a
browsing-only client. This is measured, not assumed: the bootstrap
harness records the installed predecessor's gate state.

## Later updates (procedure, not yet demonstrated end to end)

- After each release is published, a catalog commit records its
  qualified facts (S, D, package root, fixed asset URL) on `main`, so
  every client can *see* the new version via `check-updates`.
- Moving to a newer release repeats the first-hop shape with the
  newest release ZIP: the user downloads a new external client, runs
  `--offline install`, gives the word, and installs the qualified
  predecessor — an enabled client from 0.2.6 onward. Each update
  requires a newly obtained, independently reviewed external client.
- A subsequent published-artifact hop is **blocked until its artifact
  exists**: this document invents no source commit or digest for an
  unpublished release. Qualification of the next hop happens when the
  next release is built.

## Withdrawal

Withdrawing an entry returns it to list-only and installed packages
are never auto-deleted. Withdrawal cannot revoke an older bundled
catalog an installed client already carries; that client's authority
is frozen at the release it was built from.

## Evidence

`scripts/qualify_bootstrap.py` exercises the shipped candidate CLI with
no gate or trust injection: exact candidate version/root/gate,
complete predecessor identity (S, D, version, package root, asset URL),
dry run, real install of the published predecessor, installed-gate
assertion, and a zero-mutation no-op repeat. Records are retained in
CI on Linux and Windows.
