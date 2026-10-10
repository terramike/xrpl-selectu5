# Bootstrap and subsequent updates — Selectu5 self-install path

Defined 2026-10-10 in response to Mike's enablement review. This is the
procedure the 0.2.6 enablement ships with.

## The constraint

A release package cannot record its own artifact digest: the digest
exists only after the package is built. Therefore a client can only
ever be authorized to install versions whose qualified records were
bundled **before** that client was built. Remote catalogs are
browse-only and never grant install authority.

## Bootstrap (first installation)

1. The user obtains the current Selectu5 release ZIP manually. Trust for
   this first copy comes from the release process: prep artifact digest
   approved by Mike, published asset re-verified after download, release
   immutability on.
2. Unzip it anywhere **outside** the skills folder and run the client
   from there.
3. `selectu5.py --offline install xrpl-selectu5` shows the permissions
   card and canonical plan. `--offline` selects the bundled catalog —
   the only install authority.
4. The user gives the word for the exact entry and version in chat
   (consent ceremony); the host then runs with `--yes <version>` and
   `--plan <digest>`.
5. The client installs the qualified predecessor release into the
   skills folder (for 0.2.6: Selectu5 0.2.5), preserving any replaced
   version as a backup.

## Subsequent updates

- After each release is published, a catalog commit records its
  qualified facts (S, D, package root, fixed asset URL) on `main`, so
  every client can *see* the new version via `check-updates`.
- A new client's bundled catalog authorizes its predecessor. Moving to
  the newest release repeats the bootstrap shape with the newest ZIP:
  download, `--offline install`, consent, done. Each hop installs a
  gate-enabled client once the predecessor itself ships enabled
  (from 0.2.6 onward), so the chain is self-sustaining.
- An installed client's bundled catalog never gains new authority on
  its own. Update notices are information, not authorization.

## Known limitation of the first hop

The 0.2.5 artifact predates enablement (`INSTALL_ENABLED = False`
inside it), so a client bootstrapped from 0.2.6 lands a browsing-only
0.2.5. The next release (whose bundle records 0.2.6) removes this: its
bootstrap installs the enabled 0.2.6. The bootstrap harness records the
installed predecessor's gate state so this is measured, not assumed.

## Evidence

`scripts/qualify_bootstrap.py` exercises the shipped CLI from a built
candidate ZIP with no gate or trust injection: dry run, real install of
the published predecessor, gate-state record, no-op repeat.
