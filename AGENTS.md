# AGENTS.md

<!-- agentictools:central -->

This repository is the **central, single source of truth** for all agentic
configuration. Any project that adopts it delegates here instead of keeping its
own rules, skills, prompts, hooks, custom agents, workflows, MCP integrations or
tools.

## For agents working in a *consumer* project

If you are in a project whose root contains `agentictools.config.json`:

1. Read `agentictools.config.json` first.
2. Load **only** the modules it enables (see `.agentictools/active.md` if it
   exists, otherwise resolve against `${AGENTICTOOLS_HOME}/agentictools.json`).
3. Never create or edit rules/skills/prompts/hooks/agents/workflows/MCP/tools in
   that project. Add them here and reference them from the project.
4. The canonical instructions are in this file plus the enabled rule files.

## Mandatory rules (binding on every agent and harness)

These apply to **every** AI coding harness (Claude Code, opencode, Codex,
Antigravity, Cursor, ...) and every human contributor working in *this*
repository, exactly as they apply to consumer projects. Harness-specific note
files must reference them, not restate or weaken them.

- `rules/00-agentictools-source-of-truth.md` — all agent artifacts live here.
- `rules/05-docs-wiki.md` — `docs/wiki` must exist (GitLab wiki clone); it is
  the documentation root with a table of contents; commit and push wiki changes
  automatically when a task is finished.
- `rules/06-development-status.md` — `docs/wiki/DEVELOPMENT-STATUS.md` is the
  standing decision log and diary; record non-obvious decisions in the same
  change-set.
- `rules/07-devenvironment.md` — load `.devenvironment/env.sh` before any
  build/setup or configured tool/MCP call; add new config/auth keys with the
  `<insert your .... here>` placeholder.
- `rules/16-project-documentation.md` — update `docs/project/**` architectural
  documentation before creating the MR (separate from `docs/wiki`).

## For agents working in *this* repository

- **Dual registry during transition (2026-10):** `harnessator.toml` is the
  canonical registry (source manifest); `agentictools.json` is its legacy
  mirror, still read by `scripts/sync.sh` until every consuming project
  runs `harnessator setup`. When adding or changing a module, update BOTH
  files in the same commit. Projects already migrated to harnessator
  ignore the legacy files entirely.
- Add a new artifact in its category folder and register it in
  `agentictools.json` (id, path, tags, description).
- Keep each file small and focused; context is a scarce resource.
- Never duplicate an artifact across category folders or per-agent folders. The
  per-agent folders (`hooks/<agent>`, `agents/<agent>`) only hold thin adapters.

<!-- /agentictools:central -->
