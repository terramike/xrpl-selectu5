# Selectu5 — the XRPL Muse skill store

**xrpl-selectu5 0.2.4** · Companion skill for the XRPL Muse skill family.
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

Status: version 0.2.4 adds fixed-asset transport support behind the disabled gate; 0.2.3 contains the remaining audit repairs.
Real installation remains disabled. Catalog browsing and local inventory remain available.
Use Python 3.12 or later on Linux or Windows.
See `REPAIR-REPORT.md` for the new tests and remaining release conditions.

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
Copyright 2026 Mike Mingucci.
