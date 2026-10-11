# Selectu5 implementation plan

This plan addresses the current audit findings A01 through A04.
Use the exact commit identities in the audit report as the repair baseline.
Check for newer commits before edits.

## Authority

Agents may implement fixes, run isolated tests, and prepare review pull requests.
Agents must not infer enablement approval from this plan.
Agents must not publish a release or install into a user skills folder.
Preserve the disabled gate on main until Mike approves the exact enablement change.
Do not broaden catalog trust or transport host rules.
Do not modify core skills, credentials, or companion repositories.

## Task A01 — Repair recovery evidence

Owner: the agent responsible for qualification code.

1. Use the production recovery directory constant.
2. Create a transaction through the engine or its production schema.
3. Use a valid transaction identifier and identity fields.
4. Interrupt a real directory move in a disposable root.
5. Record the unresolved production journal before recovery.
6. Instrument dummy credential reads during the recovery operation.
7. Count public core-manifest reads separately.
8. Assert a specific restoration or completion action.
9. Assert the fixture journal reaches its expected terminal state.
10. Compare restored package content and provenance with the baseline.
11. Check repeat recovery and a subsequent permitted operation.
12. Add a regression that removes or misplaces the fixture journal.
13. Require that regression to fail the claimed recovery check.
14. Correct PR #11's evidence description.

Acceptance: a fresh install cannot satisfy the recovery check.
Acceptance: a prohibited dummy credential read fails the instrumented check.
Acceptance: partial evidence identifies setup, recovery, or assertion failure.

## Task A02 — Repair the printed command

Owner: the agent responsible for CLI behavior.

1. Preserve `--offline` in the real-install command for bundled authority.
2. Keep the global option before the install subcommand.
3. Keep the exact version and plan digest in the command.
4. Explain browse-only catalog refusal before suggesting a real install.
5. Add an isolated test that executes the printed arguments.
6. Test changed plans, missing plans, and wrong versions.
7. Require zero fetches and zero mutation for those refusals.

Acceptance: the displayed command uses the authority reviewed in the dry run.
Acceptance: remote catalog data never gains installation authority.

## Task A03 — Strengthen bootstrap evidence

Owner: the agent responsible for packaging and CI.

1. Add an exact expected client version.
2. Add an exact expected client package root.
3. Record the candidate ZIP SHA-256 and byte count.
4. Validate the candidate archive before extraction.
5. Reject multiple roots and unexpected archive structures.
6. Record qualification checkout, installer checkout, platform, and Python version.
7. Record predecessor S, D, version, package root, and fixed asset URL.
8. Distinguish local development builds from independently rebuilt release-prep artifacts.
9. Assert expected candidate and installed gate states.
10. Bind `SELECTU5_CORE_DIR` to the disposable dummy core.
11. Control inherited catalog overrides and record all test environment settings.
12. Compare installed artifact bytes and provenance with reviewed identity.
13. Compare complete tree snapshots before and after the repeat operation.
14. Measure zero production fetches during the repeat operation.
15. Keep production transport active for the real installation case.
16. Do not inject gate or catalog trust into shipped CLI qualification.
17. Write partial evidence before risky operations.
18. Retain bootstrap JSON and the candidate build record with `if: always()`.
19. Retain both Linux and Windows evidence.
20. Return nonzero when a mandatory check fails or remains blocked.

Acceptance: missing, corrupted, or incorrectly identified packages cannot pass.
Acceptance: a mutated no-op tree cannot pass.
Acceptance: reviewers can download structured evidence from both CI jobs.

## Task A04 — Define the release model

Owner: Mike selects the model. An agent documents and tests it.

The current candidate requires an external release client for each new catalog authority.
The first hop installs the disabled 0.2.5 client.
This is a documented limit, not an enabled installed-store demonstration.

1. Describe the first hop with exact client and installed versions.
2. State which client performs every later update.
3. State how the user obtains and checks that external client.
4. State how its bundled catalog acquires reviewed authority.
5. Describe version lag without claiming installation of the newest package.
6. Mark the next published-artifact hop blocked until its artifact exists.
7. Preserve installed packages and backups during withdrawal.
8. State that withdrawal cannot revoke an older bundled catalog automatically.
9. Replace premature shipped or production-complete claims with candidate status.
10. Record Mike's release-model decision separately from consent confirmation.

Do not add signed catalogs or remote authorization as a routine repair.
Prepare a separate design if Mike selects that model.

## Final verification

1. Run the meaningful regression tests for each finding.
2. Run the repository suite.
3. Run synthetic qualification with corrected recovery instrumentation.
4. Run bootstrap qualification through the shipped CLI.
5. Preserve actual Stage 3 results as separately identified evidence.
6. Confirm all required Linux and Windows jobs on the final candidate head.
7. Record PR checkout and synthetic merge checkout separately.
8. Update acceptance, checklist, review document, and HANDOFF.md.
9. Request the required pull request review.
10. Present exact remaining release decisions to Mike.

Do not mark future artifact checks as passed.
Do not reuse historical CI as proof for changed code.
