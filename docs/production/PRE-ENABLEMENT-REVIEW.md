# Pre-enablement review — host consent, catalog authority, credential reads

Prepared 2026-10-10, before any installer-enablement decision.
`INSTALL_ENABLED = False` remains the shipped gate throughout.

## 1. Host consent

**What the code does today (inspected, `cmd_install`):**

- Always prints the permissions card and the full canonical plan (entry,
  version, destination, commit, artifact digest, package root,
  distribution URL) with its plan digest, before any fetch.
- Refuses when `--plan` does not match the plan just shown.
- Dry run by default: a real installation additionally requires
  `--yes <exact registry version>` and `--plan <digest>`.
- Gate and trust checks run before any fetch: disabled gate returns 2,
  browse-only catalog returns 1, list-only entry returns 1, incompatible
  core returns 1 — all with zero network and zero writes.
- Every plan print carries the standing warning: "A plan digest proves
  content consistency only. It does not prove a human approved it; the
  host must get the user's word before any real install call."

**What the code does not do:** it records no consent artifact. `--yes`
and `--plan` are arguments an agent could type; they encode the word,
they do not prove it. Consent is therefore a host-flow obligation
(SKILL.md): the host shows the card and plan in chat, the user gives the
word for that exact entry and version, and only then does the host run
the real install command. The chat transcript is the consent record.

**Decision required before enablement:** Mike confirms this ceremony as
the standing consent rule (exact entry + exact version word in chat,
after seeing the plan). No code change is proposed here.

## 2. Catalog authority

**What the code does today (inspected, `catalog_trust`):**

- Only the bundled, locally reviewed catalog (`local-reviewed-catalog`)
  may authorize an installation. A remotely loaded catalog is explicitly
  browse-only; `cmd_install` refuses installs from it before any fetch.
- An entry additionally needs an immutable 40-char commit, a reviewed
  SHA-256 artifact digest, and a package root, or it is list-only and
  refused before any fetch.

**Consequence for catalog C (PR #9):** merging C records qualified facts
in the repository's `registry/registry.json`, which is what browsing and
update reporting read. It becomes install-authoritative only when a
future qualified package bundles that catalog file — the installed
0.2.5 package's bundled catalog remains list-only. PR #9 therefore
changes no installed client's install capability.

**Authority summary:** repository catalog = display and update facts;
bundled catalog inside a qualified, digest-approved package = the only
install authority; shipped gate = final disable.

## 3. Credential and core read evidence

**Qualification method (`scripts/qualify.py`, synthetic harness; both CI
platforms):**

- A disposable root holds a dummy core (bound via `SELECTU5_CORE_DIR`)
  and a dummy credential sentinel. `builtins.open` is instrumented per
  operation.
- Allowed: reads of the dummy core's *public manifest* (counted and
  reported separately). Prohibited: any read of the credential sentinel
  (must be 0) and any change to sentinel bytes.
- Result (CI, linux + windows): credential sentinel reads = 0 and
  sentinel hashes unchanged across install, update, no-op, rejected
  requests, and recovery. The Stage 3 actual-artifact harnesses
  additionally verify sentinel/core dummy files unchanged on every check.

**Limits:** dummy files only — genuine credential files are never read
for a sentinel test, by design. This evidence shows the engine does not
reach outside its contract in qualification; it is not a runtime sandbox
claim about installed third-party skills (SKILL.md states this plainly).

## Enablement prerequisites (all outstanding, in order)

1. Merge PR #5 (Stage 3 evidence), PR #10 (Stage 4 package), PR #9
   (catalog C) — each with required review.
2. Mike confirms the host-consent ceremony above as the standing rule.
3. Mike selects the first installable entry (currently qualified:
   `xrpl-selectu5` 0.2.5 only).
4. Enablement itself is a code change: flipping `INSTALL_ENABLED`
   requires its own pull request, review, new package version, and the
   full prep → approve → publish release cycle. Nothing in this review
   pre-approves it.

## Consent ceremony — confirmed

Confirmed by Mike on 2026-10-10: the standing consent rule is the
user's word for the exact entry and version, given in chat after the
host shows the permissions card and the canonical plan. The chat
transcript is the consent record; `--yes` and `--plan` encode that word
for the installer and are never substitutes for it.

## Correction (2026-10-10, Mike's review)

The read-evidence sentence above originally implied coverage of every
operation class. Exact scope, now instrumented: the synthetic harness
(`scripts/qualify.py`) records per-operation core-manifest reads and
credential-sentinel reads (must be 0) for fresh installation, no-op,
update, **rejected request (wrong digest)**, and **recovery after an
interrupted publish**; the actual-artifact harnesses additionally verify
sentinel and dummy-core hashes unchanged across retrieval, install,
update, interruption, and no-op. No claim is made beyond the dummy
sentinels used, and no genuine credential file is ever read for these
tests.

Mike also identified two enablement gaps addressed on the 0.2.6 branch:
the first installed artifact (0.2.5) predates enablement, and bundled
catalogs cannot acquire new authority. The defined bootstrap and
update procedure lives in `docs/production/BOOTSTRAP-AND-UPDATE.md`
(predecessor-chain installs, catalog commit after each release), and
`scripts/qualify_bootstrap.py` tests it with the shipped CLI and actual
published artifacts, with gate and bundled-catalog state asserted by
`tests/test_enablement_state.py`.
