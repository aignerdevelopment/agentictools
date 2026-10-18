# AGENTS.md

<!-- agentictools:managed -->
This project delegates **all** agent configuration to the central
**agentictools** repository. Nothing here except references.

- Central repo: `{{AGENTICTOOLS_HOME}}`
- Selection: `./agentictools.config.json`
- Enabled modules: `.agentictools/active.md` (regenerate with
  `{{AGENTICTOOLS_HOME}}/scripts/sync.sh .`)

## Required behaviour (every agent)

1. Read `./agentictools.config.json` first.
2. Load **only** the modules it enables — never scan the whole central repo.
3. Do not create or edit rules/skills/prompts/hooks/agents/workflows/MCP/tools
   in this project. Add them to the central repo and enable them here.
4. The canonical entry point is `{{AGENTICTOOLS_HOME}}/AGENTS.md`.

## Mandatory rule

All agentic artifacts live in the central repo; this project only references
them. See
`{{AGENTICTOOLS_HOME}}/rules/00-agentictools-source-of-truth.md`.
<!-- /agentictools:managed -->
