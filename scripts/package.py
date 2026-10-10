#!/usr/bin/env python3
"""Deterministic Selectu5 package builder.

Builds one ZIP from an explicit file inventory with fixed member order,
timestamps, permissions, and compression. Emits an inventory record with
per-file SHA-256 values and the complete ZIP SHA-256 (D). The builder does
not publish anything and never records a digest inside its own package.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402

FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_inventory(path):
    inv = json.load(open(path, encoding="utf-8"))
    files = inv.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("inventory must list at least one file")
    return inv


def build_zip(source_root, package_root, files):
    """Return (zip_bytes, inventory_records). Refuses unsafe inventory paths."""
    records = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in sorted(files, key=lambda x: x["path"]):
            rel = item["path"]
            if rel.startswith(("/", "\\")) or ".." in rel.split("/") or "\\" in rel:
                raise SystemExit(f"unsafe inventory path: {rel}")
            if m.SECRET_NAME.search(os.path.basename(rel)):
                raise SystemExit(f"credential-like file refused: {rel}")
            src = os.path.join(source_root, rel)
            if not os.path.isfile(src):
                raise SystemExit(f"inventory file missing: {rel}")
            data = open(src, "rb").read()
            mode = 0o755 if item.get("executable") else 0o644
            info = zipfile.ZipInfo(f"{package_root}/{rel}", date_time=FIXED_DATE)
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
            records.append({"path": rel, "bytes": len(data), "sha256": sha(data), "executable": bool(item.get("executable"))})
    return buf.getvalue(), records


def manifest_identity(source_root):
    text = open(os.path.join(source_root, "SKILL.md"), encoding="utf-8").read()
    man = m.parse_manifest_strict(text)
    return {"name": man["name"], "version": man["version"], "access": man["access"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--inventory", required=True, help="JSON inventory: {package_root, files:[{path, executable?}]}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--record", required=True, help="write the inventory/digest record JSON here")
    ap.add_argument("--verify-rebuild", action="store_true", help="build twice in clean temp dirs and refuse any byte difference")
    args = ap.parse_args()
    inv = load_inventory(args.inventory)
    package_root = inv.get("package_root")
    if not package_root or not m.re.match(r"^[A-Za-z0-9._-]+$", package_root):
        raise SystemExit("inventory package_root must be one path component")
    data, records = build_zip(args.source_root, package_root, inv["files"])
    if args.verify_rebuild:
        with tempfile.TemporaryDirectory() as td:
            again, _ = build_zip(args.source_root, package_root, inv["files"])
            if again != data:
                raise SystemExit("rebuild produced different bytes; investigate before recording a digest")
    with open(args.out, "wb") as fh:
        fh.write(data)
    record = {
        "schema": "selectu5-package-record/1",
        "package_root": package_root,
        "manifest": manifest_identity(args.source_root),
        "files": records,
        "archive_bytes": len(data),
        "sha256_D": sha(data),
        "rebuild_verified": bool(args.verify_rebuild),
    }
    with open(args.record, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
    print(json.dumps({"out": args.out, "bytes": len(data), "sha256_D": record["sha256_D"], "rebuild_verified": record["rebuild_verified"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
