---
name: gitlab-issue
description: Download or refresh a GitLab issue into GITLAB/<project>/<iid>/ for local analysis (description, comments, system activity, linked uploads/attachments). TRIGGER when the user says "download gitlab issue <IID>", "update issue <IID>", "fetch issue <IID>", "refresh <IID>", or names a project + issue IID together with download/fetch/update intent. SKIP for read-only API questions without an issue, or requests to create/edit/comment on an issue (this skill only downloads).
---

# GitLab issue download

Wraps `.agentictools/tools/gitlab-issue-tool/gitlab_issue.py`, which pulls a full
GitLab issue into `GITLAB/<project>/<iid>/` at the repo root for follow-up
analysis. Run from the **project root**.

## 1. Identify the issue

- Extract the IID (a number) from the user's message. If ambiguous, ask.
- Project: use `.devenvironment` `GITLAB_PROJECT_PATH` unless the user names one;
  if they do, pass `--project <path|id>`.

## 2. Handle missing project context

- On **gitlab.com** the project path may be unambiguous from context; if not,
  ask for `group/project`.
- Never invent the path or token; if `GITLAB_BASE_URL`/`GITLAB_TOKEN` are still
  placeholders, point at `.devenvironment/env.sh` / `env.local.sh` (rule
  `07-devenvironment`).

## 3. Classify intent and run

- "update/refresh/sync/re-fetch" → `--mode update`
- "download/fetch/get/pull" or no local dir yet → `--mode fresh`
- If `GITLAB/<project>/<iid>/` already exists and the user said "download",
  ask: redownload (fresh) vs update (incremental).

```bash
PY=.agentictools/tools/gitlab-issue-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
"$PY" .agentictools/tools/gitlab-issue-tool/gitlab_issue.py fetch <IID>
"$PY" .agentictools/tools/gitlab-issue-tool/gitlab_issue.py fetch <IID> --project group/project
"$PY" .agentictools/tools/gitlab-issue-tool/gitlab_issue.py fetch <IID> --mode update
```

## 4. Report

Point the user at `GITLAB/<project>/<IID>/index.md` as the entry point, mentioning
`issue.md`, `comments.md`, `activity.md`, `files/` (downloaded uploads, archives
extracted) and `metadata.json`. Do not read every file into context proactively.

This complements the `gitlab-tool` (live API read/write): use this one when the
issue needs to be analyzed offline, especially alongside its attachments/images.
