#!/usr/bin/env python3
"""
Render Mermaid diagrams to PNG.

Usage:
    python render_mermaid.py                    # Render all diagrams
    python render_mermaid.py --project proj     # Render single project
    python render_mermaid.py --check            # Check which need rendering
"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_mmd_files(diagrams_dir: Path, project: str = None):
    """Find all .mmd files."""
    if project:
        search_dir = diagrams_dir / 'projects' / project
    else:
        search_dir = diagrams_dir

    if not search_dir.exists():
        return []

    return list(search_dir.rglob('*.mmd'))


def needs_rendering(mmd_file: Path) -> bool:
    """Check if PNG needs to be regenerated."""
    png_file = mmd_file.with_suffix('.png')

    if not png_file.exists():
        return True

    # Check if MMD is newer than PNG
    return mmd_file.stat().st_mtime > png_file.stat().st_mtime


def render_diagram(mmd_file: Path, diagrams_dir: Path) -> bool:
    """Render a single Mermaid diagram."""
    png_file = mmd_file.with_suffix('.png')

    cmd = [
        'mmdc',
        '-i', str(mmd_file),
        '-o', str(png_file),
        '-w', '2400',
        '-H', '1600',
        '-c', str(diagrams_dir / 'mermaid.config.json'),
        '--puppeteerConfigFile', str(diagrams_dir / '.puppeteer.json')
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"Error rendering {mmd_file.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Render Mermaid diagrams')
    parser.add_argument('--project', '-p', help='Render only specific project')
    parser.add_argument('--check', '-c', action='store_true',
                        help='Check which diagrams need rendering')
    parser.add_argument('--diagrams-dir', '-d', default='docs/diagrams',
                        help='Path to diagrams directory')

    args = parser.parse_args()

    diagrams_dir = Path(args.diagrams_dir)

    if not diagrams_dir.exists():
        print(f"Error: Diagrams directory not found: {diagrams_dir}")
        sys.exit(1)

    mmd_files = find_mmd_files(diagrams_dir, args.project)

    if not mmd_files:
        print("No Mermaid files found")
        sys.exit(0)

    print(f"Found {len(mmd_files)} Mermaid files")

    if args.check:
        # Just check which need rendering
        needs_render = [f for f in mmd_files if needs_rendering(f)]
        up_to_date = [f for f in mmd_files if not needs_rendering(f)]

        print(f"\nNeeds rendering: {len(needs_render)}")
        for f in needs_render[:10]:
            print(f"  - {f.relative_to(diagrams_dir)}")
        if len(needs_render) > 10:
            print(f"  ... and {len(needs_render) - 10} more")

        print(f"\nUp to date: {len(up_to_date)}")
    else:
        # Render files
        success_count = 0
        for mmd_file in mmd_files:
            if not needs_rendering(mmd_file):
                print(f"⏭️  {mmd_file.name} (up to date)")
                success_count += 1
                continue

            print(f"🔄 {mmd_file.name}...", end=' ', flush=True)

            if render_diagram(mmd_file, diagrams_dir):
                print("✅")
                success_count += 1
            else:
                print("❌")

        print(f"\n{success_count}/{len(mmd_files)} diagrams rendered")


if __name__ == '__main__':
    main()
