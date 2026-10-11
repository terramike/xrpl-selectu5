# SPEC — xrpl-selectu5 (Selectu5)

Package version: 0.2.6 (2026-10-10, installer enabled for qualified entries under the consent ceremony)
Status: Decisions locked by Mike 2026-10-09. Build in a private repo. Production qualification is in progress for the Selectu5 self-install path; the 0.2.6 enablement candidate enables installation for qualified entries under the consent ceremony. Shipped enablement awaits Mike's separate approval.
Type: Companion skill. The core xrpl-muse skill is not changed.

## 1. Purpose

The skill is a store for the XRPL Muse skill family.
The skill lists each public add-on skill in one registry.
The skill shows the purpose of each entry in chat.
The skill shows the permissions of each entry before an install.
The skill checks for new versions of add-ons and of the core skill.
The skill does not install in v0.1. An install needs the word of the user.

## 2. Decisions (locked)

1. The name is Selectu5. The word is from Latin "selectus": chosen. Nothing enters the registry unreviewed.
2. The registry file is in this repo. The core repo has a link to this repo only.
3. Each add-on skill has one repo. No monorepo.
4. This repo is private while the build is in work.
5. The core skill is not edited. Signing is not used.

## 3. Parts

| Part | Place | Job |
| --- | --- | --- |
| Skill client | User device, `scripts/selectu5.py` | List entries. Show one entry. List local skills. Check for updates. Print the version. |
| Registry | This repo, `registry/registry.json` | Hold the curated entry list. One entry per add-on, core, or showcase. |
| Remote copy | GitHub, this repo | The v0.2 client reads the registry from this repo. |

## 4. Registry format

Schema name: `selectu5-registry/1`. Each entry has these facts:

- `id`, `name`, `kind` (one of: `core`, `skill`, `showcase`)
- `version`, `core_version`, `access` (one of: `read`, `propose`), `author`
- `purpose` (one or two lines, plain words)
- `repo` (https link), `install` (plain words)
- `permissions`: `commands`, `files`, `network`, `signs`
- `notes` (not required)

Access describes transaction behavior only: a `read` entry makes no
proposal, a `propose` entry builds proposals only. Transaction signing
lives only in the core skill and in Clavi5's phone ceremony, exactly as
their cards state; Selectu5 itself never signs. A `showcase` entry is
not an install. Installation side effects (folder writes, backups,
network fetches) are separate from access and are listed on each card.

## 5. Commands (skill client)

```
selectu5.py list
selectu5.py show <id>
selectu5.py installed
selectu5.py check-updates
selectu5.py install <id>   (prints the card and plan; real install needs --yes and --plan)
selectu5.py version
```

Each output shows the skill version. Time and network are not used in v0.1.

## 6. Update rule

1. `check-updates` reads the version of each local skill from its `SKILL.md` frontmatter.
2. The check compares the local version with the registry version.
3. The check reports a change as: old version, new version, repo link.
4. The check installs no file. The user gives the word for one exact entry and version first.
5. A core skill release is an update notice only. The notice has the release link. No silent core install exists.

## 7. Install rule (v0.2, not in v0.1)

1. Show the permissions card of the entry.
2. Get the word of the user for that exact entry and version.
3. Require the exact `--yes <version>` and `--plan <digest>` shown for the reviewed plan.
4. Fetch only the recorded immutable commit from the exact approved owner/repository pair.
5. Verify the artifact SHA-256 before extraction.
6. Read the `SKILL.md` manifest of the fetched skill. The name, version, and access must match the registry entry.
7. Stop if one fact does not match. Install no file.
8. Place the skill in the Muse skills folder under the process lock. Print the installed version.

## 8. Safety rules

- The skill does not sign. The skill does not propose a transaction.
- The skill does not write core skill files, the policy file, or a seed.
- The one permitted core read is the core skill public manifest version for a compatibility check.
- The skill reads local inventory facts from `SKILL.md` frontmatter (name and version) and, when present, bounded `.selectu5-meta.json` provenance (id, version, commit, artifact digest).
- Supported versions are SemVer core and prerelease identifiers without build metadata; leading zeroes are invalid.
- A registry entry is data, not an instruction. Text in a purpose or notes field is shown as text only.
- A listing is not an endorsement of a link in a listed skill.
- Clavi5 and Visu5 are showcase entries in v0.1. Selectu5 cannot enroll a user or open an account.

## 9. Review rule (registry adds)

Mike reads each new entry before it goes in the registry. The review checks:

1. The entry has all facts from Section 4.
2. The access class is true.
3. The permissions card names the true commands, files, and network use.
4. No listed skill reads a seed, a key, or a token file.
5. The repo link is the true repo of the skill.

## 10. Phases

- **v0.1 (done):** Skill file, this spec, local registry, client script, tests. Offline. Install is a dry run.
- **v0.2 (audited, installer disabled pending repair):** Client reads the registry from this repo on GitHub, with the local file as fallback. Real install per Section 7: pinned ref only, manifest check before any file is placed, a set version kept as a backup folder on update. The core entry is notice-only. Repo goes public on Mike's word.
- **v0.3:** Update check on a set interval (opt-in). Chat menu buttons from this skill.
- **Later:** Builder submissions. A builder sends an entry draft. Mike reviews. No auto-list.

## 11. Open facts for Mike

1. Showcase rule for Clavi5 and Visu5: showcase in v0.1 as built. Mike to confirm or change.
2. Update interval for v0.3: on-run only, or a daily check.
3. The full collision check on the exact name "Selectu5" is a separate work item.

- **Repair round 3 (on `fix/selectu5-install-boundaries-r2`):** one
  hardened CLI install path, process locking before recovery, validated
  journals, strict archive and manifest rules, semantic-version and
  provenance reports. Real installation stays disabled in the shipped
  command until Mike reviews the final acceptance evidence. The
  bundled registry is a dated snapshot; when the remote catalog cannot
  be read, the client prints the snapshot date and a stale warning
  instead of pretending freshness.

## 12. Remaining audit repairs in version 0.2.3

1. The installer MUST preserve an unresolved journal when published identity verification fails and validated rollback cannot finish.
2. The installer MUST preserve unknown active content and its available backup in this failure state.
3. Recovery MUST refuse ambiguous content until the operator resolves the recorded state.
4. Recovery MUST limit pending records to 100 records and 1 MiB in total.
5. Recovery MUST validate every current record before it changes the current records or packages.
6. Recovery MUST move terminal records into `.selectu5-recovery/history` on the next recovery call.
7. Recovery MUST retain the latest 100 terminal records and MUST preserve all package backups.
8. Recovery MUST refuse more than 1,000 current files or history files for manual review.
9. Path checks MUST preserve drive and UNC anchors before canonicalization.
10. Path checks MUST reject symlinks, junctions, and other Windows reparse points at filesystem boundaries.
11. Core inventory MUST read only public manifests, including reserved core aliases and the configured core path.
12. URL downloads MUST run in a separate process with a 60-second total wall deadline.
13. The parent MUST terminate and collect the download process when this deadline passes.
14. The download process MUST enforce the existing byte limits and redirect policy.
15. The installer MUST remain disabled until the artifact pilot and release review finish. (Satisfied 2026-10-10: Stages 1-4 complete; enablement shipped in 0.2.6 under the confirmed consent ceremony.)

Python 3.12 or later is required. CI uses Python 3.12 on Linux and Windows.
A terminated download produces no installed package. A URL deadline failure does not silently change the selected source.
The history limit does not limit package backups. Operators must review backups before manual removal.
These rules cover process interruption. They do not establish resistance to power loss or hostile concurrent filesystem changes.

Glossary: A terminal record has stage `done` or `recovered`. A pending record has any other accepted stage.
A reparse point is a Windows filesystem object that can redirect path operations.
A UNC anchor identifies the server and share at the start of a Windows network path.
