---
description: Optional GitLab issue workflow - start, refine, implement, open the MR, merge. Discovers the active issue/phase and dispatches.
---

Drive the optional GitLab issue workflow (rule `17-issue-workflow`) using the
`issue-flow` skill.

- `new` — start a new issue (`issue-start`)
- `status [<iid>]` — show the active issue and its `status::` phase
- `resume [<iid>]` — reconstruct state from the issue and continue
- `pause [<iid>]` — checkpoint the current issue and switch away
- otherwise — infer the action from the active issue's phase

Mirror substantive user turns to the issue as `**<username> says:**` followed by
the exact text, then post the agent answer as `**agent (<harness>):**`.

Arguments:
$ARGUMENTS
