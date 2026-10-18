---
name: issue-flow
description: Orchestrate the optional GitLab issue workflow on an enabled project - detect the current issue/phase, resume from GitLab after context loss, mirror chat to issue comments, and dispatch to the start/refine/implement/mr/merge skills. TRIGGER when the user runs /issue, says "start/new issue", "what's the status of issue <IID>", "resume issue <IID>", "pause this issue", or when new work begins on a project with the gitlab-flow profile. SKIP when the project does not enable this workflow.
---

# Issue flow (orchestrator)

Follow rule `17-issue-workflow`. GitLab is the source of truth; the chat is
mirrored into the issue so any session can resume.

## Tool

```bash
PY=.agentictools/tools/gitlab-tool/.venv/bin/python
[ -x "$PY" ] || PY=python3
GL=".agentictools/tools/gitlab-tool/gitlab.py"
"$PY" "$GL" ...
```

## 1. Determine the active issue and phase

1. State file: `.agentictools/issue-flow/*.json` (one per active issue).
2. Current branch: if it matches `<iid>-<slug>`, that is the issue.
3. Otherwise ask which issue, or read the `status::` label:

```bash
"$PY" "$GL" issue-get <IID>
```

Map `status::*` → skill: `discussing`/`ready` → `issue-refine`;
`in-progress` → `issue-implement`; `review` → wait / `issue-implement` revision;
`mr-open` → `issue-mr`/`issue-merge`; `done` → nothing.

## 2. Resume after context loss / another session

Read the issue description and **all** comments in order; the mirrored
`**<user> says:**` / `**agent (<harness>):**` comments are the transcript.
Reconstruct the phase from the `status::` label and continue. Do not re-ask what
the issue already answers.

## 3. Mirroring

Before acting on any substantive user turn, post it verbatim, then post your
answer:

```bash
"$PY" "$GL" issue-note <IID> --body "**<username> says:**

<verbatim user text>"
"$PY" "$GL" issue-note <IID> --body "**agent (<harness>):**

<your answer>"
```

De-duplicate against the state file (`last_note_mirrored`) so retries or
answers already given on GitLab are not posted twice.

## 4. Start a new issue

If the user starts new work and confirms it is a new issue, use `issue-start`.

## 5. Pause / switch (parallel sessions)

- To pause: commit/push WIP, post a status comment, set `status::blocked` (or
  leave `in-progress`), update the state file, and switch to the default branch.
- Each issue belongs to one branch/worktree. For parallel work use another
  branch, `git worktree`, or another agent session.
- Never edit two issues in the same working tree.

## 6. Dispatch

Delegate to `issue-start`, `issue-refine`, `issue-implement`, `issue-mr`,
`issue-merge` as determined above, and keep the state file current.
