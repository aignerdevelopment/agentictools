---
id: 06-development-status
tags: [core, always, docs]
always: true
---

# Development status documentation discipline (all agents/harnesses)

This rule is binding for every AI coding harness (Claude Code, opencode, Codex,
Cursor, ...) and every human contributor working in this repository.
Harness-specific note files must reference it, not restate or weaken it.

In the `docs/wiki` project there must exist `DEVELOPMENT-STATUS.md`, and it is
the standing decision log and development diary, not just a feature checklist.
Its "Non-Obvious Outcomes" and dated decision entries are the project memory;
treat keeping it current as part of definition of done, not as optional
cleanup.

Document every non-obvious product, architecture, implementation, UX,
shell-integration, storage, or portability decision in the same change-set that
introduces it — never "later". A decision is non-obvious when a future human or
agent could otherwise not reconstruct why the code is shaped this way (tradeoffs
rejected, platform quirks worked around, constraints honored).

Each entry is a dated `###` heading containing: **Decision**, **Why**,
**Consequence**, and **Source**. The source is either a specification file under
version control or a verbatim `User order: "<instruction>"` quote from the user.
Do not paraphrase user orders; quote them.

Add one entry per module extraction or refactor that records the new seam: what
moved where, what the public surface of the new module is, and what boundary it
establishes — so future sessions know the structure without re-deriving it from
the code.

Keep the **Implemented / Current Behavior / Not Yet Implemented** checklists in
sync with the code in the same commit. A shipped feature must never remain
listed as pending, and a regression must never leave a checked box unchecked.

When a change makes a README statement stale (scope, features, project
structure, workflows), update `README.md` in the same change-set.

If a session ends (crash, context loss, handover) mid-task, write progress notes
to a `progress/` directory at the repo root so the next session can resume;
reference the notes from the decision-log entry once the work lands.
