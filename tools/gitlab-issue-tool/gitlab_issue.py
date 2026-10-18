#!/usr/bin/env python3
"""
GitLab Issue Sync Tool

Downloads a full GitLab issue (description, comments/notes, system activity and
linked uploads/attachments) into GITLAB/<project>/<iid>/ for offline analysis,
mirroring the jira-tool workflow.

Configuration is read from the project environment (first-class,
.devenvironment/env.sh):
    GITLAB_BASE_URL, GITLAB_TOKEN,
    GITLAB_PROJECT_PATH or GITLAB_PROJECT_ID, GITLAB_DIR (default: GITLAB)
A local config.json is optional and only overrides these.

Usage:
    python gitlab_issue.py fetch <IID> [--project PATH|ID] [--mode fresh|update]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

try:  # optional, only needed for .7z attachments
    import py7zr
except ImportError:  # pragma: no cover
    py7zr = None

ARCHIVE_EXTS = ('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.7z')
PER_PAGE = 100


@dataclass
class GitLabConfig:
    base_url: str
    token: str
    project_path: str
    project_id: str
    gitlab_dir: Path
    project_override: str = ""

    @property
    def project_ref(self) -> str:
        """Value to use in the API path: numeric id or URL-encoded path."""
        if self.project_id:
            return self.project_id
        if self.project_path:
            return urllib.parse.quote(self.project_path, safe='')
        return urllib.parse.quote(self.project_override, safe='')

    @property
    def project_label(self) -> str:
        if self.project_path:
            return self.project_path
        if self.project_id:
            return f"id-{self.project_id}"
        return self.project_override

    @property
    def output_root(self) -> Path:
        return self.gitlab_dir / self.project_label.replace('/', '__')


def load_devenvironment() -> None:
    """Load <repo-root>/.devenvironment/env.sh into os.environ (rule 07)."""
    root = Path.cwd()
    for candidate in (root, *root.parents):
        if (candidate / '.devenvironment' / 'env.sh').exists():
            root = candidate
            break
    else:
        return
    try:
        out = subprocess.run(['sh', '-c', '. ./.devenvironment/env.sh >/dev/null 2>&1; env -0'],
                             cwd=str(root), capture_output=True, text=True, timeout=30).stdout
    except Exception:  # noqa: BLE001
        return
    entries = out.split('\0') if '\0' in out else out.splitlines()
    if not entries:
        try:
            out = subprocess.run(['sh', '-c', '. ./.devenvironment/env.sh >/dev/null 2>&1; env'],
                                 cwd=str(root), capture_output=True, text=True, timeout=30).stdout
        except Exception:  # noqa: BLE001
            return
        entries = out.splitlines()
    for entry in entries:
        key, sep, value = entry.partition('=')
        if sep:
            os.environ.setdefault(key, value)


def load_config(config_path: Path, project_override: str) -> GitLabConfig:
    raw: dict = {}
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

    base_url = os.environ.get('GITLAB_BASE_URL', raw.get('base_url', '')).rstrip('/')
    token = os.environ.get('GITLAB_TOKEN', raw.get('token', ''))
    project_path = os.environ.get('GITLAB_PROJECT_PATH', raw.get('project_path', ''))
    project_id = os.environ.get('GITLAB_PROJECT_ID', raw.get('project_id', ''))
    gitlab_dir_raw = os.environ.get('GITLAB_DIR', raw.get('gitlab_dir', 'GITLAB'))

    project_override = project_override or ''
    if project_override:
        if project_override.isdigit():
            project_id = project_override
            project_path = ''
        else:
            project_path = project_override
            project_id = ''

    for key, value in (("GITLAB_BASE_URL", base_url), ("GITLAB_TOKEN", token)):
        if not value or "<insert your" in value:
            print(f"Error: {key} is not configured; set it in .devenvironment/env.local.sh (rule 07).")
            sys.exit(1)
    if not project_path and not project_id:
        print("Error: no project set. Set GITLAB_PROJECT_PATH / GITLAB_PROJECT_ID or pass --project.")
        sys.exit(1)

    gitlab_dir_path = Path(gitlab_dir_raw)
    gitlab_dir = gitlab_dir_path if gitlab_dir_path.is_absolute() else (Path.cwd() / gitlab_dir_path).resolve()

    return GitLabConfig(
        base_url=base_url,
        token=token,
        project_path=project_path,
        project_id=project_id,
        gitlab_dir=gitlab_dir,
        project_override=project_override,
    )


class GitLabClient:
    """Thin wrapper around the GitLab REST API v4."""

    def __init__(self, config: GitLabConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "PRIVATE-TOKEN": config.token,
            "Accept": "application/json",
        })

    def _api(self, path: str) -> str:
        return f"{self.config.base_url}/api/v4/projects/{self.config.project_ref}{path}"

    def get_issue(self, iid: str) -> dict:
        resp = self.session.get(self._api(f"/issues/{iid}"))
        resp.raise_for_status()
        return resp.json()

    def get_notes(self, iid: str) -> list:
        notes = []
        page = 1
        while True:
            resp = self.session.get(
                self._api(f"/issues/{iid}/notes"),
                params={"per_page": PER_PAGE, "sort": "asc", "order_by": "created_at", "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            notes.extend(batch)
            if len(batch) < PER_PAGE:
                break
            page += 1
        notes.sort(key=lambda n: n.get("created_at", ""))
        return notes

    def download(self, url: str, dest: Path) -> None:
        resp = self.session.get(url, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_upload_refs(text: str) -> list:
    """Find /uploads/... references (absolute or project-relative) in markdown/HTML."""
    if not text:
        return []
    refs = set()
    for m in re.finditer(r'https?://[^\s)"\'<>\]]+', text):
        url = m.group(0).split('#')[0].split('?')[0]
        if '/uploads/' in url:
            refs.add(url)
    # Search relative references only outside absolute URLs.
    stripped = re.sub(r'https?://[^\s)"\'<>\]]+', ' ', text)
    for m in re.finditer(r'(?<![:/])/(?:[^\s)"\'<>\]]*?/)?uploads/[^\s)"\'<>\]]+', stripped):
        refs.add(m.group(0).split('#')[0].split('?')[0])
    return sorted(refs)


def normalize_url(ref: str, base_url: str, project_path: str) -> str:
    if ref.startswith('http'):
        return ref
    if ref.startswith('/uploads/') and project_path:
        return f"{base_url}/{project_path}{ref}"
    if ref.startswith('/'):
        return f"{base_url}{ref}"
    return ref


def parse_last_fetched(path: Path) -> dict:
    """Parse a previous last_fetched.md into {upload_path: filename}."""
    result = {}
    if not path.exists():
        return result
    in_table = False
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped.startswith("| Upload Path"):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            in_table = False
            continue
        if set(stripped) <= set("|-: "):
            continue
        parts = [p.strip() for p in stripped.strip("|").split("|")]
        if len(parts) < 2:
            continue
        result[parts[0]] = parts[1]
    return result


def unique_filename(files_dir: Path, name: str) -> str:
    candidate = name
    stem, dot, ext = name.rpartition('.')
    counter = 1
    while (files_dir / candidate).exists():
        if dot:
            candidate = f"{stem} ({counter}).{ext}"
        else:
            candidate = f"{name} ({counter})"
        counter += 1
    return candidate


def extract_archive(archive: Path, files_dir: Path) -> None:
    dest = files_dir / archive.name[: -len(''.join(archive.suffixes))] if archive.suffixes else files_dir / archive.stem
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    try:
        if name.endswith('.zip'):
            with zipfile.ZipFile(archive) as z:
                z.extractall(dest)
        elif name.endswith(('.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.tar')):
            with tarfile.open(archive) as t:
                t.extractall(dest)
        elif name.endswith('.7z'):
            if py7zr is None:
                print(f"  (skipping {archive.name}: py7zr not installed)")
                return
            with py7zr.SevenZipFile(archive) as z:
                z.extractall(dest)
        else:
            return
        print(f"  extracted: {archive.name} -> {dest}")
    except Exception as exc:  # noqa: BLE001 - best effort
        print(f"  (could not extract {archive.name}: {exc})")


def process_attachments(client: "GitLabClient", refs: list, files_dir: Path,
                        previous: dict, mode: str) -> list:
    files_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    current_refs = set()
    seen_paths = set()

    for ref in refs:
        url = normalize_url(ref, client.config.base_url, client.config.project_path)
        upload_path = urllib.parse.urlparse(url).path
        if '/uploads/' in upload_path:
            upload_path = '/uploads/' + upload_path.split('/uploads/', 1)[1]
        else:
            upload_path = url
        if upload_path in seen_paths:
            continue
        seen_paths.add(upload_path)
        current_refs.add(upload_path)

        filename = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name) or 'attachment'
        dest = files_dir / filename

        if mode == 'update' and upload_path in previous:
            existing = files_dir / previous[upload_path]
            if existing.exists():
                rows.append({
                    "upload_path": upload_path, "filename": previous[upload_path],
                    "sha256": sha256_of(existing), "size": existing.stat().st_size,
                    "status": "skipped",
                })
                continue

        if dest.exists():
            dest = files_dir / unique_filename(files_dir, filename)
        try:
            print(f"  downloading: {filename}")
            client.download(url, dest)
        except requests.HTTPError as exc:
            print(f"  (could not download {url}: {exc})")
            continue

        rows.append({
            "upload_path": upload_path, "filename": dest.name,
            "sha256": sha256_of(dest), "size": dest.stat().st_size,
            "status": "downloaded",
        })
        if dest.name.lower().endswith(ARCHIVE_EXTS):
            extract_archive(dest, files_dir)

    for upload_path, filename in previous.items():
        if upload_path not in current_refs and (files_dir / filename).exists():
            existing = files_dir / filename
            rows.append({
                "upload_path": upload_path, "filename": filename,
                "sha256": sha256_of(existing), "size": existing.stat().st_size,
                "status": "orphaned",
            })

    return rows


def build_issue_md(issue: dict) -> str:
    lines = [f"# {issue.get('title', '(untitled)')}", ""]
    lines.append(f"- **Issue:** {issue.get('references', {}).get('full', '') or issue.get('iid', '')}")
    lines.append(f"- **State:** {issue.get('state', '')}")
    lines.append(f"- **Author:** {(issue.get('author') or {}).get('name', '')}")
    assignees = ", ".join(a.get('name', '') for a in issue.get('assignees') or [])
    lines.append(f"- **Assignees:** {assignees or '-'}")
    lines.append(f"- **Labels:** {', '.join(issue.get('labels') or []) or '-'}")
    milestone = (issue.get('milestone') or {}).get('title', '')
    lines.append(f"- **Milestone:** {milestone or '-'}")
    lines.append(f"- **Created:** {issue.get('created_at', '')}")
    lines.append(f"- **Updated:** {issue.get('updated_at', '')}")
    if issue.get('closed_at'):
        lines.append(f"- **Closed:** {issue.get('closed_at')}")
    if issue.get('due_date'):
        lines.append(f"- **Due:** {issue.get('due_date')}")
    lines.append(f"- **Confidential:** {issue.get('confidential', False)}")
    lines.append(f"- **Web:** {issue.get('web_url', '')}")
    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(issue.get('description') or "_(no description)_")
    lines.append("")
    return "\n".join(lines)


def build_comments_md(notes: list) -> str:
    user_notes = [n for n in notes if not n.get('system')]
    lines = ["# Comments", ""]
    if not user_notes:
        lines.append("_(no comments)_")
        return "\n".join(lines) + "\n"
    for n in user_notes:
        author = (n.get('author') or {}).get('name', 'unknown')
        lines.append(f"## {author} — {n.get('created_at', '')}")
        lines.append("")
        lines.append(n.get('body') or '')
        lines.append("")
    return "\n".join(lines)


def build_activity_md(notes: list) -> str:
    system_notes = [n for n in notes if n.get('system')]
    lines = ["# Activity (system notes)", ""]
    if not system_notes:
        lines.append("_(none)_")
        return "\n".join(lines) + "\n"
    for n in system_notes:
        lines.append(f"- {n.get('created_at', '')} — {(n.get('body') or '').strip()}")
    lines.append("")
    return "\n".join(lines)


def build_metadata(issue: dict, notes: list, attachment_rows: list) -> dict:
    return {
        "iid": issue.get('iid'),
        "title": issue.get('title'),
        "state": issue.get('state'),
        "url": issue.get('web_url'),
        "author": (issue.get('author') or {}).get('username'),
        "assignees": [a.get('username') for a in issue.get('assignees') or []],
        "labels": issue.get('labels') or [],
        "milestone": (issue.get('milestone') or {}).get('title'),
        "created_at": issue.get('created_at'),
        "updated_at": issue.get('updated_at'),
        "closed_at": issue.get('closed_at'),
        "due_date": issue.get('due_date'),
        "confidential": issue.get('confidential', False),
        "user_notes_count": issue.get('user_notes_count', 0),
        "comments": len([n for n in notes if not n.get('system')]),
        "attachments": [
            {"path": r["upload_path"], "filename": r["filename"], "sha256": r["sha256"]}
            for r in attachment_rows if r["status"] != "orphaned"
        ],
    }


def build_index_md(issue: dict, has_attachments: bool, fetched_at: str) -> str:
    lines = [f"# {issue.get('title', '(untitled)')}", ""]
    lines.append(f"GitLab issue {issue.get('references', {}).get('full', '')} — {issue.get('state', '')}")
    lines.append("")
    lines.append("| File | Contents |")
    lines.append("|---|---|")
    lines.append("| `issue.md` | metadata + description |")
    lines.append("| `comments.md` | user comments |")
    lines.append("| `activity.md` | system activity |")
    lines.append("| `metadata.json` | structured metadata |")
    if has_attachments:
        lines.append("| `files/` | downloaded attachments (archives extracted) |")
    lines.append("")
    lines.append(f"Fetched: {fetched_at}")
    lines.append(f"Web: {issue.get('web_url', '')}")
    lines.append("")
    return "\n".join(lines)


def build_last_fetched_md(fetched_at: str, docs: list, rows: list) -> str:
    lines = ["# Last Fetched", "", f"Fetched: {fetched_at}", "", "## Generated documents", ""]
    for d in docs:
        lines.append(f"- {d}")
    lines += ["", "## Attachments", "",
              "| Upload Path | Filename | SHA256 | Size (bytes) | Status |",
              "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['upload_path']} | {r['filename']} | {r['sha256']} | {r['size']} | {r['status']} |")
    lines.append("")
    return "\n".join(lines)


def collect_upload_refs(issue: dict, notes: list) -> list:
    texts = [issue.get('description') or '']
    texts += [n.get('body') or '' for n in notes]
    refs = set()
    for t in texts:
        refs.update(find_upload_refs(t))
    return sorted(refs)


def fetch_issue(iid: str, config: GitLabConfig, mode: str) -> None:
    issue_dir = config.output_root / iid
    files_dir = issue_dir / "files"
    last_fetched_path = issue_dir / "last_fetched.md"

    if mode == 'fresh' and issue_dir.exists():
        print(f"Clearing existing directory: {issue_dir}")
        shutil.rmtree(issue_dir)

    previous = parse_last_fetched(last_fetched_path) if mode == 'update' else {}
    issue_dir.mkdir(parents=True, exist_ok=True)

    client = GitLabClient(config)

    print(f"Fetching {config.project_label}#{iid} from {config.base_url} ...")
    issue = client.get_issue(iid)

    print("Fetching notes ...")
    notes = client.get_notes(iid)

    (issue_dir / "issue.md").write_text(build_issue_md(issue) + "\n", encoding='utf-8')
    (issue_dir / "comments.md").write_text(build_comments_md(notes), encoding='utf-8')
    (issue_dir / "activity.md").write_text(build_activity_md(notes), encoding='utf-8')

    refs = collect_upload_refs(issue, notes)
    print(f"Processing {len(refs)} attachment reference(s) ({mode} mode) ...")
    attachment_rows = process_attachments(client, refs, files_dir, previous, mode)

    (issue_dir / "metadata.json").write_text(
        json.dumps(build_metadata(issue, notes, attachment_rows), indent=2, ensure_ascii=False) + "\n",
        encoding='utf-8',
    )

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    has_attachments = any(r["status"] != "orphaned" for r in attachment_rows)
    (issue_dir / "index.md").write_text(
        build_index_md(issue, has_attachments, fetched_at) + "\n", encoding='utf-8'
    )

    docs = ["issue.md", "comments.md", "activity.md", "index.md", "metadata.json"]
    last_fetched_path.write_text(build_last_fetched_md(fetched_at, docs, attachment_rows), encoding='utf-8')

    print(f"\nDone. Issue bundle written to: {issue_dir}")
    print(f"Start here: {issue_dir / 'index.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='GitLab Issue Sync Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fetch 42
  %(prog)s fetch 42 --project group/project
  %(prog)s fetch 42 --mode update
        """,
    )
    sub = parser.add_subparsers(dest='command')
    fetch = sub.add_parser('fetch', help='Fetch or update a GitLab issue')
    fetch.add_argument('iid', type=str, help='GitLab issue IID, e.g. 42')
    fetch.add_argument('--project', default='', help='Project path (group/project) or numeric id (overrides env)')
    fetch.add_argument('--mode', choices=['fresh', 'update'], default=None,
                       help='fresh = clear and redownload; update = incremental (default: auto-detect)')
    fetch.add_argument('--config', '-c', type=Path, default=Path(__file__).parent / 'config.json',
                       help='Path to optional configuration JSON (default: config.json)')

    args = parser.parse_args()
    if args.command != 'fetch':
        parser.print_help()
        return 1

    load_devenvironment()
    config = load_config(args.config, args.project)
    issue_dir = config.output_root / args.iid
    mode = args.mode or ('update' if issue_dir.exists() else 'fresh')

    try:
        fetch_issue(args.iid, config, mode)
    except requests.HTTPError as exc:
        print(f"Error: GitLab API request failed: {exc}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
