import copy, hashlib, io, json, os, sys, tempfile, unittest, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import selectu5 as m
import package as pkg

S = "b" * 40
D = "c" * 64
BASE = None

def reg_entry():
    global BASE
    if BASE is None:
        reg = json.load(open(os.path.join(SKILL, "registry", "registry.json")))
        BASE = next(e for e in reg["entries"] if e["id"] == "xrpl-selectu5")
    e = copy.deepcopy(BASE)
    e["ref"] = S
    e["artifact_sha256"] = D
    e["package_root"] = "xrpl-selectu5-0.2.4"
    e["distribution"] = {
        "type": "github_release_asset",
        "source_commit": S,
        "asset_url": "https://github.com/terramike/xrpl-selectu5/releases/download/v0.2.4/xrpl-selectu5-0.2.4.zip",
        "asset_name": "xrpl-selectu5-0.2.4.zip",
    }
    return e

def validate(e):
    reg = {"schema": "selectu5-registry/1", "updated_at": "2026-10-10", "curator": "test", "entries": [e]}
    return m.validate_registry(reg)

class TestFixedAssets(unittest.TestCase):
    def test_distribution_entry_validates(self):
        validate(reg_entry())

    def test_distribution_rejects_wrong_repo_and_host(self):
        e = reg_entry(); e["distribution"]["asset_url"] = "https://github.com/terramike/xrpl-demo/releases/download/v1/x.zip"
        with self.assertRaises(m.RegistryError): validate(e)
        e = reg_entry(); e["distribution"]["asset_url"] = "https://evil.example.com/terramike/xrpl-selectu5/releases/download/v1/x.zip"
        with self.assertRaises(m.RegistryError): validate(e)
        e = reg_entry(); e["distribution"]["asset_name"] = "other.zip"
        with self.assertRaises(m.RegistryError): validate(e)
        e = reg_entry(); e["distribution"]["source_commit"] = "d" * 40
        with self.assertRaises(m.RegistryError): validate(e)

    def test_distribution_requires_digest_and_root(self):
        e = reg_entry(); e["artifact_sha256"] = None
        with self.assertRaises(m.RegistryError): validate(e)
        e = reg_entry(); e["package_root"] = None
        with self.assertRaises(m.RegistryError): validate(e)

    def test_plan_binds_asset_locator(self):
        e = reg_entry()
        _, d1 = m.build_plan(e, "/tmp/skills/xrpl-selectu5")
        e2 = reg_entry(); e2["distribution"]["asset_url"] = e2["distribution"]["asset_url"].replace("v0.2.4", "v0.2.5")
        _, d2 = m.build_plan(e2, "/tmp/skills/xrpl-selectu5")
        self.assertNotEqual(d1, d2)

    def test_fetch_uses_recorded_asset_url(self):
        seen = {}
        orig = m.read_limited
        m.read_limited = lambda src, limit: seen.update(src=src) or b"zip-bytes"
        try:
            self.assertEqual(m.fetch_distribution(reg_entry()), b"zip-bytes")
        finally:
            m.read_limited = orig
        self.assertEqual(seen["src"], reg_entry()["distribution"]["asset_url"])

    def test_redirect_policy(self):
        handler = m._HttpsOnlyRedirect()
        req = m.urllib.request.Request("https://github.com/terramike/xrpl-selectu5/releases/download/v1/x.zip")
        ok = handler.redirect_request(req, None, 302, "Found", {}, "https://release-assets.githubusercontent.com/x.zip?sig=1")
        self.assertIsNotNone(ok)
        with self.assertRaises(m.RegistryError):
            handler.redirect_request(req, None, 302, "Found", {}, "https://evil.example.com/x.zip")

    def test_deterministic_packaging(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "src"); os.makedirs(os.path.join(src, "scripts"))
            open(os.path.join(src, "SKILL.md"), "w").write("---\nname: xrpl-demo\nversion: 1.0.0\naccess: read\n---\n")
            open(os.path.join(src, "scripts", "x.py"), "w").write("x=1\n")
            files = [{"path": "SKILL.md"}, {"path": "scripts/x.py", "executable": True}]
            a, _ = pkg.build_zip(src, "pkg-1", files)
            b, _ = pkg.build_zip(src, "pkg-1", files)
            self.assertEqual(a, b)
            open(os.path.join(src, "scripts", "x.py"), "w").write("x=2\n")
            c, _ = pkg.build_zip(src, "pkg-1", files)
            self.assertNotEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(c).hexdigest())
            with zipfile.ZipFile(io.BytesIO(a)) as z:
                self.assertEqual(z.namelist(), ["pkg-1/SKILL.md", "pkg-1/scripts/x.py"])

if __name__ == "__main__":
    unittest.main()
