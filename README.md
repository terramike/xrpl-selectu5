# Selectu5 — the XRPL Muse skill store

**xrpl-selectu5 0.2.2** · Companion skill for the XRPL Muse skill family.
Core skill is not changed by this repo.

Selectu5 (Latin *selectus* — chosen) is one curated registry
of XRPL Muse add-on skills. In chat it shows:

- each add-on, its purpose, and its version
- the permissions card of each entry before an install
- which local skills are installed, and which ones have an update

It never signs, never proposes, and never installs without the user's
word for that exact skill and version. Clavi5 and Visu5 are showcase
cards: the next step is enroll or open, not install.

```bash
python3 scripts/selectu5.py list
python3 scripts/selectu5.py show xrpl-view-export
python3 scripts/selectu5.py installed
python3 scripts/selectu5.py check-updates
```

Registry: `registry/registry.json` (`selectu5-registry/1`), curated by
@terramike. One repo per add-on skill. Spec: `SPEC.md`.

Private while building. Public on the maintainer's word.

Status (2026-10-09): the v0.2.2 candidate is under round-3 audit repair on
`fix/selectu5-install-boundaries-r2`. Real installation is disabled
until Mike reviews the final acceptance evidence and Windows CI result;
browsing, permissions cards, and update checks remain available.
License: not yet selected; the maintainer decides before any public
distribution. See `REPAIR-REPORT.md`.
