---
id: 00-agentictools-source-of-truth
tags: [core, always]
always: true
---

# Single source of truth for agent configuration

In every project that checks in an `agentictools.config.json`:

1. **All** agentic artifacts live in the central `agentictools` repository:
   rules, skills, prompts, hooks, custom agents, workflows, MCP integrations and
   tools. They are **not** kept in the consuming project.
2. The project only contains **references**: the redirect files created by
   `scripts/bootstrap.sh` and the `agentictools.config.json` selection.
3. Never create, copy or edit a rule/skill/prompt/hook/agent/workflow/MCP
   integration/tool inside a consuming project. Instead:
   - add it to `agentictools` and register it in `agentictools.json`, then
   - enable it from the project's `agentictools.config.json`.
4. When a project-specific rule is unavoidable, capture it as an override in the
   project's config (e.g. `rules.exclude`) rather than as a local copy — or, if
   it is genuinely reusable, upstream it to the central repo.
5. Load only the modules the project enables. Do not eagerly read the whole
   central repo.
