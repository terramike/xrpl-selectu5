# Selectu5 0.2.3 catalog-only release notes (draft for Mike's review)

Status: draft only. This note does not approve publication, visibility change, or installer enablement.

## Included

- Curated catalog browsing: list, show, installed inventory, and update notices.
- Permissions cards for each catalog entry.
- Offline bundled catalog use with `--offline`.
- Python 3.12+ on Linux and Windows for local (non-UNC) skills roots.

## Not included / limitations

- Real installation remains disabled in shipped code (`INSTALL_ENABLED = False`).
- No bundled skill entry is qualified as installable; entries without reviewed artifact digest and package root remain list-only.
- Private GitHub artifact retrieval through the production installer transport is not qualified.
- UNC/network-share skills roots are excluded from production support until a native UNC pilot passes.
- Process-interruption recovery is tested; power-loss durability is not claimed.
- License selection is pending Mike's decision before public distribution.

## Release decision points for Mike

1. Select license and distribution scope.
2. Approve or reject catalog-only publication after CI and evidence review.
3. Decide repository branch controls (required Linux/Windows checks, PR review, force-push protection).
4. Separately decide any pilot artifact/catalog approval.
5. Separately decide installer enablement and public visibility. Neither is approved by this note.
