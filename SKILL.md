---
name: xrpl-promptu5
version: 0.1.0
core_version: ">=0.14.1"
access: read
author: terramike
description: "Promptu5 — the app store for the XRPL Muse skill family: browse curated add-on skills, see each skill's purpose and permissions in chat, install on your word, and check for updates to add-ons and the core skill. Companion skill — never edits the core xrpl-muse skill, never proposes or signs."
---

# xrpl-promptu5 (Promptu5)

Companion skill to xrpl-muse-skill. Spec: `SPEC.md` in this directory.
Brand: **Promptu5** (Latin *promptus* — kept ready at hand).

## What it does

Runs `scripts/promptu5.py`, which reads a curated registry and reports
what is installed on this machine.

- `list` — every registry entry: purpose, version, access class.
- `show <id>` — one entry in full: purpose, permissions (approved core
  commands, approved files, network use), repo, install state.
- `installed` — local `xrpl-*` skills found, with their versions.
- `check-updates` — compare local versions with the registry. Report
  only. Never installs.
- `install <id>` — v0.1 prints the install plan only (dry run). A real
  install lands in v0.2 and needs the user's word for that exact skill
  and version.
- `version` — print the skill version.

The registry is `registry/registry.json` in this repo. Set
`PROMPTU5_REGISTRY` to a file path or an https URL to use another copy.
Set `PROMPTU5_SKILLS_DIR` to scan a different skills folder.

## Rules (never break)

- Read only. Never proposes, never signs, never touches policy, seeds,
  or the core skill's files.
- The registry is curated by Mike. A listing is not an endorsement of
  any external link inside a listed skill.
- An update notice is information, not an install. No install or core
  update runs without the user's word for that exact item and version.
- A showcase entry (Clavi5, Visu5) is not an install. Show its real
  next step: enroll or open the page.
- Every output prints the version line: `xrpl-promptu5 0.1.0`.

## Use

```bash
python3 scripts/promptu5.py list
python3 scripts/promptu5.py show xrpl-community-shows
python3 scripts/promptu5.py installed
python3 scripts/promptu5.py check-updates
```

Then tell the user: what is listed or installed, any update with its
old and new version, and the skill version. If an entry is a showcase,
say what the real next step is instead of offering an install.

## Updates

Skills do not auto-update. This skill's version is in this file's
frontmatter and is printed by every command. Promptu5 itself is listed
in its own registry, so `check-updates` covers it too. Never install an
update without the user's approval.
