#!/usr/bin/env python3
"""Deterministic Selectu5 package builder.

Builds one ZIP from an explicit file inventory with fixed member order,
timestamps, permissions, and compression. Source paths are checked before
any file is read: symlink, junction, and reparse-point components are
refused, and every resolved file must stay inside the source root.

Evidence classes:
- development-working-tree: built from a working tree. Development only.
- clean-export-rebuild: built from two independent clean exports of one
  recorded source commit S and compared byte for byte.

The builder does not publish anything and never records a digest inside
its own package.
"""
import argparse
import hashlib
import io
import json
import os
import platform
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402

BUILDER_VERSION = "1.1"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inventory(path):
    inv = json.load(open(path, encoding="utf-8"))
    files = inv.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("inventory must list at least one file")
    return inv


def _check_components(path):
    """Refuse symlink/junction/reparse components in an existing path."""
    cur = os.path.abspath(path)
    parts = []
    while True:
        head, tail = os.path.split(cur)
        if tail:
            parts.append(cur)
            cur = head
        else:
            break
    for component in reversed(parts):
        if os.path.lexists(component) and m._is_redirect(component):
            raise SystemExit(f"refused symlink or reparse component in source path: {component}")


def _resolved_source_file(source_root, rel):
    """Return the contained real path for one inventory file, before reading."""
    if not isinstance(rel, str) or not rel:
        raise SystemExit("inventory path must be a non-empty string")
    if rel.startswith(("/", "\\")) or "\\" in rel:
        raise SystemExit(f"unsafe inventory path: {rel}")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise SystemExit(f"unsafe inventory path: {rel}")
    if m.SECRET_NAME.search(os.path.basename(rel)):
        raise SystemExit(f"credential-like file refused: {rel}")
    root = os.path.realpath(source_root)
    cur = root
    for part in parts:
        cur = os.path.join(cur, part)
        if os.path.lexists(cur) and m._is_redirect(cur):
            raise SystemExit(f"refused symlink or reparse component in source path: {cur}")
    if not os.path.isfile(cur):
        raise SystemExit(f"inventory file missing: {rel}")
    resolved = os.path.realpath(cur)
    if os.path.commonpath((resolved, root)) != root:
        raise SystemExit(f"inventory file escapes the source root: {rel}")
    return resolved


def build_zip(source_root, package_root, files):
    """Return (zip_bytes, inventory_records). Validates the finished ZIP."""
    seen = {}
    for item in files:
        rel = item.get("path") if isinstance(item, dict) else None
        if not isinstance(rel, str):
            raise SystemExit("inventory entries must be objects with a path string")
        key = rel.lower()
        if key in seen:
            raise SystemExit(f"duplicate or colliding inventory path: {rel}")
        seen[key] = rel
    records = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in sorted(files, key=lambda x: x["path"]):
            rel = item["path"]
            src = _resolved_source_file(source_root, rel)
            data = open(src, "rb").read()
            mode = 0o755 if item.get("executable") else 0o644
            info = zipfile.ZipInfo(f"{package_root}/{rel}", date_time=FIXED_DATE)
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
            records.append({"path": rel, "bytes": len(data), "sha256": sha(data), "executable": bool(item.get("executable"))})
    data = buf.getvalue()
    # The finished archive must pass the installer's own structural checks
    # before any successful package evidence is written.
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        m.validate_archive(zf, package_root)
    return data, records


def manifest_identity(source_root):
    path = _resolved_source_file(source_root, "SKILL.md")
    man = m.parse_manifest_strict(open(path, encoding="utf-8").read())
    return {"name": man["name"], "version": man["version"], "access": man["access"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True, help="working tree (development evidence) or clean export A")
    ap.add_argument("--inventory", required=True, help="JSON inventory: {package_root, files:[{path, executable?}]}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--record", required=True, help="write the inventory/digest record JSON here")
    ap.add_argument("--verify-rebuild", action="store_true", help="also build from --export-b and refuse any byte difference")
    ap.add_argument("--export-b", help="second independent clean export of the same source commit")
    ap.add_argument("--source-commit", help="source commit S the clean exports were taken from (required with --verify-rebuild)")
    args = ap.parse_args()
    inv = load_inventory(args.inventory)
    package_root = inv.get("package_root")
    if not package_root or not m.re.match(r"^[A-Za-z0-9._-]+$", package_root):
        raise SystemExit("inventory package_root must be one path component")
    _check_components(args.source_root)
    data, records = build_zip(args.source_root, package_root, inv["files"])
    evidence_class = "development-working-tree"
    rebuild_verified = False
    if args.verify_rebuild:
        if not args.export_b or not args.source_commit or not m.COMMIT_RE.match(args.source_commit):
            raise SystemExit("--verify-rebuild requires --export-b and a full 40-char --source-commit")
        _check_components(args.export_b)
        again, _ = build_zip(args.export_b, package_root, inv["files"])
        if again != data:
            raise SystemExit("clean-export rebuild produced different bytes; investigate before recording a digest")
        evidence_class = "clean-export-rebuild"
        rebuild_verified = True
    with open(args.out, "wb") as fh:
        fh.write(data)
    record = {
        "schema": "selectu5-package-record/1",
        "evidence_class": evidence_class,
        "source_commit_S": args.source_commit if rebuild_verified else None,
        "build_tool": {"package_py": BUILDER_VERSION, "python": platform.python_version()},
        "package_root": package_root,
        "manifest": manifest_identity(args.source_root),
        "files": records,
        "archive_bytes": len(data),
        "sha256_D": sha(data),
        "rebuild_verified": rebuild_verified,
    }
    with open(args.record, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
    print(json.dumps({"out": args.out, "bytes": len(data), "sha256_D": record["sha256_D"],
                      "evidence_class": evidence_class, "rebuild_verified": rebuild_verified}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
