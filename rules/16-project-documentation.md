---
id: 16-project-documentation
tags: [core, always, docs]
always: true
---

# Project documentation discipline

Two kinds of documentation exist, and they are not interchangeable:

- `docs/wiki/` — the **discussion** record (rules `05-docs-wiki` and
  `06-development-status`): stakeholders, decisions, handover. Lives in the
  separate GitLab wiki repo.
- `docs/project/` — **architectural documentation that ships with the source
  code** (techstack, architecture, API reference, domain model, configuration,
  ADRs, integration guide, diagrams). It is intended to feed SBOM/CRA-style
  requirements. See the `project-documentation` skill.

## Update before the MR

When the user agrees to create the merge request for the current work, **first**
update the project documentation for the affected project(s) on the **current
working branch**, so the documentation merges together with the code:

1. Run the `project-documentation` skill for the affected project(s).
2. Write/update the files under `docs/project/**` following the guidelines in
   the central `project-documentation` tool.
3. Only then create the MR.

This applies whenever the project has the `project-documentation` tool enabled
(i.e. `.agentictools/tools/project-documentation` exists). Projects that do not
enable it are unaffected.

If the documentation cannot be updated (missing config, rendering failure,
unclear scope), **warn the user** and add a note to the MR description, e.g.
`project documentation not updated: <reason>`. Do not silently skip it and do
not block the MR unless the user wants that.

## Standard

The documentation standard/guidelines are part of the central
`project-documentation` tool. When you improve them, commit and push the change
to the agentictools repository (rule `00-agentictools-source-of-truth`), like any
other rule or skill.
