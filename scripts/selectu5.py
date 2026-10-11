#!/usr/bin/env python3
"""xrpl-selectu5 2.0.0 — Selectu5, the XRPL Muse skill menu.

Companion skill. Menu mode: it lists the curated XRPL Muse skill family,
shows each skill's purpose and permissions, and checks installed
versions against the registry. It installs nothing and modifies nothing
outside reading. It never proposes, never signs, never reads seeds,
keys, tokens, or policy files.
"""
import argparse
import io
import json
import os
import re
import stat
import sys
import urllib.parse
import urllib.request
import zipfile

VERSION = "2.0.0"
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

LIMITS = {
    "archive_members": 2000,
    "expanded_total": 100 * 1024 * 1024,
    "expanded_file": 20 * 1024 * 1024,
    "manifest_bytes": 64 * 1024,
    "member_path": 240,
    "download_bytes": 25 * 1024 * 1024,
}

WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|version|access):\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.M)


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



def local_skills(skills_dir):
    found = {}
    if not os.path.exists(skills_dir):
        return found
    _root_components(skills_dir)  # raises on any supplied symlink component
    if not os.path.isdir(skills_dir):
        raise RegistryError("skills root is not a directory")
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
        found[name] = {"version": version, "path": os.path.join(skills_dir, name)}
    for folder, entry_id in {"xrpl": "xrpl-muse-skill"}.items():
        if folder in found and entry_id not in found:
            found[entry_id] = found[folder]
    return found


LAST_CATALOG = {}



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



def header(source=None):
    print(f"xrpl-selectu5 {VERSION} — Selectu5, the XRPL Muse skill menu")
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



def esc(text):
    """Escape control characters so catalog text cannot drive the terminal."""
    return CONTROL_RE.sub(lambda m: "\\x%02x" % ord(m.group(0)), str(text))



def _check_text(value, field, limit):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise RegistryError(f"{field}: must be text of 1..{limit} chars")
    if CONTROL_RE.search(value):
        raise RegistryError(f"{field}: control characters are not allowed")



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



def validate_registry(reg):
    """Menu-mode registry validation: identity and text safety only.
    Install-authority fields (ref, artifact_sha256, package_root) are not
    required and not checked; v2 installs nothing."""
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
            raise RegistryError(f"{eid}: id must match xrpl-<name>")
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
        perm = e.get("permissions")
        if not isinstance(perm, dict):
            raise RegistryError(f"{eid}: permissions must be an object")
        for key in ("commands", "files"):
            if not isinstance(perm.get(key), list) or not all(isinstance(x, str) for x in perm[key]):
                raise RegistryError(f"{eid}: permissions.{key} must be a list of text")
        for key in ("network", "signs"):
            _check_text(perm.get(key), f"{eid} permissions.{key}", 200)
    return reg


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
        cmp = compare_versions(have["version"], e["version"])
        if cmp is None:
            unknown.append((e, have["version"]))
        elif cmp < 0:
            updates.append((e, have["version"]))
        elif cmp > 0:
            newer.append((e, have["version"]))
        else:
            current.append(e)
    if updates:
        print("\nupdates available:")
        for e, have in updates:
            if e["kind"] == "core":
                print(f"  {e['id']}: {have} -> {e['version']} — notice only; update it yourself from {esc(e['repo'])}")
            else:
                print(f"  {e['id']}: {have} -> {e['version']} — get it at {esc(e['repo'])}")
        print("\nSelectu5 never installs updates. Follow the repo link above.")
    if newer:
        print("\nnewer than the catalog:")
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
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="selectu5.py", description="Selectu5: browse the XRPL Muse skill family and check versions.")
    ap.add_argument("--offline", action="store_true", help="use only the bundled registry file")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list every catalog entry")
    show_p = sub.add_parser("show", help="show one entry's card")
    show_p.add_argument("id")
    sub.add_parser("installed", help="list local skills and versions")
    sub.add_parser("check-updates", help="compare installed versions against the catalog")
    sub.add_parser("version", help="print the Selectu5 version")
    args = ap.parse_args(argv)
    if args.cmd == "version":
        print(f"xrpl-selectu5 {VERSION}")
        return 0
    if args.cmd is None:
        ap.print_help()
        return 2
    skills_dir = os.environ.get("SELECTU5_SKILLS_DIR", DEFAULT_SKILLS_DIR)
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
