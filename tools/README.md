# Tools

Shared tools agents can call. A tool is **either a single file** (e.g. a shell
script, or an opencode `.ts` tool) **or a directory** (a self-contained package
with a script, templates, `requirements.txt`, etc.).

`scripts/sync.sh` materialises every enabled tool into the project:

- file tool  -> `.agentictools/tools/<basename>`
- directory tool -> `.agentictools/tools/<id>/` (a real dir containing symlinks
  to each central file, so central edits propagate; local state such as
  `config.json` and `.venv` stays local because `.agentictools/` is gitignored)
- opencode `*.ts` tools are additionally linked into `.opencode/tool/`

Configuration/credentials come from `.devenvironment/env.sh`
(rule `07-devenvironment`), never hardcoded.

## Install dependencies

```sh
AGENTICTOOLS_HOME=/path/to/agentictools AGENTICTOOLS_HOME/scripts/install.sh /path/to/project
```

`install.sh` reads the project's `.agentictools/active.json` and, for each
directory tool with a `requirements.txt`, creates
`.agentictools/tools/<id>/.venv` and installs the requirements there.

## Current tools

| id | kind | description |
|---|---|---|
| `example-tool` | file (`.ts`) | template opencode tool |
| `gitlab-tool` | dir | GitLab issues/MRs/labels CLI (`issue-*` skills) |
| `gitlab-issue-tool` | dir | download GitLab issues + attachments (`gitlab-issue` skill) |
| `jira-tool` | dir | fetch Jira Cloud issues locally (`jira-issue` skill) |
| `project-documentation` | dir | architectural docs under `docs/project/` (`project-documentation` skill) |
| `rebase_all_to_main` | dir | multi-repo git sync (`rebase-all-to-main` skill) |

Register tools in `../agentictools.json` under `modules.tools` with `path` and
`targets`.
