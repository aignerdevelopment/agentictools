# Project templates

Files to copy into a **consuming project root**. They contain no real agent
configuration — only a redirect to this central repo plus a selection config.

`scripts/bootstrap.sh <target>` copies everything under
`templates/project/` into `<target>/`, replacing the `{{AGENTICTOOLS_HOME}}`
placeholder with the resolved central path. Existing files are never
overwritten.

Generated afterwards by `scripts/sync.sh <target>` (gitignore them in the
project):

- `.agentictools/active.md` / `.agentictools/active.json` — the enabled modules
- `.mcp.json`, `.codex/config.toml`, `.claude/settings.json` — merged MCP + hooks
- `.claude/skills`, `.opencode/skill`, `.agents/skills`, ... — symlinks to
  only the enabled modules

What each copied file is for:

| File | Agent |
| --- | --- |
| `AGENTS.md` | universal (opencode, Codex, Antigravity) |
| `CLAUDE.md` | Claude Code |
| `.claude/settings.json` | Claude Code base settings |
| `.codex/config.toml` | Codex CLI |
| `.agents/rules/agentictools.md` | Antigravity |
| `agentictools.config.json` | the selection, read by every agent |

opencode needs no committed config file beyond `AGENTS.md`: `sync.sh` generates
`.opencode/opencode.json` with the redirect instructions plus enabled MCP
servers.
