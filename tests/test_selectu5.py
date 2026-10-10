import io, json, os, subprocess, sys, tempfile, unittest, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..")
SCRIPT = os.path.join(SKILL, "scripts", "selectu5.py")
LOCAL_REG = os.path.join(SKILL, "registry", "registry.json")

def run(*args, env=None):
    e = dict(os.environ)
    e["SELECTU5_REGISTRY"] = LOCAL_REG
    e.update(env or {})
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e)

def make_zip(path, files, top="pkg-abc"):
    with zipfile.ZipFile(path, "w") as z:
        for rel, body in files.items():
            z.writestr(f"{top}/{rel}", body)

def reg_with(tmp, entries):
    reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "curator": "test", "entries": entries}
    p = os.path.join(tmp, "registry.json"); json.dump(reg, open(p, "w")); return p

PERM = {"commands": ["none"], "files": ["none"], "network": "none", "signs": "Never."}
def entry(eid, version, kind="skill", ref=None, archive=None):
    e = {"id": eid, "name": eid, "kind": kind, "version": version, "core_version": None,
         "access": "read", "author": "test", "purpose": "test entry",
         "repo": "https://example.invalid/repo", "install": "test", "permissions": PERM, "ref": ref}
    if archive: e["archive"] = archive
    return e

class TestSelectu5(unittest.TestCase):
    def test_version(self):
        r = run("version"); self.assertEqual(r.returncode, 0); self.assertIn("0.2.0", r.stdout)

    def test_list_has_seed_entries(self):
        r = run("list"); self.assertEqual(r.returncode, 0)
        for needle in ("xrpl-community-shows", "clavi5", "visu5", "xrpl-selectu5 0.2.0"):
            self.assertIn(needle, r.stdout)

    def test_show_permissions_card(self):
        r = run("show", "xrpl-view-export"); self.assertEqual(r.returncode, 0)
        self.assertIn("permissions:", r.stdout); self.assertIn("signs: Never.", r.stdout)

    def test_show_unknown_fails(self):
        r = run("show", "nope"); self.assertEqual(r.returncode, 1)

    def test_showcase_install_is_not_an_install(self):
        r = run("install", "clavi5"); self.assertEqual(r.returncode, 0)
        self.assertIn("not an install", r.stdout)

    def test_core_install_is_notice_only(self):
        r = run("install", "xrpl-muse-skill", "--yes", "0.14.1"); self.assertEqual(r.returncode, 0)
        self.assertIn("does not install the core", r.stdout)

    def test_install_dry_run(self):
        r = run("install", "xrpl-community-shows"); self.assertEqual(r.returncode, 0)
        self.assertIn("Dry run", r.stdout); self.assertIn("--yes 0.2.1", r.stdout)

    def test_install_yes_must_match(self):
        r = run("install", "xrpl-community-shows", "--yes", "9.9.9"); self.assertEqual(r.returncode, 1)

    def test_install_from_local_zip(self):
        self.skipTest("real install disabled during audit repair; fixture kept for re-enable criteria")
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n# demo\n"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="abc", archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(os.path.join(skills, "xrpl-demo", "SKILL.md")))
            self.assertIn("installed: xrpl-demo 1.0.0", r.stdout)

    def test_install_manifest_mismatch_refused(self):
        self.skipTest("real install disabled during audit repair; fixture kept for re-enable criteria")
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 2.0.0\n---\n"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="abc", archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(r.returncode, 1)
            self.assertFalse(os.path.exists(os.path.join(skills, "xrpl-demo")))

    def test_install_disabled_during_repair(self):
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="abc", archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(r.returncode, 2)
            self.assertIn("disabled during the Selectu5 audit repair", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(skills, "xrpl-demo")))

    def test_install_secret_named_file_refused(self):
        self.skipTest("real install disabled during audit repair; fixture kept for re-enable criteria")
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\n---\n", "seed.txt": "x"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="abc", archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(r.returncode, 1)
            self.assertFalse(os.path.exists(os.path.join(skills, "xrpl-demo")))

    def test_check_updates_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "xrpl-view-export"); os.makedirs(p)
            with open(os.path.join(p, "SKILL.md"), "w") as fh:
                fh.write("---\nname: xrpl-view-export\nversion: 0.0.9\n---\n")
            r = run("check-updates", env={"SELECTU5_SKILLS_DIR": d})
            self.assertEqual(r.returncode, 0); self.assertIn("0.0.9 -> 0.1.0", r.stdout)

    def test_remote_registry_fallback(self):
        r = run("list", env={"SELECTU5_REGISTRY": "https://example.invalid/nope.json"})
        self.assertEqual(r.returncode, 1)  # override names one source only; a bad one fails loud

    def test_registry_schema(self):
        with open(LOCAL_REG) as fh: reg = json.load(fh)
        self.assertEqual(reg["schema"], "selectu5-registry/1")
        for e in reg["entries"]:
            for k in ("id", "name", "kind", "version", "access", "author", "purpose", "repo", "permissions", "ref"):
                self.assertIn(k, e, e["id"])
            self.assertIn(e["access"], ("read", "propose"))
            self.assertIn(e["kind"], ("core", "skill", "showcase"))

if __name__ == "__main__":
    unittest.main()
