---
id: 18-docs-sync
tags: [core, docs]
---

# Documentation duty: every doc current with every change

## Requirement

When a change alters functionality or any user-facing surface - CLI
commands, flags, file formats, environment variables, configuration keys,
prerequisites, install or usage behavior - **all affected documentation is
updated in the same change-set**, never "later":

1. **README** - pitch, feature list, quick start.
2. **Usage documentation** (e.g. `USAGE.md`) - the full command/parameter
   reference with examples. One new or changed flag means one edit here.
3. **Build/installation documentation** (e.g. `BUILDING.md`) - toolchain,
   prerequisites, cross-OS builds, packaging.
4. **Man pages** (e.g. `man/man1/*`, `man/man5/*`) - regenerate/update
   whenever the command surface changes; they are part of the product.
5. **Wiki** - decision log and proposal pages per rules
   `05-docs-wiki` and `06-development-status`.

Stale documentation is a defect: treat it as blocking the MR. If something
cannot be updated (missing info, unclear scope), warn and add a note to the
MR description - never silently skip it.

## Why

Users and AI agents act on the docs; a wrong flag in a man page or a
missing prerequisite in BUILDING.md costs them a broken run and their
trust. Documentation that lives in the repository but is not maintained is
worse than no documentation, because it lies with authority.

## Apply

- Keep examples runnable: after a flag rename, `grep -rn` the docs for the
  old spelling within the same commit.
- Prefer deriving: where possible generate or check docs from code
  (usage text, schema); where hand-written, re-read the touched command
  against `--help` before committing.
