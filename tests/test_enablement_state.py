"""Enablement invariants for 0.2.6 (Mike's review requirements).

- The shipped gate state is asserted, not assumed.
- The bundled catalog authorizes exactly the qualified entries listed here.
- Version surfaces agree (code, manifest, skill instructions).
"""
import json, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import selectu5 as s

class TestEnablementState(unittest.TestCase):
    def test_shipped_gate_enabled_in_026(self):
        self.assertEqual(s.VERSION, "0.2.6")
        self.assertIs(s.INSTALL_ENABLED, True)

    def test_bundled_catalog_authorizes_exactly_qualified_entries(self):
        reg = json.load(open(os.path.join(ROOT, "registry", "registry.json"), encoding="utf-8"))
        qualified = {e["id"]: e["version"] for e in reg["entries"]
                     if e.get("ref") and e.get("artifact_sha256") and e.get("package_root")}
        self.assertEqual(qualified, {"xrpl-selectu5": "0.2.5"})

    def test_version_surfaces_agree(self):
        skill = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
        man = s.parse_manifest_strict(skill)
        self.assertEqual(man["version"], s.VERSION)
        self.assertIn(f"`xrpl-selectu5 {s.VERSION}`", skill)
        readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
        self.assertIn(f"**xrpl-selectu5 {s.VERSION}**", readme)

if __name__ == "__main__":
    unittest.main()
