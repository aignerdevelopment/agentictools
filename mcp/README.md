# MCP integrations

Canonical MCP server definitions live in `servers.json`. Each entry holds the
per-target shape so `scripts/sync.sh` can emit the right file:

- Claude Code -> project `.mcp.json` (`mcpServers`)
- opencode -> `.opencode/opencode.json` (`mcp`, `type: local|remote`)
- Codex -> `.codex/config.toml` (`[mcp_servers.<name>]`)
- Antigravity -> workspace `.agents/mcp_config.json` (remote servers use
  `serverUrl`)

Never hardcode secrets: reference environment variables from
`.devenvironment/env.sh` (rule `07-devenvironment`). Use the client's native
syntax: `{env:MCP_API_TOKEN}` for opencode and `${MCP_API_TOKEN}` for Claude.
When adding a server that needs config/auth, add the matching key (with the
`<insert your .... here>` placeholder) to `.devenvironment/env.sh` and
`templates/project/.devenvironment/env.sh`. Register servers in
`../agentictools.json` under `modules.mcp` with a `targets` list.
