# Custom agents

Definitions for primary agents and subagents, grouped by target agent:

```
agents/claude/<id>.md      # Claude Code subagent
agents/opencode/<id>.md    # opencode agent
```

The same logical agent gets one thin file per target; the behavior lives in the
body, not duplicated logic. Register each in `../agentictools.json` under
`modules.agents` with the `targets` it supports. `scripts/sync.sh` symlinks only
the enabled, targeted files into the project.
