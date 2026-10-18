---
id: 20-git-workflow
tags: [git]
always: false
---

# Git workflow

- Never commit unless the user explicitly asks.
- Before committing: inspect `git status`, `git diff` and `git log --oneline -10`.
- Stage only the files that belong to the change; never commit secrets.
- Write concise, imperative commit messages that match the repo's style.
- Do not amend or force-push unless the user explicitly asks.
- Prefer a feature branch per change; keep history clean and linear.
