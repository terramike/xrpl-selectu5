#!/usr/bin/env python3
"""Stage 3 actual-artifact qualification harness.

Retrieves the reviewed release asset through the production fetcher and
exercises fresh installation and no-op against that exact artifact in a
disposable root. Synthetic fetchers are never used for the actual checks.
Every override is recorded. The shipped INSTALL_ENABLED flag is never
changed; a gate override is passed only to cmd_install inside this
harness and does not establish human consent.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import selectu5 as m  # noqa: E402

OVERRIDES = [
    "install_enabled=True passed only to cmd_install inside this harness",
    "fetcher wraps selectu5.fetch_distribution (production transport) with a call counter",
    "trusted_catalog=TRUSTED_INSTALL_SOURCE injected for the local qualification catalog",
    "core_version_text supplied from the dummy core manifest bound by SELECTU5_CORE_DIR",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with open(path, "rb") as fh:
        return sha(fh.read())


def snapshot_key(path, root):
    """Normalize a snapshot key to forward slashes so it can be compared
    with ZIP member names on every platform (Windows os.path uses \\)."""
    rel = os.path.relpath(path, root)
    return rel.replace(os.sep, "/").replace("\\", "/")


def snapshot_tree(root):
    snap = {}
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            snap[snapshot_key(p, root)] = file_sha(p)
    return snap


def tree_diff(expected, actual):
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatched = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
    return missing, unexpected, mismatched


def capture(fn):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn()
    return rc, out.getvalue(), err.getvalue()


def trace_redirects(url):
    """Record the redirect chain as host+path only (no query strings)."""
    chain = []

    class Recorder(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            p = urllib.parse.urlparse(newurl)
            chain.append(f"{p.hostname}{p.path}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(Recorder())
    req = urllib.request.Request(url, headers={"User-Agent": "selectu5-stage3-trace"})
    try:
        with opener.open(req, timeout=30) as resp:
            resp.read()
            p = urllib.parse.urlparse(resp.geturl())
            chain.append(f"{p.hostname}{p.path}")
    except Exception as exc:
        chain.append(f"ERROR {type(exc).__name__}: {exc}")
    return chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-commit", required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--asset-url", required=True)
    ap.add_argument("--package-root", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--entry-id", default="xrpl-selectu5")
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-md", required=True)
    args = ap.parse_args()

    checks = []

    def add(name, kind, status, evidence, **extra):
        item = {"name": name, "kind": kind, "status": status, "evidence": evidence,
                "artifact_source_commit_S": args.source_commit, "test_overrides": OVERRIDES if kind != "source_inspection" else []}
        item.update(extra)
        checks.append(item)

    # Build the local qualification catalog entry from the bundled entry.
    reg = json.load(open(os.path.join(REPO, "registry", "registry.json"), encoding="utf-8"))
    base = next(e for e in reg["entries"] if e["id"] == args.entry_id)
    e = dict(base)
    e.update({"version": args.version, "ref": args.source_commit, "artifact_sha256": args.sha256,
              "package_root": args.package_root,
              "distribution": {"type": "github_release_asset", "source_commit": args.source_commit,
                               "asset_url": args.asset_url, "asset_name": args.asset_url.rstrip("/").rsplit("/", 1)[-1]}})
    qreg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "stage3-qualification", "entries": [e]}
    try:
        m.validate_registry(qreg)
        add("qualification catalog validates", "source_inspection", "pass", f"entry {e['id']} {e['version']} with distribution {args.asset_url}")
    except Exception as exc:
        add("qualification catalog validates", "source_inspection", "fail", str(exc))

    # Actual retrieval through the production fetcher.
    chain = trace_redirects(args.asset_url)
    try:
        data = m.fetch_distribution(e)
        ok = sha(data) == args.sha256
        add("actual production retrieval", "actual_artifact", "pass" if ok else "fail",
            f"bytes={len(data)} sha256={sha(data)} expected={args.sha256}", redirect_chain=chain, archive_bytes=len(data))
    except Exception as exc:
        add("actual production retrieval", "actual_artifact", "blocked", f"{type(exc).__name__}: {exc}", redirect_chain=chain)
        data = None

    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump({"schema": "selectu5-stage3-evidence/1", "partial": True, "checks": checks}, fh, indent=2)

    # Disposable environment with bound dummy core and credential sentinel.
    root = tempfile.mkdtemp(prefix="selectu5-stage3-")
    skills = os.path.join(root, "skills"); os.makedirs(skills)
    dummy_core = os.path.join(root, "dummy-core"); os.makedirs(dummy_core)
    dummy_manifest = os.path.join(dummy_core, "SKILL.md")
    with open(dummy_manifest, "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\nversion: 0.14.1\naccess: propose\n---\n")
    sentinel = os.path.join(root, "credential-sentinel.txt")
    with open(sentinel, "w", encoding="utf-8") as fh:
        fh.write("dummy credential sentinel - not a real credential\n")
    os.environ["SELECTU5_CORE_DIR"] = dummy_core
    core_text = m.parse_manifest_strict(open(dummy_manifest, encoding="utf-8").read())["version"]
    sentinels = {p: file_sha(p) for p in (dummy_manifest, sentinel)}

    def sentinels_ok():
        return all(file_sha(p) == h for p, h in sentinels.items())

    class ProdFetcher:
        def __init__(self):
            self.calls = 0

        def __call__(self, entry):
            self.calls += 1
            return m.fetch_distribution(entry)

    plan, digest = None, None
    dest = m.validate_destination(skills, e["id"])
    plan, digest = m.build_plan(e, dest)

    # Fresh installation with the actual artifact.
    fetch1 = ProdFetcher()
    rc, out, err = capture(lambda: m.cmd_install(qreg, {}, e["id"], args.version, m.LOCAL_REGISTRY, digest,
                                                 skills_dir=skills, fetcher=fetch1, install_enabled=True,
                                                 trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    target = os.path.join(skills, e["id"])
    tree_ok, tree_detail = False, "target missing"
    if data is not None and os.path.isdir(target):
        expected = {}
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if not info.is_dir():
                    expected[info.filename[len(args.package_root) + 1:]] = sha(zf.read(info.filename))
        actual = snapshot_tree(target)
        actual.pop(".selectu5-meta.json", None)
        missing, unexpected, mismatched = tree_diff(expected, actual)
        tree_ok = not (missing or unexpected or mismatched)
        tree_detail = (f"package files={len(expected)} installed files={len(actual)} match={tree_ok} "
                       f"missing={missing} unexpected={unexpected} hash_mismatched={mismatched}")
    prov = {}
    meta_path = os.path.join(target, ".selectu5-meta.json")
    if os.path.exists(meta_path):
        prov = json.load(open(meta_path, encoding="utf-8"))
    prov_ok = prov.get("artifact_sha256") == args.sha256 and prov.get("commit") == args.source_commit and prov.get("version") == args.version
    add("actual fresh installation", "actual_artifact", "pass" if (rc == 0 and tree_ok and prov_ok and sentinels_ok()) else "fail",
        (out + err).strip()[-300:] + f" | fetcher_calls={fetch1.calls} | {tree_detail} | provenance={prov}", fetcher_calls=fetch1.calls)

    # Same-version no-op: zero fetches, zero mutation.
    fetch2 = ProdFetcher()
    before = snapshot_tree(skills)
    rc, out, err = capture(lambda: m.cmd_install(qreg, m.local_skills(skills), e["id"], args.version, m.LOCAL_REGISTRY, digest,
                                                 skills_dir=skills, fetcher=fetch2, install_enabled=True,
                                                 trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    noop_ok = rc == 0 and fetch2.calls == 0 and snapshot_tree(skills) == before and sentinels_ok()
    add("actual same-version no-op", "actual_artifact", "pass" if noop_ok else "fail",
        (out + err).strip()[-250:] + f" | fetcher_calls={fetch2.calls} | tree_unchanged={snapshot_tree(skills) == before}", fetcher_calls=fetch2.calls)

    # Rejected requests: wrong version, wrong plan, wrong digest, bad core.
    fetch3 = ProdFetcher()
    rc_wrong_version, _, _ = capture(lambda: m.cmd_install(qreg, m.local_skills(skills), e["id"], "9.9.9", m.LOCAL_REGISTRY, digest,
                                                           skills_dir=skills, fetcher=fetch3, install_enabled=True,
                                                           trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    rc_wrong_plan, _, _ = capture(lambda: m.cmd_install(qreg, m.local_skills(skills), e["id"], args.version, m.LOCAL_REGISTRY, "0" * 64,
                                                        skills_dir=skills, fetcher=fetch3, install_enabled=True,
                                                        trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    bad = dict(e); bad["artifact_sha256"] = "0" * 64
    bad_reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "stage3-qualification", "entries": [bad]}
    bad_skills = os.path.join(root, "skills-bad")
    bad_dest = m.validate_destination(bad_skills, e["id"])
    bad_plan, bad_digest = m.build_plan(bad, bad_dest)
    fetch_bad = ProdFetcher()
    rc_bad_digest, _, err_bad = capture(lambda: m.cmd_install(bad_reg, {}, e["id"], args.version, m.LOCAL_REGISTRY, bad_digest,
                                                              skills_dir=bad_skills, fetcher=fetch_bad, install_enabled=True,
                                                              trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    bad_target_absent = not os.path.exists(os.path.join(bad_skills, e["id"]))
    badcore = dict(e); badcore["core_version"] = ">=99.0.0"
    bc_reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "stage3-qualification", "entries": [badcore]}
    bc_plan, bc_digest = m.build_plan(badcore, dest)
    fetch_bc = ProdFetcher()
    rc_bad_core, _, _ = capture(lambda: m.cmd_install(bc_reg, m.local_skills(skills), e["id"], args.version, m.LOCAL_REGISTRY, bc_digest,
                                                      skills_dir=skills, fetcher=fetch_bc, install_enabled=True,
                                                      trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
    rejected_ok = (rc_wrong_version == 1 and rc_wrong_plan == 1 and rc_bad_digest == 1 and rc_bad_core == 1
                    and fetch3.calls == 0 and fetch_bc.calls == 0 and fetch_bad.calls >= 1 and bad_target_absent
                    and "digest" in err_bad.lower()
                    and snapshot_tree(skills) == before and sentinels_ok())
    add("actual rejected requests", "actual_artifact", "pass" if rejected_ok else "fail",
        f"wrong_version rc={rc_wrong_version}, wrong_plan rc={rc_wrong_plan}, wrong_digest rc={rc_bad_digest} (fetches={fetch_bad.calls}, target_absent={bad_target_absent}, reason={err_bad.strip()[-120:]}), bad_core rc={rc_bad_core} (fetches={fetch_bc.calls}); active tree unchanged={snapshot_tree(skills) == before}")

    # Lock contention: hold a fresh root's lock and confirm the install is
    # refused there, while the already-qualified tree stays coherent.
    fetch4 = ProdFetcher()
    locked_root = os.path.join(root, "skills-locked"); os.makedirs(locked_root)
    locked_dest = m.validate_destination(locked_root, e["id"])
    _, locked_digest = m.build_plan(e, locked_dest)
    try:
        with m.skills_lock(locked_root):
            rc_lock, out_lock, err_lock = capture(lambda: m.cmd_install(qreg, {}, e["id"], args.version, m.LOCAL_REGISTRY, locked_digest,
                                                                        skills_dir=locked_root, fetcher=fetch4, install_enabled=True,
                                                                        trusted_catalog=m.TRUSTED_INSTALL_SOURCE, core_version_text=core_text))
        lock_ok = (rc_lock == 1 and "lock" in (out_lock + err_lock).lower()
                   and not os.path.exists(os.path.join(locked_root, e["id"])) and snapshot_tree(skills) == before and sentinels_ok())
        lock_ev = (out_lock + err_lock).strip()[-250:]
    except Exception as exc:
        lock_ok, lock_ev = False, f"{type(exc).__name__}: {exc}"
    add("actual lock contention refusal", "actual_artifact", "pass" if lock_ok else "fail", lock_ev + f" | fetcher_calls={fetch4.calls}")

    evidence = {"schema": "selectu5-stage3-evidence/1",
                "artifact": {"id": args.entry_id, "version": args.version, "source_commit_S": args.source_commit,
                             "sha256_D": args.sha256, "asset_url": args.asset_url, "package_root": args.package_root},
                "disposable_root": root, "test_overrides": OVERRIDES, "checks": checks,
                "known_limits": ["Actual update qualification needs a second distinct reviewed artifact.", "Windows actual-artifact run is executed by CI on the qualification branch.", "Interruption/recovery is covered by the repository suite; the actual-artifact interruption run is recorded separately when executed."]}
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    lines = ["# Selectu5 Stage 3 actual-artifact qualification", "",
             f"Artifact: `{args.entry_id}` {args.version} from S `{args.source_commit}`", f"SHA-256 D: `{args.sha256}`", "",
             "| Check | Kind | Status |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['name']} | {c['kind']} | {c['status']} |")
    with open(args.output_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps({"root": root, "checks": len(checks), "statuses": [c["status"] for c in checks]}))
    return 0 if all(c["status"] == "pass" for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
