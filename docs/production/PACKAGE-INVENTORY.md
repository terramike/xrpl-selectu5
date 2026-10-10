# Proposed public package inventory — Selectu5 pilot

Status: proposal for Mike's approval. Nothing here is published by this document.

Package root inside the ZIP: `xrpl-selectu5-<version>/` (one root component, recorded as `package_root` in the catalog).

## Included files

| Path in ZIP | Source | Purpose |
|---|---|---|
| `SKILL.md` | repo root | Skill manifest and operating rules (required at package root) |
| `scripts/selectu5.py` | `scripts/selectu5.py` | Client and installation engine |
| `registry/registry.json` | `registry/registry.json` | Bundled reviewed catalog snapshot |
| `README.md` | repo root | User-facing overview |
| `SPEC.md` | repo root | Specification |
| `CHANGELOG.md` | repo root | Version history |
| `LICENSE` | repo root | Apache License, Version 2.0 |
| `NOTICE` | repo root | Project attribution |

## Excluded

- `.github/` CI definitions and repository metadata
- `tests/`, `scripts/qualify.py` (qualification tooling, not shipped product)
- `docs/production/` working evidence and decision records
- `AUDIT-PACKET.md`, `REPAIR-REPORT.md`, `HANDOFF.md` (historical/internal records)
- credentials, local state, caches, `__pycache__`, temporary evidence files

## Content warnings for Mike's review

- A public ZIP exposes every source file inside it, including Python source. A separate distribution repository does not keep packaged Python source private.
- The bundled catalog names companion repositories and permissions cards; publishing this package publishes that catalog text.
- Mike selected Apache-2.0 on 2026-10-10. Include `LICENSE` and `NOTICE` in every distributed package.
