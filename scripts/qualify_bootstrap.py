"""Bootstrap qualification for the Selectu5 self-install path.

Uses the SHIPPED CLI from a candidate release ZIP (no gate injection, no
trust injection). The candidate client installs the real, published,
qualified predecessor artifact through its bundled catalog with
`--offline`, then a repeat run proves the no-op steady state. The
installed predecessor's own gate state is inspected and recorded: a
release cannot record its own digest, so each release bundles its
predecessor's qualified record, and the self-update chain advances one
published release at a time (see BOOTSTRAP-AND-UPDATE.md).

Run:
  python3 scripts/package.py --source-dir <export> --output /tmp/cand/xrpl-selectu5-0.2.6.zip
  python3 scripts/qualify_bootstrap.py --client-zip /tmp/cand/xrpl-selectu5-0.2.6.zip \
      --expect-install-version 0.2.5 --output-json /tmp/bootstrap-evidence.json
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, zipfile

def sha(b):
    return hashlib.sha256(b).hexdigest()

def run_cli(client_scripts, args, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    proc = subprocess.run([sys.executable, os.path.join(client_scripts, "selectu5.py")] + args,
                          capture_output=True, text=True, env=env, timeout=120)
    return proc.returncode, proc.stdout, proc.stderr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-zip", required=True)
    ap.add_argument("--expect-install-version", required=True)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    root = tempfile.mkdtemp(prefix="selectu5-bootstrap-")
    client_dir = os.path.join(root, "client")
    with zipfile.ZipFile(args.client_zip) as zf:
        names = zf.namelist()
        roots = {n.split("/")[0] for n in names if n.strip("/")}
        zf.extractall(client_dir)
    root_name = sorted(roots)[0]
    client_pkg = os.path.join(client_dir, root_name)
    client_scripts = os.path.join(client_pkg, "scripts")

    # Disposable dummy core inside the skills root, exactly where a real
    # user's core skill lives (the CLI reads its public manifest version).
    skills = os.path.join(root, "skills")
    dummy_core = os.path.join(skills, "xrpl-muse-skill")
    os.makedirs(dummy_core)
    with open(os.path.join(dummy_core, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: xrpl-muse-skill\ndescription: dummy core for bootstrap qualification\nversion: 0.14.1\n---\n")
    env = {"SELECTU5_SKILLS_DIR": skills}

    checks = []
    def add(name, ok, detail, **extra):
        item = {"name": name, "status": "pass" if ok else "fail", "evidence": detail}
        item.update(extra)
        checks.append(item)

    rc, out, err = run_cli(client_scripts, ["version"], env)
    add("candidate client runs", rc == 0 and out.strip().startswith("xrpl-selectu5"), (out + err).strip()[-200:])

    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5"], env)
    m = re.search(r"plan digest \(sha256\): ([0-9a-f]{64})", out)
    dry_ok = rc == 0 and m and "does not prove a human approved it" in out
    add("dry run shows plan and consent warning", dry_ok, (out + err).strip()[-300:])
    digest = m.group(1) if m else ""

    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5",
                                            "--yes", args.expect_install_version, "--plan", digest], env)
    target = os.path.join(skills, "xrpl-selectu5")
    manifest = os.path.join(target, "SKILL.md")
    installed_version = None
    if os.path.exists(manifest):
        vm = re.search(r"^version: (.+)$", open(manifest, encoding="utf-8").read(), re.M)
        installed_version = vm.group(1).strip() if vm else None
    add("bootstrap installs qualified predecessor via shipped CLI",
        rc == 0 and installed_version == args.expect_install_version,
        (out + err).strip()[-300:], installed_version=installed_version)

    # Installed predecessor's shipped gate state (its own code, inspected).
    pred_scripts = os.path.join(target, "scripts", "selectu5.py")
    pred_gate = None
    if os.path.exists(pred_scripts):
        gm = re.search(r"^INSTALL_ENABLED = (True|False)", open(pred_scripts, encoding="utf-8").read(), re.M)
        pred_gate = gm.group(1) if gm else None
    add("installed predecessor gate state recorded", pred_gate is not None,
        f"INSTALL_ENABLED in installed {args.expect_install_version} artifact: {pred_gate}",
        installed_gate=pred_gate)

    rc, out, err = run_cli(client_scripts, ["--offline", "install", "xrpl-selectu5",
                                            "--yes", args.expect_install_version, "--plan", digest], env)
    add("repeat install is a no-op", rc == 0 and "already installed" in out, (out + err).strip()[-200:])

    evidence = {"schema": "selectu5-bootstrap-evidence/1", "disposable_root": root,
                "client_zip": args.client_zip, "client_package_root": root_name,
                "expect_install_version": args.expect_install_version,
                "checks": checks,
                "chain_rule": "Each release bundles its predecessor's qualified catalog record; "
                              "an installed client can install exactly the versions its bundled catalog authorizes."}
    with open(args.output_json, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
    print(json.dumps({"root": root, "checks": len(checks),
                      "all_pass": all(c["status"] == "pass" for c in checks)}, indent=2))
    return 0 if all(c["status"] == "pass" for c in checks) else 1

if __name__ == "__main__":
    raise SystemExit(main())
