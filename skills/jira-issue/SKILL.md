---
name: jira-issue
description: Fetch or refresh a Jira issue into JIRA/<KEY>/ for local analysis (defect, analysis, workaround, comments, attachments). TRIGGER when the user says "download <KEY>", "update <KEY>", "fetch jira issue <KEY>", "refresh <KEY>", "sync <KEY>", or mentions a Jira issue key together with download/fetch/update/refresh/sync intent. SKIP for general Jira questions without a specific key, or requests to create/edit/comment on an issue (this skill is read-only).
---

# Jira issue sync

Wraps `.agentictools/tools/jira-tool/jira_tool.py`, which pulls a full Jira
Cloud issue into `JIRA/<ISSUE-KEY>/` at the repo root for follow-up analysis.
Run from the **project root**.

## 1. Extract the issue key

Match `[A-Z][A-Z0-9]+-\d+` (e.g. `SYFU-12277`). If none, ask which issue.

## 2. Classify intent

- "update", "refresh", "sync", "re-fetch" → `update`
- "download", "fetch", "get", "pull", or no local dir yet → `download`

## 3. Check whether already downloaded

Check for `JIRA/<KEY>/index.md`.

| Intent | Dir exists? | Action |
|---|---|---|
| `update` | any | run `--mode update` directly |
| `download` | no | run `--mode fresh` directly |
| `download` | yes | ask: "Redownload (clear + refetch)" vs "Just update (incremental)"; then run the matching mode |

## 4. Run

Use the tool venv if `scripts/install.sh` created one:

```bash
PY=.agentictools/tools/jira-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" .agentictools/tools/jira-tool/jira_tool.py fetch <KEY> --mode fresh
"$PY" .agentictools/tools/jira-tool/jira_tool.py fetch <KEY> --mode update
```

Config comes from `.devenvironment/env.sh` (first-class):
`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, optional `JIRA_DIR`. If auth or
config fails, point the user at those keys (rule `07-devenvironment`); do not try
to fix credentials yourself.

## 5. Report

Point the user at `JIRA/<KEY>/index.md` as the entry point, mentioning
`defect.md`, `analysis.md`, `workaround.md`, `comments.md`, `files/` and
`metadata.json`. Do not read every file into context proactively.
