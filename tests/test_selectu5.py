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
         "repo": "https://github.com/terramike/xrpl-demo", "install": "test", "permissions": PERM, "ref": ref}
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
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="a" * 40, archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills, "SELECTU5_TEST_MODE": "1", "SELECTU5_TEST_ARCHIVE": "file://" + zp})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(os.path.join(skills, "xrpl-demo", "SKILL.md")))
            self.assertIn("installed: xrpl-demo 1.0.0", r.stdout)

    def test_install_manifest_mismatch_refused(self):
        self.skipTest("real install disabled during audit repair; fixture kept for re-enable criteria")
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 2.0.0\n---\n"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="a" * 40, archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills, "SELECTU5_TEST_MODE": "1", "SELECTU5_TEST_ARCHIVE": "file://" + zp})
            self.assertEqual(r.returncode, 1)
            self.assertFalse(os.path.exists(os.path.join(skills, "xrpl-demo")))

    def test_install_disabled_during_repair(self):
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="a" * 40, archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills, "SELECTU5_TEST_MODE": "1", "SELECTU5_TEST_ARCHIVE": "file://" + zp})
            self.assertEqual(r.returncode, 2)
            self.assertIn("disabled during the Selectu5 audit repair", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(skills, "xrpl-demo")))

    def test_install_secret_named_file_refused(self):
        self.skipTest("real install disabled during audit repair; fixture kept for re-enable criteria")
        with tempfile.TemporaryDirectory() as d:
            zp = os.path.join(d, "a.zip")
            make_zip(zp, {"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\n---\n", "seed.txt": "x"})
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="a" * 40, archive="file://" + zp)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            r = run("install", "xrpl-demo", "--yes", "1.0.0",
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills, "SELECTU5_TEST_MODE": "1", "SELECTU5_TEST_ARCHIVE": "file://" + zp})
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

class TestAuditRegression(unittest.TestCase):
    def reg_file(self, tmp, entries):
        p = os.path.join(tmp, "registry.json")
        json.dump({"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "entries": entries}, open(p, "w"))
        return p

    def test_A01_unsafe_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("../outside", "/abs/path", "xrpl-demo\\x", "xrpl.Demo", "xrpl-"):
                reg = self.reg_file(d, [entry(bad, "1.0.0", ref="a" * 40)])
                r = run("list", env={"SELECTU5_REGISTRY": reg})
                self.assertEqual(r.returncode, 1, bad)
                self.assertNotIn("Traceback", r.stderr)

    def test_A02_reserved_core_id_cannot_be_skill(self):
        with tempfile.TemporaryDirectory() as d:
            reg = self.reg_file(d, [entry("xrpl-muse-skill", "1.0.0", kind="skill", ref="a" * 40)])
            r = run("list", env={"SELECTU5_REGISTRY": reg})
            self.assertEqual(r.returncode, 1); self.assertIn("reserved", r.stderr)

    def test_A05_duplicate_and_unknown_kind_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            reg = self.reg_file(d, [entry("xrpl-demo", "1.0.0"), entry("xrpl-demo", "1.0.0")])
            r = run("list", env={"SELECTU5_REGISTRY": reg}); self.assertEqual(r.returncode, 1)
            e2 = entry("xrpl-demo", "1.0.0"); e2["kind"] = "widget"
            reg = self.reg_file(d, [e2])
            r = run("list", env={"SELECTU5_REGISTRY": reg}); self.assertEqual(r.returncode, 1)
            p = os.path.join(d, "empty.json"); json.dump({"schema": "selectu5-registry/1"}, open(p, "w"))
            r = run("list", env={"SELECTU5_REGISTRY": p}); self.assertEqual(r.returncode, 1)
            self.assertNotIn("Traceback", r.stderr); self.assertNotIn("KeyError", r.stderr)

    def test_A20_backup_and_symlink_not_in_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            bak = os.path.join(d, "xrpl-demo.bak-1.0.0"); os.makedirs(bak)
            with open(os.path.join(bak, "SKILL.md"), "w") as fh: fh.write("---\nname: xrpl-demo\nversion: 9.9.9\n---\n")
            outside = os.path.join(d, "outside.md")
            with open(outside, "w") as fh: fh.write("---\nname: xrpl-demo\nversion: CANARY\n---\n")
            link_dir = os.path.join(d, "xrpl-demo"); os.makedirs(link_dir)
            os.symlink(outside, os.path.join(link_dir, "SKILL.md"))
            r = run("installed", env={"SELECTU5_SKILLS_DIR": d})
            self.assertEqual(r.returncode, 0)
            self.assertNotIn("9.9.9", r.stdout); self.assertNotIn("CANARY", r.stdout)

    def test_A21_version_states(self):
        with tempfile.TemporaryDirectory() as d:
            for name, ver in (("xrpl-view-export", "0.0.9"), ("xrpl-community-shows", "9.0.0"), ("xrpl-selectu5", "unknown")):
                p = os.path.join(d, name); os.makedirs(p)
                with open(os.path.join(p, "SKILL.md"), "w") as fh: fh.write(f"---\nname: {name}\nversion: {ver}\n---\n")
            r = run("check-updates", env={"SELECTU5_SKILLS_DIR": d})
            self.assertEqual(r.returncode, 0)
            self.assertIn("0.0.9 -> 0.1.0", r.stdout)
            self.assertIn("newer than the catalog", r.stdout)
            self.assertIn("not claimed current", r.stdout)

    def test_A23_installed_without_registry(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("installed", env={"SELECTU5_REGISTRY": os.path.join(d, "missing.json"), "SELECTU5_SKILLS_DIR": d})
            self.assertEqual(r.returncode, 0)

    def test_A25_catalog_text_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            e = entry("xrpl-demo", "1.0.0", ref="a" * 40)
            e["purpose"] = "bad \x1b[31m text"
            reg = self.reg_file(d, [e])
            r = run("list", env={"SELECTU5_REGISTRY": reg})
            self.assertEqual(r.returncode, 1)  # control chars rejected at validation

    def test_destination_validation(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        with tempfile.TemporaryDirectory() as d:
            target = selectu5.validate_destination(d, "xrpl-demo")
            self.assertEqual(os.path.dirname(target), os.path.realpath(d))
            os.makedirs(os.path.join(d, "Xrpl-Demo"))
            with self.assertRaises(Exception):
                selectu5.validate_destination(d, "xrpl-demo")

class TestPlanIdentity(unittest.TestCase):
    def sysmod(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        return selectu5

    def test_A06_plan_digest_binds_fields(self):
        m = self.sysmod()
        e = entry("xrpl-demo", "1.0.0", ref="a" * 40)
        _, d1 = m.build_plan(e, "/tmp/skills/xrpl-demo")
        e2 = json.loads(json.dumps(e)); e2["permissions"] = dict(e["permissions"], network="https://evil.example")
        _, d2 = m.build_plan(e2, "/tmp/skills/xrpl-demo")
        self.assertNotEqual(d1, d2)

    def test_A07_floating_ref_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "registry.json")
            json.dump({"schema": "selectu5-registry/1", "entries": [entry("xrpl-demo", "1.0.0", ref="main")]}, open(p, "w"))
            r = run("list", env={"SELECTU5_REGISTRY": p})
            self.assertEqual(r.returncode, 1); self.assertIn("40-char", r.stderr)

    def test_A09_artifact_digest_verify(self):
        m = self.sysmod()
        import hashlib
        good = hashlib.sha256(b"pkg").hexdigest()
        self.assertEqual(m.verify_artifact(b"pkg", good), good)
        with self.assertRaises(Exception):
            m.verify_artifact(b"pkg", "0" * 64)
        with self.assertRaises(Exception):
            m.verify_artifact(b"pkg", None)

    def test_plan_shown_in_dry_run(self):
        r = run("install", "xrpl-community-shows")
        self.assertEqual(r.returncode, 0)
        self.assertIn("plan digest (sha256):", r.stdout)
        self.assertIn("does not prove a human approved it", r.stdout)

    def test_plan_mismatch_refused(self):
        r = run("install", "xrpl-community-shows", "--plan", "0" * 64)
        self.assertEqual(r.returncode, 1)

class TestArchiveAndManifest(unittest.TestCase):
    def mod(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        return selectu5

    def zio(self, files):
        import zipfile as zf_mod
        buf = io.BytesIO()
        with zf_mod.ZipFile(buf, "w") as z:
            for rel, body in files.items():
                z.writestr(rel, body)
        buf.seek(0)
        return zf_mod.ZipFile(buf)

    def test_A12_two_roots_and_traversal_rejected(self):
        m = self.mod()
        with self.assertRaises(Exception):
            m.validate_archive(self.zio({"a/SKILL.md": "x", "b/SKILL.md": "y"}), "a")
        with self.assertRaises(Exception):
            m.validate_archive(self.zio({"root/../evil": "x", "root/SKILL.md": "y"}), "root")
        with self.assertRaises(Exception):
            m.validate_archive(self.zio({"root\\evil": "x", "root/SKILL.md": "y"}), "root")
        dup = io.BytesIO()
        import zipfile as zf_mod
        with zf_mod.ZipFile(dup, "w") as z:
            z.writestr("root/SKILL.md", "x"); z.writestr("root/skill.md", "y")
        dup.seek(0)
        with self.assertRaises(Exception):
            m.validate_archive(zf_mod.ZipFile(dup), "root")

    def test_A10_A11_limits(self):
        m = self.mod()
        old = dict(m.LIMITS); m.LIMITS["expanded_file"] = 10; m.LIMITS["expanded_total"] = 15
        try:
            with self.assertRaises(Exception):
                m.validate_archive(self.zio({"root/SKILL.md": "x" * 40}), "root")
        finally:
            m.LIMITS.update(old)

    def test_A13_strict_manifest(self):
        m = self.mod()
        ok = m.parse_manifest_strict("---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n")
        self.assertEqual(ok["access"], "read")
        with self.assertRaises(Exception):
            m.parse_manifest_strict("---\nname: xrpl-demo\nversion: 1.0.0\n---\n")
        with self.assertRaises(Exception):
            m.parse_manifest_strict("---\nname: a\nname: b\nversion: 1.0.0\naccess: read\n---\n")

    def test_A14_core_compat(self):
        m = self.mod()
        self.assertTrue(m.check_core_compat(">=1.2.3", "1.2.3"))
        with self.assertRaises(Exception):
            m.check_core_compat(">=999.0.0", "0.14.1")
        with self.assertRaises(Exception):
            m.check_core_compat(">=1.0.0", "unknown")
        with self.assertRaises(Exception):
            m.check_core_compat("~1.0", "1.0.0")
