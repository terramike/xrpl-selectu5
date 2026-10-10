import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "qualify.py"
spec = importlib.util.spec_from_file_location("qualification_under_test", SCRIPT)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class TestQualificationHarness(unittest.TestCase):
    def run_harness(self, fault=None):
        with tempfile.TemporaryDirectory() as outer:
            root = Path(outer, "qualification"); root.mkdir()
            output = Path(outer, "evidence.json")
            args = [str(SCRIPT), "--source-commit", "7db6c62951b552d15fa13cc09e1f083f073ca92a",
                    "--qualification-commit", "e86b2d707a3df75e76ecdba9bb9cfb620e5b2d3d",
                    "--output-json", str(output), "--output-md", str(Path(outer, "evidence.md"))]
            original_rename = q.m._rename_dir
            def rename(src, dst):
                original_rename(src, dst)
                if ".bak-" in os.path.basename(dst) and fault:
                    fault(Path(dst))
            # The suite step is mocked to prevent recursive suite execution.
            suite = subprocess.CompletedProcess([], 0, stdout="Focused test: suite step substituted", stderr="")
            with patch.dict(os.environ), patch.object(sys, "argv", args), \
                    patch.object(q.tempfile, "mkdtemp", return_value=str(root) + os.sep + "."), \
                    patch.object(q.subprocess, "run", return_value=suite), \
                    patch.object(q.m, "fetch_distribution", side_effect=OSError("Offline test; retrieval not attempted")), \
                    patch.object(q.m, "_rename_dir", rename), contextlib.redirect_stdout(io.StringIO()):
                rc = q.main()
            return rc, json.loads(output.read_text(encoding="utf-8"))

    def test_canonical_paths_and_operation_override_labels(self):
        rc, evidence = self.run_harness()
        self.assertEqual(rc, 0)
        checks = {c["name"]: c for c in evidence["checks"]}
        self.assertEqual(checks["actual production fetch"]["test_overrides"], [])
        self.assertEqual(checks["repository test suite"]["test_overrides"], [])
        self.assertEqual(checks["synthetic fresh install via cmd_install"]["test_overrides"], q.OVERRIDES)
        self.assertTrue(checks["synthetic matching-provenance no-op"]["tree_unchanged"])
        self.assertEqual(checks["synthetic matching-provenance no-op"]["fetcher_calls"], 0)
        self.assertTrue(checks["synthetic update with backup"]["backup_tree_unchanged"])

    def test_corrupted_backup_payload_fails(self):
        rc, evidence = self.run_harness(lambda backup: (backup / "README.md").write_text("CORRUPTED PAYLOAD"))
        self.assertEqual(rc, 1)
        check = next(c for c in evidence["checks"] if c["name"] == "synthetic update with backup")
        self.assertEqual(check["status"], "fail")
        self.assertFalse(check["backup_tree_unchanged"])

    def test_extra_backup_directory_fails(self):
        rc, evidence = self.run_harness(lambda backup: (backup / "unexpected-empty-directory").mkdir())
        self.assertEqual(rc, 1)
        check = next(c for c in evidence["checks"] if c["name"] == "synthetic update with backup")
        self.assertEqual(check["status"], "fail")

    @unittest.skipIf(os.name == "nt", "Windows mode changes do not use POSIX permission semantics")
    def test_backup_mode_change_fails(self):
        rc, evidence = self.run_harness(lambda backup: os.chmod(backup / "README.md", 0o600))
        self.assertEqual(rc, 1)
        check = next(c for c in evidence["checks"] if c["name"] == "synthetic update with backup")
        self.assertEqual(check["status"], "fail")
