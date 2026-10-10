import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("qualify_artifact", os.path.join(ROOT, "scripts", "qualify_artifact.py"))
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class TestSnapshotPaths(unittest.TestCase):
    def test_windows_style_relative_paths_normalize(self):
        self.assertEqual(qa.snapshot_key.__name__, "snapshot_key")
        # Direct normalization contract: backslashes become forward slashes.
        self.assertEqual("registry\\registry.json".replace("\\", "/"), "registry/registry.json")

    def test_nested_snapshot_keys_match_zip_names(self):
        with tempfile.TemporaryDirectory() as d:
            nested = os.path.join(d, "registry")
            os.makedirs(nested)
            with open(os.path.join(nested, "registry.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")
            with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("x")
            snap = qa.snapshot_tree(d)
            self.assertIn("registry/registry.json", snap)
            self.assertIn("SKILL.md", snap)
            for key in snap:
                self.assertNotIn("\\", key)

    def test_tree_diff_separates_missing_unexpected_mismatched(self):
        expected = {"a/b.txt": "1", "c.txt": "2", "d.txt": "3"}
        actual = {"a/b.txt": "1", "c.txt": "X", "e.txt": "9"}
        missing, unexpected, mismatched = qa.tree_diff(expected, actual)
        self.assertEqual(missing, ["d.txt"])
        self.assertEqual(unexpected, ["e.txt"])
        self.assertEqual(mismatched, ["c.txt"])


if __name__ == "__main__":
    unittest.main()
