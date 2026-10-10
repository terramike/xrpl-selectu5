import io, json, os, re, subprocess, sys, tempfile, unittest, zipfile
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
    p = os.path.join(tmp, "registry.json")
    with open(p, "w") as fh: json.dump(reg, fh)
    return p

PERM = {"commands": ["none"], "files": ["none"], "network": "none", "signs": "Never."}
def entry(eid, version, kind="skill", ref=None, archive=None):
    e = {"id": eid, "name": eid, "kind": kind, "version": version, "core_version": None,
         "access": "read", "author": "test", "purpose": "test entry",
         "repo": "https://github.com/terramike/xrpl-demo", "install": "test", "permissions": PERM, "ref": ref}
    return e

class TestSelectu5(unittest.TestCase):
    def test_version(self):
        r = run("version"); self.assertEqual(r.returncode, 0); self.assertIn("0.2.2", r.stdout)

    def test_list_has_seed_entries(self):
        r = run("list"); self.assertEqual(r.returncode, 0)
        for needle in ("xrpl-community-shows", "clavi5", "visu5", "xrpl-selectu5 0.2.2"):
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
        self.assertIn("Dry run", r.stdout); self.assertIn("--yes 0.2.2", r.stdout)

    def test_install_yes_must_match(self):
        r = run("install", "xrpl-community-shows", "--yes", "9.9.9"); self.assertEqual(r.returncode, 1)

    def test_install_disabled_during_repair(self):
        with tempfile.TemporaryDirectory() as d:
            reg = reg_with(d, [entry("xrpl-demo", "1.0.0", ref="a" * 40)])
            skills = os.path.join(d, "skills"); os.makedirs(skills)
            dry = run("install", "xrpl-demo", env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(dry.returncode, 0, dry.stderr)
            digest = re.search(r"--plan ([0-9a-f]{64})", dry.stdout).group(1)
            r = run("install", "xrpl-demo", "--yes", "1.0.0", "--plan", digest,
                    env={"SELECTU5_REGISTRY": reg, "SELECTU5_SKILLS_DIR": skills})
            self.assertEqual(r.returncode, 2)
            self.assertIn("disabled during the Selectu5 audit repair", r.stderr)
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
        with open(p, "w") as fh: json.dump({"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "entries": entries}, fh)
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
            p = os.path.join(d, "empty.json")
            with open(p, "w") as fh: json.dump({"schema": "selectu5-registry/1"}, fh)
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
            with open(p, "w") as fh: json.dump({"schema": "selectu5-registry/1", "entries": [entry("xrpl-demo", "1.0.0", ref="main")]}, fh)
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

class TestRecoverableInstall(unittest.TestCase):
    def mod(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        return selectu5

    def pkg(self, files, top="xrpl-demo-abc"):
        buf = io.BytesIO()
        import zipfile as zf_mod
        with zf_mod.ZipFile(buf, "w") as z:
            for rel, body in files.items():
                z.writestr(f"{top}/{rel}", body)
        return buf.getvalue()

    def demo_entry(self, data):
        import hashlib
        e = entry("xrpl-demo", "1.0.0", ref="a" * 40)
        e["artifact_sha256"] = hashlib.sha256(data).hexdigest()
        e["package_root"] = "xrpl-demo-abc"
        return e

    MANIFEST = "---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n# demo\n"

    def test_A15_A16_offline_install_and_credential_refusal(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST, "data/shows-fixture.json": "{}"})
            out = m.install_package(self.demo_entry(data), data, d, "0.14.1")
            self.assertTrue(os.path.isfile(os.path.join(out["installed"], "SKILL.md")))
            bad = self.pkg({"SKILL.md": self.MANIFEST, "seed.txt": "x"})
            e = self.demo_entry(bad)
            with self.assertRaises(Exception):
                m.install_package(e, bad, d, "0.14.1")

    def test_A17_failed_final_move_restores_active(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST})
            m.install_package(self.demo_entry(data), data, d, "0.14.1")
            marker = os.path.join(d, "xrpl-demo", "SKILL.md")
            with open(marker) as fh: before = fh.read()
            real_rename = m._rename_dir
            calls = {"n": 0}
            def flaky(src, dst):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("injected failure")
                return real_rename(src, dst)
            m._rename_dir = flaky
            try:
                with self.assertRaises(Exception):
                    m.install_package(self.demo_entry(data), data, d, "0.14.1")
            finally:
                m._rename_dir = real_rename
            self.assertTrue(os.path.isfile(marker))
            with open(marker) as fh: self.assertEqual(fh.read(), before)

    def test_A18_recovery_record_rolls_back(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            tx = "abc123-" + "a" * 16
            target = os.path.join(d, "xrpl-demo"); backup = os.path.join(d, f"xrpl-demo.bak-{tx}")
            os.makedirs(backup)
            with open(os.path.join(backup, "SKILL.md"), "w") as fh: fh.write("old")
            rec = os.path.join(d, m.RECOVERY_DIRNAME); os.makedirs(rec)
            with open(os.path.join(rec, tx + ".json"), "w") as fh:
                json.dump({"tx": tx, "id": "xrpl-demo", "version": "1.0.0", "stage": "active-moved", "backup_name": f"xrpl-demo.bak-{tx}"}, fh)
            with m.skills_lock(d):
                actions = m.recover_transactions(d)
            self.assertTrue(actions)
            self.assertTrue(os.path.isfile(os.path.join(target, "SKILL.md")))

    def test_A19_lock_conflict(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            release = m.install_lock(d)
            try:
                with self.assertRaises(Exception):
                    m.install_lock(d)
            finally:
                release()

    def test_A29_interrupted_self_update_restores_active(self):
        m = self.mod()
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            def self_pkg(ver):
                return self.pkg({"SKILL.md": f"---\nname: xrpl-selectu5\nversion: {ver}\naccess: read\n---\n"}, top="xrpl-selectu5-abc")
            def self_entry(ver, data):
                e = entry("xrpl-selectu5", ver, ref="b" * 40)
                e["artifact_sha256"] = hashlib.sha256(data).hexdigest(); e["package_root"] = "xrpl-selectu5-abc"
                return e
            v1 = self_pkg("0.2.2"); m.install_package(self_entry("0.2.2", v1), v1, d, "0.14.1")
            marker = os.path.join(d, "xrpl-selectu5", "SKILL.md")
            with open(marker) as fh: before = fh.read()
            v2 = self_pkg("0.2.3")
            real_rename = m._rename_dir; calls = {"n": 0}
            def flaky(src, dst):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("injected self-update failure")
                return real_rename(src, dst)
            m._rename_dir = flaky
            try:
                with self.assertRaises(Exception):
                    m.install_package(self_entry("0.2.3", v2), v2, d, "0.14.1")
            finally:
                m._rename_dir = real_rename
            with open(marker) as fh: self.assertEqual(fh.read(), before)

class TestRound2Integration(unittest.TestCase):
    def mod(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        return selectu5

    def pkg(self, files, top="xrpl-demo-abc"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for rel, body in files.items():
                z.writestr(f"{top}/{rel}", body)
        return buf.getvalue()

    def installable(self, data, version="1.0.0"):
        import hashlib, contextlib
        e = entry("xrpl-demo", version, ref="a" * 40)
        e["artifact_sha256"] = hashlib.sha256(data).hexdigest(); e["package_root"] = "xrpl-demo-abc"
        reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-09", "entries": [e]}
        return reg, e

    MANIFEST = "---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n# demo\n"

    def call_install(self, m, reg, e, d, data, enabled=True):
        import contextlib
        plan, digest = m.build_plan(e, m.validate_destination(d, e["id"]))
        out = io.StringIO(); err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = m.cmd_install(reg, {}, e["id"], e["version"], m.LOCAL_REGISTRY, digest,
                               skills_dir=d, fetcher=lambda entry: data,
                               install_enabled=enabled, trusted_catalog=m.TRUSTED_INSTALL_SOURCE,
                               core_version_text="0.14.1")
        return rc, out.getvalue(), err.getvalue(), digest

    def test_R01_missing_plan_refuses_before_fetch(self):
        m = self.mod(); calls = []
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST})
            reg, e = self.installable(data)
            out = io.StringIO(); err = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = m.cmd_install(reg, {}, "xrpl-demo", "1.0.0", m.LOCAL_REGISTRY, None,
                                   skills_dir=d, fetcher=lambda entry: calls.append(1) or data,
                                   install_enabled=True, trusted_catalog=m.TRUSTED_INSTALL_SOURCE,
                                   core_version_text="0.14.1")
            self.assertEqual(rc, 1); self.assertEqual(calls, [])
            self.assertFalse(os.path.exists(os.path.join(d, "xrpl-demo")))

    def test_R01_command_path_installs_and_rejects_wrong_digest(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST})
            reg, e = self.installable(data)
            rc, out, err, _ = self.call_install(m, reg, e, d, data)
            self.assertEqual(rc, 0, err)
            self.assertTrue(os.path.isfile(os.path.join(d, "xrpl-demo", ".selectu5-meta.json")))
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST})
            reg, e = self.installable(data); e["artifact_sha256"] = "0" * 64
            rc, out, err, _ = self.call_install(m, reg, e, d, data)
            self.assertEqual(rc, 1); self.assertFalse(os.path.exists(os.path.join(d, "xrpl-demo")))

    def test_R01_command_path_rejects_missing_access_and_core_prerelease(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": "---\nname: xrpl-demo\nversion: 1.0.0\n---\n"})
            reg, e = self.installable(data)
            rc, out, err, _ = self.call_install(m, reg, e, d, data)
            self.assertEqual(rc, 1); self.assertFalse(os.path.exists(os.path.join(d, "xrpl-demo")))
        with self.assertRaises(Exception):
            m.check_core_compat(">=1.0.0", "1.0.0-alpha")
        self.assertGreater(m.compare_versions("1.0.0", "1.0.0-alpha"), 0)
        self.assertGreater(m.compare_versions("1.0.0-alpha.10", "1.0.0-alpha.2"), 0)

    def test_R02_R03_lock_journal_and_root_symlink(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            with m.skills_lock(d):
                with self.assertRaises(m.LockHeldError):
                    with m.skills_lock(d):
                        pass
            rec = os.path.join(d, m.RECOVERY_DIRNAME); os.makedirs(rec)
            with open(os.path.join(rec, "bad.json"), "w") as fh: fh.write("{")
            with m.skills_lock(d):
                with self.assertRaises(m.RegistryError):
                    m.recover_transactions(d)
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "real"); os.makedirs(real)
            link = os.path.join(d, "link"); os.symlink(real, link)
            with self.assertRaises(m.RegistryError):
                m.validate_destination(os.path.join(link, "skills"), "xrpl-demo")

    def test_R06_archive_portable_policy(self):
        m = self.mod()
        with self.assertRaises(m.RegistryError):
            m._member_relpath("root\\evil")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("root/SKILL.md", "x")
            z.writestr(zipfile.ZipInfo("root/docs/"), "")
            z.writestr("root/docs", "file")
        buf.seek(0)
        with self.assertRaises(m.RegistryError):
            m.validate_archive(zipfile.ZipFile(buf), "root")

    def test_R07_provenance_difference_reported(self):
        m = self.mod(); import contextlib
        with tempfile.TemporaryDirectory() as d:
            data = self.pkg({"SKILL.md": self.MANIFEST})
            reg, e = self.installable(data)
            rc, out, err, _ = self.call_install(m, reg, e, d, data)
            self.assertEqual(rc, 0, err)
            e2 = json.loads(json.dumps(e)); e2["artifact_sha256"] = "f" * 64
            reg2 = {"schema": "selectu5-registry/1", "entries": [e2]}
            local = m.local_skills(d)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                m.cmd_check(reg2, local, "test")
            self.assertIn("provenance difference", buf.getvalue())

class TestRound2RecoveryEvidence(unittest.TestCase):
    def mod(self):
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        import selectu5
        return selectu5

    def test_default_catalog_fallback_is_separate_from_override(self):
        m = self.mod(); orig = m.read_limited
        def fake(src, limit):
            if src == m.REMOTE_REGISTRY:
                raise OSError("simulated outage")
            return orig(src, limit)
        m.read_limited = fake
        try:
            reg, source = m.load_registry()
        finally:
            m.read_limited = orig
        self.assertIsNotNone(reg); self.assertEqual(source, m.LOCAL_REGISTRY)

    def test_catalog_metadata_controls_rejected(self):
        m = self.mod()
        reg = {"schema": "selectu5-registry/1", "updated_at": "2026\x1b[31m", "entries": [entry("xrpl-demo", "1.0.0", ref="a" * 40)]}
        with self.assertRaises(m.RegistryError):
            m.validate_registry(reg)

    def test_process_death_releases_lock_and_recovery_completes(self):
        m = self.mod()
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "skills"); os.makedirs(root)
            code = ("import sys, time; sys.path.insert(0, %r); import selectu5; "
                    "cm = selectu5.skills_lock(%r); cm.__enter__(); print('locked', flush=True); time.sleep(30)") % (os.path.join(SKILL, "scripts"), root)
            proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(), "locked")
                proc.terminate(); proc.wait(timeout=10)
            finally:
                if proc.poll() is None:
                    proc.kill()
            tx = "def456-" + "b" * 16
            backup_name = f"xrpl-demo.bak-{tx}"
            backup = os.path.join(root, backup_name); os.makedirs(backup)
            with open(os.path.join(backup, "SKILL.md"), "w") as fh: fh.write("old")
            rec = os.path.join(root, m.RECOVERY_DIRNAME); os.makedirs(rec)
            with open(os.path.join(rec, tx + ".json"), "w") as fh:
                json.dump({"tx": tx, "id": "xrpl-demo", "version": "1.0.0", "stage": "active-moved", "backup_name": backup_name}, fh)
            data_case = TestRound2Integration("test_R01_command_path_installs_and_rejects_wrong_digest")
            data = data_case.pkg({"SKILL.md": data_case.MANIFEST})
            reg, e = data_case.installable(data)
            out = m.install_package(e, data, root, "0.14.1")
            self.assertTrue(os.path.isfile(os.path.join(root, "xrpl-demo", "SKILL.md")))

    def test_backup_collision_refused_without_nesting(self):
        m = self.mod(); import hashlib
        case = TestRound2Integration("test_R01_command_path_installs_and_rejects_wrong_digest")
        with tempfile.TemporaryDirectory() as d:
            v1 = case.pkg({"SKILL.md": case.MANIFEST}); reg, e = case.installable(v1)
            m.install_package(e, v1, d, "0.14.1")
            fixed = "cafe99-" + "c" * 16
            collision = os.path.join(d, f"xrpl-demo.bak-{fixed}"); os.makedirs(collision)
            with open(os.path.join(collision, "keep.txt"), "w") as fh: fh.write("keep")
            v2 = case.pkg({"SKILL.md": case.MANIFEST.replace("1.0.0", "1.0.1")})
            e2 = entry("xrpl-demo", "1.0.1", ref="a" * 40)
            e2["artifact_sha256"] = hashlib.sha256(v2).hexdigest(); e2["package_root"] = "xrpl-demo-abc"
            old = m._txid; m._txid = lambda: fixed
            try:
                with self.assertRaises(m.RegistryError):
                    m.install_package(e2, v2, d, "0.14.1")
            finally:
                m._txid = old
            self.assertTrue(os.path.isfile(os.path.join(collision, "keep.txt")))
            self.assertFalse(os.path.exists(os.path.join(collision, "xrpl-demo")))
