#!/usr/bin/env python3
"""xrpl-selectu5 0.2.0 — Selectu5, the XRPL Muse skill app store.

Companion skill. Read-only toward the core: it reads a curated registry
and the version frontmatter of local skills. Installs happen only with
the user's word for an exact entry and version, from a pinned ref,
after manifest verification. It never proposes, never signs, never
reads seeds, keys, tokens, or policy files.
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "0.2.0"
# Audit repair gate (2026-10-09): real installation stays disabled until
# the acceptance criteria in the audit report pass. Dry-run cards stay on.
INSTALL_ENABLED = False
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_REGISTRY = os.path.join(SKILL_DIR, "registry", "registry.json")
REMOTE_REGISTRY = "https://raw.githubusercontent.com/terramike/xrpl-selectu5/main/registry/registry.json"
DEFAULT_SKILLS_DIR = os.path.expanduser("~/workspace/skills")
MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
SECRET_NAME = re.compile(r"(seed|secret|\.pem$|\.key$|id_rsa)", re.I)

ID_RE = re.compile(r"^xrpl-[a-z0-9]+(?:-[a-z0-9]+)*$")
SHOWCASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
CORE_VERSION_RE = re.compile(r"^>=\d+\.\d+\.\d+$")
RESERVED_CORE_IDS = {"xrpl", "xrpl-muse", "xrpl-muse-skill"}
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_ENTRIES = 200


class RegistryError(ValueError):
    pass


APPROVED_REPO_OWNERS = {"terramike"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://"):
            raise RegistryError("redirect to a non-https URL is refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_HttpsOnlyRedirect())


def read_limited(src, limit):
    """Read a source in bounded chunks. Stop before the limit is passed."""
    import time
    deadline = time.monotonic() + 60
    if src.startswith(("https://", "file://")):
        req = urllib.request.Request(src, headers={"User-Agent": f"xrpl-selectu5/{VERSION}"})
        with _OPENER.open(req, timeout=20) as resp:
            chunks, total = [], 0
            while True:
                if time.monotonic() > deadline:
                    raise RegistryError("network deadline passed")
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise RegistryError(f"source passes the {limit}-byte limit")
                chunks.append(chunk)
            return b"".join(chunks)
    data = open(src, "rb").read(limit + 1)
    if len(data) > limit:
        raise RegistryError(f"source passes the {limit}-byte limit")
    return data


def build_plan(e, destination):
    """One canonical plan for review. Its digest binds the approval to content."""
    plan = {
        "id": e["id"],
        "version": e["version"],
        "kind": e["kind"],
        "access": e["access"],
        "core_version": e.get("core_version"),
        "repo": e["repo"],
        "commit": e.get("ref"),
        "artifact_sha256": e.get("artifact_sha256"),
        "package_root": e.get("package_root"),
        "permissions": e["permissions"],
        "destination": destination,
    }
    blob = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return plan, __import__("hashlib").sha256(blob).hexdigest()


LIMITS = {
    "archive_members": 2000,
    "expanded_total": 100 * 1024 * 1024,
    "expanded_file": 20 * 1024 * 1024,
    "manifest_bytes": 64 * 1024,
    "member_path": 240,
    "download_bytes": 25 * 1024 * 1024,
}


def _member_relpath(name):
    if "\\" in name:
        raise RegistryError(f"archive member uses a backslash: {name!r}")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or name.startswith("\\\\"):
        raise RegistryError(f"archive member path is absolute: {name!r}")
    parts = [x for x in name.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise RegistryError(f"archive member path escapes its root: {name!r}")
    return "/".join(parts)


def validate_archive(zf, package_root):
    """Validate archive structure before any byte is extracted. Returns root."""
    infos = zf.infolist()
    if len(infos) > LIMITS["archive_members"]:
        raise RegistryError("archive has too many members")
    if not package_root:
        raise RegistryError("the catalog records no package root for this entry")
    seen, total = {}, 0
    manifest_count = 0
    for info in infos:
        rel = _member_relpath(info.filename)
        if len(info.filename) > LIMITS["member_path"]:
            raise RegistryError("archive member path is too long")
        if info.flag_bits & 0x1:
            raise RegistryError("encrypted archive members are refused")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise RegistryError("unsupported archive compression method")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise RegistryError("symbolic links in archives are refused")
        if info.is_dir():
            continue
        if SECRET_NAME.search(os.path.basename(rel)):
            raise RegistryError(f"credential-named file in package: {rel}")
        key = rel.lower()
        if key in seen:
            raise RegistryError(f"duplicate or colliding archive member: {rel}")
        seen[key] = rel
        parts = rel.split("/")
        if parts[0] != package_root:
            raise RegistryError("archive root does not match the recorded package root")
        if len(parts) == 2 and parts[1] == "SKILL.md":
            manifest_count += 1
            if info.file_size > LIMITS["manifest_bytes"]:
                raise RegistryError("manifest passes the size limit")
        if info.file_size > LIMITS["expanded_file"]:
            raise RegistryError(f"archive member passes the per-file limit: {rel}")
        total += info.file_size
        if total > LIMITS["expanded_total"]:
            raise RegistryError("expanded package passes the total limit")
    for key in seen:
        parts = key.split("/")
        for i in range(1, len(parts)):
            if "/".join(parts[:i]) in seen:
                raise RegistryError("file and directory paths collide in the archive")
    if manifest_count != 1:
        raise RegistryError("archive must hold exactly one package-root SKILL.md")
    return package_root


def extract_member(zf, info, dest_path):
    """Decompress one member with an actual byte counter, never a trust fall."""
    written = 0
    with zf.open(info) as src, open(dest_path, "wb") as out:
        while True:
            chunk = src.read(65536)
            if not chunk:
                break
            written += len(chunk)
            if written > LIMITS["expanded_file"]:
                raise RegistryError("expanded file passes the per-file limit")
            out.write(chunk)
    return written


def parse_manifest_strict(text):
    """The supported frontmatter grammar: flat key: value lines, no duplicates."""
    m = FRONTMATTER.search(text or "")
    if not m:
        raise RegistryError("manifest has no frontmatter")
    fields = {}
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        km = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if not km:
            raise RegistryError(f"manifest line is outside the supported grammar: {line[:40]!r}")
        key, value = km.group(1), km.group(2).strip().strip("\"'")
        if key in ("name", "version", "access") and key in fields:
            raise RegistryError(f"manifest repeats the safety field {key}")
        fields.setdefault(key, value)
        if key in ("name", "version", "access"):
            fields[key] = value
    for key in ("name", "version", "access"):
        if not fields.get(key):
            raise RegistryError(f"manifest has no {key} field")
    if not VERSION_RE.match(fields["version"]):
        raise RegistryError("manifest version must be MAJOR.MINOR.PATCH")
    if fields["access"] not in ("read", "propose"):
        raise RegistryError("manifest access must be read or propose")
    return fields


def check_core_compat(required, core_version_text):
    """Support >=MAJOR.MINOR.PATCH only. Unknown or old core refuses install."""
    if required is None:
        return True
    if not CORE_VERSION_RE.match(required):
        raise RegistryError(f"unsupported core version expression: {required!r}")
    have = parse_version(core_version_text)
    if have is None:
        raise RegistryError("the installed core version is unknown; installation is refused")
    need = parse_version(required[2:])
    if have[:3] < need[:3]:
        raise RegistryError(f"core {core_version_text} does not meet {required}")
    return True


def verify_artifact(data, expected_sha256):
    import hashlib
    actual = hashlib.sha256(data).hexdigest()
    if not expected_sha256 or actual != expected_sha256:
        raise RegistryError("artifact digest does not match the reviewed digest")
    return actual


def esc(text):
    """Escape control characters so catalog text cannot drive the terminal."""
    return CONTROL_RE.sub(lambda m: "\\x%02x" % ord(m.group(0)), str(text))


def _check_text(value, field, limit):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise RegistryError(f"{field}: must be text of 1..{limit} chars")
    if CONTROL_RE.search(value):
        raise RegistryError(f"{field}: control characters are not allowed")


def validate_registry(reg):
    if not isinstance(reg, dict):
        raise RegistryError("registry: top level must be an object")
    if reg.get("schema") != "selectu5-registry/1":
        raise RegistryError(f"registry: unsupported schema {reg.get('schema')!r}")
    entries = reg.get("entries")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_ENTRIES:
        raise RegistryError("registry: entries must be a list of 1..200 items")
    seen = {}
    for e in entries:
        if not isinstance(e, dict):
            raise RegistryError("registry: each entry must be an object")
        eid = e.get("id")
        if not isinstance(eid, str) or CONTROL_RE.search(eid or ""):
            raise RegistryError("entry id: missing or unsafe")
        low = eid.lower()
        if low in seen:
            raise RegistryError(f"entry id {eid!r}: duplicate identifier (case-insensitive)")
        seen[low] = eid
        kind = e.get("kind")
        if kind not in ("core", "skill", "showcase"):
            raise RegistryError(f"{eid}: unsupported kind {kind!r}")
        if eid in RESERVED_CORE_IDS and kind != "core":
            raise RegistryError(f"{eid}: reserved core identifier cannot be kind {kind!r}")
        if kind in ("core", "skill") and not ID_RE.match(eid):
            raise RegistryError(f"{eid}: installable id must match xrpl-<name>")
        if kind == "showcase" and not SHOWCASE_ID_RE.match(eid):
            raise RegistryError(f"{eid}: showcase id is unsafe")
        if e.get("access") not in ("read", "propose"):
            raise RegistryError(f"{eid}: unsupported access {e.get('access')!r}")
        version = e.get("version")
        if kind in ("core", "skill"):
            if not isinstance(version, str) or not VERSION_RE.match(version):
                raise RegistryError(f"{eid}: version must be MAJOR.MINOR.PATCH")
        else:
            _check_text(version, f"{eid} version", 32)
            if "/" in version or "\\" in version:
                raise RegistryError(f"{eid}: version cannot contain a path separator")
        _check_text(e.get("name"), f"{eid} name", 120)
        _check_text(e.get("author"), f"{eid} author", 80)
        _check_text(e.get("purpose"), f"{eid} purpose", 400)
        repo = e.get("repo")
        _check_text(repo, f"{eid} repo", 300)
        if not repo.startswith("https://"):
            raise RegistryError(f"{eid}: repo must be an https URL")
        _check_text(e.get("install"), f"{eid} install", 400)
        cv = e.get("core_version")
        if cv is not None and (not isinstance(cv, str) or not CORE_VERSION_RE.match(cv)):
            raise RegistryError(f"{eid}: core_version must look like >=1.2.3")
        ref = e.get("ref")
        if ref is not None and (not isinstance(ref, str) or CONTROL_RE.search(ref) or "/" in ref or "\\" in ref):
            raise RegistryError(f"{eid}: ref is unsafe")
        if kind == "skill":
            m = re.match(r"^https://github\.com/([^/]+)/([A-Za-z0-9._-]+)$", repo)
            if not m or m.group(1) not in APPROVED_REPO_OWNERS:
                raise RegistryError(f"{eid}: repo is not an approved GitHub owner/repo pair")
            if ref is not None and not COMMIT_RE.match(ref):
                raise RegistryError(f"{eid}: installable ref must be a full 40-char commit SHA")
            digest = e.get("artifact_sha256")
            if digest is not None and not SHA256_RE.match(digest):
                raise RegistryError(f"{eid}: artifact_sha256 must be 64 lower hex chars")
            root = e.get("package_root")
            if root is not None and (not isinstance(root, str) or not re.match(r"^[A-Za-z0-9._-]+$", root)):
                raise RegistryError(f"{eid}: package_root must be one path component")
        perm = e.get("permissions")
        if not isinstance(perm, dict):
            raise RegistryError(f"{eid}: permissions must be an object")
        for key in ("commands", "files"):
            val = perm.get(key)
            if not isinstance(val, list) or not val or any(not isinstance(x, str) or CONTROL_RE.search(x) or len(x) > 200 for x in val):
                raise RegistryError(f"{eid}: permissions.{key} must be a list of short text items")
        for key in ("network", "signs"):
            _check_text(perm.get(key), f"{eid} permissions.{key}", 300)
        if e.get("notes") is not None:
            _check_text(e["notes"], f"{eid} notes", 400)
        if e.get("archive") is not None:
            raise RegistryError(f"{eid}: archive overrides are not allowed in a catalog")
    return reg


def parse_version(text):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$", str(text or ""))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "")


def validate_destination(skills_dir, entry_id):
    """Return the canonical target path or raise RegistryError. No mutation."""
    root = os.path.realpath(skills_dir)
    home = os.path.realpath(os.path.expanduser("~"))
    forbidden = [os.path.join(home, ".xrpl"),
                 os.path.realpath(os.environ.get("SELECTU5_CORE_DIR", os.path.expanduser("~/workspace/xrpl-muse-skill")))]
    for bad in forbidden:
        if root == bad or root.startswith(bad + os.sep):
            raise RegistryError("skills root cannot sit inside the core or credential directory")
    if os.path.islink(skills_dir):
        raise RegistryError("skills root cannot be a symlink")
    target = os.path.join(root, entry_id)
    if os.path.dirname(os.path.realpath(target)) != root and os.path.lexists(target):
        raise RegistryError("target escapes the skills root")
    if os.path.islink(target):
        raise RegistryError("target cannot be a symlink")
    if os.path.lexists(target) and not os.path.isdir(target):
        raise RegistryError("target exists and is not a directory")
    if os.path.isdir(root):
        for name in os.listdir(root):
            if name != entry_id and name.lower() == entry_id.lower():
                raise RegistryError("target collides with an existing folder on case-insensitive filesystems")
    return target


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|version|access):\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.M)


def read_source(src):
    if src.startswith(("https://", "file://")):
        req = urllib.request.Request(src, headers={"User-Agent": f"xrpl-selectu5/{VERSION}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    with open(src, "rb") as fh:
        return fh.read()


def load_registry():
    """Return (registry_dict, source_label). Remote first, local fallback."""
    override = os.environ.get("SELECTU5_REGISTRY")
    if override:
        candidates = [override]
    else:
        candidates = [REMOTE_REGISTRY, LOCAL_REGISTRY]
    errors = []
    for src in candidates:
        try:
            reg = json.loads(read_limited(src, 1024 * 1024).decode("utf-8"))
            reg = validate_registry(reg)
            LAST_CATALOG["date"] = reg.get("updated_at")
            return reg, src
        except Exception as exc:
            errors.append(f"{src}: {exc}")
    print(f"xrpl-selectu5 {VERSION}: cannot read any registry ({'; '.join(errors)})", file=sys.stderr)
    return None, None


def parse_manifest(text):
    m = FRONTMATTER.search(text or "")
    return dict(FIELD.findall(m.group(1))) if m else {}


def local_skills(skills_dir):
    found = {}
    if not os.path.isdir(skills_dir):
        return found
    for name in sorted(os.listdir(skills_dir)):
        if not name.startswith("xrpl") or ".bak-" in name or name.startswith("."):
            continue
        path = os.path.join(skills_dir, name)
        if os.path.islink(path) or not os.path.isdir(path):
            continue
        md = os.path.join(path, "SKILL.md")
        if os.path.islink(md) or not os.path.isfile(md):
            continue
        try:
            with open(md, encoding="utf-8") as fh:
                fields = parse_manifest(fh.read(65536))
        except Exception:
            continue
        if fields.get("name") and fields["name"] != name and not (name == "xrpl" and fields["name"] == "xrpl-muse-skill"):
            fields["version"] = "unknown"
        found[name] = {"version": fields.get("version", "unknown"), "path": os.path.join(skills_dir, name)}
    for folder, entry_id in {"xrpl": "xrpl-muse-skill"}.items():
        if folder in found and entry_id not in found:
            found[entry_id] = found[folder]
    return found


LAST_CATALOG = {}


def header(source=None):
    print(f"xrpl-selectu5 {VERSION} — Selectu5, the XRPL Muse skill store")
    if source:
        label = "local registry" if source == LOCAL_REGISTRY else source
        print(f"registry: {label}")
        if LAST_CATALOG.get("date"):
            print(f"catalog date: {LAST_CATALOG['date']}")
        if source == LOCAL_REGISTRY and not os.environ.get("SELECTU5_REGISTRY"):
            print("note: the remote catalog could not be read; this bundled snapshot may be stale.")


def get_entry(reg, entry_id):
    return next((e for e in reg["entries"] if e["id"] == entry_id), None)


def permissions_card(e):
    perm = e["permissions"]
    lines = [
        f"purpose: {esc(e['purpose'])}",
        f"repo / page: {esc(e['repo'])}",
        "permissions:",
        f"  core commands: {'; '.join(esc(x) for x in perm['commands'])}",
        f"  files: {'; '.join(esc(x) for x in perm['files'])}",
        f"  network: {esc(perm['network'])}",
        f"  signs: {esc(perm['signs'])}",
    ]
    if e.get("notes"):
        lines.append(f"notes: {esc(e['notes'])}")
    return "\n".join(lines)


RECOVERY_DIRNAME = ".selectu5-recovery"
STAGING_DIRNAME = ".selectu5-staging"


class LockHeldError(RegistryError):
    pass


def install_lock(skills_root):
    """One exclusive lock file for the skills root. Returns a release function."""
    lock_path = os.path.join(skills_root, ".selectu5.lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        raise LockHeldError("another Selectu5 install holds the skills-root lock")
    os.write(fd, f"{os.getpid()}\n".encode())
    os.close(fd)

    def release():
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            pass

    return release


def _txid():
    import time
    return f"{int(time.time() * 1000):x}-{os.getpid():x}"


def recover_transactions(skills_root):
    """Finish or roll back any recorded update before a new mutation starts."""
    actions = []
    rec_dir = os.path.join(skills_root, RECOVERY_DIRNAME)
    if not os.path.isdir(rec_dir):
        return actions
    for name in sorted(os.listdir(rec_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(rec_dir, name)
        try:
            tx = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if tx.get("stage") == "done":
            continue
        target, backup = tx.get("target"), tx.get("backup")
        if backup and os.path.isdir(backup) and target and not os.path.isdir(target):
            shutil.move(backup, target)
            actions.append(f"restored {tx.get('id')} from its update backup")
        tx["stage"] = "recovered"
        json.dump(tx, open(path, "w", encoding="utf-8"), indent=2)
    return actions


def install_package(e, data, skills_root, core_version_text):
    """The recoverable install engine. The CLI gate stays shut until acceptance.

    Stages on the destination filesystem, records the transaction before
    the first rename, keeps every prior backup, and restores the original
    active folder when the final rename fails.
    """
    verify_artifact(data, e.get("artifact_sha256"))
    if not e.get("package_root"):
        raise RegistryError("the catalog records no package root for this entry")
    skills_root = os.path.realpath(skills_root)
    os.makedirs(skills_root, exist_ok=True)
    recovered = recover_transactions(skills_root)
    release = install_lock(skills_root)
    txid = _txid()
    rec_dir = os.path.join(skills_root, RECOVERY_DIRNAME)
    staging_root = os.path.join(skills_root, STAGING_DIRNAME)
    staged = os.path.join(staging_root, txid)
    target = validate_destination(skills_root, e["id"])
    backup = os.path.join(skills_root, f"{e['id']}.bak-{txid}")
    record = {"tx": txid, "id": e["id"], "version": e["version"], "stage": "staging",
              "target": target, "backup": backup if os.path.isdir(target) else None,
              "commit": e.get("ref"), "artifact_sha256": e.get("artifact_sha256")}
    try:
        os.makedirs(rec_dir, exist_ok=True)
        os.makedirs(staged, exist_ok=False)
        zf = zipfile.ZipFile(io.BytesIO(data))
        validate_archive(zf, e["package_root"])
        root_prefix = e["package_root"] + "/"
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = _member_relpath(info.filename)[len(root_prefix):]
            dest = os.path.join(staged, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            extract_member(zf, info, dest)
        manifest = parse_manifest_strict(open(os.path.join(staged, "SKILL.md"), encoding="utf-8").read(LIMITS["manifest_bytes"]))
        if manifest["name"] != e["id"] or manifest["version"] != e["version"] or manifest["access"] != e["access"]:
            raise RegistryError("manifest does not match the approved plan")
        check_core_compat(e.get("core_version"), core_version_text)
        meta = {"id": e["id"], "version": e["version"], "commit": e.get("ref"),
                "artifact_sha256": e.get("artifact_sha256"), "tx": txid}
        json.dump(meta, open(os.path.join(staged, ".selectu5-meta.json"), "w", encoding="utf-8"), indent=2)
        # Recheck approval-critical facts under the lock, then record before rename.
        target = validate_destination(skills_root, e["id"])
        record["stage"] = "validated"
        json.dump(record, open(os.path.join(rec_dir, txid + ".json"), "w", encoding="utf-8"), indent=2)
        moved_active = False
        try:
            if os.path.isdir(target):
                shutil.move(target, backup)
                moved_active = True
                record["stage"] = "active-moved"
                json.dump(record, open(os.path.join(rec_dir, txid + ".json"), "w", encoding="utf-8"), indent=2)
            shutil.move(staged, target)
        except Exception:
            if moved_active and not os.path.isdir(target) and os.path.isdir(backup):
                shutil.move(backup, target)
            raise
        record["stage"] = "done"
        json.dump(record, open(os.path.join(rec_dir, txid + ".json"), "w", encoding="utf-8"), indent=2)
        return {"installed": target, "backup": backup if moved_active else None, "recovered": recovered}
    finally:
        if os.path.isdir(staged):
            shutil.rmtree(staged, ignore_errors=True)
        release()


def cmd_list(reg, local, source):
    header(source)
    for e in reg["entries"]:
        state = ""
        if e["id"] in local:
            v = local[e["id"]]["version"]
            state = f" — installed {v}" if v != "unknown" else " — installed (version not stated)"
            if v not in ("unknown", e["version"]):
                state += f" (registry {e['version']})"
        elif e["kind"] == "showcase":
            state = " — showcase, not an install"
        print(f"\n[{e['id']}] {e['name']} — registry {e['version']}{state}")
        print(f"  access: {e['access']} · kind: {e['kind']} · by {e['author']}")
        print(f"  {esc(e['purpose'])}")
    return 0


def cmd_show(reg, local, entry_id, source):
    e = get_entry(reg, entry_id)
    if not e:
        print(f"xrpl-selectu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header(source)
    state = (f"installed {local[entry_id]['version']}" if entry_id in local
             else ("showcase — not an install" if e["kind"] == "showcase" else "not installed"))
    print(f"\n{e['name']} [{e['id']}] — registry {e['version']} · {state}")
    print(f"access: {e['access']} · kind: {e['kind']} · by {e['author']}")
    if e.get("core_version"):
        print(f"needs core: {e['core_version']}")
    print()
    print(permissions_card(e))
    if e["kind"] == "showcase":
        print("\nThis is a showcase card. Selectu5 cannot install or enroll it; use the link above.")
    return 0


def cmd_installed(local, source):
    header(source)
    if not local:
        print("\nNo local xrpl-* skills found.")
        return 0
    print("\ninstalled:")
    for name, info in local.items():
        print(f"  {name} {info['version']} — {info['path']}")
    return 0


def cmd_check(reg, local, source):
    header(source)
    updates, current, missing, newer, unknown = [], [], [], [], []
    for e in reg["entries"]:
        if e["kind"] == "showcase":
            continue
        have = local.get(e["id"])
        if not have:
            missing.append(e)
            continue
        hv, rv = parse_version(have["version"]), parse_version(e["version"])
        if hv is None:
            unknown.append((e, have["version"]))
        elif hv < rv:
            updates.append((e, have["version"]))
        elif hv > rv:
            newer.append((e, have["version"]))
        else:
            current.append(e)
    if updates:
        print("\nupdates available (nothing installed — your word first):")
        for e, have in updates:
            print(f"  {e['id']}: {have} -> {e['version']} — {esc(e['repo'])}")
    if newer:
        print("\nnewer than the catalog (no downgrade is offered):")
        for e, have in newer:
            print(f"  {e['id']}: installed {have}, catalog {e['version']}")
    if unknown:
        print("\ninstalled, version unknown or invalid (not claimed current):")
        for e, have in unknown:
            print(f"  {e['id']}: {esc(have)}")
    if missing:
        print("\nlisted, not installed:")
        for e in missing:
            print(f"  {e['id']} {e['version']} — {esc(e['purpose'])}")
    if current:
        print("\ncurrent:")
        for e in current:
            print(f"  {e['id']} {e['version']}")
    if not updates and not missing and not newer and not unknown:
        print("\nEverything listed is installed and current.")
    print("\nAn update notice is information, not an install.")
    return 0


def fetch_archive(e):
    # Test transport only: a named local fixture replaces the network fetch.
    # Production catalogs cannot carry archive overrides (validator rejects them).
    if os.environ.get("SELECTU5_TEST_MODE") == "1" and os.environ.get("SELECTU5_TEST_ARCHIVE"):
        url = os.environ["SELECTU5_TEST_ARCHIVE"]
        return read_source(url), url
    url = f"{e['repo'].rstrip('/')}/archive/{e['ref']}.zip"
    data = read_source(url)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError(f"archive too large ({len(data)} bytes)")
    return data, url


def install_root(zf):
    names = [n for n in zf.namelist() if n and not n.endswith("/")]
    for n in names:
        if n.startswith("/") or ".." in n.split("/"):
            raise ValueError(f"unsafe path in archive: {n}")
        if SECRET_NAME.search(os.path.basename(n)):
            raise ValueError(f"refusing archive with secret-named file: {n}")
    skill_mds = [n for n in names if os.path.basename(n) == "SKILL.md"]
    if not skill_mds:
        raise ValueError("archive has no SKILL.md")
    md = min(skill_mds, key=len)
    root = os.path.dirname(md)
    return root, md


def cmd_install(reg, local, entry_id, yes_version, source, plan_arg=None):
    e = get_entry(reg, entry_id)
    if not e:
        print(f"xrpl-selectu5 {VERSION}: no registry entry '{entry_id}'. Run: list", file=sys.stderr)
        return 1
    header(source)
    if e["kind"] == "showcase":
        print(f"\n{e['name']} is a showcase entry, not an install.")
        print(f"next step: {e['install']}")
        print(f"open: {e['repo']}")
        return 0
    if e["kind"] == "core":
        print(f"\n{e['name']} is the core skill. Selectu5 reports core updates; it does not install the core.")
        print(f"release: {e['repo']} (pinned ref: {e.get('ref') or 'none listed'})")
        print(f"manual path: {e['install']}")
        return 0
    print(f"\n{e['name']} [{e['id']}] — registry {e['version']}")
    print(permissions_card(e))
    try:
        destination = validate_destination(os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR), e["id"])
    except RegistryError as exc:
        print(f"\nRefused: unsafe destination: {exc}", file=sys.stderr)
        return 1
    plan, plan_digest = build_plan(e, destination)
    print("\ninstall plan (review every field):")
    print(json.dumps(plan, indent=2, sort_keys=True))
    print(f"plan digest (sha256): {plan_digest}")
    print("A plan digest proves content consistency only. It does not prove a human approved it;")
    print("the host must get the user's word before any real install call.")
    if plan_arg and plan_arg != plan_digest:
        print("\nRefused: --plan does not match the plan shown. Review the plan above and approve again.", file=sys.stderr)
        return 1
    if not yes_version:
        print(f"\nDry run — nothing installed. To install this exact version, the user gives the word, then run:")
        print(f"  selectu5.py install {e['id']} --yes {e['version']}")
        return 0
    if yes_version != e["version"]:
        print(f"\nRefused: --yes {yes_version} does not match registry version {e['version']}. Nothing installed.", file=sys.stderr)
        return 1
    if not INSTALL_ENABLED:
        print("\nReal installation is disabled during the Selectu5 audit repair. "
              "The card above stays available as a dry run. Nothing was installed.", file=sys.stderr)
        return 2
    if not e.get("ref"):
        print(f"\n{e['id']} has no pinned ref in the registry yet, so it is not installable. Nothing installed.", file=sys.stderr)
        return 1
    skills_dir = os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    target = os.path.join(skills_dir, e["id"])
    have = local.get(e["id"])
    if have and have["version"] == e["version"]:
        print(f"\n{e['id']} {e['version']} is already installed. Nothing changed.")
        return 0
    try:
        data, url = fetch_archive(e)
        print(f"\nfetched: {url} ({len(data)} bytes, pinned ref {e['ref']})")
        with tempfile.TemporaryDirectory() as tmp:
            zf = zipfile.ZipFile(io.BytesIO(data))
            root, md_rel = install_root(zf)
            zf.extractall(tmp)
            src_dir = os.path.join(tmp, root) if root else tmp
            manifest = parse_manifest(open(os.path.join(src_dir, "SKILL.md"), encoding="utf-8").read(4096))
            problems = []
            if manifest.get("name") != e["id"]:
                problems.append(f"manifest name {manifest.get('name')!r} != registry id {e['id']!r}")
            if manifest.get("version") != e["version"]:
                problems.append(f"manifest version {manifest.get('version')!r} != registry version {e['version']!r}")
            if manifest.get("access") and manifest["access"] != e["access"]:
                problems.append(f"manifest access {manifest['access']!r} != registry access {e['access']!r}")
            if problems:
                print("Refused: manifest does not match the registry entry:", file=sys.stderr)
                for p in problems:
                    print(f"  - {p}", file=sys.stderr)
                print("Nothing installed.", file=sys.stderr)
                return 1
            if not manifest.get("access"):
                print("note: the skill manifest has no access field; the registry card above is the authority for this install.")
            os.makedirs(skills_dir, exist_ok=True)
            backup = None
            if os.path.isdir(target):
                backup = target + f".bak-{have['version'] if have else 'unknown'}"
                if os.path.isdir(backup):
                    shutil.rmtree(backup)
                shutil.move(target, backup)
            shutil.move(src_dir, target)
    except Exception as exc:
        print(f"Install failed, nothing installed: {exc}", file=sys.stderr)
        return 1
    print(f"installed: {e['id']} {e['version']} -> {target}")
    if backup:
        print(f"previous version kept at: {backup}")
    print(f"xrpl-selectu5 {VERSION}: install complete. The new skill shows its own version on its next run.")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="selectu5")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p_show = sub.add_parser("show"); p_show.add_argument("id")
    sub.add_parser("installed")
    sub.add_parser("check-updates")
    p_inst = sub.add_parser("install"); p_inst.add_argument("id")
    p_inst.add_argument("--yes", metavar="VERSION", default=None,
                        help="install exactly this registry version (the user's word, encoded)")
    p_inst.add_argument("--plan", metavar="SHA256", default=None,
                        help="the plan digest the user approved after review")
    sub.add_parser("version")
    args = ap.parse_args()
    if args.cmd in (None, "version"):
        print(f"xrpl-selectu5 {VERSION}")
        return 0
    skills_dir = os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    if args.cmd == "installed":
        return cmd_installed(local_skills(skills_dir), "local inventory (no registry used)")
    reg, source = load_registry()
    if reg is None:
        return 1
    local = local_skills(skills_dir)
    if args.cmd == "list":
        return cmd_list(reg, local, source)
    if args.cmd == "show":
        return cmd_show(reg, local, args.id, source)
    if args.cmd == "installed":
        return cmd_installed(local, source)
    if args.cmd == "check-updates":
        return cmd_check(reg, local, source)
    if args.cmd == "install":
        return cmd_install(reg, local, args.id, args.yes, source, args.plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
