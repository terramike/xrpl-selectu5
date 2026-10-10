#!/usr/bin/env python3
"""Stage 3 actual-artifact interruption qualification.

Installs the published 0.2.4 asset through the production fetcher, starts
the real 0.2.5 update, and kills the child process (SIGKILL) at a
directory-move boundary. The parent then invokes the next operation,
which must recover to a coherent state and complete. Disposable roots
only; the shipped gate is never changed.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402
from qualify_update import verify_backup, package_matches

CHILD = r'''
import hashlib, json, os, sys, time
sys.path.insert(0, {scripts!r})
import selectu5 as m
from qualify import snapshot_tree

cfg = json.load(open(sys.argv[1]))
os.environ["SELECTU5_CORE_DIR"] = cfg["core_dir"]

bundled = json.load(open(cfg["registry_path"], encoding="utf-8"))
base = next(e for e in bundled["entries"] if e["id"] == "xrpl-selectu5")
def entry(v, c, d, u):
    e = dict(base)
    e.update({"version": v, "ref": c, "artifact_sha256": d, "package_root": "xrpl-selectu5-" + v,
              "distribution": {"type": "github_release_asset", "source_commit": c, "asset_url": u,
                               "asset_name": u.rsplit("/", 1)[-1]}})
    return e
def reg(e):
    return {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "interrupt", "entries": [e]}

skills = cfg["skills"]
e_from = entry(cfg["from_version"], cfg["from_commit"], cfg["from_sha256"], cfg["from_url"])
e_to = entry(cfg["to_version"], cfg["to_commit"], cfg["to_sha256"], cfg["to_url"])
dest = m.validate_destination(skills, "xrpl-selectu5")
_, p_from = m.build_plan(e_from, dest)
rc = m.cmd_install(reg(e_from), {}, "xrpl-selectu5", cfg["from_version"], m.LOCAL_REGISTRY, p_from,
                   skills_dir=skills, fetcher=m.fetch_distribution, install_enabled=True,
                   trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1")
print("INSTALLED", rc, flush=True)
if rc != 0:
    sys.exit(3)
print("BASELINE " + json.dumps(snapshot_tree(os.path.join(skills, "xrpl-selectu5")), sort_keys=True), flush=True)

orig = m._rename_dir
count = {"n": 0}
def slow(src, dst):
    count["n"] += 1
    print("MOVE" + str(count["n"]) + " " + src + " -> " + dst, flush=True)
    time.sleep(2.5)
    return orig(src, dst)
m._rename_dir = slow
_, p_to = m.build_plan(e_to, dest)
rc = m.cmd_install(reg(e_to), {"xrpl-selectu5": {"version": cfg["from_version"]}}, "xrpl-selectu5", cfg["to_version"],
                   m.LOCAL_REGISTRY, p_to, skills_dir=skills, fetcher=m.fetch_distribution,
                   install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1")
print("UPDATED", rc, flush=True)
'''


def file_sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-version", default="0.2.4")
    ap.add_argument("--from-commit", default="5e157df7062e0528f04add18d4bc4f0cf2586b2e")
    ap.add_argument("--from-sha256", default="98ccb8d50f2a66c105a0efa39aa337f234d11b135245ce5b0054156e74b3f5a2")
    ap.add_argument("--from-url", default="https://github.com/terramike/xrpl-selectu5/releases/download/v0.2.4/xrpl-selectu5-0.2.4.zip")
    ap.add_argument("--to-version", default="0.2.5")
    ap.add_argument("--to-commit", default="6b942346ea6ffaa86f71aa80cf1e741822c2dc31")
    ap.add_argument("--to-sha256", default="06b10f880d48cb426ddfddc9088fd40d04ace1372324756f2575b9a37a63ea2d")
    ap.add_argument("--to-url", default="https://github.com/terramike/xrpl-selectu5/releases/download/v0.2.5/xrpl-selectu5-0.2.5.zip")
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    args = ap.parse_args()

    root = tempfile.mkdtemp(prefix="selectu5-interrupt-")
    skills = os.path.join(root, "skills"); os.makedirs(skills)
    core = os.path.join(root, "dummy-core"); os.makedirs(core)
    manifest = os.path.join(core, "SKILL.md")
    with open(manifest, "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\nversion: 0.14.1\naccess: propose\n---\n")
    sentinel = os.path.join(root, "credential-sentinel.txt")
    with open(sentinel, "w", encoding="utf-8") as fh:
        fh.write("dummy credential sentinel - not a real credential\n")
    guards = {p: file_sha(p) for p in (manifest, sentinel)}

    cfg = {"core_dir": core, "registry_path": os.path.join(REPO, "registry", "registry.json"), "skills": skills,
           "from_version": args.from_version, "from_commit": args.from_commit, "from_sha256": args.from_sha256, "from_url": args.from_url,
           "to_version": args.to_version, "to_commit": args.to_commit, "to_sha256": args.to_sha256, "to_url": args.to_url}
    cfg_path = os.path.join(root, "cfg.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)

    proc = subprocess.Popen([sys.executable, "-c", CHILD.replace("{scripts!r}", repr(HERE)), cfg_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    moves = []
    killed_at = None
    old_tree = None
    child_lines = []
    for line in proc.stdout:
        line = line.strip()
        child_lines.append(line)
        if line.startswith("BASELINE "):
            old_tree = json.loads(line[len("BASELINE "):])
        if line.startswith("MOVE"):
            moves.append(line)
            if len(moves) == 2:
                proc.kill()  # SIGKILL on POSIX, TerminateProcess on Windows
                killed_at = line
                break
    proc.wait(timeout=30)
    mid_state = sorted(os.listdir(skills))

    # Recovery + completion by the next operation (production fetcher again).
    os.environ["SELECTU5_CORE_DIR"] = core
    bundled = json.load(open(os.path.join(REPO, "registry", "registry.json"), encoding="utf-8"))
    base = next(e for e in bundled["entries"] if e["id"] == "xrpl-selectu5")
    e_to = dict(base)
    e_to.update({"version": args.to_version, "ref": args.to_commit, "artifact_sha256": args.to_sha256,
                 "package_root": f"xrpl-selectu5-{args.to_version}",
                 "distribution": {"type": "github_release_asset", "source_commit": args.to_commit,
                                  "asset_url": args.to_url, "asset_name": args.to_url.rsplit("/", 1)[-1]}})
    reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "interrupt", "entries": [e_to]}
    dest = m.validate_destination(skills, "xrpl-selectu5")
    _, plan_to = m.build_plan(e_to, dest)
    rc = m.cmd_install(reg, m.local_skills(skills), "xrpl-selectu5", args.to_version, m.LOCAL_REGISTRY, plan_to,
                       skills_dir=skills, fetcher=m.fetch_distribution, install_enabled=True,
                       trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1")
    target = os.path.join(skills, "xrpl-selectu5")
    meta = {}
    meta_path = os.path.join(target, ".selectu5-meta.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
    man = m.parse_manifest_strict(open(os.path.join(target, "SKILL.md"), encoding="utf-8").read()) if os.path.isdir(target) else {}
    guards_ok = all(file_sha(p) == h for p, h in guards.items())
    data = m.fetch_distribution(e_to)
    m.verify_artifact(data, args.to_sha256)
    backup_ok, backups = verify_backup(skills, "xrpl-selectu5", old_tree) if old_tree is not None else (False, [])
    active_ok = package_matches(target, data, e_to["package_root"])
    coherent = (rc == 0 and meta.get("version") == args.to_version and meta.get("artifact_sha256") == args.to_sha256
                and meta.get("commit") == args.to_commit and man.get("version") == args.to_version
                and guards_ok and backup_ok and active_ok)
    status = "pass" if (killed_at and coherent) else "fail"
    evidence = {"schema": "selectu5-stage3-interrupt-evidence/1", "qualification_code_commit": os.environ.get("GITHUB_SHA"),
                "installer_code_commit": os.environ.get("GITHUB_SHA"), "platform": sys.platform,
                "catalog_commit_C": None, "catalog_authority": "injected qualification catalog",
                "disposable_root": root,
                "killed_at_move": killed_at, "moves_seen": moves, "mid_state_entries": mid_state,
                "child_exit_code": proc.returncode, "child_output_tail": child_lines[-20:],
                "recovery_install_rc": rc, "final_provenance": meta, "guards_unchanged": guards_ok,
                "backup_matches_complete_baseline": backup_ok, "backups": backups, "active_matches_artifact": active_ok,
                "checks": [{"name": "actual-artifact interruption at a directory move, then recovery", "kind": "actual_artifact", "status": status,
                            "evidence": f"killed at: {killed_at}; mid-state: {mid_state}; recovery rc={rc}; final active={meta.get('version')} sha={meta.get('artifact_sha256')} guards_ok={guards_ok}"}]}
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    with open(args.output_md, "w", encoding="utf-8") as fh:
        fh.write("# Selectu5 Stage 3 actual-artifact interruption\n\n"
                 f"Killed the real {args.from_version} -> {args.to_version} update at: `{killed_at}`\n\n"
                 f"| Check | Kind | Status |\n|---|---|---|\n| actual-artifact interruption at a directory move, then recovery | actual_artifact | {status} |\n")
    print(json.dumps({"status": status, "killed_at": killed_at}))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
