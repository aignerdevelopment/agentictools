# gitlab-issue-tool

Downloads a full GitLab issue into `GITLAB/<project>/<iid>/` for offline
analysis (description, comments, system activity, and linked uploads /
attachments with archive extraction), mirroring `jira-tool`.

Wrapped as the `gitlab-issue` skill.

## Setup

```bash
pip install -r requirements.txt   # or use scripts/install.sh in the central repo
```

Configure via the project environment (`.devenvironment/env.sh`, first-class;
real values in the gitignored `env.local.sh`):

```sh
GITLAB_BASE_URL="https://gitlab.example.org"
GITLAB_TOKEN="..."
GITLAB_PROJECT_PATH="group/project"   # or GITLAB_PROJECT_ID
GITLAB_DIR="GITLAB"                    # output dir, relative to repo root
```

`config.json` is optional and only overrides the above.

## Usage

```bash
python gitlab_issue.py fetch 42                       # auto mode
python gitlab_issue.py fetch 42 --project group/proj  # override project
python gitlab_issue.py fetch 42 --mode update         # incremental
python gitlab_issue.py fetch 42 --mode fresh          # redownload everything
```

## Output

```
GITLAB/<project>/<42>/
├── issue.md          # metadata + description
├── comments.md       # user comments
├── activity.md       # system notes
├── index.md          # one-page orientation + links
├── metadata.json     # structured metadata
├── last_fetched.md   # fetch timestamp + attachment table (drives update mode)
└── files/            # downloaded uploads; archives (.zip/.tar*/.../.7z) extracted
```

Attachments are discovered from `/uploads/...` references in the description and
notes (GitLab has no separate attachment listing for issues), downloaded with
`PRIVATE-TOKEN` auth, deduplicated by filename, hashed with SHA-256, and archives
are auto-extracted into a sibling directory.
