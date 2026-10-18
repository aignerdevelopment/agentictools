#!/usr/bin/env python3
"""
Jira Issue Sync Tool

Fetches a full Jira Cloud issue (description, analysis/workaround fields,
comments, attachments) into a local directory for offline analysis
(e.g. with the clouseau or log-analysis skills).

Usage:
    python jira_tool.py fetch SYFU-12277
    python jira_tool.py fetch SYFU-12277 --mode fresh
    python jira_tool.py fetch SYFU-12277 --mode update
    python jira_tool.py fetch SYFU-12277 --config /path/to/config.json
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False

try:
    import html2text
except ImportError:
    print("Error: html2text is required. Run: pip install -r requirements.txt")
    sys.exit(1)


@dataclass
class JiraConfig:
    base_url: str
    email: str
    api_token: str
    jira_dir: Path
    analysis_field_name: str
    workaround_field_name: str
    extra_fields: dict


# Custom fields seen on IN-project ("Inbox") issues, beyond the fields every
# issue type has. Keyed by output name in metadata.json; value is the Jira
# field display name to resolve via the issue's `names` map. Issues that
# don't have a given field simply report an empty value for it.
DEFAULT_EXTRA_FIELDS = {
    "product_description": "Product Description",
    "requires_documentation": "Requires documentation",
    "severity": "Severity",
    "found_in_version": "Found in Version",
    "customer_project": "Customerproject",
    "reaction_until": "Reaction until",
    "reacted_date": "Reacted date",
    "fixed_in_build": "Fixed in build",
    "third_party_tracker_id": "3rd party tracker id",
}


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


def load_config(config_path: Path) -> JiraConfig:
    """Load configuration from JSON (if present), overridden by JIRA_* env vars.

    Credentials should live in .devenvironment/env.sh / env.local.sh:
    JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_DIR (optional).
    A local config.json is optional and only needed for field-name overrides.
    """
    raw: dict = {}
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

    base_url = os.environ.get('JIRA_BASE_URL', raw.get('base_url', '')).rstrip('/')
    email = os.environ.get('JIRA_EMAIL', raw.get('email', ''))
    api_token = os.environ.get('JIRA_API_TOKEN', raw.get('api_token', ''))

    for key, value in (("JIRA_BASE_URL", base_url), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", api_token)):
        if not value or "<insert your" in value:
            print(f"Error: {key} is not configured; set it in .devenvironment/env.local.sh (rule 07).")
            sys.exit(1)

    jira_dir_raw = os.environ.get('JIRA_DIR', raw.get('jira_dir', 'JIRA'))
    jira_dir_path = Path(jira_dir_raw)
    jira_dir = jira_dir_path if jira_dir_path.is_absolute() else (Path.cwd() / jira_dir_path).resolve()

    fields = raw.get('fields', {})

    return JiraConfig(
        base_url=base_url,
        email=email,
        api_token=api_token,
        jira_dir=jira_dir,
        analysis_field_name=fields.get('analysis_field_name', 'Analysis'),
        workaround_field_name=fields.get('workaround_field_name', 'Workaround'),
        extra_fields=fields.get('extra_fields', DEFAULT_EXTRA_FIELDS),
    )


def stringify(value) -> str:
    """Best-effort plain-text rendering of a raw Jira field value."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("displayName", "name", "value"):
            if key in value and value[key]:
                return str(value[key])
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(stringify(v) for v in value if v is not None)
    return str(value)


def html_to_markdown(html: Optional[str]) -> str:
    """Convert Jira's renderedFields HTML into Markdown."""
    if not html:
        return ""
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.unicode_snob = True
    return converter.handle(html).strip()


def field_to_markdown(field_id: str, fields: dict, rendered_fields: dict) -> str:
    """Resolve a field's content to Markdown, preferring the rendered HTML version."""
    rendered = rendered_fields.get(field_id)
    if rendered:
        return html_to_markdown(rendered)
    return stringify(fields.get(field_id)).strip()


class JiraClient:
    """Thin wrapper around the Jira Cloud REST API v3."""

    def __init__(self, config: JiraConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.email, config.api_token)
        self.session.headers.update({"Accept": "application/json"})

    def get_issue(self, issue_key: str) -> dict:
        url = f"{self.config.base_url}/rest/api/3/issue/{issue_key}"
        resp = self.session.get(url, params={
            "fields": "*all",
            "expand": "renderedFields,names",
        })
        resp.raise_for_status()
        return resp.json()

    def get_comments(self, issue_key: str) -> list:
        comments = []
        start_at = 0
        while True:
            url = f"{self.config.base_url}/rest/api/3/issue/{issue_key}/comment"
            resp = self.session.get(url, params={
                "expand": "renderedBody",
                "startAt": start_at,
                "maxResults": 100,
            })
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("comments", [])
            comments.extend(batch)
            start_at += len(batch)
            if start_at >= data.get("total", 0) or not batch:
                break
        comments.sort(key=lambda c: c.get("created", ""))
        return comments

    def download_attachment(self, url: str, dest: Path) -> None:
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


def find_field_id_by_name(names: dict, target_name: str) -> Optional[str]:
    target = target_name.strip().lower()
    for field_id, label in names.items():
        if isinstance(label, str) and label.strip().lower() == target:
            return field_id
    return None


def parse_last_fetched(last_fetched_path: Path) -> dict:
    """Parse a previous last_fetched.md's attachment table into {attachment_id: filename}."""
    result = {}
    if not last_fetched_path.exists():
        return result

    in_table = False
    for line in last_fetched_path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if stripped.startswith("| Attachment ID"):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            in_table = False
            continue
        if stripped.startswith("|---") or stripped.startswith("| ---"):
            continue
        parts = [p.strip() for p in stripped.strip("|").split("|")]
        if len(parts) < 5:
            continue
        attachment_id, filename, _sha, _size, status = parts[:5]
        if attachment_id and filename and status != "orphaned":
            result[attachment_id] = filename
    return result


def build_defect_md(issue_key: str, base_url: str, fields: dict, rendered_fields: dict) -> str:
    summary = stringify(fields.get("summary"))
    lines = [f"# {issue_key}: {summary}", ""]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    meta = [
        ("Status", stringify(fields.get("status"))),
        ("Type", stringify(fields.get("issuetype"))),
        ("Priority", stringify(fields.get("priority"))),
        ("Reporter", stringify(fields.get("reporter"))),
        ("Assignee", stringify(fields.get("assignee"))),
        ("Created", stringify(fields.get("created"))),
        ("Updated", stringify(fields.get("updated"))),
        ("Resolution", stringify(fields.get("resolution"))),
        ("Labels", stringify(fields.get("labels"))),
        ("Components", stringify(fields.get("components"))),
        ("Fix Versions", stringify(fields.get("fixVersions"))),
        ("Affects Versions", stringify(fields.get("versions"))),
        ("Jira Link", f"{base_url}/browse/{issue_key}"),
    ]
    for label, value in meta:
        lines.append(f"| {label} | {value or '-'} |")

    lines.append("")
    lines.append("## Description")
    lines.append("")
    description_md = field_to_markdown("description", fields, rendered_fields)
    lines.append(description_md if description_md else "_No description._")
    lines.append("")
    return "\n".join(lines)


def build_comments_md(issue_key: str, comments: list) -> str:
    if not comments:
        return f"# Comments — {issue_key}\n\nNo comments.\n"

    lines = [f"# Comments — {issue_key}", ""]
    for c in comments:
        author = stringify(c.get("author"))
        created = c.get("created", "")
        body_md = html_to_markdown(c.get("renderedBody")) or stringify(c.get("body"))
        lines.append(f"## {author} — {created}")
        lines.append("")
        lines.append(body_md if body_md else "_Empty comment._")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def build_index_md(issue_key: str, base_url: str, fields: dict, has_analysis: bool,
                    has_workaround: bool, attachment_count: int, fetched_at: str) -> str:
    summary = stringify(fields.get("summary"))
    lines = [
        f"# {issue_key}: {summary}",
        "",
        f"- **Status:** {stringify(fields.get('status')) or '-'}",
        f"- **Type:** {stringify(fields.get('issuetype')) or '-'}",
        f"- **Priority:** {stringify(fields.get('priority')) or '-'}",
        f"- **Assignee:** {stringify(fields.get('assignee')) or '-'}",
        f"- **Reporter:** {stringify(fields.get('reporter')) or '-'}",
        f"- **Jira link:** {base_url}/browse/{issue_key}",
        "",
        "## Files in this bundle",
        "",
        "- [defect.md](defect.md) — full description and metadata",
    ]
    if has_analysis:
        lines.append("- [analysis.md](analysis.md) — analysis notes")
    if has_workaround:
        lines.append("- [workaround.md](workaround.md) — workaround notes")
    lines.append("- [comments.md](comments.md) — all comments, chronological")
    lines.append(f"- [files/](files/) — {attachment_count} attachment(s)")
    lines.append("- [last_fetched.md](last_fetched.md) — fetch/update audit trail")
    lines.append("- [metadata.json](metadata.json) — machine-readable issue metadata")
    lines.append("")
    lines.append(f"_Fetched: {fetched_at}_")
    lines.append("")
    return "\n".join(lines)


def build_metadata_json(issue_key: str, base_url: str, fields: dict, names: dict,
                         extra_fields: dict, attachments_meta: list) -> dict:
    metadata = {
        "key": issue_key,
        "url": f"{base_url}/browse/{issue_key}",
        "summary": stringify(fields.get("summary")),
        "status": stringify(fields.get("status")),
        "issue_type": stringify(fields.get("issuetype")),
        "priority": stringify(fields.get("priority")),
        "assignee": stringify(fields.get("assignee")),
        "reporter": stringify(fields.get("reporter")),
        "created": stringify(fields.get("created")),
        "updated": stringify(fields.get("updated")),
        "resolution": stringify(fields.get("resolution")),
        "labels": fields.get("labels") or [],
        "components": [stringify(c) for c in (fields.get("components") or [])],
        "fix_versions": [stringify(v) for v in (fields.get("fixVersions") or [])],
        "affected_versions": [stringify(v) for v in (fields.get("versions") or [])],
    }
    for output_key, display_name in extra_fields.items():
        field_id = find_field_id_by_name(names, display_name)
        metadata[output_key] = stringify(fields.get(field_id)) if field_id else ""
    metadata["attachments"] = attachments_meta
    return metadata


def unique_filename(desired: str, reserved: set) -> str:
    if desired not in reserved:
        return desired
    path = Path(desired)
    stem, suffix = path.stem, path.suffix
    n = 1
    while f"{stem} ({n}){suffix}" in reserved:
        n += 1
    return f"{stem} ({n}){suffix}"


# Compound suffixes must be checked before their single-suffix counterparts
# (e.g. "foo.tar.gz" must match ".tar.gz", not fall through to ".gz").
_COMPOUND_TAR_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz")
_SIMPLE_TAR_SUFFIXES = (".tar", ".tgz", ".tbz2", ".tb2", ".txz")


def get_archive_kind(filename: str) -> Optional[str]:
    """Classify a filename as an extractable archive type, or None."""
    lower = filename.lower()
    if lower.endswith(".zip"):
        return "zip"
    if lower.endswith(".7z"):
        return "7z"
    if lower.endswith(_COMPOUND_TAR_SUFFIXES) or lower.endswith(_SIMPLE_TAR_SUFFIXES):
        return "tar"
    return None


def get_archive_stem(filename: str) -> str:
    """Base name to use as the extraction directory, with compound suffixes fully stripped."""
    lower = filename.lower()
    for suffix in _COMPOUND_TAR_SUFFIXES:
        if lower.endswith(suffix):
            return filename[: -len(suffix)]
    return Path(filename).stem


def extract_archive(dest: Path, filename: str, kind: str, extract_dir: Path) -> None:
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    try:
        if kind == "zip":
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(extract_dir)
        elif kind == "tar":
            with tarfile.open(dest, "r:*") as tf:
                tf.extractall(extract_dir)
        elif kind == "7z":
            if not HAS_PY7ZR:
                print(f"    Warning: py7zr not installed, skipping extraction of {filename} "
                      f"(pip install py7zr)")
                shutil.rmtree(extract_dir)
                return
            with py7zr.SevenZipFile(dest, mode="r") as zf:
                zf.extractall(path=extract_dir)
        print(f"    Extracted {kind} to files/{extract_dir.name}/")
    except Exception as e:
        print(f"    Warning: failed to extract {filename}: {e}")
        shutil.rmtree(extract_dir, ignore_errors=True)


def process_attachments(client: JiraClient, attachments: list, files_dir: Path,
                         previous_ids: dict, mode: str) -> list:
    """Download new/changed attachments, skip unchanged ones, extract archives. Returns row dicts."""
    files_dir.mkdir(parents=True, exist_ok=True)
    reserved = {p.name for p in files_dir.iterdir()} if mode == 'update' else set()
    rows = []
    current_ids = set()

    for att in attachments:
        att_id = str(att.get("id"))
        current_ids.add(att_id)
        orig_filename = att.get("filename", f"attachment-{att_id}")

        if mode == 'update' and att_id in previous_ids and (files_dir / previous_ids[att_id]).exists():
            filename = previous_ids[att_id]
            dest = files_dir / filename
            status = "carried-over"
        else:
            filename = unique_filename(orig_filename, reserved)
            reserved.add(filename)
            dest = files_dir / filename
            print(f"  Downloading attachment: {filename}")
            client.download_attachment(att["content"], dest)
            status = "downloaded"

            archive_kind = get_archive_kind(filename)
            if archive_kind:
                extract_dir = files_dir / get_archive_stem(filename)
                extract_archive(dest, filename, archive_kind, extract_dir)

        file_hash = sha256_of(dest)
        rows.append({
            "attachment_id": att_id,
            "filename": filename,
            "sha256": file_hash,
            "size": dest.stat().st_size,
            "status": status,
            "mime_type": att.get("mimeType", ""),
        })

    # Orphaned attachments: previously downloaded, no longer present on the issue.
    for att_id, filename in previous_ids.items():
        if att_id in current_ids:
            continue
        existing = files_dir / filename
        if existing.exists():
            rows.append({
                "attachment_id": att_id,
                "filename": filename,
                "sha256": sha256_of(existing),
                "size": existing.stat().st_size,
                "status": "orphaned",
                "mime_type": "",
            })

    return rows


def build_last_fetched_md(fetched_at: str, generated_docs: list, attachment_rows: list) -> str:
    lines = [f"# Last Fetched", "", f"Fetched: {fetched_at}", "", "## Generated documents", ""]
    for doc in generated_docs:
        lines.append(f"- {doc}")
    lines.append("")
    lines.append("## Attachments")
    lines.append("")
    lines.append("| Attachment ID | Filename | SHA256 | Size (bytes) | Status |")
    lines.append("|---|---|---|---|---|")
    for row in attachment_rows:
        lines.append(
            f"| {row['attachment_id']} | {row['filename']} | {row['sha256']} | "
            f"{row['size']} | {row['status']} |"
        )
    lines.append("")
    return "\n".join(lines)


def fetch_issue(issue_key: str, config: JiraConfig, mode: str) -> None:
    issue_dir = config.jira_dir / issue_key
    files_dir = issue_dir / "files"
    last_fetched_path = issue_dir / "last_fetched.md"

    if mode == 'fresh' and issue_dir.exists():
        print(f"Clearing existing directory: {issue_dir}")
        shutil.rmtree(issue_dir)

    previous_ids = {}
    if mode == 'update' and issue_dir.exists():
        previous_ids = parse_last_fetched(last_fetched_path)

    issue_dir.mkdir(parents=True, exist_ok=True)

    client = JiraClient(config)

    print(f"Fetching {issue_key} from {config.base_url} ...")
    issue = client.get_issue(issue_key)
    fields = issue.get("fields", {})
    rendered_fields = issue.get("renderedFields", {})
    names = issue.get("names", {})

    print("Fetching comments ...")
    comments = client.get_comments(issue_key)

    # defect.md
    (issue_dir / "defect.md").write_text(
        build_defect_md(issue_key, config.base_url, fields, rendered_fields) + "\n",
        encoding='utf-8'
    )

    # analysis.md / workaround.md (only if the field resolves and has content)
    has_analysis = False
    has_workaround = False
    for target_name, out_name, flag_setter in [
        (config.analysis_field_name, "analysis.md", "analysis"),
        (config.workaround_field_name, "workaround.md", "workaround"),
    ]:
        field_id = find_field_id_by_name(names, target_name)
        content = field_to_markdown(field_id, fields, rendered_fields) if field_id else ""
        out_path = issue_dir / out_name
        if content.strip():
            out_path.write_text(f"# {target_name} — {issue_key}\n\n{content}\n", encoding='utf-8')
            if flag_setter == "analysis":
                has_analysis = True
            else:
                has_workaround = True
        elif out_path.exists():
            out_path.unlink()

    # comments.md
    (issue_dir / "comments.md").write_text(
        build_comments_md(issue_key, comments) + "\n", encoding='utf-8'
    )

    # attachments
    attachments = fields.get("attachment", []) or []
    print(f"Processing {len(attachments)} attachment(s) ({mode} mode) ...")
    attachment_rows = process_attachments(client, attachments, files_dir, previous_ids, mode)

    # metadata.json
    attachments_meta = [
        {"id": r["attachment_id"], "filename": r["filename"], "mime_type": r["mime_type"]}
        for r in attachment_rows if r["status"] != "orphaned"
    ]
    metadata = build_metadata_json(issue_key, config.base_url, fields, names,
                                    config.extra_fields, attachments_meta)
    (issue_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding='utf-8'
    )

    # index.md
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (issue_dir / "index.md").write_text(
        build_index_md(issue_key, config.base_url, fields, has_analysis, has_workaround,
                        len([r for r in attachment_rows if r["status"] != "orphaned"]), fetched_at) + "\n",
        encoding='utf-8'
    )

    # last_fetched.md
    generated_docs = ["defect.md", "comments.md", "index.md", "metadata.json"]
    if has_analysis:
        generated_docs.append("analysis.md")
    if has_workaround:
        generated_docs.append("workaround.md")
    last_fetched_path.write_text(
        build_last_fetched_md(fetched_at, generated_docs, attachment_rows), encoding='utf-8'
    )

    print(f"\nDone. Issue bundle written to: {issue_dir}")
    print(f"Start here: {issue_dir / 'index.md'}")


def main():
    parser = argparse.ArgumentParser(
        description='Jira Issue Sync Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fetch SYFU-12277
  %(prog)s fetch SYFU-12277 --mode fresh
  %(prog)s fetch SYFU-12277 --mode update
        """
    )
    subparsers = parser.add_subparsers(dest='command')

    fetch_parser = subparsers.add_parser('fetch', help='Fetch or update a Jira issue')
    fetch_parser.add_argument('issue_key', type=str, help='Jira issue key, e.g. SYFU-12277')
    fetch_parser.add_argument(
        '--mode', choices=['fresh', 'update'], default=None,
        help='fresh = clear and redownload everything; update = incremental (default: auto-detect)'
    )
    fetch_parser.add_argument(
        '--config', '-c', type=Path, default=Path(__file__).parent / 'config.json',
        help='Path to configuration JSON file (default: config.json)'
    )

    args = parser.parse_args()

    if args.command != 'fetch':
        parser.print_help()
        sys.exit(1)

    load_devenvironment()
    config = load_config(args.config)

    issue_dir = config.jira_dir / args.issue_key
    mode = args.mode
    if mode is None:
        mode = 'update' if issue_dir.exists() else 'fresh'

    try:
        fetch_issue(args.issue_key, config, mode)
    except requests.HTTPError as e:
        print(f"Error: Jira API request failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
