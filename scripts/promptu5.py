#!/usr/bin/env python3
"""xrpl-promptu5 0.1.0 — Promptu5, the XRPL Muse skill app store.

Companion skill. Read-only: it reads a curated registry and the version
frontmatter of local skills. It never proposes, never signs, never
reads seeds, keys, tokens, or policy files, and never installs in v0.1.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

VERSION = "0.1.0"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(SKILL_DIR, "registry", "registry.json")
DEFAULT_SKILLS_DIR = os.path.expanduser("~/workspace/skills")

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|version):\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.M)


def load_registry():
    src = os.environ.get("PROMPTU5_REGISTRY", DEFAULT_REGISTRY)
    try:
        if src.startswith("https://"):
            req = urllib.request.Request(src, headers={"User-Agent": "xrpl-promptu5/0.1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8")), src
        with open(src, encoding="utf-8") as fh:
            return json.load(fh), src
    except Exception as exc:
        print(f"xrpl-promptu5 {VERSION}: cannot read registry ({src}): {exc}", file=sys.stderr)
        return None, src


ALIASES = {"xrpl": "xrpl-muse-skill"}


def local_skills(skills_dir):
    found = {}
    if not os.path.isdir(skills_dir):
        return found
    for name in sorted(os.listdir(skills_dir)):
        if not name.startswith("xrpl"):
            continue
        md = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(md):
            continue
        try:
            text = open(md, encoding="utf-8").read(4096)
        except Exception:
            continue
        m = FRONTMATTER.search(text)
        fields = dict(FIELD.findall(m.group(1))) if m else {}
        found[name] = {"version": fields.get("version", "unknown"), "path": os.path.join(skills_dir, name)}
    for folder, entry_id in ALIASES.items():
        if folder in found and entry_id not in found:
            found[entry_id] = found[folder]
    return found


def header():
    print(f"xrpl-promptu5 {VERSION} — Promptu5, the XRPL Muse skill store")


def cmd_list(reg, local):
    header()
    for e in reg["entries"]:
        state = ""
        if e["id"] in local:
            state = f" — installed {local[e['id']]['version']}"
            if local[e["id"]]["version"] != e["version"]:
                state += f" (registry {e['version']})"
        elif e["kind"] == "showcase":
            state = " — showcase, not an install"
        print(f"\n[{e['id']}] {e['name']} — registry {e['version']}{state}")
        print(f"  access: {e['access']} · kind: {e['kind']} · by {e['author']}")
        print(f"  {e['purpose']}")
    return 0


def cmd_show(reg, local, entry_id):
    entry = next((e for e in reg["entries"] if e["id"] == entry_id), None)
    if not entry:
        print(f"xrpl-promptu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header()
    state = (f"installed {local[entry_id]['version']}" if entry_id in local
             else ("showcase — not an install" if entry["kind"] == "showcase" else "not installed"))
    print(f"\n{entry['name']} [{entry['id']}] — registry {entry['version']} · {state}")
    print(f"access: {entry['access']} · kind: {entry['kind']} · by {entry['author']}")
    if entry.get("core_version"):
        print(f"needs core: {entry['core_version']}")
    print(f"\npurpose: {entry['purpose']}")
    print(f"repo / page: {entry['repo']}")
    print(f"install: {entry['install']}")
    perm = entry["permissions"]
    print("\npermissions:")
    print(f"  core commands: {'; '.join(perm['commands'])}")
    print(f"  files: {'; '.join(perm['files'])}")
    print(f"  network: {perm['network']}")
    print(f"  signs: {perm['signs']}")
    if entry.get("notes"):
        print(f"\nnotes: {entry['notes']}")
    if entry["kind"] == "showcase":
        print("\nThis is a showcase card. Promptu5 cannot install or enroll it; use the link above.")
    return 0


def cmd_installed(local):
    header()
    if not local:
        print("\nNo local xrpl-* skills found.")
        return 0
    print("\ninstalled:")
    for name, info in local.items():
        print(f"  {name} {info['version']} — {info['path']}")
    return 0


def cmd_check(reg, local):
    header()
    updates, current, missing = [], [], []
    for e in reg["entries"]:
        if e["kind"] == "showcase":
            continue
        have = local.get(e["id"])
        if not have:
            missing.append(e)
        elif have["version"] == "unknown":
            current.append(e)
        elif have["version"] != e["version"]:
            updates.append((e, have["version"]))
        else:
            current.append(e)
    if updates:
        print("\nupdates available (nothing installed — your word first):")
        for e, have in updates:
            print(f"  {e['id']}: {have} -> {e['version']} — {e['repo']}")
    if missing:
        print("\nlisted, not installed:")
        for e in missing:
            print(f"  {e['id']} {e['version']} — {e['purpose']}")
    if current:
        print("\ncurrent:")
        for e in current:
            print(f"  {e['id']} {e['version']}")
    if not updates and not missing:
        print("\nEverything listed is installed and current.")
    print("\nAn update notice is information, not an install.")
    return 0


def cmd_install(reg, entry_id):
    entry = next((e for e in reg["entries"] if e["id"] == entry_id), None)
    if not entry:
        print(f"xrpl-promptu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header()
    if entry["kind"] == "showcase":
        print(f"\n{entry['name']} is a showcase entry, not an install.")
        print(f"next step: {entry['install']}")
        print(f"open: {entry['repo']}")
        return 0
    print(f"\ninstall plan for {entry['id']} {entry['version']} (v0.1 dry run — nothing installed):")
    print(f"  1. read the registry entry and show its permissions card")
    print(f"  2. fetch the pinned release from {entry['repo']}")
    print(f"  3. verify the SKILL.md manifest (name, version, access) matches this entry")
    print(f"  4. place it in the Muse skills folder and print the installed version")
    print("Real installs land in v0.2 and need your word for that exact skill and version.")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="promptu5")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p_show = sub.add_parser("show"); p_show.add_argument("id")
    sub.add_parser("installed")
    sub.add_parser("check-updates")
    p_inst = sub.add_parser("install"); p_inst.add_argument("id")
    sub.add_parser("version")
    args = ap.parse_args()
    if args.cmd in (None, "version"):
        print(f"xrpl-promptu5 {VERSION}")
        return 0
    reg, src = load_registry()
    if reg is None:
        return 1
    skills_dir = os.environ.get("PROMPTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    local = local_skills(skills_dir)
    if args.cmd == "list":
        return cmd_list(reg, local)
    if args.cmd == "show":
        return cmd_show(reg, local, args.id)
    if args.cmd == "installed":
        return cmd_installed(local)
    if args.cmd == "check-updates":
        return cmd_check(reg, local)
    if args.cmd == "install":
        return cmd_install(reg, args.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
