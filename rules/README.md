# Rules

Always-on, concise behavioral instructions. Each rule is a small markdown file.
Prefer many small rules over one huge one so projects can enable exactly what
they need.

Naming: `NN-slug.md` (the number orders them; keep them independent).

A rule may start with optional frontmatter:

```markdown
---
id: 10-code-style
tags: [style]
always: false
---

...
```

- `always: true` means "load this whenever the agentictools system is active",
  regardless of profile.
- Register every new rule in `../agentictools.json` under `modules.rules`.

The `00-agentictools-source-of-truth.md` rule is mandatory everywhere.
