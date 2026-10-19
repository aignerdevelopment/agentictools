# agentictools

Central, single-source collection of everything an AI coding agent needs, shared
across **all** of my projects and **all** of my agents:

Published and consumed through [harnessator](https://github.com/aignerdevelopment/harnessator) -
the Terraform-for-AI-coding-agents tool this corpus dogfoods:

- rules
- skills
- prompts
- hooks
- custom agents / subagents
- workflows
- MCP integrations
- tools
- providers & model policies (governance)

Projects do **not** keep their own copies. They keep a tiny, checked-in
configuration plus redirect files that point at this repo. Only the modules a
project enables are ever loaded, so context stays small.

Supported agents (at least): **Claude Code**, **opencode**, **Codex**, **Antigravity**.

## The one rule that matters

> Every rule, skill, prompt, hook, custom agent, workflow, MCP integration and
> tool lives **in this repo**. A project only *references* them.
> See `rules/00-agentictools-source-of-truth.md`.

## Layout

```
agentictools/
├── AGENTS.md              # universal entry point (read by many agents)
├── CLAUDE.md              # Claude Code redirect -> AGENTS.md
├── harnessator.toml       # CANONICAL registry (harnessator source manifest)
├── agentictools.json      # LEGACY registry: same data, read by sync.sh until
│                          #   every project is on `harnessator setup`
├── agentictools.schema.json  # schema for per-project agentictools.config.json
├── rules/                 # always-on behavioral rules
├── skills/                # reusable SKILL.md packages
├── prompts/               # reusable prompt/command bodies
├── hooks/                 # lifecycle hooks + per-agent adapters
├── agents/                # custom agent / subagent definitions
├── workflows/             # multi-step workflows (Antigravity + slash commands)
├── mcp/                   # canonical MCP server definitions
├── tools/                 # custom tools
├── .devenvironment/       # environment variables (rule 07); env.local.sh gitignored
├── templates/project/     # files to copy into a project root
└── scripts/               # bootstrap / sync / new-project
```

## How a project consumes this

1. Run the bootstrapper in the project root (copies redirect files, fills in the
   central path):

   ```sh
   AGENTICTOOLS_HOME=/path/to/agentictools \
     /path/to/agentictools/scripts/bootstrap.sh .
   ```

2. Edit the generated `agentictools.config.json`: choose a `profile` and/or list
   the exact modules to `include`/`exclude`.

3. Materialise the enabled modules into the project (symlinks per item + generated
   MCP/hook config), so only enabled modules are visible to the agent:

   ```sh
   AGENTICTOOLS_HOME=/path/to/agentictools \
     /path/to/agentictools/scripts/sync.sh .
   ```

4. Commit the redirect files + `agentictools.config.json`. Do **not** commit the
   generated, machine-specific artifacts (see `.gitignore`).

## Configuration in one glance

`agentictools.config.json` (project root):

```json
{
  "$schema": "/path/to/agentictools/agentictools.schema.json",
  "agentictoolsHome": "/path/to/agentictools",
  "profile": "minimal",
  "rules":   { "include": [], "exclude": [] },
  "skills":  { "include": ["example-skill"] },
  "mcp":     { "include": ["example-remote"] },
  "options": { "maxRules": 8, "targets": ["opencode", "claude", "codex"] }
}
```

- `profile` pulls a named preset from `agentictools.json`.
- `include`/`exclude` refine it (`"*"` = everything in that category).
- `options.maxRules` caps how many rule files are loaded.
- `options.targets` limits which agents get generated artifacts.

Adding something new? Add it here and register it in `agentictools.json`; never
add it to an individual project.

## Optional GitLab issue workflow

Projects can enable the `gitlab-flow` profile for an adaptive, conversational
issue workflow (rule `17-issue-workflow`): one issue ↔ one branch ↔ one MR,
chat mirrored into the issue as `**<username> says:**` / `**agent (<harness>):**`
comments, scoped `type::*` / `status::*` labels, project docs updated before the
MR (rule 16), and a review gate before merge. Entry point: the `/issue`
workflow (`workflows/issue.md`) plus the `issue-flow`, `issue-start`,
`issue-refine`, `issue-implement`, `issue-mr` and `issue-merge` skills. GitLab
operations use `tools/gitlab-tool/` (Python; encoded paths, idempotent MR
creation, safe merge). Project issue templates live in
`templates/project/.gitlab/issue_templates/`.
