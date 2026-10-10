#!/usr/bin/env python3
"""xrpl-selectu5 0.2.4 — Selectu5, the XRPL Muse skill app store.

Companion skill. Read-only toward the core: it reads a curated registry
and the version frontmatter of local skills. Installs happen only with
the user's word for an exact entry and version, from a pinned ref,
after manifest verification. It never proposes, never signs, never
reads seeds, keys, tokens, or policy files.
"""
import argparse
import contextlib
import io
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

VERSION = "0.2.4"
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
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
CORE_VERSION_RE = re.compile(r"^>=(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
RESERVED_CORE_IDS = {"xrpl", "xrpl-muse", "xrpl-muse-skill"}
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_ENTRIES = 200


class RegistryError(ValueError):
    pass


def _load_json_strict(data, limit, label):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if len(data) > limit:
        raise RegistryError(f"{label} passes the {limit}-byte limit")
    def no_dupes(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise RegistryError(f"{label} repeats the key {key!r}")
            obj[key] = value
        return obj
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=no_dupes)
    except RegistryError:
        raise
    except Exception as exc:
        raise RegistryError(f"{label} is not valid JSON") from exc


APPROVED_REPO_PAIRS = {
    ("terramike", "xrpl-muse-skill"),
    ("terramike", "xrpl-view-export"),
    ("terramike", "xrpl-community-shows"),
    ("terramike", "xrpl-selectu5"),
    ("terramike", "xrpl-demo"),
}
ALLOWED_DOWNLOAD_HOSTS = {"github.com", "codeload.github.com"}
# GitHub-operated hosts that may serve an approved release asset after a
# redirect from github.com. Any other redirect destination is refused.
ALLOWED_REDIRECT_HOSTS = ALLOWED_DOWNLOAD_HOSTS | {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}
TRUSTED_INSTALL_SOURCE = "local-reviewed-catalog"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_asset_url(e):
    """Validate a recorded GitHub release-asset locator. Returns the URL.

    The original string is checked before URL parsing: controls, embedded
    whitespace, backslashes, and percent-encoded separators or dot
    components are refused, and malformed values raise RegistryError.
    """
    dist = e.get("distribution")
    if not isinstance(dist, dict):
        raise RegistryError("distribution must be an object")
    if dist.get("type") != "github_release_asset":
        raise RegistryError("distribution type is not supported")
    source_commit = dist.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_RE.match(source_commit):
        raise RegistryError("distribution source_commit must be a full 40-char commit SHA")
    if source_commit != e.get("ref"):
        raise RegistryError("distribution source_commit must equal the pinned ref")
    repo = e.get("repo")
    if not isinstance(repo, str):
        raise RegistryError("repository is not an approved owner/repo pair")
    m = re.match(r"^https://github\.com/([^/]+)/([A-Za-z0-9._-]+)$", repo)
    if not m or (m.group(1), m.group(2)) not in APPROVED_REPO_PAIRS:
        raise RegistryError("repository is not an approved owner/repo pair")
    url = dist.get("asset_url")
    if not isinstance(url, str) or not url:
        raise RegistryError("asset_url is not an approved GitHub release-asset URL")
    if any(ord(c) < 0x20 or ord(c) == 0x7f for c in url) or any(c.isspace() for c in url) or "\\" in url:
        raise RegistryError("asset_url contains controls, whitespace, or a backslash")
    lowered = url.lower()
    if "%2f" in lowered or "%5c" in lowered or "%00" in lowered:
        raise RegistryError("asset_url contains an encoded separator or NUL")
    raw_path = url.split("?", 1)[0].split("#", 1)[0]
    decoded_segments = [urllib.parse.unquote(seg) for seg in raw_path.split("/")]
    if any(seg in (".", "..") for seg in decoded_segments):
        raise RegistryError("asset_url contains a dot path component")
    try:
        parsed = urllib.parse.urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise RegistryError("asset_url is malformed") from exc
    am = re.match(r"^/([^/]+)/([A-Za-z0-9._-]+)/releases/download/([^/]+)/([^/]+)$", parsed.path or "")
    if (parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password
            or port not in (None, 443) or parsed.query or parsed.fragment or not am):
        raise RegistryError("asset_url is not an approved GitHub release-asset URL")
    if (am.group(1), am.group(2)) != (m.group(1), m.group(2)):
        raise RegistryError("asset_url repository does not match the catalog repository")
    if not am.group(4).endswith(".zip") or dist.get("asset_name") != am.group(4):
        raise RegistryError("asset_name must equal the .zip file name in asset_url")
    return url


class _HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_REDIRECT_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise RegistryError("redirect destination is not an approved HTTPS endpoint")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_HttpsOnlyRedirect())


DOWNLOAD_DEADLINE = 60


def _read_url(src, limit):
    """Child-only transport. The parent enforces the total wall deadline."""
    req = urllib.request.Request(src, headers={"User-Agent": f"xrpl-selectu5/{VERSION}"})
    with _OPENER.open(req, timeout=20) as resp:
        chunks, total = [], 0
        while True:
            chunk = resp.read(min(65536, limit + 1 - total))
            if not chunk:
                return b"".join(chunks)
            total += len(chunk)
            if total > limit:
                raise RegistryError(f"source passes the {limit}-byte limit")
            chunks.append(chunk)


def _download_worker():
    try:
        src, limit = json.loads(sys.stdin.buffer.read())
        sys.stdout.buffer.write(_read_url(src, limit))
        return 0
    except Exception as exc:
        sys.stderr.write(str(exc))
        return 2 if isinstance(exc, RegistryError) else 3


def _read_url_bounded(src, limit):
    # A process can be terminated even when a socket read makes slow progress.
    code = "import runpy,sys; d=runpy.run_path(sys.argv[1]); sys.exit(d['_download_worker']())"
    try:
        result = subprocess.run([sys.executable, "-c", code, os.path.abspath(__file__)],
                                input=json.dumps([src, limit]).encode("utf-8"),
                                capture_output=True, timeout=DOWNLOAD_DEADLINE)
    except subprocess.TimeoutExpired as exc:
        raise RegistryError("network deadline passed") from exc
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace")[:4096]
        if result.returncode == 2:
            raise RegistryError(message)
        raise OSError(message or "download worker failed")
    if len(result.stdout) > limit:
        raise RegistryError(f"source passes the {limit}-byte limit")
    return result.stdout


def read_limited(src, limit):
    """Read bounded data. Terminate URL transport after 60 wall seconds."""
    if src.startswith(("https://", "file://")):
        return _read_url_bounded(src, limit)
    with open(src, "rb") as fh:
        data = fh.read(limit + 1)
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
    dist = e.get("distribution")
    if isinstance(dist, dict):
        plan["distribution"] = {"type": dist.get("type"), "source_commit": dist.get("source_commit"),
                               "asset_url": dist.get("asset_url"), "asset_name": dist.get("asset_name")}
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


WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}


def _member_relpath(name):
    if "\\" in name:
        raise RegistryError(f"archive member uses a backslash: {name!r}")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name) or name.startswith("\\\\"):
        raise RegistryError(f"archive member path is absolute: {name!r}")
    parts = [x for x in name.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise RegistryError(f"archive member path escapes its root: {name!r}")
    for part in parts:
        if ":" in part:
            raise RegistryError(f"archive member path contains a colon: {name!r}")
        if part.endswith((" ", ".")):
            raise RegistryError(f"archive member path is not portable to Windows: {name!r}")
        if part.split(".")[0].lower() in WINDOWS_RESERVED:
            raise RegistryError(f"archive member uses a Windows reserved name: {name!r}")
    return "/".join(parts)


def validate_archive(zf, package_root):
    """Validate archive structure before any byte is extracted. Returns root."""
    infos = zf.infolist()
    if len(infos) > LIMITS["archive_members"]:
        raise RegistryError("archive has too many members")
    if not package_root:
        raise RegistryError("the catalog records no package root for this entry")
    files, dirs, total = {}, set(), 0
    manifest_count = 0
    for info in infos:
        original = info.orig_filename
        if "\x00" in original or CONTROL_RE.search(original):
            raise RegistryError("archive member name contains a forbidden control character")
        rel = _member_relpath(original)
        if not rel:
            continue
        if len(original) > LIMITS["member_path"]:
            raise RegistryError("archive member path is too long")
        if info.flag_bits & 0x1:
            raise RegistryError("encrypted archive members are refused")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise RegistryError("unsupported archive compression method")
        ftype = stat.S_IFMT((info.external_attr >> 16) or 0)
        if ftype and ftype not in (stat.S_IFREG, stat.S_IFDIR):
            raise RegistryError("unsupported archive member type")
        parts = rel.split("/")
        if parts[0] != package_root:
            raise RegistryError("archive root does not match the recorded package root")
        key = rel.lower()
        if info.is_dir():
            if key in files:
                raise RegistryError(f"file and directory paths collide in the archive: {rel}")
            dirs.add(key)
            continue
        if key in files or key in dirs:
            raise RegistryError(f"duplicate or colliding archive member: {rel}")
        if SECRET_NAME.search(os.path.basename(rel)):
            raise RegistryError(f"credential-named file in package: {rel}")
        files[key] = rel
        if len(parts) == 2 and parts[1] == "SKILL.md":
            manifest_count += 1
            if info.file_size > LIMITS["manifest_bytes"]:
                raise RegistryError("manifest passes the size limit")
        if info.file_size > LIMITS["expanded_file"]:
            raise RegistryError(f"archive member passes the per-file limit: {rel}")
        total += info.file_size
        if total > LIMITS["expanded_total"]:
            raise RegistryError("expanded package passes the total limit")
    for key in files:
        parts = key.split("/")
        for i in range(1, len(parts)):
            if "/".join(parts[:i]) in files:
                raise RegistryError("file and directory paths collide in the archive")
    if manifest_count != 1:
        raise RegistryError("archive must hold exactly one package-root SKILL.md")
    return package_root


def extract_member(zf, info, dest_path, deadline=None):
    """Decompress one member with actual byte and time counters."""
    written = 0
    with zf.open(info) as src, open(dest_path, "wb") as out:
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise RegistryError("extraction deadline passed")
            chunk = src.read(65536)
            if deadline is not None and time.monotonic() > deadline:
                raise RegistryError("extraction deadline passed")
            if not chunk:
                break
            written += len(chunk)
            if written > LIMITS["expanded_file"]:
                raise RegistryError("expanded file passes the per-file limit")
            out.write(chunk)
    if deadline is not None and time.monotonic() > deadline:
        raise RegistryError("extraction deadline passed")
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
    if have[:3] == need[:3] and have[3]:
        raise RegistryError(f"core {core_version_text} is a prerelease and does not meet {required}")
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
    for meta_key in ("updated_at", "curator"):
        if reg.get(meta_key) is not None:
            _check_text(reg.get(meta_key), f"registry {meta_key}", 80)
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
            if not m or (m.group(1), m.group(2)) not in APPROVED_REPO_PAIRS:
                raise RegistryError(f"{eid}: repo is not an approved GitHub owner/repo pair")
            if ref is not None and not COMMIT_RE.match(ref):
                raise RegistryError(f"{eid}: installable ref must be a full 40-char commit SHA")
            digest = e.get("artifact_sha256")
            if digest is not None and not SHA256_RE.match(digest):
                raise RegistryError(f"{eid}: artifact_sha256 must be 64 lower hex chars")
            root = e.get("package_root")
            if root is not None and (not isinstance(root, str) or not re.match(r"^[A-Za-z0-9._-]+$", root)):
                raise RegistryError(f"{eid}: package_root must be one path component")
            if e.get("distribution") is not None:
                try:
                    validate_asset_url(e)
                except RegistryError as exc:
                    raise RegistryError(f"{eid}: {exc}") from exc
                if not COMMIT_RE.match(ref or "") or not SHA256_RE.match(digest or "") or not root:
                    raise RegistryError(f"{eid}: a distributed entry needs a pinned ref, artifact digest, and package root")
        if e.get("distribution") is not None and kind != "skill":
            raise RegistryError(f"{eid}: distribution records are allowed only on skill entries")
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
    m = VERSION_RE.match(str(text or ""))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "")


def version_key(text):
    """Semantic-version sort key. A release sorts after its prereleases."""
    parsed = parse_version(text)
    if parsed is None:
        return None
    major, minor, patch, pre = parsed
    if not pre:
        return (major, minor, patch, 1, ())
    ids = []
    for part in pre.split("."):
        if part.isdigit():
            ids.append((0, int(part), ""))
        else:
            ids.append((1, 0, part))
    return (major, minor, patch, 0, tuple(ids))


def compare_versions(a, b):
    ka, kb = version_key(a), version_key(b)
    if ka is None or kb is None:
        return None
    return (ka > kb) - (ka < kb)


def _is_redirect(path):
    """Reject symlinks, junctions, and other Windows reparse points."""
    if os.path.islink(path) or getattr(os.path, "isjunction", lambda p: False)(path):
        return True
    if os.name == "nt" and os.path.lexists(path):
        return bool(getattr(os.lstat(path), "st_file_attributes", 0) &
                    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return False


def _root_components(skills_dir):
    """Check anchored components before canonicalization. No mutation."""
    supplied = os.path.abspath(os.path.expanduser(str(skills_dir)))
    drive, tail = os.path.splitdrive(supplied)
    cur = drive + os.path.sep
    if os.path.lexists(cur) and _is_redirect(cur):
        raise RegistryError("skills root path contains a symlink or reparse component")
    for part in tail.split(os.path.sep):
        if not part:
            continue
        cur = os.path.join(cur, part)
        if os.path.lexists(cur) and _is_redirect(cur):
            raise RegistryError("skills root path contains a symlink or reparse component")
    return os.path.realpath(supplied)


def _within(path, parent):
    path, parent = os.path.normcase(path), os.path.normcase(parent)
    try:
        return os.path.commonpath((path, parent)) == parent
    except ValueError:  # Different Windows drives have no common path.
        return False


def validate_destination(skills_dir, entry_id):
    """Return the canonical target path or raise RegistryError. No mutation."""
    if not ID_RE.match(entry_id or "") or entry_id in RESERVED_CORE_IDS:
        raise RegistryError("destination identifier is not an installable skill id")
    root = _root_components(skills_dir)
    home = os.path.realpath(os.path.expanduser("~"))
    core_dir = os.path.realpath(os.environ.get("SELECTU5_CORE_DIR", os.path.expanduser("~/workspace/xrpl-muse-skill")))
    for bad in (os.path.join(home, ".xrpl"), core_dir):
        if _within(root, bad):
            raise RegistryError("skills root cannot sit inside the core or credential directory")
    target = os.path.join(root, entry_id)
    if _within(target, core_dir) or _within(core_dir, target):
        raise RegistryError("target overlaps the configured core directory")
    if os.path.dirname(target) != root:
        raise RegistryError("target escapes the skills root")
    if os.path.lexists(target):
        if _is_redirect(target) or not os.path.isdir(target):
            raise RegistryError("target exists and is not a plain directory")
    if os.path.isdir(root):
        for name in os.listdir(root):
            if name != entry_id and name.lower() == entry_id.lower():
                raise RegistryError("target collides with an existing folder on case-insensitive filesystems")
    return target


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|version|access):\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.M)


def catalog_trust(source):
    """Only the bundled reviewed catalog may authorize installs."""
    return TRUSTED_INSTALL_SOURCE if source == LOCAL_REGISTRY else "browse-only"


def load_registry(offline=False):
    """Return (registry_dict, source_label). Remote first unless offline."""
    override = os.environ.get("SELECTU5_REGISTRY")
    if offline:
        candidates = [LOCAL_REGISTRY]
    elif override:
        candidates = [override]
    else:
        candidates = [REMOTE_REGISTRY, LOCAL_REGISTRY]
    errors = []
    for src in candidates:
        try:
            raw = read_limited(src, 1024 * 1024)
        except RegistryError as exc:
            print(f"xrpl-selectu5 {VERSION}: catalog data from {src} is invalid: {exc}", file=sys.stderr)
            return None, None
        except Exception as exc:  # transport unavailable: fallback may proceed
            errors.append(f"{src}: {exc}")
            continue
        try:
            reg = validate_registry(json.loads(raw.decode("utf-8")))
        except Exception as exc:
            print(f"xrpl-selectu5 {VERSION}: catalog data from {src} is invalid: {exc}", file=sys.stderr)
            return None, None
        LAST_CATALOG["date"] = reg.get("updated_at")
        LAST_CATALOG["curator"] = reg.get("curator")
        LAST_CATALOG["offline"] = offline
        return reg, src
    print(f"xrpl-selectu5 {VERSION}: cannot read any registry ({'; '.join(errors)})", file=sys.stderr)
    return None, None


def parse_manifest(text):
    m = FRONTMATTER.search(text or "")
    return dict(FIELD.findall(m.group(1))) if m else {}


def _manifest_identity(text):
    """Inventory identity parser: legacy access may be absent, duplicates may not."""
    m = FRONTMATTER.search(text or "")
    if not m:
        return {}
    fields, dupes = {}, set()
    for line in m.group(1).splitlines():
        km = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if not km:
            continue
        key, value = km.group(1), km.group(2).strip().strip("\"'")
        if key in ("name", "version") and key in fields:
            dupes.add(key)
        fields.setdefault(key, value)
    if dupes:
        return {"invalid_identity": True}
    return fields


def _read_provenance(path, expected_id=None, expected_version=None):
    meta_path = os.path.join(path, ".selectu5-meta.json")
    if _is_redirect(meta_path) or not os.path.isfile(meta_path):
        return None
    try:
        if os.path.getsize(meta_path) > 16384:
            return {"invalid": True}
        with open(meta_path, "rb") as fh:
            meta = _load_json_strict(fh.read(16385), 16384, "provenance record")
    except Exception:
        return {"invalid": True}
    if not isinstance(meta, dict) or meta.get("schema") != "selectu5-install/1":
        return {"invalid": True}
    if not ID_RE.match(str(meta.get("id", ""))) or not VERSION_RE.match(str(meta.get("version", ""))):
        return {"invalid": True}
    if expected_id is not None and meta.get("id") != expected_id:
        return {"invalid": True}
    if expected_version is not None and meta.get("version") != expected_version:
        return {"invalid": True}
    if not COMMIT_RE.match(str(meta.get("commit", ""))) or not SHA256_RE.match(str(meta.get("artifact_sha256", ""))):
        return {"invalid": True}
    return meta


def local_skills(skills_dir):
    found = {}
    if not os.path.exists(skills_dir):
        return found
    _root_components(skills_dir)  # raises on any supplied symlink component
    if not os.path.isdir(skills_dir):
        raise RegistryError("skills root is not a directory")
    core_dir = os.path.realpath(os.environ.get("SELECTU5_CORE_DIR", os.path.expanduser("~/workspace/xrpl-muse-skill")))
    for name in sorted(os.listdir(skills_dir)):
        if not name.startswith("xrpl") or ".bak-" in name or name.startswith("."):
            continue
        path = os.path.join(skills_dir, name)
        if _is_redirect(path) or not os.path.isdir(path):
            continue
        md = os.path.join(path, "SKILL.md")
        if _is_redirect(md) or not os.path.isfile(md):
            continue
        try:
            with open(md, encoding="utf-8") as fh:
                fields = _manifest_identity(fh.read(65536))
        except Exception:
            continue
        identity_ok = (not fields.get("invalid_identity")) and (fields.get("name") == name or (name == "xrpl" and fields.get("name") == "xrpl-muse-skill"))
        version_ok = bool(VERSION_RE.match(fields.get("version", "")))
        version = fields.get("version") if identity_ok and version_ok else "unknown"
        expected_id = fields.get("name") if identity_ok else name
        found[name] = {"version": version, "path": os.path.join(skills_dir, name),
                       "provenance": None if name in RESERVED_CORE_IDS or _within(os.path.realpath(path), core_dir) else _read_provenance(path, expected_id, version if version_ok else None)}
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
            print(f"catalog date: {esc(LAST_CATALOG['date'])}")
        if source == LOCAL_REGISTRY and not os.environ.get("SELECTU5_REGISTRY") and not LAST_CATALOG.get("offline"):
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


def _ensure_internal_dir(root, name):
    path = os.path.join(root, name)
    if os.path.lexists(path):
        if _is_redirect(path) or not os.path.isdir(path):
            raise RegistryError(f"internal path {name} is not a plain directory")
        return path
    os.makedirs(path)
    return path


def _check_internal_file(path, label):
    if os.path.lexists(path) and (_is_redirect(path) or not os.path.isfile(path)):
        raise RegistryError(f"{label} is not a plain file")


@contextlib.contextmanager
def skills_lock(skills_root):
    """OS process lock. Process death releases it; the file is a rendezvous."""
    _root_components(skills_root)
    os.makedirs(skills_root, exist_ok=True)
    lock_path = os.path.join(skills_root, ".selectu5.lock")
    _check_internal_file(lock_path, "skills-root lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    locked = False
    try:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except ImportError:
            try:
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError as exc:
                raise LockHeldError("another Selectu5 install holds the skills-root lock") from exc
        except BlockingIOError as exc:
            raise LockHeldError("another Selectu5 install holds the skills-root lock") from exc
        yield lock_path
    finally:
        try:
            if locked:
                try:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except ImportError:
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)


def install_lock(skills_root):
    cm = skills_lock(skills_root)
    cm.__enter__()
    return lambda: cm.__exit__(None, None, None)


def _txid():
    return f"{int(time.time() * 1000):x}-{secrets.token_hex(8)}"


def _fsync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _write_journal(rec_dir, record):
    """Atomic journal replacement: temp file, flush, fsync, replace."""
    tx = record["tx"]
    final = os.path.join(rec_dir, tx + ".json")
    tmp = os.path.join(rec_dir, f".{tx}.{secrets.token_hex(4)}.tmp")
    with open(tmp, "x", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, final)
    _fsync_dir(rec_dir)
    return final


JOURNAL_MAX_RECORDS = 100
JOURNAL_MAX_BYTES = 1024 * 1024
JOURNAL_RECORD_BYTES = 16384


def _package_identity(path):
    """Validated package identity at a path, or None when not identifiable."""
    if not path or _is_redirect(path) or not os.path.isdir(path):
        return None
    md = os.path.join(path, "SKILL.md")
    if _is_redirect(md) or not os.path.isfile(md):
        return None
    try:
        with open(md, encoding="utf-8") as fh:
            fields = _manifest_identity(fh.read(65536))
    except Exception:
        return None
    if fields.get("invalid_identity") or not fields.get("name") or not VERSION_RE.match(fields.get("version", "")):
        return None
    meta = _read_provenance(path, fields["name"], fields["version"])
    return {"id": fields["name"], "version": fields["version"], "provenance": meta}


def _identity_is(identity, entry_id, version):
    return bool(identity and identity.get("id") == entry_id and identity.get("version") == version)


def _is_old_identity(identity, tx):
    if not _identity_is(identity, tx.get("id"), tx.get("old_version")):
        return False
    expected = tx.get("old_artifact_sha256")
    if expected:
        meta = identity.get("provenance")
        return bool(meta and not meta.get("invalid") and meta.get("artifact_sha256") == expected and meta.get("commit") == tx.get("old_commit"))
    return True


def _is_new_identity(identity, tx):
    if not _identity_is(identity, tx.get("id"), tx.get("new_version")):
        return False
    meta = identity.get("provenance")
    return bool(meta and not meta.get("invalid") and meta.get("artifact_sha256") == tx.get("artifact_sha256") and meta.get("commit") == tx.get("commit"))


def _validate_journal(rec_dir, name, root):
    path = os.path.join(rec_dir, name)
    if _is_redirect(path) or not os.path.isfile(path):
        raise RegistryError(f"recovery record {name} is not a plain file")
    if os.path.getsize(path) > JOURNAL_RECORD_BYTES:
        raise RegistryError(f"recovery record {name} passes the size limit; no mutation was made")
    try:
        with open(path, "rb") as fh:
            tx = _load_json_strict(fh.read(JOURNAL_RECORD_BYTES + 1), JOURNAL_RECORD_BYTES, f"recovery record {name}")
    except RegistryError as exc:
        raise RegistryError(f"recovery record {name} is corrupt; no mutation was made") from exc
    if not isinstance(tx, dict):
        raise RegistryError("recovery record is not an object; no mutation was made")
    txid = tx.get("tx")
    if not isinstance(txid, str) or not re.match(r"^[0-9a-f]+-[0-9a-f]{16}$", txid) or name != txid + ".json":
        raise RegistryError("recovery record has an invalid transaction id")
    entry_id = tx.get("id")
    if not isinstance(entry_id, str) or not ID_RE.match(entry_id) or entry_id in RESERVED_CORE_IDS:
        raise RegistryError("recovery record has an invalid skill id")
    if tx.get("stage") not in ("prepared", "old-moved", "published", "done", "recovered"):
        raise RegistryError("recovery record has an invalid stage")
    if not isinstance(tx.get("new_version"), str) or not VERSION_RE.match(tx["new_version"]):
        raise RegistryError("recovery record has an invalid new version")
    old_version = tx.get("old_version")
    if old_version is not None and (not isinstance(old_version, str) or not VERSION_RE.match(old_version)):
        raise RegistryError("recovery record has an invalid old version")
    if not COMMIT_RE.match(str(tx.get("commit", ""))) or not SHA256_RE.match(str(tx.get("artifact_sha256", ""))):
        raise RegistryError("recovery record has invalid new-content identity")
    for key in ("old_commit", "old_artifact_sha256"):
        if tx.get(key) is not None and not (COMMIT_RE.match(str(tx[key])) if key == "old_commit" else SHA256_RE.match(str(tx[key]))):
            raise RegistryError("recovery record has invalid old-content identity")
    backup_name = tx.get("backup_name")
    if old_version is None and backup_name is not None:
        raise RegistryError("recovery record names a backup without old content")
    if old_version is not None and backup_name != f"{entry_id}.bak-{txid}":
        raise RegistryError("recovery record has an invalid backup name")
    target = validate_destination(root, entry_id)
    backup = os.path.join(root, backup_name) if backup_name else None
    for candidate in (target, backup):
        if candidate and os.path.lexists(candidate) and _is_redirect(candidate):
            raise RegistryError("recovery path is a symlink; no mutation was made")
    return tx, target, backup


def _rename_dir(src, dst):
    if os.path.lexists(dst):
        raise RegistryError(f"destination already exists: {dst}")
    os.rename(src, dst)


def _cleanup_staged(root, txid):
    staging_root = os.path.join(root, STAGING_DIRNAME)
    if os.path.lexists(staging_root):
        if _is_redirect(staging_root) or not os.path.isdir(staging_root):
            raise RegistryError("staging path is not a plain directory")
        staged = os.path.join(staging_root, txid)
        if os.path.lexists(staged):
            if _is_redirect(staged) or not os.path.isdir(staged):
                raise RegistryError("staged path is not a plain directory")
            shutil.rmtree(staged)


def _archive_history(rec_dir, root, records):
    """Keep the latest 100 terminal journals. Never remove package backups."""
    terminal = [tx for tx, _, _ in records if tx["stage"] in ("done", "recovered")]
    history = os.path.join(rec_dir, "history")
    if not terminal and not os.path.lexists(history):
        return
    history = _ensure_internal_dir(rec_dir, "history")
    names = sorted(os.listdir(history))
    if len(names) > 1000:
        raise RegistryError("too many history records; manual review is required")
    for name in names:
        tx, _, _ = _validate_journal(history, name, root)
        if tx["stage"] not in ("done", "recovered"):
            raise RegistryError("history contains a pending recovery record")
    for tx in terminal:
        name = tx["tx"] + ".json"
        if os.path.lexists(os.path.join(history, name)):
            raise RegistryError("history record collides with a current record")
    for tx in terminal:
        name = tx["tx"] + ".json"
        os.rename(os.path.join(rec_dir, name), os.path.join(history, name))
    for name in sorted(os.listdir(history))[:-100]:
        os.unlink(os.path.join(history, name))
    _fsync_dir(history)
    _fsync_dir(rec_dir)


def recover_transactions(skills_root):
    """Resolve recorded updates. Call only while holding skills_lock()."""
    root = os.path.dirname(validate_destination(skills_root, "xrpl-selectu5"))
    actions = []
    rec_dir = os.path.join(root, RECOVERY_DIRNAME)
    if not os.path.isdir(rec_dir):
        return actions
    if _is_redirect(rec_dir):
        raise RegistryError("recovery directory is a symlink")
    names = [n for n in sorted(os.listdir(rec_dir)) if n.endswith(".json") and not n.startswith(".")]
    if len(names) > 1000:
        raise RegistryError("too many recovery files; manual review is required")
    total_bytes = 0
    records = []
    for name in names:  # validate the whole pending set before any mutation
        path = os.path.join(rec_dir, name)
        records.append(_validate_journal(rec_dir, name, root))
        if records[-1][0]["stage"] not in ("done", "recovered"):
            total_bytes += os.path.getsize(path)
    pending = [r for r in records if r[0]["stage"] not in ("done", "recovered")]
    if len(pending) > JOURNAL_MAX_RECORDS or total_bytes > JOURNAL_MAX_BYTES:
        raise RegistryError("pending recovery records pass the limits; no mutation was made")
    _archive_history(rec_dir, root, records)
    for tx, target, backup in records:
        if tx["stage"] in ("done", "recovered"):
            continue
        active = _package_identity(target) if os.path.lexists(target) else None
        backed = _package_identity(backup) if backup and os.path.lexists(backup) else None
        stage = tx["stage"]
        try:
            if _is_new_identity(active, tx):
                tx["stage"] = "done"
                _write_journal(rec_dir, tx)
                actions.append(f"recognized completed {tx['id']} {tx['new_version']}")
                continue
            if stage in ("prepared", "old-moved", "published"):
                if _is_old_identity(active, tx):
                    tx["stage"] = "recovered"
                    _write_journal(rec_dir, tx)
                    _cleanup_staged(root, tx["tx"])
                    actions.append(f"kept active {tx['id']} {tx['old_version']}")
                    continue
                if not os.path.lexists(target) and _is_old_identity(backed, tx):
                    _rename_dir(backup, target)
                    actions.append(f"restored {tx['id']} {tx['old_version']} from its update backup")
                    tx["stage"] = "recovered"
                    _write_journal(rec_dir, tx)
                    _cleanup_staged(root, tx["tx"])
                    continue
                if not os.path.lexists(target) and tx.get("old_version") is None:
                    tx["stage"] = "recovered"
                    _write_journal(rec_dir, tx)
                    _cleanup_staged(root, tx["tx"])
                    actions.append(f"cleared incomplete new install {tx['id']}")
                    continue
            raise RegistryError(f"recovery state for {tx['id']} is ambiguous; no recovery action was taken for that record")
        except RegistryError:
            if actions:
                raise RegistryError("recovery stopped after completed actions: " + "; ".join(actions))
            raise
    return actions


def install_package(e, data, skills_root, core_version_text):
    """One recoverable install engine. The CLI is the only caller in production."""
    if e.get("kind") != "skill" or not ID_RE.match(e.get("id") or "") or e.get("id") in RESERVED_CORE_IDS:
        raise RegistryError("engine accepts only installable skill entries")
    verify_artifact(data, e.get("artifact_sha256"))
    if not e.get("package_root"):
        raise RegistryError("the catalog records no package root for this entry")
    if not COMMIT_RE.match(e.get("ref") or ""):
        raise RegistryError("the catalog records no immutable commit for this entry")
    target = validate_destination(skills_root, e["id"])
    root = os.path.dirname(target)
    with skills_lock(root):
        recovered = recover_transactions(root)
        txid = _txid()
        rec_dir = _ensure_internal_dir(root, RECOVERY_DIRNAME)
        staging_root = _ensure_internal_dir(root, STAGING_DIRNAME)
        staged = os.path.join(staging_root, txid)
        backup_name = f"{e['id']}.bak-{txid}"
        backup = os.path.join(root, backup_name)
        old_identity = _package_identity(target) if os.path.lexists(target) else None
        if os.path.lexists(target) and not _is_old_identity(old_identity, {"id": e["id"], "old_version": old_identity.get("version") if old_identity else None, "old_commit": None, "old_artifact_sha256": None}):
            raise RegistryError("active package identity is unknown; installation is refused")
        old_meta = old_identity.get("provenance") if old_identity else None
        record = {"tx": txid, "id": e["id"], "new_version": e["version"],
                  "old_version": old_identity.get("version") if old_identity else None,
                  "stage": "prepared", "backup_name": backup_name if old_identity else None,
                  "commit": e.get("ref"), "artifact_sha256": e.get("artifact_sha256"),
                  "old_commit": old_meta.get("commit") if old_meta and not old_meta.get("invalid") else None,
                  "old_artifact_sha256": old_meta.get("artifact_sha256") if old_meta and not old_meta.get("invalid") else None}
        moved_active = False
        published = False
        try:
            os.makedirs(staged, exist_ok=False)
            _write_journal(rec_dir, record)
            deadline = time.monotonic() + 120
            total = 0
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                validate_archive(zf, e["package_root"])
                root_prefix = e["package_root"] + "/"
                for info in zf.infolist():
                    if time.monotonic() > deadline:
                        raise RegistryError("extraction deadline passed")
                    if info.is_dir():
                        continue
                    rel = _member_relpath(info.orig_filename)[len(root_prefix):]
                    dest = os.path.join(staged, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    total += extract_member(zf, info, dest, deadline)
                    if total > LIMITS["expanded_total"]:
                        raise RegistryError("expanded package passes the total limit")
                    mode = (info.external_attr >> 16) & 0o777
                    if stat.S_ISREG((info.external_attr >> 16) or 0o100644) and mode & 0o111:
                        os.chmod(dest, 0o755)
            if time.monotonic() > deadline:
                raise RegistryError("extraction deadline passed")
            with open(os.path.join(staged, "SKILL.md"), encoding="utf-8") as fh:
                manifest = parse_manifest_strict(fh.read(LIMITS["manifest_bytes"] + 1))
            if manifest["name"] != e["id"] or manifest["version"] != e["version"] or manifest["access"] != e["access"]:
                raise RegistryError("manifest does not match the approved plan")
            check_core_compat(e.get("core_version"), core_version_text)
            meta = {"schema": "selectu5-install/1", "id": e["id"], "version": e["version"],
                    "commit": e.get("ref"), "artifact_sha256": e.get("artifact_sha256"), "tx": txid}
            with open(os.path.join(staged, ".selectu5-meta.json"), "w", encoding="utf-8") as fh:
                json.dump(meta, fh, indent=2, sort_keys=True)
            target = validate_destination(root, e["id"])
            current_identity = _package_identity(target) if os.path.lexists(target) else None
            if old_identity and not _is_old_identity(current_identity, record):
                raise RegistryError("active package changed during staging; installation is refused")
            if not old_identity and os.path.lexists(target):
                raise RegistryError("active package appeared during staging; installation is refused")
            if os.path.lexists(backup):
                raise RegistryError("backup destination already exists")
            try:
                if old_identity:
                    record["stage"] = "old-moved"
                    _write_journal(rec_dir, record)
                    _rename_dir(target, backup)
                    moved_active = True
                record["stage"] = "published"
                _write_journal(rec_dir, record)
                _rename_dir(staged, target)
                published = True
            except Exception:
                if moved_active and not os.path.lexists(target) and os.path.isdir(backup):
                    _rename_dir(backup, target)
                    record["stage"] = "recovered"
                    _write_journal(rec_dir, record)
                raise
            try:
                placed_identity = _package_identity(target)
                if not _is_new_identity(placed_identity, record):
                    raise RegistryError("installed package failed identity verification")
                record["stage"] = "done"
                _write_journal(rec_dir, record)
            except Exception:
                # Rollback protocol for post-publication failures.
                failed_dir = os.path.join(staging_root, txid + "-failed")
                if _is_new_identity(_package_identity(target), record) and not os.path.lexists(failed_dir):
                    _rename_dir(target, failed_dir)
                if moved_active and not os.path.lexists(target) and os.path.isdir(backup):
                    _rename_dir(backup, target)
                restored = _package_identity(target) if os.path.lexists(target) else None
                resolved = (_is_old_identity(restored, record) if moved_active else not os.path.lexists(target))
                record["stage"] = "recovered" if resolved else "published"
                _write_journal(rec_dir, record)
                if not resolved:
                    raise RegistryError("published identity is invalid; recovery remains unresolved; preserve active content and backup")
                raise
            return {"installed": target, "backup": backup if moved_active else None, "recovered": recovered}
        finally:
            if os.path.isdir(staged):
                shutil.rmtree(staged, ignore_errors=True)


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
    shown = set()
    for name, info in local.items():
        if info["path"] in shown or (name == "xrpl" and "xrpl-muse-skill" in local):
            continue
        shown.add(info["path"])
        print(f"  {name} {info['version']} — {info['path']}")
    return 0


def cmd_check(reg, local, source):
    header(source)
    updates, current, missing, newer, unknown, provenance = [], [], [], [], [], []
    for e in reg["entries"]:
        if e["kind"] == "showcase":
            continue
        have = local.get(e["id"])
        if not have:
            missing.append(e)
            continue
        cmp = compare_versions(have["version"], e["version"])
        if cmp is None:
            unknown.append((e, have["version"]))
        elif cmp < 0:
            updates.append((e, have["version"]))
        elif cmp > 0:
            newer.append((e, have["version"]))
        else:
            meta = have.get("provenance")
            expected = e.get("artifact_sha256")
            if expected and (not meta or meta.get("invalid") or meta.get("artifact_sha256") != expected or meta.get("commit") != e.get("ref")):
                provenance.append((e, have["version"]))
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
    if provenance:
        print("\nprovenance difference (same version, content not verified as the catalog artifact):")
        for e, have in provenance:
            print(f"  {e['id']}: installed {have}, catalog digest or commit differs or is unrecorded")
    if current:
        print("\ncurrent:")
        for e in current:
            print(f"  {e['id']} {e['version']}")
    if not updates and not missing and not newer and not unknown and not provenance:
        print("\nEverything listed is installed and current.")
    print("\nAn update notice is information, not an install.")
    return 0


def fetch_distribution(e):
    """Bounded retrieval from the exact approved repository pair only.

    A reviewed release-asset locator (catalog `distribution`) is used when
    recorded; otherwise the legacy generated source-archive URL is used.
    """
    m = re.match(r"^https://github\.com/([^/]+)/([A-Za-z0-9._-]+)$", e.get("repo") or "")
    if not m or (m.group(1), m.group(2)) not in APPROVED_REPO_PAIRS:
        raise RegistryError("repository is not an approved owner/repo pair")
    if not COMMIT_RE.match(e.get("ref") or ""):
        raise RegistryError("distribution has no immutable commit")
    if e.get("distribution") is not None:
        url = validate_asset_url(e)
    else:
        url = f"{e['repo'].rstrip('/')}/archive/{e['ref']}.zip"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise RegistryError("distribution URL is not an approved HTTPS endpoint")
    return read_limited(url, LIMITS["download_bytes"])


def cmd_install(reg, local, entry_id, yes_version, source, plan_arg=None, skills_dir=None,
                fetcher=None, install_enabled=None, trusted_catalog=None, core_version_text=None):
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
    skills_dir = skills_dir or os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
    try:
        destination = validate_destination(skills_dir, e["id"])
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
        print(f"  selectu5.py install {e['id']} --yes {e['version']} --plan {plan_digest}")
        return 0
    if yes_version != e["version"]:
        print(f"\nRefused: --yes {yes_version} does not match registry version {e['version']}. Nothing installed.", file=sys.stderr)
        return 1
    if not plan_arg:
        print("\nRefused: a real installation requires --plan with the reviewed plan digest. Nothing was fetched.", file=sys.stderr)
        return 1
    enabled = INSTALL_ENABLED if install_enabled is None else install_enabled
    if not enabled:
        print("\nReal installation is disabled during the Selectu5 audit repair. "
              "The card above stays available as a dry run. Nothing was installed.", file=sys.stderr)
        return 2
    trust = catalog_trust(source) if trusted_catalog is None else trusted_catalog
    if trust != TRUSTED_INSTALL_SOURCE:
        print("\nRefused: this catalog is browse-only. Installations require the locally reviewed catalog. Nothing was fetched.", file=sys.stderr)
        return 1
    if not COMMIT_RE.match(e.get("ref") or "") or not SHA256_RE.match(e.get("artifact_sha256") or "") or not e.get("package_root"):
        print("\nRefused: this entry is list-only. It needs an immutable commit, a reviewed artifact digest, and a package root. Nothing was fetched.", file=sys.stderr)
        return 1
    if core_version_text is None:
        core = local.get("xrpl-muse-skill") if isinstance(local, dict) else None
        core_version_text = core.get("version") if core else "unknown"
    try:
        check_core_compat(e.get("core_version"), core_version_text)
    except RegistryError as exc:
        print(f"\nRefused: {exc} Nothing was fetched.", file=sys.stderr)
        return 1
    have = local.get(e["id"]) if isinstance(local, dict) else None
    if have and have.get("version") == e["version"]:
        meta = have.get("provenance")
        if meta and not meta.get("invalid") and meta.get("artifact_sha256") == e.get("artifact_sha256") and meta.get("commit") == e.get("ref"):
            print(f"\n{e['id']} {e['version']} is already installed with matching provenance. Nothing changed.")
            return 0
        print(f"\n{e['id']} {e['version']} is installed but its provenance differs. Selectu5 does not silently replace it.", file=sys.stderr)
        return 1
    try:
        data = fetcher(e) if fetcher is not None else fetch_distribution(e)
        result = install_package(e, data, skills_dir, core_version_text)
    except Exception as exc:
        print(f"Install failed: {exc}", file=sys.stderr)
        print(f"active location checked: {destination}", file=sys.stderr)
        print("Any completed backup keeps its unique transaction name in the skills root.", file=sys.stderr)
        return 1
    for action in result.get("recovered") or []:
        print(f"recovery: {action}")
    print(f"installed: {e['id']} {e['version']} -> {result['installed']}")
    if result.get("backup"):
        print(f"previous version kept at: {result['backup']}")
    print(f"xrpl-selectu5 {VERSION}: install complete. The new skill shows its own version on its next run.")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="selectu5")
    ap.add_argument("--offline", action="store_true", help="use only the bundled local catalog")
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
        try:
            return cmd_installed(local_skills(skills_dir), "local inventory (no registry used)")
        except RegistryError as exc:
            print(f"xrpl-selectu5 {VERSION}: {exc}", file=sys.stderr)
            return 1
    reg, source = load_registry(offline=args.offline)
    if reg is None:
        return 1
    try:
        local = local_skills(skills_dir)
    except RegistryError as exc:
        print(f"xrpl-selectu5 {VERSION}: {exc}", file=sys.stderr)
        return 1
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
