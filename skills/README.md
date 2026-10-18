# Skills

Reusable, on-demand capabilities. Each skill is a folder containing `SKILL.md`
plus any supporting files (scripts, references).

```
skills/<skill-name>/SKILL.md
```

`SKILL.md` frontmatter:

```markdown
---
name: skill-name
description: What it does AND when to trigger it. Front-load trigger keywords.
---
```

Works as-is for opencode (`.opencode/skill(s)/`) and Claude Code
(`.claude/skills/`). `scripts/sync.sh` symlinks only the skills a project
enables, so disabled skills never enter context.

Register each skill in `../agentictools.json` under `modules.skills`.
