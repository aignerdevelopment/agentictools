---
name: issue-merge
description: Merge the MR for an approved GitLab issue and clean up - verify approval/CI, merge with the gitlab-tool (squash, remove source branch), switch back to the default branch and pull, delete the local branch, comment the outcome and set status::done. TRIGGER when the user or another agent says the MR is approved/merge it, for an issue in status::mr-open.
---

# Merge an issue

Follow rule `17-issue-workflow`. Only merge after approval and a passing
pipeline (or when the user explicitly says to merge).

## Tool

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=.agentictools/tools/gitlab-tool/gitlab.py
```

## 1. Find the MR and check state

```bash
"$PY" "$GL" mr-list --source-branch <iid>-<slug> --state opened
"$PY" "$GL" mr-get <mr_iid>
```

If the pipeline is still running and the user wants auto-merge, pass
`--when-pipeline-succeeds` below; otherwise wait for green.

## 2. Merge (squash, remove source branch)

```bash
"$PY" "$GL" mr-merge <mr_iid> --squash --remove-source-branch
# or, to auto-merge when the pipeline succeeds:
"$PY" "$GL" mr-merge <mr_iid> --squash --remove-source-branch --when-pipeline-succeeds
```

The tool passes the MR `sha` to avoid races. On failure it reports GitLab's exact
message (e.g. not mergeable, pipeline failing, conflicts) — surface it, do not
guess.

## 3. Clean up and close out

```bash
git checkout <default_branch> && git pull
git branch -d <iid>-<slug> || git branch -D <iid>-<slug>
```

```bash
"$PY" "$GL" issue-note <iid> --body "**agent (<harness>):**

Merged via !<mr_iid> (squash, source branch removed). On <default_branch>."
"$PY" "$GL" issue-label <iid> --remove "status::mr-open" --add "status::done"
```

Optionally close the issue (`issue-update <iid> --state-event close`). Update the
state file to `"phase": "done"` and move on to the next issue.
