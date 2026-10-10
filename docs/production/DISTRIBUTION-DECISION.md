# Distribution and license decision record

Status: Mike selected Apache-2.0 on 2026-10-10. Other distribution decisions remain pending.
Publication, visibility changes, and installer enablement require separate approval.

## Decision required

| Field | Mike's decision |
|---|---|
| Distribution model | _Select one option below_ |
| Distribution repository | _Name the repository that will serve the uploaded ZIP assets_ |
| Permitted package contents | _Approve or amend `docs/production/PACKAGE-INVENTORY.md`_ |
| License | Apache-2.0. Mike selected this license on 2026-10-10. See `LICENSE`. |
| Intended audience | _Team only / named pilot users / public_ |
| Publication authority | _Who may publish a release asset and catalog commit_ |
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

After Mike records the decision, Codex can prepare the exact pilot asset (S, D, package root) and a later catalog commit C for review. Uploading any asset, changing any repository visibility, or enabling the installer still needs Mike's approval of that concrete action.
