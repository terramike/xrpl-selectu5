# Codex goal — Selectu5 enablement repair

## Goal

Resolve findings A01 through A04 in the current Selectu5 audit.
Prepare a reviewable enablement candidate with accurate evidence and a defined bootstrap procedure.
Stop before installer enablement approval, publication, or real user installation.

## Read first

1. Read repository instructions, including AGENTS.md when present.
2. Read `docs/agent-team/README.md`.
3. Read `docs/agent-team/AUDIT-2026-10-11.md`.
4. Read `docs/agent-team/IMPLEMENTATION-PLAN.md`.
5. Read HANDOFF.md, SKILL.md, SPEC.md, and the production evidence documents.
6. Inspect PR #11 and PR #12 at their current heads.

## Starting identities

Main: `eb4c56ca94a53347e1579e44cf287459ca7f3e27`.
PR #11: `0bfb00a04b0161fd823775e1ffde3ec4254dbfc4`.
PR #12: `83d4452959ab9a2a60c21263aff2aa028ed1c852`.

These identities describe the audit baseline, not future work.
Record a newer baseline if either pull request changes.

## Required outcomes

- The recovery fixture uses a real production transaction.
- Recovery assertions require resolution of that transaction.
- Dummy credential-read instrumentation covers the claimed recovery operation.
- The printed command preserves bundled catalog authority.
- Bootstrap evidence binds exact code and artifact identities.
- Bootstrap no-op evidence proves zero fetches and zero mutation.
- CI retains bootstrap and build records on both platforms.
- The release documents describe the disabled first hop and manual external-client updates accurately.
- Mike receives a concrete release-model decision before enablement acceptance.

## Boundaries

Use disposable roots and dummy core and credential files.
Keep genuine credential files outside model context and tests.
Do not execute code from unreviewed packages.
Keep the production fetcher active during actual bootstrap installation.
Do not inject gate or trust overrides into shipped CLI qualification.
Synthetic tests may use existing disclosed function injection.
Separate synthetic, actual-artifact, inspected, and unperformed checks.

Do not merge the enablement candidate from broad historical authorization.
Do not publish a ZIP, release, or tag.
Do not change repository visibility or protection.
Do not install into a user's skills folder.
Do not broaden endpoint hosts or local catalog authority.
Do not modify companion repositories or core skill files.

## Completion

1. Complete each implementation-plan acceptance condition.
2. Confirm exact-head Linux and Windows CI.
3. Preserve raw structured evidence in retained CI artifacts.
4. Correct unsupported historical or candidate claims.
5. Update HANDOFF.md with tested identities and unresolved decisions.
6. Provide PR links, commands, results, and evidence locations.
7. State which release action still requires Mike's decision.

A passing suite does not approve installer enablement.
A successful merge does not approve publication.
A bootstrap pass does not prove a future published-artifact hop.

## Glossary

Client: the Selectu5 executable package used for an operation.
Predecessor: the older qualified package recorded in a client's bundled catalog.
S: the artifact source commit.
D: the artifact SHA-256 digest.
C: the subsequent catalog commit containing reviewed artifact identity.
I: the installer code checkout.
Q: the qualification code checkout.
No-op: an operation with zero artifact fetches and zero tree mutation.
