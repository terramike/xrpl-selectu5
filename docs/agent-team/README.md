# Selectu5 agent instructions

Use this directory as the shared instruction entry point.
The current review concerns PR #11 and PR #12.
This package does not approve installer enablement or publication.

## Read order

1. Read [the current audit](AUDIT-2026-10-11.md).
2. Read [the implementation plan](IMPLEMENTATION-PLAN.md).
3. Use [the current Codex goal](CODEX-GOAL.md) for this repair cycle.
4. Check [the evidence record](audit-evidence.json).
5. Read [the instruction history](INSTRUCTION-HISTORY.md) for earlier requirements.

The current goal replaces earlier starting-point instructions for this repair cycle.
It preserves earlier authority limits.
Historical approvals do not approve a different artifact or release.

## Team procedure

1. Check the current main commit before work.
2. Record the exact candidate commit.
3. Select one task identifier from the implementation plan.
4. Record the task owner in the pull request description.
5. Preserve changes from other agents.
6. Implement the task on a review branch.
7. Attach observed evidence to the pull request.
8. Update HANDOFF.md before a pause.

Do not force-update another agent's branch.
Do not infer permission to publish from this instruction upload.
The user requested an audit and shared instructions, not enablement.

## Existing specifications and prompts

- [Earlier production goal](../production/CODEX-GOAL.md).
- [Release checklist](../production/RELEASE-CHECKLIST.md).
- [Acceptance record](../production/ACCEPTANCE.md).
- [Evidence template](../production/evidence-template.json).
- [Fixed-asset design](../production/FIXED-ASSET-DESIGN.md).
- [Distribution decision](../production/DISTRIBUTION-DECISION.md).
- [Package inventory](../production/PACKAGE-INVENTORY.md).
- [Release automation](../production/RELEASE-AUTOMATION.md).
- [Operator actions](../production/OPERATOR-ACTIONS.md).
- [Skill instructions](../../SKILL.md).
- [Specification](../../SPEC.md).
- [Repair report](../../REPAIR-REPORT.md).
- [Historical audit packet](../../AUDIT-PACKET.md).

PR #11 proposes `docs/production/PRE-ENABLEMENT-REVIEW.md`.
PR #12 proposes `docs/production/BOOTSTRAP-AND-UPDATE.md`.
Read those files at their audited commits until the pull requests merge.
The current audit records those commit identities.

Instructions use STE100-based structure.
This description does not claim certified STE100 compliance.
