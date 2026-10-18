# project-documentation

Generates and maintains **architectural documentation that lives with the
source code** in `docs/project/`, so it ships with the code and can later feed
SBOM/CRA-style tooling.

This is **not** the same as `docs/wiki`:

| | `docs/project/` (this tool) | `docs/wiki/` (rules 05/06) |
|---|---|---|
| Audience | Developers, build/audit tooling | Stakeholders, discussion, decisions |
| Lives | In the repo, merged with the code | Separate GitLab wiki clone |
| Updated | On the working branch, before the MR | When decisions/discussion happen |

## Layout

```
docs/
├── README.md                 # points to docs/project/
├── project/                  # generated architectural documentation
│   ├── <project>/index.md
│   ├── <project>/techstack.md (+ .yaml)
│   ├── <project>/architecture.md
│   ├── <project>/api-reference.md
│   ├── <project>/domain-model.md
│   ├── <project>/configuration.md
│   ├── <project>/design-decisions.md
│   ├── <project>/integration-guide.md
│   └── <project>/...         # optional: messaging.md, protocols.md
└── wiki/                     # separate git repo (rule 05)
```

The documentation **standard/guidelines** are part of this central tool:
`docs/DOCUMENTATION-GUIDELINES.md`. Editing them here improves every project;
commit and push the change to the agentictools repo.

## Install

Python 3.10+. Diagram rendering additionally needs:

- Mermaid: Node.js + `@mermaid-js/mermaid-cli` (`mmdc`) + Chrome/Chromium.
- PlantUML: nothing (uses the public Kroki service) or a local `plantuml`.

Per-tool Python dependencies are installed by `scripts/install.sh` (see the
central repo), into `.agentictools/tools/project-documentation/.venv`.

## Configure

Copy `config.example.json` to `config.json` in this directory (local,
gitignored) and list your projects. The docs output directory defaults to
`docs/project` and can be overridden with `PROJECT_DOCS_DIR`.

## Usage

```bash
# Generate the documentation prompt for a project, then write the docs yourself
python project_docs.py --create-docs --project <name>

# Render diagrams
python project_docs.py --render-diagrams --project <name>
python scripts/render_mermaid.py --project <name>
python scripts/render_plantuml.py --project <name>

# Coverage check
python project_docs.py --check-completeness
```

`--create-docs` only writes `.documentation-prompt.md`; the agent then writes
the actual documentation files following `docs/DOCUMENTATION-GUIDELINES.md`.
