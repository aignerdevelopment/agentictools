# Prompts

Reusable prompt bodies. Sync materialises them as slash commands:

- opencode: `.opencode/command/<name>.md`
- Claude Code: `.claude/commands/<name>.md`
- Antigravity: workflow under `.agents/workflows/`
- Codex: prompt under `.codex/prompts/`

Each prompt is plain markdown. Use `$ARGUMENTS` for opencode/Claude command
input. Register each prompt in `../agentictools.json` under `modules.prompts`.
