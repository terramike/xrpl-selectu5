#!/usr/bin/env python3
"""xrpl-selectu5 0.2.0 — Selectu5, the XRPL Muse skill app store.

Companion skill. Read-only toward the core: it reads a curated registry
and the version frontmatter of local skills. Installs happen only with
the user's word for an exact entry and version, from a pinned ref,
after manifest verification. It never proposes, never signs, never
reads seeds, keys, tokens, or policy files.
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "0.2.0"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_REGISTRY = os.path.join(SKILL_DIR, "registry", "registry.json")
REMOTE_REGISTRY = "https://raw.githubusercontent.com/terramike/xrpl-selectu5/main/registry/registry.json"
DEFAULT_SKILLS_DIR = os.path.expanduser("~/workspace/skills")
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
SECRET_NAME = re.compile(r"(seed|secret|\.pem$|\.key$|id_rsa)", re.I)

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|version|access):\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.M)


def read_source(src):
    if src.startswith(("https://", "file://")):
        req = urllib.request.Request(src, headers={"User-Agent": f"xrpl-selectu5/{VERSION}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    with open(src, "rb") as fh:
        return fh.read()


def load_registry():
    """Return (registry_dict, source_label). Remote first, local fallback."""
    override = os.environ.get("SELECTU5_REGISTRY")
    if override:
        candidates = [override]
    else:
        candidates = [REMOTE_REGISTRY, LOCAL_REGISTRY]
    errors = []
    for src in candidates:
        try:
            reg = json.loads(read_source(src).decode("utf-8"))
            if reg.get("schema") != "selectu5-registry/1":
                raise ValueError(f"bad schema: {reg.get('schema')!r}")
            return reg, src
        except Exception as exc:
            errors.append(f"{src}: {exc}")
    print(f"xrpl-selectu5 {VERSION}: cannot read any registry ({'; '.join(errors)})", file=sys.stderr)
    return None, None


def parse_manifest(text):
    m = FRONTMATTER.search(text or "")
    return dict(FIELD.findall(m.group(1))) if m else {}


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
            fields = parse_manifest(open(md, encoding="utf-8").read(4096))
        except Exception:
            continue
        found[name] = {"version": fields.get("version", "unknown"), "path": os.path.join(skills_dir, name)}
    for folder, entry_id in {"xrpl": "xrpl-muse-skill"}.items():
        if folder in found and entry_id not in found:
            found[entry_id] = found[folder]
    return found


def header(source=None):
    print(f"xrpl-selectu5 {VERSION} — Selectu5, the XRPL Muse skill store")
    if source:
        label = "local registry" if source == LOCAL_REGISTRY else source
        print(f"registry: {label}")


def get_entry(reg, entry_id):
    return next((e for e in reg["entries"] if e["id"] == entry_id), None)


def permissions_card(e):
    perm = e["permissions"]
    lines = [
        f"purpose: {e['purpose']}",
        f"repo / page: {e['repo']}",
        "permissions:",
        f"  core commands: {'; '.join(perm['commands'])}",
        f"  files: {'; '.join(perm['files'])}",
        f"  network: {perm['network']}",
        f"  signs: {perm['signs']}",
    ]
    if e.get("notes"):
        lines.append(f"notes: {e['notes']}")
    return "\n".join(lines)


def cmd_list(reg, local, source):
    header(source)
    for e in reg["entries"]:
        state = ""
        if e["id"] in local:
            v = local[e["id"]]["version"]
            state = f" — installed {v}" if v != "unknown" else " — installed (version not stated)"
            if v not in ("unknown", e["version"]):
                state += f" (registry {e['version']})"
        elif e["kind"] == "showcase":
            state = " — showcase, not an install"
        print(f"\n[{e['id']}] {e['name']} — registry {e['version']}{state}")
        print(f"  access: {e['access']} · kind: {e['kind']} · by {e['author']}")
        print(f"  {e['purpose']}")
    return 0


def cmd_show(reg, local, entry_id, source):
    e = get_entry(reg, entry_id)
    if not e:
        print(f"xrpl-selectu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header(source)
    state = (f"installed {local[entry_id]['version']}" if entry_id in local
             else ("showcase — not an install" if e["kind"] == "showcase" else "not installed"))
    print(f"\n{e['name']} [{e['id']}] — registry {e['version']} · {state}")
    print(f"access: {e['access']} · kind: {e['kind']} · by {e['author']}")
    if e.get("core_version"):
        print(f"needs core: {e['core_version']}")
    print()
    print(permissions_card(e))
    if e["kind"] == "showcase":
        print("\nThis is a showcase card. Selectu5 cannot install or enroll it; use the link above.")
    return 0


def cmd_installed(local, source):
    header(source)
    if not local:
        print("\nNo local xrpl-* skills found.")
        return 0
    print("\ninstalled:")
    for name, info in local.items():
        print(f"  {name} {info['version']} — {info['path']}")
    return 0


def cmd_check(reg, local, source):
    header(source)
    updates, current, missing = [], [], []
    for e in reg["entries"]:
        if e["kind"] == "showcase":
            continue
        have = local.get(e["id"])
        if not have:
            missing.append(e)
        elif have["version"] in ("unknown", e["version"]):
            current.append(e)
        else:
            updates.append((e, have["version"]))
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


def fetch_archive(e):
    url = e.get("archive") or f"{e['repo'].rstrip('/')}/archive/{e['ref']}.zip"
    data = read_source(url)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError(f"archive too large ({len(data)} bytes)")
    return data, url


def install_root(zf):
    names = [n for n in zf.namelist() if n and not n.endswith("/")]
    for n in names:
        if n.startswith("/") or ".." in n.split("/"):
            raise ValueError(f"unsafe path in archive: {n}")
        if SECRET_NAME.search(os.path.basename(n)):
            raise ValueError(f"refusing archive with secret-named file: {n}")
    skill_mds = [n for n in names if os.path.basename(n) == "SKILL.md"]
    if not skill_mds:
        raise ValueError("archive has no SKILL.md")
    md = min(skill_mds, key=len)
    root = os.path.dirname(md)
    return root, md


def cmd_install(reg, local, entry_id, yes_version, source):
    e = get_entry(reg, entry_id)
    if not e:
        print(f"xrpl-selectu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header(source)
    if e["kind"] == "showcase":
        print(f"\n{e['name']} is a showcase entry, not an install.")
        print(f"next step: {e['install']}")
        print(f"open: {e['repo']}")
        return 0
    if e["kind"] == "core":
        print(f"\n{e['name']} is the core skill. Selectu5 reports core updates; it does not install the core.")
        print(f"release: {e['repo']} (pinned ref: {e.get('ref') or 'none listed'})")
        print(f"manual path: {e['install']}")
        return 0
    print(f"\n{e['name']} [{e['id']}] — registry {e['version']}")
    print(permissions_card(e))
    if not yes_version:
        print(f"\nDry run — nothing installed. To install this exact version, the user gives the word, then run:")
        print(f"  selectu5.py install {e['id']} --yes {e['version']}")
        return 0
    if yes_version != e["version"]:
        print(f"\nRefused: --yes {yes_version} does not match registry version {e['version']}. Nothing installed.", file=sys.stderr)
        return 1
    if not e.get("ref"):
        print(f"\n{e['id']} has no pinned ref in the registry yet, so it is not installable. Nothing installed.", file=sys.stderr)
        return 1
    skills_dir = os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    target = os.path.join(skills_dir, e["id"])
    have = local.get(e["id"])
    if have and have["version"] == e["version"]:
        print(f"\n{e['id']} {e['version']} is already installed. Nothing changed.")
        return 0
    try:
        data, url = fetch_archive(e)
        print(f"\nfetched: {url} ({len(data)} bytes, pinned ref {e['ref']})")
        with tempfile.TemporaryDirectory() as tmp:
            zf = zipfile.ZipFile(io.BytesIO(data))
            root, md_rel = install_root(zf)
            zf.extractall(tmp)
            src_dir = os.path.join(tmp, root) if root else tmp
            manifest = parse_manifest(open(os.path.join(src_dir, "SKILL.md"), encoding="utf-8").read(4096))
            problems = []
            if manifest.get("name") != e["id"]:
                problems.append(f"manifest name {manifest.get('name')!r} != registry id {e['id']!r}")
            if manifest.get("version") != e["version"]:
                problems.append(f"manifest version {manifest.get('version')!r} != registry version {e['version']!r}")
            if manifest.get("access") and manifest["access"] != e["access"]:
                problems.append(f"manifest access {manifest['access']!r} != registry access {e['access']!r}")
            if problems:
                print("Refused: manifest does not match the registry entry:", file=sys.stderr)
                for p in problems:
                    print(f"  - {p}", file=sys.stderr)
                print("Nothing installed.", file=sys.stderr)
                return 1
            if not manifest.get("access"):
                print("note: the skill manifest has no access field; the registry card above is the authority for this install.")
            os.makedirs(skills_dir, exist_ok=True)
            backup = None
            if os.path.isdir(target):
                backup = target + f".bak-{have['version'] if have else 'unknown'}"
                if os.path.isdir(backup):
                    shutil.rmtree(backup)
                shutil.move(target, backup)
            shutil.move(src_dir, target)
    except Exception as exc:
        print(f"Install failed, nothing installed: {exc}", file=sys.stderr)
        return 1
    print(f"installed: {e['id']} {e['version']} -> {target}")
    if backup:
        print(f"previous version kept at: {backup}")
    print(f"xrpl-selectu5 {VERSION}: install complete. The new skill shows its own version on its next run.")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="selectu5")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p_show = sub.add_parser("show"); p_show.add_argument("id")
    sub.add_parser("installed")
    sub.add_parser("check-updates")
    p_inst = sub.add_parser("install"); p_inst.add_argument("id")
    p_inst.add_argument("--yes", metavar="VERSION", default=None,
                        help="install exactly this registry version (the user's word, encoded)")
    sub.add_parser("version")
    args = ap.parse_args()
    if args.cmd in (None, "version"):
        print(f"xrpl-selectu5 {VERSION}")
        return 0
    reg, source = load_registry()
    if reg is None:
        return 1
    skills_dir = os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    local = local_skills(skills_dir)
    if args.cmd == "list":
        return cmd_list(reg, local, source)
    if args.cmd == "show":
        return cmd_show(reg, local, args.id, source)
    if args.cmd == "installed":
        return cmd_installed(local, source)
    if args.cmd == "check-updates":
        return cmd_check(reg, local, source)
    if args.cmd == "install":
        return cmd_install(reg, local, args.id, args.yes, source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
