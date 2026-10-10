# Fixed-asset delivery design (Stage 2)

Status: implemented behind the existing disabled installer gate. No asset is published by this design, and no catalog entry becomes installable until Mike approves a concrete pilot distribution.

## Problem

The current transport downloads `https://github.com/<owner>/<repo>/archive/<commit>.zip`. That path needs unauthenticated access, so a private repository returns 404. GitHub also generates source archives on demand; a fixed commit does not guarantee permanent ZIP bytes. Distribution must therefore use one reviewed ZIP uploaded as a release asset, with the complete SHA-256 verified before extraction.

## Identities (keep separate)

| Symbol | Meaning |
|---|---|
| S | Source commit used to create the package |
| D | SHA-256 of the complete distributed ZIP |
| C | Reviewed catalog commit that records S, D, and the package root |
| I | Installer code commit used for qualification |
| Q | Qualification code commit / CI checkout identity |

A catalog cannot contain the digest of its own future archive. Build from S, calculate D, then record D in a later reviewed catalog commit C. Never reuse a version for changed package bytes.

## Catalog extension (compatible with `selectu5-registry/1`)

Existing entries stay valid. A skill entry may add one optional object:

```json
"distribution": {
  "type": "github_release_asset",
  "source_commit": "<full 40-char commit S>",
  "asset_url": "https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>.zip",
  "asset_name": "<asset>.zip"
}
```

Rules enforced by the catalog validator:

- `distribution` is allowed only on `kind: "skill"` entries; the validator refuses it on core and showcase entries.
- `type` must be `github_release_asset`.
- `source_commit` must equal the entry's pinned `ref` (S).
- `asset_url` is checked as an original string before parsing: controls, whitespace, backslashes, percent-encoded separators/NUL, and dot components are refused, and malformed ports or non-string values raise `RegistryError`. It must then be HTTPS on `github.com`, with no credentials, no non-443 port, and the exact path `/<owner>/<repo>/releases/download/<tag>/<asset>` for the entry's approved owner/repository pair.
- `asset_name` must equal the final path component of `asset_url`.
- An entry with `distribution` must also carry `ref`, `artifact_sha256` (D), and `package_root`; otherwise the catalog is malformed and refused, not silently downgraded.
- Old list-only entries without `distribution` display exactly as before.

## Plan binding

The canonical installation plan now includes the distribution type, source commit, asset URL, and asset name when present. A changed asset locator, digest, permissions card, or canonical destination changes the plan digest and needs new approval. A plan digest proves content consistency only; it does not prove human consent.

## Transport policy

- With `distribution`, the fetcher uses the recorded `asset_url` instead of the generated `/archive/<commit>.zip` URL.
- The initial URL must be the validated `github.com` release-asset URL above.
- Redirects must stay on HTTPS, carry no credentials, and land only on approved hosts: `github.com`, `codeload.github.com`, `release-assets.githubusercontent.com`, or `objects.githubusercontent.com` (GitHub-operated asset delivery hosts). The observed redirect chain must still be recorded during Stage 3 qualification; a new host not on this list is refused.
- Redirect targets are never written to approval cards or evidence with query strings; if a signed redirect ever carries temporary query credentials, record host and path only.
- Existing limits stay: 60-second total download deadline, 25 MiB download limit, archive/member/expanded limits, digest verification before extraction, destination validation, locking, journals, and backup verification.
- No private-token delivery is added. A private repository stays a transport blocker until Mike chooses a distribution model.

## Packaging

`scripts/package.py` builds one deterministic ZIP from an explicit inventory:

- fixed member order (sorted), fixed timestamps, fixed permissions, fixed compression;
- refuses absolute paths, traversal, credential-like file names, and duplicate or case-colliding inventory paths;
- refuses symlink, junction, and reparse-point components in every source path, and verifies each resolved file stays inside the source root before reading it;
- validates the finished ZIP with the installer's own archive validator before writing successful package evidence;
- `--verify-rebuild` requires a second independent clean export (`--export-b`) and the recorded source commit S, and refuses any byte difference. Records carry the source commit and build-tool versions; working-tree builds are labeled `development-working-tree`, clean-export builds `clean-export-rebuild`.

Installation always uses the published asset's exact bytes; reproducibility of the build does not replace digest verification.

## Stage gates

- Stage 2 acceptance: fixed assets reach the existing verification/installation engine without weakening boundaries; Linux and Windows CI pass at the final PR head; `INSTALL_ENABLED` remains `False`.
- Stage 3 performs real retrieval/installation/update qualification only after Mike approves the concrete pilot distribution.
