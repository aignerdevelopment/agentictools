---
name: issue-mr
description: Create the merge request for an approved GitLab issue - after the user says to create it, update the project documentation per rule 16, ensure the branch is pushed, create the MR idempotently with the gitlab-tool (squash, remove source branch), post the link to the issue and move to status::mr-open. TRIGGER when the user says "ok, create the MR", "open the merge request", or "go ahead" for an issue in status::review.
---

# Create the MR

Follow rule `17-issue-workflow`. Only run after the user explicitly approves
creating the MR.

## 1. Update project documentation (rule 16)

Run the `project-documentation` skill for the affected project(s) and commit the
`docs/project/**` changes on the current branch. If it cannot be updated, warn
the user and include a note in the MR description:
`project documentation not updated: <reason>`.

## 2. Ensure the branch is pushed

```bash
git add -A && git commit -m "#<iid> docs update" || true
git push -u origin <iid>-<slug>
```

## 3. Create the MR (idempotent)

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=.agentictools/tools/gitlab-tool/gitlab.py
"$PY" "$GL" mr-create \
  --source <iid>-<slug> --target <default_branch> \
  --title "#<iid>: <title>" \
  --description "Closes #<iid>

<summary + acceptance criteria outcomes>" \
  --squash --remove-source-branch
```

`mr-create` returns the existing open MR if one already exists, so it is safe to
re-run. Parse `iid` and `web_url` from the JSON.

## 4. Record and hand off

```bash
"$PY" "$GL" issue-note <iid> --body "**agent (<harness>):**

Merge request opened: !<mr_iid> (<web_url>)"
"$PY" "$GL" issue-label <iid> --remove "status::review" --add "status::mr-open"
```

Then wait for review/CI. The `issue-merge` skill handles merging.
