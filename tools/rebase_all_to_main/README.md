# rebase_all_to_main

Keeps a list of local repositories in sync with their remote branches: stashes
dirty state, fetches, rebases/fast-forwards, restores the stash, and prints a
summary. Windows-friendly (`.bat` launcher) but runs anywhere with Python 3.8+.

Wrapped as the `rebase-all-to-main` skill.

## Files

| File | Purpose |
|------|---------|
| `rebase_all_to_main.py` | Main script |
| `rebase_all_to_main.bat` | Windows launcher |
| `config.example.json` | Template — copy to `config.json` (local, gitignored) |

## Configure

```bash
cp config.example.json config.json
# edit config.json: root_dir, doc_branch, and the projects list
```

Config lives in this tool's local directory
(`.agentictools/tools/rebase_all_to_main/config.json`), not in the central repo.

## Usage

```bash
python rebase_all_to_main.py --list
python rebase_all_to_main.py --dry-run
python rebase_all_to_main.py -p my-project -p other-project
python rebase_all_to_main.py
```

Options: `-c/--config PATH`, `-n/--dry-run`, `-p/--project NAME` (repeatable),
`-l/--list`.

Per project: skips non-git dirs; stashes dirty trees; fetches; on the doc branch
rebases onto `origin/<main_branch>`, on the main branch fast-forwards, on other
branches skips; pops the stash; prints OK/SKIPPED/FAILED counts.
