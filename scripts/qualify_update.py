#!/usr/bin/env python3
"""Stage 3 actual update qualification: install one published release asset
through the production fetcher, then update to the next published asset the
same way, in a disposable root. Records fetcher calls and tree identities.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402
from qualify import snapshot_tree as complete_snapshot

OVERRIDES = [
    "install_enabled=True passed only to cmd_install inside this harness",
    "fetcher is selectu5.fetch_distribution (production transport) with a call counter",
    "trusted_catalog=TRUSTED_INSTALL_SOURCE injected for the local qualification catalog",
    "core_version_text supplied from the dummy core manifest bound by SELECTU5_CORE_DIR",
]


def file_sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def snapshot(root):
    return complete_snapshot(root)


def verify_backup(skills, entry_id, before):
    backups = sorted(d for d in os.listdir(skills) if d.startswith(entry_id + ".bak-"))
    return (len(backups) == 1 and snapshot(os.path.join(skills, backups[0])) == before), backups


def package_matches(target, data, package_root):
    expected = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        m.validate_archive(zf, package_root)
        for info in zf.infolist():
            if not info.is_dir():
                expected[info.filename[len(package_root) + 1:]] = hashlib.sha256(zf.read(info)).hexdigest()
    actual = {}
    for dp, _, files in os.walk(target, followlinks=False):
        for name in files:
            path = os.path.join(dp, name)
            rel = os.path.relpath(path, target).replace(os.sep, "/")
            if rel == ".selectu5-meta.json":
                continue
            if m._is_redirect(path):
                return False
            actual[rel] = file_sha(path)
    return expected == actual


def capture(fn):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn()
    return rc, (out.getvalue() + err.getvalue()).strip()


class ProdFetcher:
    def __init__(self):
        self.calls = 0

    def __call__(self, entry):
        self.calls += 1
        return m.fetch_distribution(entry)


def make_entry(base, version, commit, digest, asset_url, root_name):
    e = dict(base)
    e.update({"version": version, "ref": commit, "artifact_sha256": digest, "package_root": root_name,
              "distribution": {"type": "github_release_asset", "source_commit": commit,
                               "asset_url": asset_url, "asset_name": asset_url.rsplit("/", 1)[-1]}})
    return e


def reg_of(entry):
    return {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "stage3-qualification", "entries": [entry]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-version", required=True)
    ap.add_argument("--from-commit", required=True)
    ap.add_argument("--from-sha256", required=True)
    ap.add_argument("--from-url", required=True)
    ap.add_argument("--to-version", required=True)
    ap.add_argument("--to-commit", required=True)
    ap.add_argument("--to-sha256", required=True)
    ap.add_argument("--to-url", required=True)
    ap.add_argument("--entry-id", default="xrpl-selectu5")
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    args = ap.parse_args()

    bundled = json.load(open(os.path.join(REPO, "registry", "registry.json"), encoding="utf-8"))
    base = next(e for e in bundled["entries"] if e["id"] == args.entry_id)
    e_from = make_entry(base, args.from_version, args.from_commit, args.from_sha256, args.from_url, f"xrpl-selectu5-{args.from_version}")
    e_to = make_entry(base, args.to_version, args.to_commit, args.to_sha256, args.to_url, f"xrpl-selectu5-{args.to_version}")
    m.validate_registry(reg_of(e_from)); m.validate_registry(reg_of(e_to))

    root = tempfile.mkdtemp(prefix="selectu5-update-")
    skills = os.path.join(root, "skills"); os.makedirs(skills)
    core = os.path.join(root, "dummy-core"); os.makedirs(core)
    manifest = os.path.join(core, "SKILL.md")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\nversion: 0.14.1\naccess: propose\n---\n")
    os.environ["SELECTU5_CORE_DIR"] = core
    sentinel = os.path.join(root, "credential-sentinel.txt")
    with open(sentinel, "w", encoding="utf-8") as fh:
        fh.write("dummy credential sentinel - not a real credential\n")
    guards = {p: file_sha(p) for p in (manifest, sentinel)}

    def guards_ok():
        return all(file_sha(p) == h for p, h in guards.items())

    dest = m.validate_destination(skills, args.entry_id)
    _, plan_from = m.build_plan(e_from, dest)
    _, plan_to = m.build_plan(e_to, dest)
    checks = []

    from_data = m.fetch_distribution(e_from)
    to_data = m.fetch_distribution(e_to)
    m.verify_artifact(from_data, args.from_sha256)
    m.verify_artifact(to_data, args.to_sha256)

    f1 = ProdFetcher()
    rc, out = capture(lambda: m.cmd_install(reg_of(e_from), {}, args.entry_id, args.from_version, m.LOCAL_REGISTRY, plan_from,
                                            skills_dir=skills, fetcher=f1, install_enabled=True,
                                            trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    meta1 = json.load(open(os.path.join(skills, args.entry_id, ".selectu5-meta.json"), encoding="utf-8"))
    target = os.path.join(skills, args.entry_id)
    old_tree = snapshot(target)
    old_ok = (meta1.get("id") == args.entry_id and meta1.get("commit") == args.from_commit
              and meta1.get("artifact_sha256") == args.from_sha256
              and package_matches(target, from_data, e_from["package_root"]))
    checks.append({"name": "actual fresh installation of the earlier published asset", "kind": "actual_artifact",
                   "status": "pass" if rc == 0 and f1.calls == 1 and old_ok and meta1.get("version") == args.from_version and guards_ok() else "fail",
                   "evidence": out[-250:] + f" | fetcher_calls={f1.calls} | active={meta1.get('version')}"})

    f2 = ProdFetcher()
    rc, out = capture(lambda: m.cmd_install(reg_of(e_to), m.local_skills(skills), args.entry_id, args.to_version, m.LOCAL_REGISTRY, plan_to,
                                            skills_dir=skills, fetcher=f2, install_enabled=True,
                                            trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    meta2 = json.load(open(os.path.join(skills, args.entry_id, ".selectu5-meta.json"), encoding="utf-8"))
    backup_ok, backups = verify_backup(skills, args.entry_id, old_tree)
    active_ok = (meta2.get("id") == args.entry_id and meta2.get("commit") == args.to_commit
                 and package_matches(target, to_data, e_to["package_root"]))
    checks.append({"name": "actual update between published assets", "kind": "actual_artifact",
                   "status": "pass" if rc == 0 and f2.calls == 1 and active_ok and meta2.get("version") == args.to_version and meta2.get("artifact_sha256") == args.to_sha256 and backup_ok and guards_ok() else "fail",
                   "evidence": out[-250:] + f" | fetcher_calls={f2.calls} | active={meta2.get('version')} sha={meta2.get('artifact_sha256')} backups={backups} backup_is_from={backup_ok}"})

    f3 = ProdFetcher()
    before = snapshot(skills)
    rc, out = capture(lambda: m.cmd_install(reg_of(e_to), m.local_skills(skills), args.entry_id, args.to_version, m.LOCAL_REGISTRY, plan_to,
                                            skills_dir=skills, fetcher=f3, install_enabled=True,
                                            trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    checks.append({"name": "actual post-update no-op", "kind": "actual_artifact",
                   "status": "pass" if rc == 0 and f3.calls == 0 and snapshot(skills) == before and guards_ok() else "fail",
                   "evidence": out[-250:] + f" | fetcher_calls={f3.calls} | tree_unchanged={snapshot(skills) == before}"})

    # The downloaded bytes must hash to the approved digest (independent check).
    data = m.fetch_distribution(e_to)
    got = hashlib.sha256(data).hexdigest()
    checks.append({"name": "published asset digest equals approved digest", "kind": "actual_artifact",
                   "status": "pass" if got == args.to_sha256 else "fail",
                   "evidence": f"bytes={len(data)} sha256={got} expected={args.to_sha256}"})

    evidence = {"schema": "selectu5-stage3-update-evidence/1",
                "from": {"version": args.from_version, "source_commit_S": args.from_commit, "sha256_D": args.from_sha256, "asset_url": args.from_url},
                "to": {"version": args.to_version, "source_commit_S": args.to_commit, "sha256_D": args.to_sha256, "asset_url": args.to_url},
                "qualification_code_commit": os.environ.get("GITHUB_SHA"),
                "installer_code_commit": os.environ.get("GITHUB_SHA"), "platform": sys.platform,
                "catalog_commit_C": None, "catalog_authority": "injected qualification catalog",
                "disposable_root": root, "test_overrides": OVERRIDES, "checks": checks}
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    lines = ["# Selectu5 Stage 3 actual update qualification", "",
             f"From {args.from_version} (S `{args.from_commit}`, D `{args.from_sha256}`) to {args.to_version} (S `{args.to_commit}`, D `{args.to_sha256}`) via the production fetcher.", "",
             "| Check | Kind | Status |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['name']} | {c['kind']} | {c['status']} |")
    with open(args.output_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"statuses": [c["status"] for c in checks]}))
    return 0 if all(c["status"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
