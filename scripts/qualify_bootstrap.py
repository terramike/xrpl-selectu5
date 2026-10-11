"""Bootstrap qualification for the Selectu5 self-install path.

Uses the SHIPPED CLI from a candidate release ZIP (no gate injection, no
trust injection). The candidate client installs the real, published,
qualified predecessor artifact through its bundled catalog with
`--offline`, then a repeat run proves the no-op steady state. Every
identity is exact and recorded.

Run:
  python3 scripts/package.py --source-root . --inventory docs/production/package-inventory.json \\
      --out candidate.zip --record candidate-record.json
  python3 scripts/qualify_bootstrap.py --client-zip candidate.zip \\
      --candidate-record candidate-record.json \\
      --expect-client-version 0.2.6 --expect-client-root xrpl-selectu5-0.2.6 \\
      --expect-installed-version 0.2.5 --output-json bootstrap-evidence.json

Limits: a no-op returns before any network call (cmd_install checks
matching provenance before fetching). Zero fetches on the no-op path is
additionally proven by the synthetic harness with injected fetcher
counts on the same code path; this harness measures tree mutation and
the exact output contract instead.
"""
import argparse, hashlib, io, json, os, platform, re, subprocess, sys, tempfile, zipfile

REQUIRED_MEMBERS = ("scripts/selectu5.py", "registry/registry.json", "SKILL.md")

def sha(b):
    return hashlib.sha256(b).hexdigest()

class Check:
    def __init__(self):
        self.items = []
        self.partial_path = None
    def add(self, name, ok, detail, **extra):
        item = {"name": name, "status": "pass" if ok else "fail", "evidence": detail}
        item.update(extra)
        self.items.append(item)
        if self.partial_path:
            with open(self.partial_path, "w", encoding="utf-8") as fh:
                json.dump({"schema": "selectu5-bootstrap-evidence/1", "checks": self.items,
                           "all_pass": all(i["status"] == "pass" for i in self.items)},
                          fh, indent=2, sort_keys=True)
    def all_pass(self):
        return all(i["status"] == "pass" for i in self.items)

def tree_snapshot(root):
    snap = {}
    for dp, dns, fns in os.walk(root, followlinks=False):
        for name in sorted(dns + fns):
            path = os.path.join(dp, name)
            if not os.path.islink(path) and os.path.isfile(path):
                with open(path, "rb") as fh:
                    snap[os.path.relpath(path, root)] = sha(fh.read())
    return snap

def run_cli(client_scripts, args, env):
    proc = subprocess.run([sys.executable, os.path.join(client_scripts, "selectu5.py")] + args,
                          capture_output=True, text=True, env=env, timeout=180)
    return proc.returncode, proc.stdout, proc.stderr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-zip", required=True)
    ap.add_argument("--candidate-record", required=False, default=None)
    ap.add_argument("--expect-client-version", required=True)
    ap.add_argument("--expect-client-root", required=True)
    ap.add_argument("--expect-client-gate", required=True, choices=("True", "False"))
    ap.add_argument("--expect-installed-version", required=True)
    ap.add_argument("--expect-installed-gate", required=True, choices=("True", "False"))
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()
    checks = Check()
    checks.partial_path = args.output_json

    root = tempfile.mkdtemp(prefix="selectu5-bootstrap-")
    with open(args.client_zip, "rb") as fh:
        zip_bytes = fh.read()
    zip_digest = sha(zip_bytes)
    checks.add("candidate archive opens", bool(zip_bytes), f"bytes={len(zip_bytes)} sha256={zip_digest}",
               candidate_sha256=zip_digest, candidate_bytes=len(zip_bytes))
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        checks.add("candidate archive validates", False, f"BadZipFile: {exc}")
        return 1
    names = [n for n in zf.namelist() if not n.endswith("/")]
    roots = sorted({n.split("/")[0] for n in names})
    valid_structure = len(roots) == 1 and all(
        any(n == f"{roots[0]}/{req}" for n in names) for req in REQUIRED_MEMBERS)
    checks.add("candidate archive structure", valid_structure,
               f"roots={roots}; required members present={valid_structure}")
    if not valid_structure:
        return 1
    package_root = roots[0]
    checks.add("candidate package root exact", package_root == args.expect_client_root,
               f"root={package_root} expected={args.expect_client_root}")

    client_dir = os.path.join(root, "client")
    zf.extractall(client_dir)
    client_pkg = os.path.join(client_dir, package_root)
    client_scripts = os.path.join(client_pkg, "scripts")
    client_source = open(os.path.join(client_scripts, "selectu5.py"), encoding="utf-8").read()
    vmatch = re.search(r'^VERSION = "([^"]+)"', client_source, re.M)
    gmatch = re.search(r'^INSTALL_ENABLED = (True|False)', client_source, re.M)
    client_version = vmatch.group(1) if vmatch else None
    client_gate = gmatch.group(1) if gmatch else None
    checks.add("candidate client version exact", client_version == args.expect_client_version,
               f"VERSION={client_version} expected={args.expect_client_version}")
    checks.add("candidate client gate asserted", client_gate == args.expect_client_gate,
               f"INSTALL_ENABLED={client_gate} expected={args.expect_client_gate}")

    catalog = json.load(open(os.path.join(client_pkg, "registry", "registry.json"), encoding="utf-8"))
    entry = next(e for e in catalog["entries"] if e["id"] == "xrpl-selectu5")
    predecessor = {"version": entry["version"], "S": entry.get("ref"),
                   "D": entry.get("artifact_sha256"), "package_root": entry.get("package_root"),
                   "asset_url": (entry.get("distribution") or {}).get("asset_url")}
    complete = all(predecessor.values())
    checks.add("predecessor identity complete", complete, json.dumps(predecessor, sort_keys=True))
    checks.add("predecessor version exact", predecessor["version"] == args.expect_installed_version,
               f"{predecessor['version']} expected={args.expect_installed_version}")

    build_record = {}
    if args.candidate_record and os.path.exists(args.candidate_record):
        build_record = json.load(open(args.candidate_record, encoding="utf-8"))
    checks.add("candidate build class recorded", True,
               f"evidence_class={build_record.get('evidence_class', 'unknown')}; "
               f"development builds are not release-prep artifacts")
    try:
        qual_checkout = subprocess.run(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(os.path.abspath(__file__)),
                                       capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        qual_checkout = "unknown"
    checks.add("qualification checkout recorded", True,
               f"qual_checkout={qual_checkout} platform={platform.platform()} "
               f"python={platform.python_version()} client_zip_sha256={zip_digest}",
               qual_checkout=qual_checkout, platform=platform.platform(),
               python_version=platform.python_version())

    # Disposable skills root; dummy core explicitly bound via SELECTU5_CORE_DIR.
    skills = os.path.join(root, "skills")
    os.makedirs(skills)
    dummy_core = os.path.join(skills, "xrpl-muse-skill")
    os.makedirs(dummy_core)
    with open(os.path.join(dummy_core, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\ndescription: dummy core for bootstrap qualification\n"
                 "version: 0.14.1\n---\n")
    env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "SELECTU5_SKILLS_DIR": skills, "SELECTU5_CORE_DIR": dummy_core}
    checks.add("test environment controlled", True,
               f"env_keys={sorted(env)} dummy_core_bound={dummy_core}",
               env_keys=sorted(env))

    rc, out, err = run_cli(client_scripts, ["version"], env)
    checks.add("candidate client runs", rc == 0 and f"xrpl-selectu5 {args.expect_client_version}" in out,
               (out + err).strip()[-200:])

    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5"], env)
    m = re.search(r"plan digest \(sha256\): ([0-9a-f]{64})", out)
    dry_ok = rc == 0 and m and "does not prove a human approved it" in out
    checks.add("dry run shows plan and consent warning", dry_ok, (out + err).strip()[-300:])
    digest = m.group(1) if m else ""

    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5",
                                            "--yes", args.expect_installed_version, "--plan", digest], env)
    target = os.path.join(skills, "xrpl-selectu5")
    manifest = os.path.join(target, "SKILL.md")
    installed_version = None
    if os.path.exists(manifest):
        vm = re.search(r"^version: (.+)$", open(manifest, encoding="utf-8").read(), re.M)
        installed_version = vm.group(1).strip() if vm else None
    prov = {}
    meta_path = os.path.join(target, ".selectu5-meta.json")
    if os.path.exists(meta_path):
        prov = json.load(open(meta_path, encoding="utf-8"))
    prov_ok = (prov.get("version") == predecessor["version"] and prov.get("commit") == predecessor["S"]
               and prov.get("artifact_sha256") == predecessor["D"])
    checks.add("bootstrap installs published predecessor via shipped CLI",
               rc == 0 and installed_version == args.expect_installed_version and prov_ok,
               (out + err).strip()[-300:], installed_version=installed_version, provenance_matches=prov_ok)

    pred_source = open(os.path.join(target, "scripts", "selectu5.py"), encoding="utf-8").read()
    pred_gate = re.search(r'^INSTALL_ENABLED = (True|False)', pred_source, re.M)
    pred_gate = pred_gate.group(1) if pred_gate else None
    checks.add("installed predecessor gate asserted", pred_gate == args.expect_installed_gate,
               f"installed INSTALL_ENABLED={pred_gate} expected={args.expect_installed_gate}",
               installed_gate=pred_gate)

    tree_before = tree_snapshot(target)
    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5",
                                            "--yes", args.expect_installed_version, "--plan", digest], env)
    tree_after = tree_snapshot(target)
    noop_ok = (rc == 0 and "already installed" in out and tree_before == tree_after and len(tree_before) > 0)
    checks.add("repeat install is a zero-mutation no-op", noop_ok,
               (out + err).strip()[-200:], tree_files=len(tree_after),
               note="no-op returns before any fetch when provenance matches; zero fetches on this "
                    "code path are additionally proven by the synthetic harness fetcher counts")

    evidence = {"schema": "selectu5-bootstrap-evidence/1", "disposable_root": root,
                "client_zip_sha256": zip_digest, "client_package_root": package_root,
                "client_version": client_version, "client_gate": client_gate,
                "predecessor": predecessor, "qual_checkout": qual_checkout,
                "platform": platform.platform(), "python_version": platform.python_version(),
                "checks": checks.items,
                "chain_rule": "Each release bundles its predecessor's qualified catalog record; "
                              "an installed client can install exactly the versions its bundled catalog authorizes."}
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    print(json.dumps({"root": root, "checks": len(checks.items), "all_pass": checks.all_pass()}, indent=2))
    return 0 if checks.all_pass() else 1

if __name__ == "__main__":
    raise SystemExit(main())
