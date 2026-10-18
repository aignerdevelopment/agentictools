# Workflows

Multi-step, higher-level procedures that orchestrate skills, prompts and tools.
Written once, then materialised per target:

- Antigravity: `.agents/workflows/<id>.md` (deprecated in favour of skills;
  skills are also linked under `.agents/skills/`)
- opencode: `.opencode/command/<id>.md`
- Claude Code: `.claude/commands/<id>.md`
- Codex: `.codex/prompts/<id>.md`

Register each workflow in `../agentictools.json` under `modules.workflows` with
its `targets`. Keep workflows declarative: list the steps and the artifacts to
touch, not a fragile transcript.
