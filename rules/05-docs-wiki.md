---
id: 05-docs-wiki
tags: [core, always, docs]
always: true
---

# Development documentation lives in the project wiki (`docs/wiki`)

## Requirement

Every project **must** contain a `docs/wiki` directory: a clone of the project's
GitLab wiki. This wiki is the **root of all development documentation**.

If `docs/wiki` does not exist, stop and tell the developer exactly how to clone
it (below) before doing any documentation work.

## How to clone (GitLab)

The wiki is a separate git repository. Derive its URL from the project remote by
replacing the trailing `.git` with `.wiki.git`:

```sh
# SSH remote
git@gitlab.example.com:group/project.git   ->  git@gitlab.example.com:group/project.wiki.git
# HTTPS remote
https://gitlab.example.com/group/project.git -> https://gitlab.example.com/group/project.wiki.git
```

Clone it into `docs/wiki`:

```sh
git clone <project>.wiki.git docs/wiki

# if the wiki is brand new and the remote branch does not exist yet:
#   mkdir -p docs/wiki && git -C docs/wiki init
#   git -C docs/wiki remote add origin <project>.wiki.git
```

`docs/wiki/` is ignored by the main repository (see `.gitignore`); never commit
the wiki into the main repo. If the clone fails because the wiki is disabled or
the URL cannot be derived, ask the developer for the exact wiki clone URL and
GitLab access.

## Documentation root and table of contents

- Keep the wiki home page (`Home.md`) as the table of contents.
- For every content part, add one entry: a link to the subpage plus a one-line
  description of what it covers and when to read it.
- Link with relative wiki page names, e.g. `[Architecture](Architecture)` for
  `Architecture.md`.
- Write the content on its own subpage; do not bury everything in `Home.md`.
- Whenever you add, rename, move or delete a wiki page, update `Home.md` in the
  same change.
- Put durable knowledge (architecture, decisions, runbooks, onboarding) in the
  wiki, not in ad-hoc files in the main repo.

## Commit and push automatically

When you have written or changed wiki content **and** the task you were asked to
do is finished:

1. In `docs/wiki`, review `git status` and `git diff`.
2. Commit with a concise, descriptive, imperative message.
3. Push to the wiki remote (`git push`; set upstream on the first push).
4. Tell the user which pages changed, the commit message/hash, and that the push
   succeeded.

Do this automatically — do not wait for a separate instruction. If the push
fails (auth, conflicts, network), report the exact error and the command the
developer can run to resolve it; never force-push.

Never commit secrets, credentials or generated artifacts to the wiki.
