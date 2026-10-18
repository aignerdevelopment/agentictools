---
id: 17-issue-workflow
tags: [gitlab, workflow]
always: false
---

# Optional GitLab issue workflow

Binding **only** for projects that enable it (select this rule or the
`gitlab-flow` profile). It replaces the old Discussion → ToDo flow.

## Core model

- **One issue ↔ one branch ↔ one MR.** Branch name `<iid>-<slug>`. Never mix two
  issues in one working tree; for parallel work use separate branches/worktrees
  or separate agent sessions.
- **GitLab is the single source of truth.** The chat is ephemeral. Every step
  must be reconstructable from the issue alone (a fresh agent can resume by
  reading it). Record live state in `.agentictools/issue-flow/<iid>.json`.

## Mirroring (transparent history)

For every substantive turn during an issue:

1. Post the user's instruction as a comment, verbatim:
   `**<username> says:**` followed by the exact text.
2. Post the agent's answer as a comment: `**agent (<harness>):**`.
3. De-duplicate: before posting, check the issue notes/state file so a retry or
   a message already given on GitLab is not posted twice.
4. Trivial acknowledgements/greetings may be batched; instructions, decisions
   and answers are always mirrored.

## Labels

- Type (choose one): `type::feature`, `type::bug`, `type::chore`.
- Status (exactly one): `status::discussing`, `status::ready`,
  `status::in-progress`, `status::review`, `status::mr-open`, `status::done`,
  plus `status::blocked` and `status::wontfix` when needed.

## Phases and gates

1. **discussing** — issue created (or detected + confirmed); branch created;
   agent posts understanding, draft acceptance criteria and questions; refine
   until the user says it is complete.
2. **ready** — rewrite the issue description to the full spec (what and why)
   plus acceptance criteria, preserving the original under `## Original
   context`.
3. **in-progress** — implement on the branch; commit and push at working
   checkpoints (reference `#<iid>` in messages); post progress comments.
4. **review** — post a detailed completion comment (what changed, acceptance
   criteria outcomes, how to verify) and **stop**. Do not push further until the
   user requests a revision.
5. **mr-open** — once the user approves, update `docs/project/**` (rule
   `16-project-documentation`), then create the MR with the `gitlab-tool`
   (`--remove-source-branch --squash`); post the link.
6. **done** — after approval / green pipeline, merge (squash, remove source
   branch), switch to the default branch and pull, delete the local branch, set
   `status::done`, and move on to the next issue.

## Rules

- Never create an issue without explicit user confirmation.
- Never merge without approval or a passing pipeline.
- Use the Python `gitlab-tool` for all GitLab operations; do not hand-roll curl.
- Commit often on the branch; keep the default branch clean.
- Non-obvious decisions still go to `docs/wiki/DEVELOPMENT-STATUS.md` (rule 06).
