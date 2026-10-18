# Hooks

Lifecycle hooks, defined once and adapted per agent. Never copy hook logic into a
project; reference it.

```
hooks/
├── shared/        # agent-agnostic scripts (the real logic)
├── claude/        # Claude Code adapters (settings.json fragments)
└── opencode/      # opencode plugin adapters (.ts)
```

Each shared hook receives its context via environment variables and/or argv and
must be safe to run on every event. Register hooks in `../agentictools.json`
under `modules.hooks` with a `targets` list.

`scripts/sync.sh` merges the enabled adapters into the project's
`.claude/settings.json` and `.opencode/plugin/`.
