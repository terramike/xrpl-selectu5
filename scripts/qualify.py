#!/usr/bin/env python3
"""Selectu5 production qualification harness.

Separate from the production CLI. It creates a disposable root, records
every test override, runs synthetic isolated installs, attempts the actual
production fetcher for one immutable source commit, and emits evidence.
It never changes INSTALL_ENABLED in shipped code and never installs into
a user skills folder.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402

PERM = {"commands": ["none"], "files": ["none"], "network": "none", "signs": "Never."}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def zip_bytes(version):
    buf = io.BytesIO()
    manifest = f"---\nname: xrpl-demo\nversion: {version}\naccess: read\n---\n# demo\n"
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pkg-abc/SKILL.md", manifest)
        z.writestr("pkg-abc/README.md", f"demo {version}\n")
    return buf.getvalue()


def entry(version, data):
    return {
        "id": "xrpl-demo", "name": "xrpl-demo", "kind": "skill", "version": version,
        "core_version": None, "access": "read", "author": "qualification",
        "purpose": "synthetic qualification entry", "repo": "https://github.com/terramike/xrpl-demo",
        "install": "synthetic", "permissions": PERM, "ref": "a" * 40,
        "artifact_sha256": sha(data), "package_root": "pkg-abc",
    }


def capture(fn):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn()
    return rc, out.getvalue(), err.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        print("source commit must be a full 40-char SHA", file=sys.stderr)
        return 2

    checks = []
    overrides = ["install_enabled=True passed only to cmd_install inside this harness"]

    # Source inspection (no installed code executed).
    reg = json.load(open(os.path.join(REPO, "registry", "registry.json"), encoding="utf-8"))
    manifest = m.parse_manifest_strict(open(os.path.join(REPO, "SKILL.md"), encoding="utf-8").read())
    self_entry = next(e for e in reg["entries"] if e["id"] == "xrpl-selectu5")
    version_ok = m.VERSION == manifest["version"] == self_entry["version"]
    list_only = []
    for e in reg["entries"]:
        if e["kind"] == "skill" and not (e.get("ref") and e.get("artifact_sha256") and e.get("package_root")):
            list_only.append(e["id"])
    checks.append({"name": "source versions and gate", "kind": "source_inspection", "status": "pass" if version_ok and m.INSTALL_ENABLED is False else "fail",
                   "evidence": f"code={m.VERSION} manifest={manifest['version']} catalog={self_entry['version']} install_enabled={m.INSTALL_ENABLED}"})
    checks.append({"name": "unqualified entries list-only", "kind": "source_inspection", "status": "pass" if list_only else "fail", "evidence": ", ".join(list_only)})

    # Repository synthetic suite.
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=REPO, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
    checks.append({"name": "repository test suite", "kind": "synthetic", "status": "pass" if proc.returncode == 0 else "fail", "command": "python3 -m unittest discover -s tests", "exit_code": proc.returncode, "evidence": "\n".join(tail)})

    # Disposable synthetic install/update with dummy sentinels.
    root = tempfile.mkdtemp(prefix="selectu5-qualify-")
    skills = os.path.join(root, "skills")
    os.makedirs(skills)
    dummy_core = os.path.join(root, "dummy-core")
    os.makedirs(dummy_core)
    with open(os.path.join(dummy_core, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\nversion: 0.14.1\naccess: propose\n---\n")
    credential_sentinel = os.path.join(root, "credential-sentinel.txt")
    with open(credential_sentinel, "w", encoding="utf-8") as fh:
        fh.write("dummy credential sentinel - not a real credential\n")
    sentinel_paths = [os.path.join(dummy_core, "SKILL.md"), credential_sentinel]
    before = {p: sha(open(p, "rb").read()) for p in sentinel_paths}

    v1 = zip_bytes("1.0.0")
    e1 = entry("1.0.0", v1)
    reg1 = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "curator": "qualification", "entries": [e1]}
    plan1 = m.build_plan(e1, os.path.join(skills, "xrpl-demo"))[1]
    rc, out, err = capture(lambda: m.cmd_install(reg1, {}, "xrpl-demo", "1.0.0", m.LOCAL_REGISTRY, plan1, skills_dir=skills, fetcher=lambda e: v1, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    checks.append({"name": "synthetic fresh install via cmd_install", "kind": "synthetic", "status": "pass" if rc == 0 and os.path.exists(os.path.join(skills, "xrpl-demo", "SKILL.md")) else "fail", "evidence": (out + err).strip()[-500:]})

    local = m.local_skills(skills)
    rc, out, err = capture(lambda: m.cmd_install(reg1, local, "xrpl-demo", "1.0.0", m.LOCAL_REGISTRY, plan1, skills_dir=skills, fetcher=lambda e: v1, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    checks.append({"name": "synthetic matching-provenance no-op", "kind": "synthetic", "status": "pass" if rc == 0 else "fail", "evidence": (out + err).strip()[-300:]})

    v2 = zip_bytes("1.0.1")
    e2 = entry("1.0.1", v2)
    reg2 = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "curator": "qualification", "entries": [e2]}
    plan2 = m.build_plan(e2, os.path.join(skills, "xrpl-demo"))[1]
    rc, out, err = capture(lambda: m.cmd_install(reg2, m.local_skills(skills), "xrpl-demo", "1.0.1", m.LOCAL_REGISTRY, plan2, skills_dir=skills, fetcher=lambda e: v2, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text="0.14.1"))
    backups = [x for x in os.listdir(skills) if x.startswith("xrpl-demo.bak-")]
    checks.append({"name": "synthetic update with backup", "kind": "synthetic", "status": "pass" if rc == 0 and backups else "fail", "evidence": (out + err).strip()[-500:], "backups": backups})

    after = {p: sha(open(p, "rb").read()) for p in sentinel_paths}
    checks.append({"name": "dummy core and credential sentinels unchanged", "kind": "synthetic", "status": "pass" if before == after else "fail", "sentinels": [{"path": os.path.basename(p), "before": before[p], "after": after[p]} for p in sentinel_paths]})

    # Actual production transport attempt for Selectu5 itself at S.
    actual_entry = {"id": "xrpl-selectu5", "repo": "https://github.com/terramike/xrpl-selectu5", "ref": args.source_commit}
    artifact = {"status": "blocked", "repository": "terramike/xrpl-selectu5", "source_commit_S": args.source_commit,
                "request_url": f"https://github.com/terramike/xrpl-selectu5/archive/{args.source_commit}.zip",
                "production_fetcher_used": "selectu5.fetch_distribution", "reason": None}
    try:
        data = m.fetch_distribution(actual_entry)
        artifact.update({"status": "retrieved", "archive_bytes": len(data), "sha256_D": sha(data)})
        checks.append({"name": "actual production fetch", "kind": "actual_artifact", "status": "pass", "evidence": f"bytes={len(data)} sha256={sha(data)}"})
    except Exception as exc:
        artifact["reason"] = f"{type(exc).__name__}: {exc}"
        checks.append({"name": "actual production fetch", "kind": "actual_artifact", "status": "blocked", "evidence": artifact["reason"]})

    evidence = {
        "schema": "selectu5-qualification-evidence/1",
        "candidate": {"branch": "codex/selectu5-production-qualification", "source_commit_S": args.source_commit, "version": m.VERSION, "install_enabled": m.INSTALL_ENABLED},
        "disposable_root": root,
        "test_overrides": overrides,
        "artifact": artifact,
        "checks": checks,
        "known_limits": ["Actual update qualification is synthetic until two production-transport artifacts exist.", "Process interruption evidence does not prove power-loss durability.", "UNC roots are excluded until a native UNC pilot passes."],
    }
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    lines = ["# Selectu5 qualification harness output", "", f"Source commit S: `{args.source_commit}`", f"Disposable root: `{root}`", "", "| Check | Kind | Status |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['name']} | {c['kind']} | {c['status']} |")
    lines += ["", f"Actual artifact status: **{artifact['status']}**."]
    if artifact.get("reason"):
        lines.append(f"Reason: {artifact['reason']}")
    with open(args.output_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"root": root, "checks": len(checks), "artifact_status": artifact["status"]}))
    return 0 if all(c["status"] in ("pass", "blocked") for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
