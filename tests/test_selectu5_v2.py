"""Selectu5 v2 (menu mode) tests: registry validation, menu commands, update checks."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import selectu5 as m

REG = {
    "schema": "selectu5-registry/1",
    "updated_at": "2026-10-11",
    "curator": "test",
    "entries": [
        {"id": "xrpl-muse-skill", "name": "XRPL Muse Skill (core)", "kind": "core",
         "version": "0.14.1", "access": "propose", "author": "terramike",
         "purpose": "core", "repo": "https://github.com/terramike/xrpl-muse-skill",
         "install": "manual",
         "permissions": {"commands": ["xrpl-trade balance"], "files": ["none"],
                         "network": "none", "signs": "never"}},
        {"id": "xrpl-view-export", "name": "XRPL View Export", "kind": "skill",
         "version": "0.1.0", "access": "read", "author": "terramike",
         "core_version": ">=0.14.1",
         "purpose": "export", "repo": "https://github.com/terramike/xrpl-view-export",
         "install": "from repo",
         "permissions": {"commands": ["xrpl-trade balance"], "files": ["none"],
                         "network": "none", "signs": "never"}},
        {"id": "visu5", "name": "Visu5", "kind": "showcase", "version": "v1",
         "access": "read", "author": "terramike",
         "purpose": "dash", "repo": "https://view.terramike.com", "install": "visit",
         "permissions": {"commands": [], "files": [], "network": "none", "signs": "never"}},
        {"id": "xrpl-selectu5", "name": "Selectu5", "kind": "skill",
         "version": "2.0.0", "access": "read", "author": "terramike",
         "purpose": "menu", "repo": "https://github.com/terramike/xrpl-selectu5",
         "install": "unzip",
         "permissions": {"commands": [], "files": [], "network": "none", "signs": "never"}},
    ],
}


def make_skills(files):
    d = tempfile.mkdtemp()
    for name, version in files:
        p = os.path.join(d, name)
        os.makedirs(p)
        with open(os.path.join(p, "SKILL.md"), "w") as fh:
            fh.write(f"---\nname: {name}\nversion: {version}\naccess: read\n---\nbody\n")
    return d


def run_main(args, env_extra=None):
    env = dict(os.environ)
    env.pop("SELECTU5_REGISTRY", None)
    env.update(env_extra or {})
    old = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = m.main(args)
        return code, buf.getvalue()
    finally:
        os.environ.clear()
        os.environ.update(old)


class TestRegistryV2(unittest.TestCase):
    def test_valid_registry_passes(self):
        self.assertEqual(m.validate_registry(REG)["schema"], "selectu5-registry/1")

    def test_install_authority_fields_not_required(self):
        e = dict(REG["entries"][1])
        self.assertNotIn("ref", e)
        self.assertNotIn("artifact_sha256", e)
        m.validate_registry(REG)

    def test_unsafe_repo_rejected(self):
        bad = json.loads(json.dumps(REG))
        bad["entries"][1]["repo"] = "http://example.com/x"
        with self.assertRaises(m.RegistryError):
            m.validate_registry(bad)

    def test_duplicate_id_rejected(self):
        bad = json.loads(json.dumps(REG))
        bad["entries"].append(dict(bad["entries"][1]))
        with self.assertRaises(m.RegistryError):
            m.validate_registry(bad)

    def test_control_chars_rejected(self):
        bad = json.loads(json.dumps(REG))
        bad["entries"][1]["purpose"] = "evil\x07purpose"
        with self.assertRaises(m.RegistryError):
            m.validate_registry(bad)

    def test_shows_all_entries_and_versions(self):
        d = make_skills([])
        fd, regfile = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps(REG).encode())
        os.close(fd)
        code, out = run_main(["--offline", "list"],
                             {"SELECTU5_REGISTRY": regfile, "SELECTU5_SKILLS_DIR": d})
        self.assertEqual(code, 0)
        for eid in ("xrpl-muse-skill", "xrpl-view-export", "visu5", "xrpl-selectu5"):
            self.assertIn(eid, out)
        self.assertIn("2.0.0", out)

    def test_show_card_has_permissions(self):
        d = make_skills([])
        fd, regfile = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps(REG).encode())
        os.close(fd)
        code, out = run_main(["--offline", "show", "xrpl-view-export"],
                             {"SELECTU5_REGISTRY": regfile, "SELECTU5_SKILLS_DIR": d})
        self.assertEqual(code, 0)
        self.assertIn("permissions:", out)
        self.assertIn("https://github.com/terramike/xrpl-view-export", out)

    def test_check_updates_reports_update_and_notice_only_core(self):
        d = make_skills([("xrpl-view-export", "0.0.9"), ("xrpl-muse-skill", "0.14.0")])
        fd, regfile = tempfile.mkstemp(suffix=".json")
        os.write(fd, json.dumps(REG).encode())
        os.close(fd)
        code, out = run_main(["--offline", "check-updates"],
                             {"SELECTU5_REGISTRY": regfile, "SELECTU5_SKILLS_DIR": d})
        self.assertEqual(code, 0)
        self.assertIn("0.0.9 -> 0.1.0", out)
        self.assertIn("notice only", out)
        self.assertNotIn("install", out.split("Selectu5 never installs")[0].lower().replace("installed", ""))

    def test_no_install_command(self):
        with self.assertRaises(SystemExit) as ctx:
            run_main(["install"], {})
        self.assertEqual(ctx.exception.code, 2)

    def test_version_command(self):
        code, out = run_main(["version"], {})
        self.assertEqual(code, 0)
        self.assertIn("2.0.0", out)


if __name__ == "__main__":
    unittest.main()
