# jira-tool

Fetches a full Jira Cloud issue into a local directory for offline analysis
(defect description, Analysis/Workaround custom fields, comments, attachments).

Wrapped as the `jira-issue` skill.

## Setup

```bash
pip install -r requirements.txt   # or use scripts/install.sh in the central repo
```

Create a Jira API token at <https://id.atlassian.com/manage-profile/security/api-tokens>.

Configure via the project environment (`.devenvironment/env.sh`, first-class;
sourced automatically — real values in the gitignored `env.local.sh`):

```sh
JIRA_BASE_URL="https://yourorg.atlassian.net"   # no trailing slash
JIRA_EMAIL="you@example.com"
JIRA_API_TOKEN="..."
JIRA_DIR="JIRA"                                  # output dir, relative to repo root
```

`config.json` is optional and only needed for custom field-name overrides; if
present it is overridden by the `JIRA_*` env vars.

## Usage

```bash
python jira_tool.py fetch SYFU-12277                 # first fetch (fresh)
python jira_tool.py fetch SYFU-12277 --mode update   # incremental
python jira_tool.py fetch SYFU-12277 --mode fresh    # redownload everything
```

Output goes to `JIRA/<KEY>/` with `defect.md`, `analysis.md`, `workaround.md`,
`comments.md`, `index.md`, `metadata.json`, `last_fetched.md` and `files/`
(attachments deduplicated; archives auto-extracted).
