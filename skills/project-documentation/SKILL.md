---
name: project-documentation
description: Generate, update, or check the architectural documentation that lives with the source code under docs/project/ (techstack, architecture, API reference, domain model, etc.), with Mermaid and PlantUML diagrams. TRIGGER when the user says "document <project>", "create/update docs for <project>", "check documentation completeness", "render diagrams for <project>", or before creating a merge request (rule 16-project-documentation). SKIP for reading already-generated docs or for docs/wiki discussion documentation.
---

# Project documentation

Wraps `.agentictools/tools/project-documentation/project_docs.py`. Produces
**architectural documentation that ships with the code** under `docs/project/`,
following the standard in
`.agentictools/tools/project-documentation/docs/DOCUMENTATION-GUIDELINES.md`
(part of the central tool — improve it there and commit to agentictools).

This is separate from `docs/wiki` (rules 05/06), which holds discussion and
decision documentation.

## 1. Identify project and action

- Project name = a `directory` in the tool's local `config.json`. Run
  `--list-projects` if unsure.
- Actions:
  - **document / create / update docs** → §2–3
  - **check completeness** → `--check-completeness` (read-only)
  - **render diagrams** → §3
  - **list projects** → `--list-projects` (read-only)

Use the tool venv if present:

```bash
PY=.agentictools/tools/project-documentation/.venv/bin/python
[ -x "$PY" ] || PY=python3
```

## 2. Generate the prompt, then write the docs yourself

`--create-docs` only writes a `.documentation-prompt.md`; you then read it and
write the actual files:

```bash
"$PY" .agentictools/tools/project-documentation/project_docs.py --create-docs --project <name>
```

1. Read `docs/project/<name>/.documentation-prompt.md`.
2. Follow it exactly: read the project's real source (never invent names,
   signatures or config keys) and write every required file plus applicable
   optional files, using the tool's `templates/` and the guidelines.
3. If docs already exist, update/extend them (do not blindly overwrite).
4. Ensure `docs/README.md` exists and points to `docs/project/`.

## 3. Render diagrams

After writing/updating `.mmd` / `.puml` sources:

```bash
python .agentictools/tools/project-documentation/scripts/render_mermaid.py --project <name>
python .agentictools/tools/project-documentation/scripts/render_plantuml.py --project <name>
```

Mermaid needs Node + `mmdc` + Chrome; PlantUML uses Kroki (or a local
`plantuml`). See the tool README if rendering fails.

## 4. Before creating the MR (rule 16)

When the user agrees to create the merge request, **first** ensure
`docs/project/**` is updated on the current working branch so it merges with the
code. If the docs cannot be updated, warn the user and add a note to the MR
description ("project documentation not updated: <reason>").

## 5. Scope guardrails

- Never write to `docs/wiki/` from this skill.
- Do not commit/push on a separate documentation branch; docs go on the working
  branch and merge with the code via the normal MR.
- Report the actual file paths written or updated.
