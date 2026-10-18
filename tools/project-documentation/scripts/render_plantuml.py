#!/usr/bin/env python3
"""
Render PlantUML diagrams to PNG.

Primary path: Kroki (https://kroki.io) over HTTP POST — no local Java needed.
Fallback: a local `plantuml` executable, if the Kroki request fails.

Usage:
    python render_plantuml.py [--project NAME] [--diagrams-dir DIR]
                              [--kroki-url URL] [--check]
"""

import argparse
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_KROKI = "https://kroki.io"


def find_puml_files(diagrams_dir: Path, project: str = None):
    """Find all .puml / .plantuml files."""
    search_dir = diagrams_dir / 'projects' / project if project else diagrams_dir
    if not search_dir.exists():
        return []
    return list(search_dir.rglob('*.puml')) + list(search_dir.rglob('*.plantuml'))


def needs_rendering(src: Path) -> bool:
    png = src.with_suffix('.png')
    return not png.exists() or src.stat().st_mtime > png.stat().st_mtime


def render_kroki(src: Path, out: Path, kroki_url: str) -> bool:
    data = src.read_bytes()
    req = urllib.request.Request(
        f"{kroki_url.rstrip('/')}/plantuml/png",
        data=data,
        headers={'Content-Type': 'text/plain'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out.write_bytes(resp.read())
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"  Kroki failed ({exc}); trying local plantuml ...", file=sys.stderr)
        return False


def render_local(src: Path, out: Path) -> bool:
    try:
        result = subprocess.run(
            ['plantuml', '-tpng', str(src)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        return False
    generated = src.with_suffix('.png')
    if result.returncode == 0 and generated.exists():
        if generated != out:
            generated.replace(out)
        return True
    if result.stderr:
        print(f"  plantuml: {result.stderr.strip()}", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Render PlantUML diagrams to PNG')
    parser.add_argument('--project', help='Only render diagrams for this project')
    parser.add_argument('--diagrams-dir', type=Path, default=Path('docs/project/diagrams'),
                        help='Directory containing .puml/.plantuml files')
    parser.add_argument('--kroki-url', default=DEFAULT_KROKI,
                        help=f'Kroki base URL (default: {DEFAULT_KROKI})')
    parser.add_argument('--check', action='store_true',
                        help='Only list diagrams that need rendering')
    args = parser.parse_args()

    files = find_puml_files(args.diagrams_dir, args.project)
    if not files:
        print(f"No PlantUML files found under {args.diagrams_dir}")
        return 0

    if args.check:
        pending = [f for f in files if needs_rendering(f)]
        for f in pending:
            print(f)
        print(f"{len(pending)} of {len(files)} need rendering")
        return 0

    failures = 0
    for src in files:
        out = src.with_suffix('.png')
        if not needs_rendering(src):
            print(f"skip (up to date): {src}")
            continue
        ok = render_kroki(src, out, args.kroki_url) or render_local(src, out)
        if ok:
            print(f"rendered: {src} -> {out}")
        else:
            print(f"FAILED: {src}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
