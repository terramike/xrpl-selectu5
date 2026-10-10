import json, os, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "promptu5.py")

def run(*args, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e)

class TestPromptu5(unittest.TestCase):
    def test_version(self):
        r = run("version"); self.assertEqual(r.returncode, 0); self.assertIn("0.1.0", r.stdout)

    def test_list_has_seed_entries(self):
        r = run("list"); self.assertEqual(r.returncode, 0)
        for needle in ("xrpl-community-shows", "clavi5", "visu5", "xrpl-promptu5 0.1.0"):
            self.assertIn(needle, r.stdout)

    def test_show_permissions_card(self):
        r = run("show", "xrpl-view-export"); self.assertEqual(r.returncode, 0)
        self.assertIn("permissions:", r.stdout); self.assertIn("signs: Never.", r.stdout)

    def test_show_unknown_fails(self):
        r = run("show", "nope"); self.assertEqual(r.returncode, 1)

    def test_showcase_install_is_not_an_install(self):
        r = run("install", "clavi5"); self.assertEqual(r.returncode, 0)
        self.assertIn("not an install", r.stdout)

    def test_check_updates_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "xrpl-view-export"); os.makedirs(p)
            open(os.path.join(p, "SKILL.md"), "w").write("---\nname: xrpl-view-export\nversion: 0.0.9\n---\n")
            r = run("check-updates", env={"PROMPTU5_SKILLS_DIR": d})
            self.assertEqual(r.returncode, 0)
            self.assertIn("0.0.9 -> 0.1.0", r.stdout)

    def test_registry_schema(self):
        reg = json.load(open(os.path.join(HERE, "..", "registry", "registry.json")))
        self.assertEqual(reg["schema"], "promptu5-registry/1")
        for e in reg["entries"]:
            for k in ("id", "name", "kind", "version", "access", "author", "purpose", "repo", "permissions"):
                self.assertIn(k, e, e["id"])
            self.assertIn(e["access"], ("read", "propose"))
            self.assertIn(e["kind"], ("core", "skill", "showcase"))

if __name__ == "__main__":
    unittest.main()
