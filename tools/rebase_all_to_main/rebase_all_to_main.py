#!/usr/bin/env python3
"""
Rebase All to Main - Windows Tool

A cross-platform tool that keeps the configured repositories in sync with their
remote main/master/develop branches.

For each configured project:
  - If on doc-branch: rebase onto origin/<main_branch>
  - If on main_branch: fast-forward pull
  - If working tree is dirty: stash before, pop after

Usage:
    python rebase_all_to_main.py [--config path/to/config.json]

Or via the batch file:
    rebase_all_to_main.bat
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    directory: str
    main_branch: str
    doc_branch: Optional[str] = None  # Override the global doc_branch if specified


@dataclass
class AppConfig:
    """Application configuration loaded from JSON."""
    root_dir: str
    doc_branch: str
    projects: list[ProjectConfig]
    # Behavior settings
    auto_stash: bool = True
    stash_include_untracked: bool = True
    abort_rebase_on_conflict: bool = True
    keep_stash_on_pop_conflict: bool = True
    # Exit settings
    exit_on_first_failure: bool = False


@dataclass
class ProjectResult:
    """Result of processing a single project."""
    project: ProjectConfig
    status: str  # 'ok', 'skipped', 'failed'
    message: str
    stashed: bool = False


def load_config(config_path: Path) -> AppConfig:
    """Load configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load behavior settings
    behavior = data.get('behavior', {})

    # Resolve root_dir relative to config file location
    root_dir = data.get('root_dir', '.')
    root_dir_path = Path(root_dir)

    if not root_dir_path.is_absolute():
        # Join with config directory and resolve to get absolute path
        root_dir_path = (config_path.parent / root_dir_path).resolve()

    projects = []
    for p in data.get('projects', []):
        if isinstance(p, dict):
            projects.append(ProjectConfig(
                directory=p['directory'],
                main_branch=p['main_branch'],
                doc_branch=p.get('doc_branch')
            ))
        elif isinstance(p, str):
            # Legacy format: "directory branch"
            parts = p.split()
            if len(parts) >= 2:
                projects.append(ProjectConfig(
                    directory=parts[0],
                    main_branch=parts[1]
                ))

    return AppConfig(
        root_dir=str(root_dir_path),
        doc_branch=data.get('doc_branch', 'docs'),
        projects=projects,
        auto_stash=behavior.get('auto_stash', True),
        stash_include_untracked=behavior.get('stash_include_untracked', True),
        abort_rebase_on_conflict=behavior.get('abort_rebase_on_conflict', True),
        keep_stash_on_pop_conflict=behavior.get('keep_stash_on_pop_conflict', True),
        exit_on_first_failure=behavior.get('exit_on_first_failure', False)
    )


def run_git(project_path: Path, *args: str, check: bool = False) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    cmd = ['git', '-C', str(project_path)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    return result.returncode, result.stdout, result.stderr


def is_git_repository(path: Path) -> bool:
    """Check if path is a git repository."""
    returncode, _, _ = run_git(path, 'rev-parse', '--git-dir')
    return returncode == 0


def get_current_branch(path: Path) -> Optional[str]:
    """Get the current branch name, or None if detached."""
    returncode, stdout, _ = run_git(path, 'rev-parse', '--abbrev-ref', 'HEAD')
    if returncode == 0:
        branch = stdout.strip()
        return None if branch == 'HEAD' else branch
    return None


def is_dirty(path: Path) -> int:
    """Check if working tree is dirty and return number of modified files."""
    returncode, stdout, _ = run_git(path, 'status', '--porcelain')
    if returncode == 0:
        # Count non-empty lines
        lines = [l for l in stdout.splitlines() if l.strip()]
        return len(lines)
    return 0


def stash_push(path: Path, include_untracked: bool) -> tuple[bool, str]:
    """Stash local changes. Returns (success, stash_message)."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    stash_msg = f"rebase_all_to_main auto-stash {timestamp}"

    cmd = ['stash', 'push', '-m', stash_msg]
    if include_untracked:
        cmd.append('-u')

    returncode, stdout, stderr = run_git(path, *cmd)
    if returncode == 0:
        return True, stash_msg
    return False, stderr or stdout


def stash_pop(path: Path) -> tuple[bool, str]:
    """Pop the stash. Returns (success, message)."""
    returncode, stdout, stderr = run_git(path, 'stash', 'pop')
    if returncode == 0:
        return True, "Stash restored successfully"
    return False, stderr or stdout


def fetch_origin(path: Path) -> tuple[bool, str]:
    """Fetch from origin. Returns (success, message)."""
    returncode, stdout, stderr = run_git(path, 'fetch', 'origin')
    if returncode == 0:
        return True, stdout or "Fetch successful"
    return False, stderr or stdout


def rebase_onto(path: Path, branch: str) -> tuple[bool, str]:
    """Rebase current branch onto origin/<branch>. Returns (success, message)."""
    # Check if a rebase is already in progress
    git_dir = path / '.git'
    rebase_merge = git_dir / 'rebase-merge'
    rebase_apply = git_dir / 'rebase-apply'

    if rebase_merge.exists() or rebase_apply.exists():
        print(f"  WARNING: Rebase already in progress, aborting it first...")
        rebase_abort(path)

    returncode, stdout, stderr = run_git(path, 'rebase', f'origin/{branch}')
    if returncode == 0:
        return True, stdout or "Rebase successful"

    # Log error details for debugging
    error_msg = stderr or stdout or "Unknown error"
    if "could not apply" in error_msg.lower() or "conflict" in error_msg.lower():
        return False, f"Rebase conflict: {error_msg[:200]}"
    elif "uncommitted changes" in error_msg.lower():
        return False, f"Uncommitted changes blocking rebase: {error_msg[:200]}"
    return False, f"Rebase failed: {error_msg[:200]}"


def rebase_abort(path: Path) -> None:
    """Abort an ongoing rebase."""
    run_git(path, 'rebase', '--abort')


def pull_ff_only(path: Path, branch: str) -> tuple[bool, str]:
    """Fast-forward pull from origin/<branch>. Returns (success, message)."""
    returncode, stdout, stderr = run_git(path, 'pull', '--ff-only', 'origin', branch)
    if returncode == 0:
        return True, stdout or "Pull successful"
    return False, stderr or stdout


def get_ahead_behind(path: Path, upstream: str) -> tuple[int, int] | None:
    """Get ahead/behind counts: (ahead, behind) or None if not tracked."""
    # Format: <ahead>\t<behind>\n or empty if not tracking
    returncode, stdout, stderr = run_git(
        path, 'rev-list', '--left-right', '--count',
        f'HEAD...{upstream}'
    )
    if returncode == 0:
        try:
            parts = stdout.strip().split('\t')
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass
    return None


def process_project(project: ProjectConfig, config: AppConfig) -> ProjectResult:
    """Process a single project."""
    full_path = Path(config.root_dir) / project.directory
    doc_branch = project.doc_branch or config.doc_branch

    print(f"\n{'=' * 40}")
    print(f"  {project.directory} (main={project.main_branch})")
    print(f"{'=' * 40}")

    # Check if it's a git repository
    if not is_git_repository(full_path):
        print(f"  SKIP: not a git repository")
        return ProjectResult(project, 'skipped', 'not a git repo')

    # Get current branch
    current_branch = get_current_branch(full_path)
    if current_branch is None:
        print(f"  SKIP: detached HEAD state")
        return ProjectResult(project, 'skipped', 'detached HEAD')
    print(f"  current branch: {current_branch}")

    # Check for dirty working tree
    dirty_count = is_dirty(full_path)
    stashed = False
    stash_msg = ""

    if dirty_count > 0 and config.auto_stash:
        print(f"  Working tree is dirty ({dirty_count} file(s) modified). Stashing...")
        success, result = stash_push(full_path, config.stash_include_untracked)
        if success:
            stashed = True
            stash_msg = result
            print(f"  Stashed local changes.")
        else:
            print(f"  FAILED: could not stash local changes")
            print(f"  {result}")
            return ProjectResult(project, 'failed', 'stash failed')

    # Fetch origin
    print(f"  Fetching origin...")
    success, msg = fetch_origin(full_path)
    if not success:
        print(f"  FAILED: fetch failed")
        print(f"  {msg}")
        if stashed:
            _pop_stash(full_path, project.directory, config)
        return ProjectResult(project, 'failed', 'fetch failed', stashed)
    print(f"  {msg.strip()}")

    # Determine action based on current branch
    result: Optional[ProjectResult] = None

    if current_branch == doc_branch:
        # Rebase doc branch on top of origin/main_branch
        print(f"  Rebasing {doc_branch} onto origin/{project.main_branch}...")

        # Show divergence info before rebase
        ahead_behind = get_ahead_behind(full_path, f'origin/{project.main_branch}')
        if ahead_behind:
            ahead, behind = ahead_behind
            print(f"  Before: {ahead} commits ahead, {behind} commits behind origin/{project.main_branch}")

        success, msg = rebase_onto(full_path, project.main_branch)
        if success:
            # Verify the rebase actually worked
            ahead_behind_after = get_ahead_behind(full_path, f'origin/{project.main_branch}')
            if ahead_behind_after:
                ahead_after, behind_after = ahead_behind_after
                if behind_after == 0:
                    print(f"  OK: rebase complete (now {ahead_after} commits ahead, 0 behind)")
                else:
                    print(f"  WARNING: Rebase claimed success but still {behind_after} commits behind origin/{project.main_branch}")
            else:
                print(f"  OK: rebase complete")
            result = ProjectResult(
                project, 'ok',
                f"rebased {doc_branch} onto origin/{project.main_branch}",
                stashed
            )
        else:
            print(f"  FAILED: rebase had conflicts")
            print(f"  {msg}")
            if config.abort_rebase_on_conflict:
                print(f"  Aborting rebase...")
                rebase_abort(full_path)
                print(f"  Rebase aborted.")
            result = ProjectResult(project, 'failed', 'rebase conflict - aborted', stashed)

    elif current_branch == project.main_branch:
        # Fast-forward pull
        print(f"  Fast-forward pull on {project.main_branch}...")
        success, msg = pull_ff_only(full_path, project.main_branch)
        if success:
            print(f"  OK: up to date")
            result = ProjectResult(
                project, 'ok',
                f"pulled {project.main_branch}",
                stashed
            )
        else:
            print(f"  FAILED: fast-forward pull failed (diverged?)")
            print(f"  {msg}")
            result = ProjectResult(project, 'failed', 'ff-pull failed', stashed)

    else:
        # Neither doc branch nor main branch
        print(f"  SKIP: branch '{current_branch}' is neither '{doc_branch}' nor '{project.main_branch}'")
        result = ProjectResult(
            project, 'skipped',
            f"unexpected branch: {current_branch}",
            stashed
        )

    # Pop stash if needed
    if stashed and result is not None:
        pop_success, pop_msg = _pop_stash(full_path, project.directory, config)
        if not pop_success:
            # Override result to failed if stash pop failed
            result = ProjectResult(
                project, 'failed',
                f"stash pop conflict - resolve manually",
                stashed
            )

    return result or ProjectResult(project, 'failed', 'unknown error', stashed)


def _pop_stash(path: Path, project_name: str, config: AppConfig) -> tuple[bool, str]:
    """Pop stash and handle conflicts. Returns (success, message)."""
    print(f"  Restoring stashed changes...")
    success, msg = stash_pop(path)
    if success:
        print(f"  OK: stash restored")
        return True, msg
    else:
        print(f"  FAILED: stash pop had conflicts - resolve manually (stash kept)")
        print(f"  {msg}")
        return False, msg


def print_summary(results: list[ProjectResult]) -> None:
    """Print the summary report."""
    ok_results = [r for r in results if r.status == 'ok']
    skipped_results = [r for r in results if r.status == 'skipped']
    failed_results = [r for r in results if r.status == 'failed']

    print(f"\n{'=' * 40}")
    print("  SUMMARY")
    print(f"{'=' * 40}")
    print()

    print(f"OK ({len(ok_results)}):")
    for r in ok_results:
        print(f"  + {r.project.directory}: {r.message}")

    print()
    print(f"SKIPPED ({len(skipped_results)}):")
    for r in skipped_results:
        print(f"  - {r.project.directory}: {r.message}")

    print()
    print(f"FAILED ({len(failed_results)}):")
    for r in failed_results:
        print(f"  ! {r.project.directory}: {r.message}")
    print()


def print_help_on_failure(results: list[ProjectResult]) -> None:
    """Print help for failed projects."""
    failed_results = [r for r in results if r.status == 'failed']
    if not failed_results:
        return

    print("=" * 40)
    print("  HOW TO RESOLVE FAILURES")
    print("=" * 40)
    print()

    for r in failed_results:
        msg_lower = r.message.lower()
        if 'stash failed' in msg_lower:
            print(f"{r.project.directory}:")
            print(f"  Check the repo manually - likely an unusual git state")
            print(f"  (e.g., mid-merge already).")
        elif 'fetch failed' in msg_lower:
            print(f"{r.project.directory}:")
            print(f"  Network/auth issue - check VPN/credentials for that remote.")
        elif 'rebase conflict' in msg_lower:
            print(f"{r.project.directory}:")
            print(f"  1. cd into the repo")
            print(f"  2. git rebase origin/{r.project.main_branch}")
            print(f"  3. Resolve conflicts manually")
            print(f"  4. git rebase --continue")
        elif 'ff-pull failed' in msg_lower:
            print(f"{r.project.directory}:")
            print(f"  Local {r.project.main_branch} has diverged from origin.")
            print(f"  Investigate why before deciding to merge/rebase/reset.")
        elif 'stash pop conflict' in msg_lower:
            print(f"{r.project.directory}:")
            print(f"  1. cd into the repo")
            print(f"  2. git status + git diff to see conflict markers")
            print(f"  3. Resolve conflicts")
            print(f"  4. git stash drop once satisfied (stash is kept until you do)")
        print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Rebase all configured projects to their main branches',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use default config.json
  %(prog)s --config my-config.json  # Use custom config file
  %(prog)s --dry-run                # Show what would be done without doing it
        """
    )
    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=None,
        help='Path to config JSON file (default: config.json next to this script)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be done without making any changes'
    )
    parser.add_argument(
        '--project', '-p',
        action='append',
        help='Process only specific project(s), can be used multiple times'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all configured projects and exit'
    )

    args = parser.parse_args()

    # Determine config path
    if args.config is None:
        script_dir = Path(__file__).parent.resolve()
        config_path = script_dir / 'config.json'
    else:
        config_path = args.config.resolve()

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print(f"Create it from the example: {config_path.with_suffix('')}.example.json")
        return 1

    # Load configuration
    try:
        config = load_config(config_path)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config file: {e}")
        return 1
    except KeyError as e:
        print(f"ERROR: Missing required config field: {e}")
        return 1

    # Filter projects if specified
    if args.project:
        filtered = [p for p in config.projects if p.directory in args.project]
        if len(filtered) != len(args.project):
            unknown = set(args.project) - {p.directory for p in filtered}
            print(f"ERROR: Unknown project(s): {', '.join(unknown)}")
            return 1
        config.projects = filtered

    # List mode
    if args.list:
        print(f"Projects configured ({len(config.projects)}):")
        for p in config.projects:
            doc_override = f" (doc: {p.doc_branch})" if p.doc_branch else ""
            print(f"  - {p.directory}: main={p.main_branch}{doc_override}")
        print(f"\nRoot directory: {config.root_dir}")
        print(f"Default doc branch: {config.doc_branch}")
        return 0

    # Dry run mode
    if args.dry_run:
        print("DRY RUN - No changes will be made")
        print(f"\nProjects to process ({len(config.projects)}):")
        for p in config.projects:
            full_path = Path(config.root_dir) / p.directory
            exists = "EXISTS" if full_path.exists() else "MISSING"
            is_git = is_git_repository(full_path) if full_path.exists() else False
            git_status = "git repo" if is_git else "not a git repo"
            print(f"  - {p.directory}: main={p.main_branch} [{exists}, {git_status}]")
        return 0

    # Process projects
    print(f"Rebase All to Main - Processing {len(config.projects)} projects")
    print(f"Root directory: {config.root_dir}")
    print(f"Default doc branch: {config.doc_branch}")

    results: list[ProjectResult] = []
    has_failures = False

    for project in config.projects:
        result = process_project(project, config)
        results.append(result)

        if result.status == 'failed':
            has_failures = True
            if config.exit_on_first_failure:
                print("\nExit on first failure enabled - stopping.")
                break

    # Print summary
    print_summary(results)

    if has_failures:
        print_help_on_failure(results)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
