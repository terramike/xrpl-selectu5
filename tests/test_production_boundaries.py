import builtins
import hashlib
import http.server
import io
import json
import ntpath
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import selectu5 as m


def package(version):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("pkg/SKILL.md", f"---\nname: xrpl-demo\nversion: {version}\naccess: read\n---\n")
    data = out.getvalue()
    return {"kind": "skill", "id": "xrpl-demo", "version": version, "access": "read",
            "core_version": None, "ref": "a" * 40, "package_root": "pkg",
            "artifact_sha256": hashlib.sha256(data).hexdigest()}, data


class TestProductionBoundaries(unittest.TestCase):
    def test_invalid_published_identity_remains_pending(self):
        for updating in (False, True):
            with self.subTest(updating=updating), tempfile.TemporaryDirectory() as root:
                if updating:
                    e, data = package("1.0.0")
                    m.install_package(e, data, root, "0.14.1")
                e, data = package("1.0.1")
                rename = m._rename_dir
                injected = []
                def corrupt(src, dst):
                    rename(src, dst)
                    if os.path.normcase(os.path.realpath(dst)) == os.path.normcase(os.path.realpath(os.path.join(root, "xrpl-demo"))):
                        Path(dst, ".selectu5-meta.json").write_text("{}")
                        injected.append(dst)
                with patch.object(m, "_rename_dir", corrupt):
                    with self.assertRaisesRegex(m.RegistryError, "unresolved"):
                        m.install_package(e, data, root, "0.14.1")
                self.assertEqual(len(injected), 1)
                rec = Path(root, m.RECOVERY_DIRNAME)
                records = [json.loads(p.read_text()) for p in rec.glob("*.json")]
                self.assertEqual([r["stage"] for r in records], ["published"])
                with m.skills_lock(root):
                    with self.assertRaisesRegex(m.RegistryError, "ambiguous"):
                        m.recover_transactions(root)
                self.assertIn("1.0.1", Path(root, "xrpl-demo", "SKILL.md").read_text())
                if updating:
                    backups = list(Path(root).glob("xrpl-demo.bak-*"))
                    self.assertEqual(len(backups), 1)
                    self.assertIn("1.0.0", (backups[0] / "SKILL.md").read_text())

    def test_150_transactions_and_restart_preserve_backups(self):
        with tempfile.TemporaryDirectory() as root:
            for i in range(150):
                e, data = package(f"1.0.{i}")
                m.install_package(e, data, root, "0.14.1")
            code = "import sys;sys.path.insert(0,sys.argv[1]);import selectu5 as m\nwith m.skills_lock(sys.argv[2]): m.recover_transactions(sys.argv[2])"
            result = subprocess.run([sys.executable, "-c", code, str(Path(m.__file__).parent), root],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            rec = Path(root, m.RECOVERY_DIRNAME)
            self.assertEqual(list(rec.glob("*.json")), [])
            self.assertEqual(len(list((rec / "history").glob("*.json"))), 100)
            self.assertEqual(len(list(Path(root).glob("xrpl-demo.bak-*"))), 149)
            e, data = package("1.0.150")
            m.install_package(e, data, root, "0.14.1")

    def test_pending_limit_preserves_records(self):
        with tempfile.TemporaryDirectory() as root:
            rec = Path(root, m.RECOVERY_DIRNAME)
            rec.mkdir()
            for i in range(101):
                tx = f"{i:x}-" + "a" * 16
                record = {"tx": tx, "id": "xrpl-demo", "new_version": "1.0.0", "old_version": None,
                          "stage": "prepared", "backup_name": None, "commit": "a" * 40,
                          "artifact_sha256": "b" * 64}
                (rec / (tx + ".json")).write_text(json.dumps(record))
            with m.skills_lock(root), self.assertRaisesRegex(m.RegistryError, "pending"):
                m.recover_transactions(root)
            self.assertEqual(len(list(rec.glob("*.json"))), 101)

    def test_legacy_terminal_records_do_not_count_as_pending(self):
        with tempfile.TemporaryDirectory() as root:
            rec = Path(root, m.RECOVERY_DIRNAME); rec.mkdir()
            for i in range(101):
                tx = f"{i:08x}-" + "a" * 16
                record = {"tx": tx, "id": "xrpl-demo", "new_version": "1.0.0", "old_version": None,
                          "stage": "done", "backup_name": None, "commit": "a" * 40,
                          "artifact_sha256": "b" * 64}
                (rec / (tx + ".json")).write_text(json.dumps(record))
            with m.skills_lock(root):
                self.assertEqual(m.recover_transactions(root), [])
            self.assertEqual(list(rec.glob("*.json")), [])
            self.assertEqual(len(list((rec / "history").glob("*.json"))), 100)

    def test_configured_core_inventory_does_not_read_provenance(self):
        with tempfile.TemporaryDirectory() as root:
            core = Path(root, "xrpl-custom-core"); core.mkdir()
            (core / "SKILL.md").write_text("---\nname: xrpl-custom-core\nversion: 0.14.1\n---\n")
            with patch.dict(os.environ, {"SELECTU5_CORE_DIR": str(core)}), \
                    patch.object(m, "_read_provenance", side_effect=AssertionError("core provenance read")):
                inventory = m.local_skills(root)
            self.assertIsNone(inventory["xrpl-custom-core"]["provenance"])

    def test_windows_drive_and_unc_components_keep_anchor(self):
        for supplied in (r"C:\root\linked\skills", r"\\server\share\root\linked\skills"):
            seen = []
            def redirect(path):
                seen.append(path)
                return path.endswith(r"\linked")
            with patch.object(m.os, "path", ntpath), patch.object(m.os, "sep", "\\"), \
                    patch.object(ntpath, "lexists", return_value=True), patch.object(m, "_is_redirect", redirect):
                with self.assertRaises(m.RegistryError):
                    m._root_components(supplied)
            drive = ntpath.splitdrive(supplied)[0]
            self.assertTrue(all(p.startswith(drive + "\\") for p in seen), seen)

    def test_core_inventory_reads_only_public_manifests(self):
        with tempfile.TemporaryDirectory() as root:
            manifests = set()
            for name in m.RESERVED_CORE_IDS:
                path = Path(root, name)
                path.mkdir()
                md = path / "SKILL.md"
                md.write_text(f"---\nname: {name}\nversion: 0.14.1\n---\n")
                (path / ".selectu5-meta.json").write_text("private sentinel")
                manifests.add(str(md))
            opened = []
            original = builtins.open
            def observe(path, *args, **kwargs):
                opened.append(str(path))
                return original(path, *args, **kwargs)
            with patch("builtins.open", observe):
                inventory = m.local_skills(root)
            self.assertEqual(set(opened), manifests)
            self.assertTrue(all(item["provenance"] is None for item in inventory.values()))

    @unittest.skipUnless(os.name == "nt", "native Windows junction test")
    def test_native_junctions_and_nonroot_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp, "root"); root.mkdir()
            external = Path(temp, "external"); external.mkdir()
            original = os.getcwd()
            os.chdir(external)
            try:
                for name in ("linked", "xrpl-demo", m.STAGING_DIRNAME, m.RECOVERY_DIRNAME,
                             "xrpl-demo.bak-beef-" + "a" * 16):
                    link = root / name
                    if link.exists():
                        os.rmdir(link)  # Previous case can create an empty internal directory.
                    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(external)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    try:
                        self.assertTrue(m._is_redirect(link))
                        with self.assertRaises(m.RegistryError):
                            m._root_components(str(link / "skills"))
                        if name == "xrpl-demo":
                            with self.assertRaises(m.RegistryError):
                                m.validate_destination(str(root), name)
                            self.assertEqual(m.local_skills(str(root)), {})
                        if name in (m.STAGING_DIRNAME, m.RECOVERY_DIRNAME):
                            with self.assertRaises(m.RegistryError):
                                m._ensure_internal_dir(str(root), name)
                            e, data = package("1.0.0")
                            with self.assertRaises(m.RegistryError):
                                m.install_package(e, data, str(root), "0.14.1")
                        if ".bak-" in name:
                            rec = root / m.RECOVERY_DIRNAME
                            rec.mkdir(exist_ok=True)
                            tx = "beef-" + "a" * 16
                            record = {"tx": tx, "id": "xrpl-demo", "new_version": "1.0.1",
                                      "old_version": "1.0.0", "backup_name": name, "stage": "old-moved",
                                      "commit": "a" * 40, "artifact_sha256": "b" * 64}
                            file = rec / (tx + ".json")
                            file.write_text(json.dumps(record))
                            with m.skills_lock(str(root)), self.assertRaises(m.RegistryError):
                                m.recover_transactions(str(root))
                            file.unlink()
                    finally:
                        os.rmdir(link)
            finally:
                os.chdir(original)
            self.assertEqual(list(external.iterdir()), [])

    def test_transport_deadline_stops_real_drip_feed(self):
        requested = threading.Event()
        class Drip(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requested.set()
                self.send_response(200); self.end_headers()
                try:
                    for _ in range(100):
                        self.wfile.write(b"x"); self.wfile.flush(); time.sleep(0.04)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Drip)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        start = time.monotonic()
        try:
            with patch.object(m, "DOWNLOAD_DEADLINE", 1):
                with self.assertRaisesRegex(m.RegistryError, "deadline"):
                    m._read_url_bounded(f"http://127.0.0.1:{server.server_port}/", 65536)
            self.assertTrue(requested.is_set())
            self.assertLess(time.monotonic() - start, 2.5)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_transport_deadline_stops_header_wait(self):
        requested = threading.Event()
        class Stall(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requested.set()
                time.sleep(3)
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stall)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch.object(m, "DOWNLOAD_DEADLINE", 1):
                with self.assertRaisesRegex(m.RegistryError, "deadline"):
                    m._read_url_bounded(f"http://127.0.0.1:{server.server_port}/", 65536)
            self.assertTrue(requested.is_set())
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_download_size_and_transport_errors(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root, "source"); source.write_bytes(b"abcdef")
            self.assertEqual(m.read_limited(source.as_uri(), 6), b"abcdef")
            with self.assertRaisesRegex(m.RegistryError, "limit"):
                m.read_limited(source.as_uri(), 5)
            with self.assertRaises(OSError):
                m.read_limited(Path(root, "missing").as_uri(), 10)
