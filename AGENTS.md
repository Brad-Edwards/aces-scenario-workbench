# ACES Scenario Workbench Agent Rules

This repository uses Ground Control for requirements management and workflow
automation. Run the repo lint and test gate before and after implementation
work.

## Ground Control Context

This repo's Ground Control project, workflow commands, SonarCloud settings, and
plan rules live in `.ground-control.yaml` at repo root (with the full plan
rules set under `.gc/plan-rules.md`). Agents read it via the
`gc_get_repo_ground_control_context` MCP tool, which returns the full workflow
config in a single call.

## Workflow Notes

- Pass full requirement UIDs exactly as they exist in Ground Control. Do not
  synthesize or rewrite requirement prefixes.
- Set `ACES_REQUIREMENT_UID` when the branch name does not already contain a
  UID such as `WB-001`.
- The required lint/test checks and hard rules are enforced by the `/implement`
  skill through the plan rules file referenced in `.ground-control.yaml` — see
  `.gc/plan-rules.md` for the authoritative list.
- Commit-time hooks are a separate contract from the committed
  `.pre-commit-config.yaml` and CI: every fresh clone must run
  `make hooks` (`scripts/install-hooks.sh`) once to activate them. See
  `CONTRIBUTING.md`.
