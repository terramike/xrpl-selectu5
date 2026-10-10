import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from qualify_update import snapshot, verify_backup
from qualify_interrupt import CHILD


class ActualBackupEvidence(unittest.TestCase):
    def test_interruption_child_source_compiles(self):
        compile(CHILD.replace("{scripts!r}", repr("scripts")), "interruption-child", "exec")

    def test_backup_corruption_extra_directory_and_extra_backup_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active = root / "xrpl-demo"
            active.mkdir()
            (active / "README.md").write_bytes(b"reviewed original bytes")
            (active / ".selectu5-meta.json").write_text('{"version":"1.0.0"}')
            before = snapshot(active)
            backup = root / "xrpl-demo.bak-first"
            active.rename(backup)
            self.assertTrue(verify_backup(root, "xrpl-demo", before)[0])
            (backup / "README.md").write_bytes(b"corrupted bytes")
            self.assertFalse(verify_backup(root, "xrpl-demo", before)[0])
            (backup / "README.md").write_bytes(b"reviewed original bytes")
            (backup / "extra-empty").mkdir()
            self.assertFalse(verify_backup(root, "xrpl-demo", before)[0])
            (backup / "extra-empty").rmdir()
            (root / "xrpl-demo.bak-second").mkdir()
            self.assertFalse(verify_backup(root, "xrpl-demo", before)[0])

    @unittest.skipIf(os.name == "nt", "POSIX permission semantics")
    def test_backup_permission_change_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup = root / "xrpl-demo.bak-first"
            backup.mkdir()
            f = backup / "README.md"
            f.write_bytes(b"same bytes")
            f.chmod(0o644)
            before = snapshot(backup)
            f.chmod(0o600)
            self.assertFalse(verify_backup(root, "xrpl-demo", before)[0])
