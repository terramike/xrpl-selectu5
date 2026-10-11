# Changelog

## 2.0.0 — 2026-10-11

Menu mode (Mike's decision). Selectu5 is now a menu of links and an update checker; it installs nothing.

- Removed the entire installer engine (install plans, staging, journals, recovery, predecessor chains, consent ceremony). The 0.2.x engine is preserved on the `v1-installer` branch for the eventual v3 installer story.
- Registry drops install-authority fields (`ref`, `artifact_sha256`, `package_root`, `distribution`). Validation is identity and text-safety only.
- `check-updates` is registry-only and report-only; the core skill is notice-only with the manual update path.
- Clavi5 showcase entry removed (not yet); Visu5 stays.
- Kept from 0.2.x: the curated registry format, deterministic packaging, and the prep → approve → publish release flow.


## 0.2.6 — 2026-10-10

Installer enablement for the Selectu5 self-install path (Mike's decision).

- `INSTALL_ENABLED = True`: qualified catalog entries can be installed under the confirmed consent ceremony (permissions card + canonical plan shown first; the user's word for the exact entry and version; `--yes` + `--plan` encode that word).
- The bundled catalog carries the qualified xrpl-selectu5 0.2.5 record (S/D/root/asset URL), the first installable entry. All other entries remain list-only.
- Catalog browsing, update reporting, recovery, and the disabled-by-default stance for unqualified entries are unchanged.

## 0.2.5 — 2026-10-10

Update-test package for Stage 3 qualification. Installer remains disabled.

- Prepared as the second distinct reviewed artifact so the actual update path (0.2.4 -> 0.2.5) can be qualified against published release assets.
- No behavior change; catalog entries remain list-only and `INSTALL_ENABLED = False`.

## 0.2.4 — 2026-10-10

Fixed-asset transport preparation. Installer remains disabled.

- Added an optional catalog `distribution` record for reviewed GitHub release assets, bound into the canonical installation plan.
- Added strict release-asset URL validation and GitHub asset redirect hosts.
- Added `scripts/package.py`: deterministic ZIP packaging with an explicit inventory, per-file hashes, and rebuild verification.
- Added Stage 1–2 production documents: fixed-asset design, package inventory, and the distribution/license decision record.

## 0.2.3 — 2026-10-09

Production-audit repair baseline merged through PR #1.

- Repaired terminal-recovery handling for ambiguous published identity.
- Limited pending recovery journals while retaining terminal history and package backups.
- Hardened Windows path boundaries, including drive/UNC anchors and reparse-point refusal.
- Limited core inventory reads to public manifests.
- Preserved raw ZIP member names in Windows negative fixtures.
- Moved URL transport into a subprocess with a 60-second total deadline.
- Kept `INSTALL_ENABLED = False`; all bundled skill entries remain list-only.

## 0.2.2 — 2026-10-09

Round-3 audit repair candidate.

- Rebuilt install recovery around journaled directory-move intent.
- Added internal staging/recovery path validation and core-overlap refusal.
- Bound provenance to package identity and suppressed false current summaries.
- Enforced archive validation from raw ZIP filenames and extraction deadlines.
- Defined the supported SemVer subset used by the client.

## 0.2.0 — 2026-10-09

Initial remote-registry and install-plan implementation. Superseded by the audit repair line.
