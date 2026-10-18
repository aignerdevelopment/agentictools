---
name: issue-refine
description: Conversational refinement of a GitLab issue in the optional issue workflow - mirror each substantive user turn and agent answer as issue comments, ask questions, propose acceptance criteria, and when complete rewrite the issue description to the full spec (what/why) plus acceptance criteria and move status::discussing to status::ready. TRIGGER while an issue is in status::discussing or status::ready, or when the user answers refinement questions for an active issue.
---

# Refine an issue

Follow rule `17-issue-workflow`. This is the core loop that turns "an idea" into
a precise, agreed spec, with a fully transparent history.

## Tool

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=.agentictools/tools/gitlab-tool/gitlab.py
```

## Each turn

1. **Mirror the user's message verbatim** (skip only trivial acknowledgements):

   ```bash
   "$PY" "$GL" issue-note <iid> --body "**<username> says:**

   <exact user text>"
   ```

2. **Answer and post the answer**:

   ```bash
   "$PY" "$GL" issue-note <iid> --body "**agent (<harness>):**

   <answer / updated understanding / questions / acceptance criteria>"
   ```

3. Update `.agentictools/issue-flow/<iid>.json` `last_note_mirrored`.
4. If the user gave images/files, download the issue with the `gitlab-issue`
   skill and read the attachments from `GITLAB/<project>/<iid>/files/`.

## Converge on acceptance criteria

- Keep a live `## Acceptance criteria` list; restate it after changes.
- Every criterion must be testable/demonstrable.
- Ask concise, numbered questions; never assume (rule
  `15-no-assumptions-ask-first`).

## When the user says it is complete

1. Rewrite the issue description with the final spec, preserving the original:

   ```bash
   "$PY" "$GL" issue-update <iid> --description "<full spec>

   ## Acceptance criteria
   - [ ] ...

   ## Original context
   <original text>"
   ```

2. Flip the label:

   ```bash
   "$PY" "$GL" issue-label <iid> --remove "status::discussing" --add "status::ready"
   ```

3. Post a short comment summarizing the final spec and that implementation
   starts next. Continue with `issue-implement`.
