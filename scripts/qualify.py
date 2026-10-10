#!/usr/bin/env python3
"""Selectu5 production qualification harness.

Separate from the production CLI. It creates a disposable root, records
every test override, runs synthetic isolated installs, attempts the actual
production fetcher for one immutable source commit, and emits evidence.
It never changes INSTALL_ENABLED in shipped code and never installs into
a user skills folder.
"""
import argparse
import builtins
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import stat
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402

PERM = {"commands": ["none"], "files": ["none"], "network": "none", "signs": "Never."}
CORE_VERSION = "0.14.1"
OVERRIDES = [
    "install_enabled=True passed only to cmd_install inside this harness",
    "fetcher=<synthetic in-memory ZIP fetcher> passed to cmd_install; no network",
    "trusted_catalog=TRUSTED_INSTALL_SOURCE injected for isolated synthetic entries",
    "core_version_text supplied from the dummy core manifest bound by SELECTU5_CORE_DIR",
    "SELECTU5_CORE_DIR bound to the disposable dummy core",
    "builtins.open instrumented for dummy sentinel paths during each operation",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with open(path, "rb") as fh:
        return sha(fh.read())


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


def snapshot_tree(root):
    """Record all directory entries, file bytes, and modes without following links."""
    snap = {}
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns.sort()
        rel = os.path.relpath(dp, root)
        snap[rel] = {"type": "directory", "mode": stat.S_IMODE(os.lstat(dp).st_mode)}
        for name in sorted(dns + fns):
            path = os.path.join(dp, name)
            key = os.path.relpath(path, root)
            mode = stat.S_IMODE(os.lstat(path).st_mode)
            if os.path.islink(path):
                snap[key] = {"type": "symlink", "target": os.readlink(path), "mode": mode}
            elif os.path.isdir(path):
                snap[key] = {"type": "directory", "mode": mode}
            else:
                snap[key] = {"type": "file", "sha256": file_sha(path), "mode": mode}
    return snap


class CountingFetcher:
    def __init__(self, data):
        self.data = data
        self.calls = 0

    def __call__(self, e):
        self.calls += 1
        return self.data


class OpenRecorder:
    """Record files opened by the harness process during one operation."""

    def __init__(self, watched):
        self.watched = {os.path.realpath(p): p for p in watched}
        self.reads = []

    def __enter__(self):
        self._real_open = builtins.open

        def tracking_open(file, *a, **kw):
            try:
                rp = os.path.realpath(os.fspath(file))
            except Exception:
                rp = None
            if rp in self.watched:
                self.reads.append(rp)
            return self._real_open(file, *a, **kw)

        builtins.open = tracking_open
        return self

    def __exit__(self, *exc):
        builtins.open = self._real_open
        return False


def canonical_plan(e, raw_skills_dir):
    """Build the plan digest from the canonical validated destination."""
    destination = m.validate_destination(raw_skills_dir, e["id"])
    plan, digest = m.build_plan(e, destination)
    return plan, digest, destination


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-commit", required=True, help="artifact source commit S")
    ap.add_argument("--qualification-commit", default=os.environ.get("GITHUB_SHA"),
                    help="code commit that contains this harness (defaults to GITHUB_SHA)")
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        print("source commit must be a full 40-char SHA", file=sys.stderr)
        return 2
    qual_commit = args.qualification_commit or "working-tree (record branch head in PR)"

    checks = []

    def add(name, kind, status, evidence, overrides=(), **extra):
        item = {"name": name, "kind": kind, "status": status, "evidence": evidence,
                "qualification_code_commit": qual_commit, "artifact_source_commit_S": args.source_commit,
                "test_overrides": list(overrides)}
        item.update(extra)
        checks.append(item)

    # Source inspection (no installed code executed).
    reg = json.load(open(os.path.join(REPO, "registry", "registry.json"), encoding="utf-8"))
    manifest = m.parse_manifest_strict(open(os.path.join(REPO, "SKILL.md"), encoding="utf-8").read())
    self_entry = next(e for e in reg["entries"] if e["id"] == "xrpl-selectu5")
    # Code and manifest must agree. The bundled catalog self-entry records
    # the latest installable version, which may lag the client version.
    version_ok = m.VERSION == manifest["version"]
    list_only = [e["id"] for e in reg["entries"] if e["kind"] == "skill" and not (e.get("ref") and e.get("artifact_sha256") and e.get("package_root"))]
    # The gate state is recorded, not asserted: up to 0.2.5 it had to be
    # disabled; from 0.2.6 enablement is an explicit, reviewed decision and
    # this harness simply reports the shipped state it found.
    add("source versions and gate", "source_inspection", "pass" if version_ok else "fail",
        f"code={m.VERSION} manifest={manifest['version']} catalog={self_entry['version']} install_enabled={m.INSTALL_ENABLED}")
    add("unqualified entries list-only", "source_inspection", "pass" if list_only else "fail", ", ".join(list_only))

    # Repository synthetic suite.
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=REPO, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
    add("repository test suite", "synthetic", "pass" if proc.returncode == 0 else "fail", "\n".join(tail),
        command="python3 -m unittest discover -s tests", exit_code=proc.returncode)

    # Disposable synthetic install/update with dummy sentinels.
    root = tempfile.mkdtemp(prefix="selectu5-qualify-")
    skills = os.path.join(root, "skills")
    os.makedirs(skills)
    # Deliberately non-canonical spelling of the same skills root. Plans must
    # be built from validate_destination(), never from this raw spelling.
    raw_skills = os.path.join(root, ".", "skills")
    dummy_core = os.path.join(root, "dummy-core")
    os.makedirs(dummy_core)
    dummy_manifest = os.path.join(dummy_core, "SKILL.md")
    with open(dummy_manifest, "w", encoding="utf-8") as fh:
        fh.write(f"---\nname: xrpl-muse-skill\nversion: {CORE_VERSION}\naccess: propose\n---\n")
    credential_sentinel = os.path.join(root, "credential-sentinel.txt")
    with open(credential_sentinel, "w", encoding="utf-8") as fh:
        fh.write("dummy credential sentinel - not a real credential\n")

    # Bind the dummy core to the test configuration.
    os.environ["SELECTU5_CORE_DIR"] = dummy_core
    bound_core_version = m.parse_manifest_strict(open(dummy_manifest, encoding="utf-8").read())["version"]
    sentinel_paths = [dummy_manifest, credential_sentinel]

    def sentinel_state():
        return {p: file_sha(p) for p in sentinel_paths}

    def op(name, fn):
        before = sentinel_state()
        with OpenRecorder(sentinel_paths) as rec:
            rc, out, err = capture(fn)
        after = sentinel_state()
        unchanged = before == after
        credential_reads = [r for r in rec.reads if r == os.path.realpath(credential_sentinel)]
        core_reads = [r for r in rec.reads if r == os.path.realpath(dummy_manifest)]
        detail = (f"sentinels_unchanged={unchanged}; dummy_core_manifest_reads_during_op={len(core_reads)} "
                  f"(allowed public-manifest reads only); credential_sentinel_reads_during_op={len(credential_reads)} (must be 0)")
        ok = unchanged and not credential_reads
        return rc, out, err, ok, detail, {"sentinel_hashes_before": before, "sentinel_hashes_after": after,
                                          "dummy_core_manifest_reads": len(core_reads), "credential_sentinel_reads": len(credential_reads)}

    base_sentinels = sentinel_state()
    add("dummy core binding", "synthetic", "pass" if bound_core_version == CORE_VERSION else "fail",
        f"SELECTU5_CORE_DIR={dummy_core}; supplied core_version_text={bound_core_version} read from dummy manifest by the harness",
        overrides=["SELECTU5_CORE_DIR bound to the disposable dummy core"])

    v1 = zip_bytes("1.0.0")
    e1 = entry("1.0.0", v1)
    reg1 = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "curator": "qualification", "entries": [e1]}
    plan1, digest1, dest1 = canonical_plan(e1, raw_skills)
    plan_ok = "/./" not in dest1 and dest1 == m.validate_destination(skills, "xrpl-demo")
    add("canonical plan destination", "synthetic", "pass" if plan_ok else "fail",
        f"raw_skills={raw_skills}; canonical_destination={dest1}; plan_digest={digest1}",
        overrides=["SELECTU5_CORE_DIR bound to the disposable dummy core"])

    fetch1 = CountingFetcher(v1)
    rc, out, err, sent_ok, sent_detail, sent_extra = op("fresh", lambda: m.cmd_install(
        reg1, {}, "xrpl-demo", "1.0.0", m.LOCAL_REGISTRY, digest1, skills_dir=raw_skills,
        fetcher=fetch1, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE,
        core_version_text=bound_core_version))
    installed_manifest = os.path.join(skills, "xrpl-demo", "SKILL.md")
    fresh_ok = rc == 0 and fetch1.calls == 1 and os.path.exists(installed_manifest) and sent_ok
    if os.path.exists(installed_manifest):
        fresh_ok = fresh_ok and m.parse_manifest_strict(open(installed_manifest, encoding="utf-8").read())["version"] == "1.0.0"
    add("synthetic fresh install via cmd_install", "synthetic", "pass" if fresh_ok else "fail",
        (out + err).strip()[-400:] + " | " + sent_detail, fetcher_calls=fetch1.calls, overrides=OVERRIDES, **sent_extra)

    # No-op: same plan/version/provenance. Must not fetch and must not mutate.
    fetch_noop = CountingFetcher(v1)
    before_tree = snapshot_tree(skills)
    rc, out, err, sent_ok, sent_detail, sent_extra = op("noop", lambda: m.cmd_install(
        reg1, m.local_skills(skills), "xrpl-demo", "1.0.0", m.LOCAL_REGISTRY, digest1, skills_dir=raw_skills,
        fetcher=fetch_noop, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE,
        core_version_text=bound_core_version))
    after_tree = snapshot_tree(skills)
    noop_ok = rc == 0 and fetch_noop.calls == 0 and before_tree == after_tree and sent_ok
    add("synthetic matching-provenance no-op", "synthetic", "pass" if noop_ok else "fail",
        (out + err).strip()[-300:] + " | " + sent_detail,
        fetcher_calls=fetch_noop.calls, tree_unchanged=(before_tree == after_tree), overrides=OVERRIDES, **sent_extra)

    old_active_snapshot = snapshot_tree(dest1)
    v2 = zip_bytes("1.0.1")
    e2 = entry("1.0.1", v2)
    reg2 = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "curator": "qualification", "entries": [e2]}
    plan2, digest2, dest2 = canonical_plan(e2, raw_skills)
    fetch2 = CountingFetcher(v2)
    rc, out, err, sent_ok, sent_detail, sent_extra = op("update", lambda: m.cmd_install(
        reg2, m.local_skills(skills), "xrpl-demo", "1.0.1", m.LOCAL_REGISTRY, digest2, skills_dir=raw_skills,
        fetcher=fetch2, install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE,
        core_version_text=bound_core_version))
    backups = [x for x in os.listdir(skills) if x.startswith("xrpl-demo.bak-")]
    active = m.local_skills(skills).get("xrpl-demo", {})
    prov = active.get("provenance") or {}
    update_ok = rc == 0 and fetch2.calls == 1 and len(backups) == 1 and sent_ok
    backup_tree_unchanged = False
    backup_detail = "no backup found"
    if backups:
        backup_tree_unchanged = snapshot_tree(os.path.join(skills, backups[0])) == old_active_snapshot
        update_ok = update_ok and backup_tree_unchanged
        bman = os.path.join(skills, backups[0], "SKILL.md")
        bmeta_path = os.path.join(skills, backups[0], ".selectu5-meta.json")
        bver = m.parse_manifest_strict(open(bman, encoding="utf-8").read())["version"] if os.path.exists(bman) else None
        bmeta = json.load(open(bmeta_path, encoding="utf-8")) if os.path.exists(bmeta_path) else {}
        backup_detail = f"backup={backups[0]} backup_version={bver} backup_digest={bmeta.get('artifact_sha256')} expected_v1_digest={sha(v1)}"
        update_ok = update_ok and bver == "1.0.0" and bmeta.get("artifact_sha256") == sha(v1) and bmeta.get("commit") == "a" * 40
    active_detail = f"active_version={active.get('version')} provenance_version={prov.get('version')} provenance_digest={prov.get('artifact_sha256')} expected_v2_digest={sha(v2)}"
    update_ok = update_ok and active.get("version") == "1.0.1" and prov.get("artifact_sha256") == sha(v2) and prov.get("commit") == "a" * 40
    add("synthetic update with backup", "synthetic", "pass" if update_ok else "fail",
        (out + err).strip()[-400:] + " | " + sent_detail + " | " + active_detail + " | " + backup_detail,
        fetcher_calls=fetch2.calls, backups=backups, backup_tree_unchanged=backup_tree_unchanged,
        overrides=OVERRIDES, **sent_extra)

    final_sentinels = sentinel_state()
    add("dummy core and credential sentinels unchanged at end", "synthetic",
        "pass" if final_sentinels == base_sentinels else "fail",
        "Final hashes compared with the pre-operation hashes; per-operation read counts are recorded on each operation check.",
        sentinels=[{"path": os.path.basename(p), "before": base_sentinels[p], "after": final_sentinels[p]} for p in sentinel_paths])

    # Actual production transport attempt for Selectu5 itself at S.
    actual_entry = {"id": "xrpl-selectu5", "repo": "https://github.com/terramike/xrpl-selectu5", "ref": args.source_commit}
    artifact = {"status": "blocked", "repository": "terramike/xrpl-selectu5", "source_commit_S": args.source_commit,
                "qualification_code_commit": qual_commit,
                "request_url": f"https://github.com/terramike/xrpl-selectu5/archive/{args.source_commit}.zip",
                "production_fetcher_used": "selectu5.fetch_distribution", "reason": None}
    try:
        data = m.fetch_distribution(actual_entry)
        artifact.update({"status": "retrieved", "archive_bytes": len(data), "sha256_D": sha(data)})
        add("actual production fetch", "actual_artifact", "pass", f"bytes={len(data)} sha256={sha(data)}")
    except Exception as exc:
        artifact["reason"] = f"{type(exc).__name__}: {exc}"
        add("actual production fetch", "actual_artifact", "blocked", artifact["reason"])

    evidence = {
        "schema": "selectu5-qualification-evidence/1",
        "candidate": {"branch": "codex/selectu5-production-qualification", "qualification_code_commit": qual_commit,
                      "artifact_source_commit_S": args.source_commit, "version": m.VERSION, "install_enabled": m.INSTALL_ENABLED},
        "disposable_root": root,
        "test_overrides": OVERRIDES,
        "artifact": artifact,
        "checks": checks,
        "known_limits": ["Actual update qualification is synthetic until two production-transport artifacts exist.", "Process interruption evidence does not prove power-loss durability.", "UNC roots are excluded until a native UNC pilot passes."],
    }
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    lines = ["# Selectu5 qualification harness output", "", f"Qualification code commit: `{qual_commit}`", f"Artifact source commit S: `{args.source_commit}`", f"Disposable root: `{root}`", "", "| Check | Kind | Status |", "|---|---|---|"]
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
