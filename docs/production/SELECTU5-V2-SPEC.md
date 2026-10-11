# Selectu5 v2 specification (menu mode)

Status: draft for Mike's review. Version target: 2.0.0, same repository
(`terramike/xrpl-selectu5`). The 0.2.x installer line is parked, not deleted.

## 1. Goal

Selectu5 v2 is a menu of links and an update checker for the XRPL Muse
skill family. It helps a user discover what exists, understand what
each skill does, find where to get it, and know whether the installed
copies are current. Easy adoption is the goal. It installs nothing.

## 2. Non-goals

- No downloading of skill packages.
- No installation, update, or removal of any skill.
- No trust decisions beyond curation: a listing means Mike reviewed the
  entry text, not that Mike endorses every link inside the skill.
- The core skill (`xrpl-muse-skill`) is notice-only. Selectu5 reports
  core updates; it never installs, updates, or modifies the core.

## 3. Registry

The registry remains `registry/registry.json`, curated by Mike through
reviewed pull requests. Each entry records:

- `id`, `name`, `version` (the latest known release)
- `kind`: `skill`, `core`, or `showcase`
- `purpose`: one or two sentences, plain language
- `repo`: the repository URL (the install source the user follows)
- `install`: how to install — a URL, a command, or short instructions
- `permissions`: what the skill can do, in the existing card format

Entries no longer need commit pins, artifact digests, or package roots.
Those fields stay in the 0.2.x history and may return with the v3
installer.

## 4. Commands

- `list` — every entry: name, version, one-line purpose.
- `show <id>` — the full card: purpose, permissions, repo link,
  install instructions.
- `installed` — versions found in the local skills folder.
- `check-updates` — compares installed versions against the registry
  and reports what is newer. For the core skill this is a notice with
  the manual update path, never an install.
- `version` — prints the Selectu5 version.

Every command prints the version line. Output stays chat-readable.

## 5. Update checking

The registry is the version authority. The curator updates an entry's
`version` when a skill releases. `check-updates` compares the local
`installed` inventory against the registry and reports differences.
No network calls to skill repositories are required; the registry is
read from the bundled file with the remote file as fallback, as today.

## 6. Security

v2 executes no skill code and writes nothing outside its own inventory
cache, if any. Links are display-only text. The whole installer threat
model (untrusted archives, path traversal, recovery, consent) does not
apply and is out of scope. The remaining trust statement is: the
registry contents reflect Mike's curation.

## 7. What is removed from 0.2.x

- `scripts/selectu5.py`: the install, update, and recovery engine is
  removed. Kept on branch `v1-installer` for the v3 installer story.
- `scripts/qualify*.py`: the installer qualification harnesses retire
  with the engine. The release packaging (`package.py`) and release
  automation stay.
- `INSTALL_ENABLED`, the consent ceremony, the predecessor chain, and
  `BOOTSTRAP-AND-UPDATE.md`: retired with the engine.

## 8. What is kept from 0.2.x

- The registry format (minus install-authority fields) and curation
  process.
- The deterministic packaging and the prep → approve → publish release
  flow.
- Branch protection, release immutability, and the Apache-2.0 license.

## 9. Migration

- 0.2.6 stays published as versioned history with a release note
  pointing at 2.0.0.
- v2 is a new manual install (download, unzip). The 0.2.6 client keeps
  working as a browser; it is not auto-replaced.
- The 2.0.0 release notes state plainly: the installer is removed in
  v2 and parked for v3.

## 10. Open decisions for Mike

1. Same repo at 2.0.0 (recommended) vs a new repository.
2. Whether `check-updates` should also read live GitHub release tags
   or stay registry-only.
3. Whether showcase entries (Clavi5, Visu5) stay in the v2 menu.
