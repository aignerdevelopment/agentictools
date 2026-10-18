#!/usr/bin/env python3
"""
GitLab tool (issues, merge requests, labels).

Replaces the old shell helper with a robust Python CLI. Configuration comes
from the project environment (first-class, .devenvironment/env.sh):
    GITLAB_BASE_URL, GITLAB_TOKEN,
    GITLAB_PROJECT_PATH or GITLAB_PROJECT_ID,
    GITLAB_DEFAULT_BRANCH (optional)
A local config.json is optional and only overrides these.

Project paths are always URL-encoded; if a path-based request 404s and no
numeric GITLAB_PROJECT_ID is set, the error tells the caller to set it.

Output is JSON on stdout; diagnostics go to stderr. Exit code is non-zero on
failure.

Usage:
    gitlab.py project-info
    gitlab.py issue-list [--labels a,b] [--state opened] [--search s]
    gitlab.py issue-get <iid>
    gitlab.py issue-create --title T [--description D] [--labels a,b]
    gitlab.py issue-update <iid> [--title T] [--description D] [--labels a,b] [--state-event close|reopen]
    gitlab.py issue-note <iid> --body B
    gitlab.py issue-label <iid> [--add a,b] [--remove c]
    gitlab.py mr-list [--source-branch B] [--state opened]
    gitlab.py mr-get <iid>
    gitlab.py mr-create [--source B] [--target B] [--title T] [--description D] [--remove-source-branch] [--squash]
    gitlab.py mr-merge <iid> [--squash] [--remove-source-branch] [--sha S] [--when-pipeline-succeeds]
    gitlab.py mr-approve <iid>
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = int(os.environ.get('GITLAB_MAX_RETRIES', '4'))


@dataclass
class Config:
    base_url: str
    token: str
    project_path: str
    project_id: str
    default_branch: str = ""

    @property
    def project_ref(self) -> str:
        if self.project_id:
            return self.project_id
        return urllib.parse.quote(self.project_path, safe='')

    @property
    def project_label(self) -> str:
        return self.project_path or (f"id-{self.project_id}" if self.project_id else "")


def load_config(config_path: Path) -> Config:
    raw: dict = {}
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding='utf-8'))
    base_url = os.environ.get('GITLAB_BASE_URL', raw.get('base_url', '')).rstrip('/')
    token = os.environ.get('GITLAB_TOKEN', raw.get('token', ''))
    project_path = os.environ.get('GITLAB_PROJECT_PATH', raw.get('project_path', ''))
    project_id = os.environ.get('GITLAB_PROJECT_ID', raw.get('project_id', ''))
    default_branch = os.environ.get('GITLAB_DEFAULT_BRANCH', raw.get('default_branch', ''))
    for key, value in (("GITLAB_BASE_URL", base_url), ("GITLAB_TOKEN", token)):
        if not value or "<insert your" in value:
            fail(f"{key} is not configured; set it in .devenvironment/env.local.sh (rule 07)")
    if not project_path and not project_id:
        fail("set GITLAB_PROJECT_PATH or GITLAB_PROJECT_ID (.devenvironment/env.sh or config.json)")
    return Config(base_url, token, project_path, project_id, default_branch)


def fail(message: str, code: int = 1) -> None:
    print(f"gitlab-tool: {message}", file=sys.stderr)
    sys.exit(code)


def emit(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def load_devenvironment() -> None:
    """Load <repo-root>/.devenvironment/env.sh into os.environ (rule 07).

    Values already present in the real environment win. Missing file is a no-op.
    """
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


def detect_git_branch() -> str:
    try:
        out = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


class Client:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "PRIVATE-TOKEN": config.token,
            "Accept": "application/json",
        })

    def url(self, endpoint: str) -> str:
        return f"{self.config.base_url}/api/v4/projects/{self.config.project_ref}{endpoint}"

    def request(self, method: str, endpoint: str, params: Optional[dict] = None,
                body: Optional[dict] = None, paginate: bool = False) -> dict:
        params = dict(params or {})
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.request(method, self.url(endpoint), params=params, json=body)
            except requests.RequestException as exc:
                if attempt >= MAX_RETRIES:
                    fail(f"network error: {exc}")
                time.sleep(min(2 ** attempt, 8))
                continue

            if resp.status_code in RETRY_STATUS and attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, 8))
                continue

            if resp.status_code == 404 and not self.config.project_id and attempt >= 1:
                fail(f"HTTP 404 for project '{self.config.project_label}'. "
                     "The GitLab API may need the numeric project id; set GITLAB_PROJECT_ID "
                     "(.devenvironment/env.sh). Server said: " + _short(resp))
            if resp.status_code >= 400:
                fail(f"HTTP {resp.status_code} {method} {endpoint}: {_short(resp)}")

            if paginate:
                data = resp.json()
                return data  # caller loops with explicit page param
            try:
                return resp.json()
            except ValueError:
                return {"raw": resp.text}

    def get(self, endpoint, **kw):
        return self.request("GET", endpoint, **kw)

    def post(self, endpoint, body=None, **kw):
        return self.request("POST", endpoint, body=body, **kw)

    def put(self, endpoint, body=None, **kw):
        return self.request("PUT", endpoint, body=body, **kw)

    def paginated(self, endpoint: str, params: Optional[dict] = None) -> list:
        params = dict(params or {})
        params.setdefault('per_page', 100)
        page = 1
        out = []
        while True:
            params['page'] = page
            resp = self.session.request("GET", self.url(endpoint), params=params)
            if resp.status_code >= 400:
                fail(f"HTTP {resp.status_code} GET {endpoint}: {_short(resp)}")
            batch = resp.json()
            out.extend(batch)
            next_page = resp.headers.get('X-Next-Page', '')
            if not next_page:
                break
            page = int(next_page)
        return out

    # -- higher level helpers -------------------------------------------------
    def issue(self, iid: str) -> dict:
        return self.get(f"/issues/{iid}")

    def default_branch(self) -> str:
        if self.config.default_branch:
            return self.config.default_branch
        for source in (["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                       ["git", "symbolic-ref", "HEAD"]):
            try:
                out = subprocess.run(source, capture_output=True, text=True, check=True).stdout.strip()
                if out:
                    return out.rsplit('/', 1)[-1]
            except Exception:  # noqa: BLE001
                continue
        project = self.get("")
        return project.get('default_branch', 'main')

    def find_open_mr(self, source_branch: str) -> Optional[dict]:
        mrs = self.get("/merge_requests", params={"source_branch": source_branch, "state": "opened"})
        return mrs[0] if isinstance(mrs, list) and mrs else None


def _short(resp: requests.Response, limit: int = 400) -> str:
    text = ""
    try:
        payload = resp.json()
        text = payload.get('message') or payload.get('error') or json.dumps(payload)
    except ValueError:
        text = resp.text
    return (text or "").strip()[:limit]


def parse_csv(value: str) -> list:
    return [v.strip() for v in (value or "").split(',') if v.strip()]


# -- command handlers ---------------------------------------------------------

def cmd_project_info(client: Client, _args) -> None:
    project = client.get("")
    emit({
        "id": project.get('id'),
        "path_with_namespace": project.get('path_with_namespace'),
        "default_branch": project.get('default_branch'),
        "project_ref_used": client.config.project_ref,
    })


def cmd_issue_list(client: Client, args) -> None:
    params = {"state": args.state}
    if args.labels:
        params["labels"] = args.labels
    if args.search:
        params["search"] = args.search
    issues = client.paginated("/issues", params)
    emit([{"iid": i.get('iid'), "title": i.get('title'), "state": i.get('state'),
           "labels": i.get('labels'), "web_url": i.get('web_url')} for i in issues])


def cmd_issue_get(client: Client, args) -> None:
    emit(client.issue(args.iid))


def cmd_issue_create(client: Client, args) -> None:
    body = {"title": args.title}
    if args.description:
        body["description"] = args.description
    if args.labels:
        body["labels"] = args.labels
    emit(client.post("/issues", body=body))


def cmd_issue_update(client: Client, args) -> None:
    body = {}
    if args.title is not None:
        body["title"] = args.title
    if args.description is not None:
        body["description"] = args.description
    if args.labels is not None:
        body["labels"] = args.labels
    if args.state_event:
        body["state_event"] = args.state_event
    if not body:
        fail("issue-update: nothing to update")
    emit(client.put(f"/issues/{args.iid}", body=body))


def cmd_issue_note(client: Client, args) -> None:
    emit(client.post(f"/issues/{args.iid}/notes", body={"body": args.body}))


def cmd_issue_label(client: Client, args) -> None:
    issue = client.issue(args.iid)
    labels = set(issue.get('labels') or [])
    labels.update(parse_csv(args.add))
    labels.difference_update(parse_csv(args.remove))
    emit(client.put(f"/issues/{args.iid}", body={"labels": sorted(labels)}))


def cmd_mr_list(client: Client, args) -> None:
    params = {"state": args.state}
    if args.source_branch:
        params["source_branch"] = args.source_branch
    mrs = client.paginated("/merge_requests", params)
    emit([{"iid": m.get('iid'), "title": m.get('title'), "state": m.get('state'),
           "source_branch": m.get('source_branch'), "target_branch": m.get('target_branch'),
           "merge_status": m.get('detailed_merge_status') or m.get('merge_status'),
           "web_url": m.get('web_url')} for m in mrs])


def cmd_mr_get(client: Client, args) -> None:
    emit(client.get(f"/merge_requests/{args.iid}"))


def cmd_mr_create(client: Client, args) -> None:
    source = args.source or detect_git_branch()
    if not source or source in ("main", "master", "HEAD"):
        fail("mr-create: specify --source <branch> (currently on default/detached branch)")
    existing = client.find_open_mr(source)
    if existing:
        print(f"gitlab-tool: open MR already exists for {source}", file=sys.stderr)
        emit(existing)
        return
    target = args.target or client.default_branch()
    body = {
        "source_branch": source,
        "target_branch": target,
        "title": args.title or f"Merge {source} into {target}",
        "description": args.description or "",
        "remove_source_branch": bool(args.remove_source_branch),
        "squash": bool(args.squash),
    }
    emit(client.post("/merge_requests", body=body))


def cmd_mr_merge(client: Client, args) -> None:
    mr = client.get(f"/merge_requests/{args.iid}")
    status = mr.get('detailed_merge_status') or mr.get('merge_status')
    body = {
        "squash": bool(args.squash),
        "should_remove_source_branch": bool(args.remove_source_branch),
        "merge_when_pipeline_succeeds": bool(args.when_pipeline_succeeds),
    }
    sha = args.sha or mr.get('sha')
    if sha:
        body["sha"] = sha
    result = client.put(f"/merge_requests/{args.iid}/merge", body=body)
    emit({"merge_status_before": status, "result": result})


def cmd_mr_approve(client: Client, args) -> None:
    emit(client.post(f"/merge_requests/{args.iid}/approve"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='GitLab tool (issues, MRs, labels)')
    parser.add_argument('--config', '-c', type=Path, default=Path(__file__).parent / 'config.json')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('project-info').set_defaults(func=cmd_project_info)

    p = sub.add_parser('issue-list')
    p.add_argument('--labels', default='')
    p.add_argument('--state', default='opened')
    p.add_argument('--search', default='')
    p.set_defaults(func=cmd_issue_list)

    p = sub.add_parser('issue-get')
    p.add_argument('iid')
    p.set_defaults(func=cmd_issue_get)

    p = sub.add_parser('issue-create')
    p.add_argument('--title', required=True)
    p.add_argument('--description', default='')
    p.add_argument('--labels', default='')
    p.set_defaults(func=cmd_issue_create)

    p = sub.add_parser('issue-update')
    p.add_argument('iid')
    p.add_argument('--title', default=None)
    p.add_argument('--description', default=None)
    p.add_argument('--labels', default=None)
    p.add_argument('--state-event', choices=['close', 'reopen'], default=None)
    p.set_defaults(func=cmd_issue_update)

    p = sub.add_parser('issue-note')
    p.add_argument('iid')
    p.add_argument('--body', required=True)
    p.set_defaults(func=cmd_issue_note)

    p = sub.add_parser('issue-label')
    p.add_argument('iid')
    p.add_argument('--add', default='')
    p.add_argument('--remove', default='')
    p.set_defaults(func=cmd_issue_label)

    p = sub.add_parser('mr-list')
    p.add_argument('--source-branch', default='')
    p.add_argument('--state', default='opened')
    p.set_defaults(func=cmd_mr_list)

    p = sub.add_parser('mr-get')
    p.add_argument('iid')
    p.set_defaults(func=cmd_mr_get)

    p = sub.add_parser('mr-create')
    p.add_argument('--source', default='')
    p.add_argument('--target', default='')
    p.add_argument('--title', default='')
    p.add_argument('--description', default='')
    p.add_argument('--remove-source-branch', action='store_true')
    p.add_argument('--squash', action='store_true')
    p.set_defaults(func=cmd_mr_create)

    p = sub.add_parser('mr-merge')
    p.add_argument('iid')
    p.add_argument('--squash', action='store_true')
    p.add_argument('--remove-source-branch', action='store_true')
    p.add_argument('--sha', default='')
    p.add_argument('--when-pipeline-succeeds', action='store_true')
    p.set_defaults(func=cmd_mr_merge)

    p = sub.add_parser('mr-approve')
    p.add_argument('iid')
    p.set_defaults(func=cmd_mr_approve)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    load_devenvironment()
    config = load_config(args.config)
    client = Client(config)
    try:
        args.func(client, args)
    except requests.RequestException as exc:
        fail(f"request failed: {exc}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
