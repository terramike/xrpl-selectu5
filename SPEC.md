# SPEC — xrpl-selectu5 (Selectu5)

Version: 0.1.0 (2026-10-09)
Status: Decisions locked by Mike 2026-10-09. Build in a private repo.
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

A `read` entry makes no proposal. A `propose` entry builds a proposal
only. No entry signs. A `showcase` entry is not an install.

## 5. Commands (skill client)

```
selectu5.py list
selectu5.py show <id>
selectu5.py installed
selectu5.py check-updates
selectu5.py install <id>   (v0.1: dry run, prints the plan only)
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
3. Fetch the pinned release (tag or commit). Do not fetch a floating branch head.
4. Read the `SKILL.md` manifest of the fetched skill. The name, version, and access must match the registry entry.
5. Stop if one fact does not match. Install no file.
6. Place the skill in the Muse skills folder. Print the installed version.

## 8. Safety rules

- The skill does not sign. The skill does not propose a transaction.
- The skill does not read or write core skill files, the policy file, or a seed.
- The skill reads one fact set from a local skill: name and version in `SKILL.md` frontmatter.
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

- **v0.1 (this build):** Skill file, this spec, local registry, client script, tests. Offline. Install is a dry run.
- **v0.2:** Client reads the registry from this repo on GitHub. Real install per Section 7. Repo goes public on Mike's word.
- **v0.3:** Update check on a set interval (opt-in). Chat menu buttons from this skill.
- **Later:** Builder submissions. A builder sends an entry draft. Mike reviews. No auto-list.

## 11. Open facts for Mike

1. Showcase rule for Clavi5 and Visu5: showcase in v0.1 as built. Mike to confirm or change.
2. Update interval for v0.3: on-run only, or a daily check.
3. The full collision check on the exact name "Selectu5" is a separate work item.
