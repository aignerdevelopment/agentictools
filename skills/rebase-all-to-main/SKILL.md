---
name: rebase-all-to-main
description: Keep the configured list of local repositories in sync with their remote branches - stash dirty state, fetch, rebase/fast-forward, restore stash, and report a summary. TRIGGER when the user says "rebase all repos", "sync all projects", "update all repos to main", or asks to bring a set of local repos up to date. SKIP for single-repo git operations.
---

# Rebase all to main

Wraps `.agentictools/tools/rebase_all_to_main/rebase_all_to_main.py`, which
processes the repositories listed in its local `config.json`. Run from the
**project root**.

## Configure

The tool's config is local and gitignored:

```bash
.agentictools/tools/rebase_all_to_main/config.json
```

If it does not exist, copy the example and fill in the repo list:

```bash
cp .agentictools/tools/rebase_all_to_main/config.example.json \
   .agentictools/tools/rebase_all_to_main/config.json
```

Fields: `root_dir` (base containing all repos), `doc_branch` (default `docs`),
`projects[]` (`directory`, `main_branch`, optional `doc_branch`), and
`behavior` flags.

## Run

```bash
PY=.agentictools/tools/rebase_all_to_main/.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" .agentictools/tools/rebase_all_to_main/rebase_all_to_main.py --dry-run
"$PY" .agentictools/tools/rebase_all_to_main/rebase_all_to_main.py
```

Options: `--list`, `--dry-run`, `-p/--project NAME` (repeatable),
`-c/--config PATH`.

## Report

Summarize the OK / SKIPPED / FAILED counts. On conflicts, leave the repo clean
(the tool aborts rebases by default) and tell the user which repo needs manual
resolution, with the exact commands.
