# Distribution and license decision record

Status: Mike selected public source distribution with fixed release assets on 2026-10-10.
Mike also selected Apache-2.0 and authorized making this repository public.
Repository visibility has not yet changed. Review public repository contents and history before the operator changes visibility.
Approval of the exact pilot asset and installer enablement remains pending.

## Decision required

| Field | Mike's decision |
|---|---|
| Distribution model | Public source repository with fixed uploaded ZIP release assets. Selected by Mike on 2026-10-10. |
| Distribution repository | `terramike/xrpl-selectu5` |
| Permitted package contents | _Approve or amend `docs/production/PACKAGE-INVENTORY.md`_ |
| License | Apache-2.0. Mike selected this license on 2026-10-10. See `LICENSE`. |
| Intended audience | Public. Start installation qualification with a controlled pilot. |
| Publication authority | Mike approves the exact pilot asset before publication. Visibility change is authorized. |
| Release approver | Mike Mingucci (recorded from the production plan) |
| Maintainer | _Name the maintainer for asset/catalog corrections_ |

## Distribution options

| Option | Consequence | Recommendation |
|---|---|---|
| Public source repository with fixed release assets | Publishes repository content; permits unauthenticated delivery of uploaded assets | Preferred if Mike intends public source distribution |
| Private development repository + public distribution repository | Publishes packaged files while keeping development history private; packaged Python source is still public inside the ZIP | Suitable if Mike wants separate development and distribution |
| Private authenticated distribution | Needs credential handling, authorization design, and extra redirect tests | Defer unless private delivery is a product requirement |

## License decision

Mike selected Apache-2.0. Include `LICENSE` and `NOTICE` in each distributed package.
The following table preserves the options considered.

| Option | Effect |
|---|---|
| MIT | Permissive reuse with attribution notice |
| Apache-2.0 | Permissive reuse with attribution and an express patent grant |
| GPL-3.0 | Copyleft terms on distribution |
| Proprietary / all rights reserved | No open-source reuse grant |

## Supported environment (first qualification)

- Python 3.12 on Linux and Windows, local filesystem destinations only.
- Additional Python versions, macOS, network shares (UNC), and other filesystems are separate qualification work.

## Effect of the decision

Prepare the exact pilot asset (S, D, package root) and a later catalog commit C for review.
Complete the repository contents and history review before the authorized visibility change.
The connected GitHub tools cannot change repository visibility. A repository administrator must perform that step.
Approve the exact release asset before publishing it. Keep `INSTALL_ENABLED = False` until qualification and enablement review pass.

## How fixed release assets work

1. Select an exact source commit S.
2. Build a ZIP from the approved file inventory.
3. Include `LICENSE` and `NOTICE`.
4. Calculate the complete ZIP SHA-256 fingerprint D.
5. Review the package contents and build evidence.
6. Upload the ZIP to a draft GitHub release.
7. Publish the approved pilot release with immutable releases enabled where available.
8. Record its exact URL, S, D, and package root in the reviewed catalog C.
9. Download and verify D before any extraction.
10. Publish a new version for changed package bytes.

The uploaded ZIP is the release asset. GitHub's automatic source ZIP is a different download.
GitHub can regenerate source archives with different compression bytes.
An uploaded immutable release asset preserves the published package identity.
Its fingerprint verifies bytes. It does not replace package review or human installation approval.

References:

- https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives
- https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
