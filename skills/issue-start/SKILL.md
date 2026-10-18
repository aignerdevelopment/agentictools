---
name: issue-start
description: Start the optional GitLab issue workflow - confirm it is a new issue and whether it is a feature/bug/chore, create the issue with the type and status::discussing labels, create the <iid>-<slug> branch, and post the understanding, draft acceptance criteria and questions as a comment. TRIGGER on "/issue new", "start a new issue", or when new work is detected and the user confirms it is a new issue on a gitlab-flow project.
---

# Start an issue

Follow rule `17-issue-workflow`. Mirror first, then act.

## 1. Confirm (never auto-create)

Ask, unless already answered:

- "New issue, or part of the current one?"
- "Feature, bug, or chore?"
- A short title (propose one from the description).

## 2. Mirror the user's start message

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=.agentictools/tools/gitlab-tool/gitlab.py
"$PY" "$GL" issue-create --title "<title>" \
  --description "<original text, verbatim>" \
  --labels "type::<feature|bug|chore>,status::discussing"
```

Then read the returned `iid`.

## 3. Branch

```bash
git checkout <default_branch> && git pull
git checkout -b <iid>-<slug>
```

## 4. Post understanding, acceptance criteria, questions

Post the user's message verbatim with the `**<username> says:**` prefix, then
your answer:

```bash
"$PY" "$GL" issue-note <iid> --body "**<username> says:**

<verbatim>"
"$PY" "$GL" issue-note <iid> --body "**agent (<harness>):**

**Understanding:** ...
**Draft acceptance criteria:**
- [ ] ...
**Questions:**
1. ..."
```

Ask about images/specs explicitly. Then continue in `issue-refine`.

## 5. State file

Create `.agentictools/issue-flow/<iid>.json`:

```json
{"iid": <iid>, "branch": "<iid>-<slug>", "type": "<type>", "phase": "discussing",
 "last_note_mirrored": <note_id>, "created_at": "<iso>"}
```
