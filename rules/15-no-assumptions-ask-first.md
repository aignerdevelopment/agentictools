---
id: 15-no-assumptions-ask-first
tags: [process]
always: false
---

# No assumptions — ask first

When requirements, scope, priorities, interfaces or data are unclear, do not
guess. Ask the user before acting, and state the question plainly.

- If something is ambiguous, stop and ask; do not silently pick an
  interpretation.
- When you must proceed on an assumption to keep moving, make it explicit
  ("Assumption: ...") and record it in `docs/wiki/DEVELOPMENT-STATUS.md` in the
  same change-set (rule `06-development-status`).
- Prefer a short clarifying question over a large wrong change.
- Never invent credentials, URLs, config values or identifiers. If a
  `.devenvironment/env.sh` key is still `<insert your .... here>`, ask for the
  value (rule `07-devenvironment`).
- Surface rejected alternatives when they matter for the decision.
