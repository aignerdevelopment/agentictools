---
name: issue-implement
description: Implement an issue in the optional GitLab issue workflow - work on the <iid>-<slug> branch following the agreed spec, commit and push at working checkpoints with #<iid> references, post progress comments, and when finished post a detailed completion comment mapping each acceptance criterion to its outcome and move to status::review. TRIGGER when an issue is status::ready to start implementation on a gitlab-flow project.
---

# Implement an issue

Follow rule `17-issue-workflow`.

## 1. Start

- Ensure you are on the issue branch `<iid>-<slug>` and up to date.
- Set status:

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=.agentictools/tools/gitlab-tool/gitlab.py
"$PY" "$GL" issue-label <iid> --remove "status::ready" --add "status::in-progress"
```

## 2. Work

- Follow the issue's spec and acceptance criteria exactly; ask instead of
  guessing (rule `15-no-assumptions-ask-first`).
- Commit and push at **working checkpoints** (build/tests green), messages
  referencing the issue, e.g. `#<iid> add validation`:

  ```bash
  git add -A && git commit -m "#<iid> <what>" && git push
  ```

- Post concise progress comments for meaningful milestones (mirror the rule:
  `**agent (<harness>):**`).
- Keep `docs/wiki/DEVELOPMENT-STATUS.md` current for non-obvious decisions
  (rule `06-development-status`).

## 3. Finish

- Run the project's tests/lint; do not declare done on a red build.
- Post the completion comment:

```bash
"$PY" "$GL" issue-note <iid> --body "**agent (<harness>):**

**Done:** <detailed summary of changes (files, behaviour)>

**Acceptance criteria:**
- [x] <criterion> — <how it was verified>
- [ ] <criterion> — <why not / how to check>

**How to verify:** <commands / steps>"
```

- Set status and **stop** (hard freeze — no further pushes until requested):

```bash
"$PY" "$GL" issue-label <iid> --remove "status::in-progress" --add "status::review"
```

Answer review feedback via `issue-refine`/revision; only proceed to `issue-mr`
after the user approves.
