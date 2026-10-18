#!/usr/bin/env python3
"""
Project Documentation Tool

Creates, updates, and manages architectural documentation that lives with the
source code under docs/project/ (configured by source_dir / PROJECT_DOCS_DIR),
following the standard in docs/DOCUMENTATION-GUIDELINES.md.

Usage:
    python project_docs.py --list-projects
    python project_docs.py --create-docs --project <name>
    python project_docs.py --create-docs --all-projects
    python project_docs.py --render-diagrams
    python project_docs.py --check-completeness
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


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


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    directory: str
    main_branch: str
    doc_branch: str
    type: str
    description: str


@dataclass
class DocumentationConfig:
    """Documentation generation configuration."""
    source_dir: str
    diagrams_dir: str
    output_format: str
    include_yaml_companion: bool
    include_diagrams: bool


class DocumentationManager:
    """Manages documentation creation, rendering, and deployment."""

    def __init__(self, config_path: Path):
        """Initialize with configuration file."""
        self.config = self._load_config(config_path)
        self.root_dir = Path(self.config.get('root_dir', '.')).resolve()
        self.doc_branch = self.config.get('doc_branch', 'docs')
        self.projects = self._load_projects()
        self.doc_config = self._load_doc_config()

    def _load_config(self, config_path: Path) -> dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_projects(self) -> list[ProjectConfig]:
        """Load project configurations."""
        projects = []
        for p in self.config.get('projects', []):
            projects.append(ProjectConfig(
                directory=p['directory'],
                main_branch=p['main_branch'],
                doc_branch=p.get('doc_branch', self.doc_branch),
                type=p['type'],
                description=p['description']
            ))
        return projects

    def _load_doc_config(self) -> DocumentationConfig:
        """Load documentation configuration."""
        doc_cfg = self.config.get('documentation', {})
        return DocumentationConfig(
            source_dir=os.environ.get('PROJECT_DOCS_DIR', doc_cfg.get('source_dir', 'docs/project')),
            diagrams_dir=doc_cfg.get('diagrams_dir', 'docs/project/diagrams'),
            output_format=doc_cfg.get('output_format', 'markdown'),
            include_yaml_companion=doc_cfg.get('include_yaml_companion', True),
            include_diagrams=doc_cfg.get('include_diagrams', True)
        )

    def list_projects(self) -> None:
        """List all configured projects."""
        print("\nConfigured Projects:")
        print("=" * 80)
        print(f"{'Directory':<25} {'Type':<20} {'Main Branch':<20} {'Doc Branch':<20}")
        print("-" * 80)
        for p in self.projects:
            print(f"{p.directory:<25} {p.type:<20} {p.main_branch:<20} {p.doc_branch:<20}")
        print(f"\nTotal: {len(self.projects)} projects")

    def setup_projects(self) -> None:
        """Interactive setup to add/remove projects from config."""
        print("\nProject Setup - Managing Configuration")
        print("=" * 80)
        print(f"Root directory: {self.root_dir}")
        print()

        # Find all directories that are git repositories
        git_dirs = self._find_git_repositories()
        print(f"Found {len(git_dirs)} git repositories:")
        print()

        # Get current project directories
        configured_dirs = {p.directory for p in self.projects}

        # Show status of each repo
        for i, (dir_name, is_configured) in enumerate(git_dirs, 1):
            status = "[CONFIGURED]" if is_configured else "[NOT CONFIGURED]"
            print(f"{i:2}. {dir_name:<30} {status}")

        print()
        print("Options:")
        print("  a) Add all unconfigured projects")
        print("  r) Remove projects")
        print("  numbers) Add specific projects (e.g., '1 3 5' or '1-5')")
        print("  s) Skip (no changes)")
        print()

        choice = input("Your choice: ").strip().lower()

        if choice == 's':
            print("No changes made.")
            return

        dirs_to_add = []
        dirs_to_remove = []

        if choice == 'a':
            # Add all unconfigured
            dirs_to_add = [d for d, configured in git_dirs if not configured]

        elif choice == 'r':
            # Remove mode
            print()
            print("Configured projects to remove:")
            for i, p in enumerate(self.projects, 1):
                print(f"{i}. {p.directory}")
            print()
            remove_input = input("Enter numbers to remove (e.g., '1 3' or '1-3'): ").strip()
            dirs_to_remove = self._parse_number_input(remove_input, [p.directory for p in self.projects])

        else:
            # Parse number input for adding
            all_dir_names = [d for d, _ in git_dirs]
            selected = self._parse_number_input(choice, all_dir_names)
            dirs_to_add = [d for d in selected if d not in configured_dirs]

        # Process removals
        if dirs_to_remove:
            print()
            print(f"Removing {len(dirs_to_remove)} project(s):")
            for d in dirs_to_remove:
                print(f"  - {d}")
            self.projects = [p for p in self.projects if p.directory not in dirs_to_remove]
            print("  ✅ Removed from configuration")

        # Process additions
        if dirs_to_add:
            print()
            print(f"Adding {len(dirs_to_add)} project(s):")

            for dir_name in dirs_to_add:
                print()
                print(f"  Project: {dir_name}")
                print("  " + "-" * 40)

                project_path = self.root_dir / dir_name

                # Detect main branch
                main_branch = self._detect_main_branch(project_path)
                print(f"  Detected main branch: {main_branch}")

                # Detect project type
                detected_type = self._detect_project_type(project_path)
                print(f"  Detected type: {detected_type}")

                # Get description
                description = self._get_project_description(project_path, dir_name)
                print(f"  Description: {description}")

                # Allow user to override
                print()
                override = input("  Press Enter to accept, or type 'edit' to modify: ").strip()

                if override.lower() == 'edit':
                    main_branch = input(f"    Main branch [{main_branch}]: ").strip() or main_branch
                    detected_type = input(f"    Type [{detected_type}]: ").strip() or detected_type
                    description = input(f"    Description [{description}]: ").strip() or description

                # Add to projects
                self.projects.append(ProjectConfig(
                    directory=dir_name,
                    main_branch=main_branch,
                    doc_branch=self.doc_branch,
                    type=detected_type,
                    description=description
                ))
                print(f"  ✅ Added {dir_name}")

        # Save configuration
        if dirs_to_add or dirs_to_remove:
            self._save_config()
            print()
            print("=" * 80)
            print(f"Configuration saved! Total projects: {len(self.projects)}")
        else:
            print()
            print("No changes made.")

    def _find_git_repositories(self) -> list[tuple[str, bool]]:
        """Find all git repositories in root directory."""
        git_dirs = []
        configured_dirs = {p.directory for p in self.projects}

        try:
            for entry in sorted(self.root_dir.iterdir()):
                if entry.is_dir() and (entry / '.git').exists():
                    is_configured = entry.name in configured_dirs
                    git_dirs.append((entry.name, is_configured))
        except Exception as e:
            print(f"Error scanning directories: {e}")

        return git_dirs

    def _detect_main_branch(self, project_path: Path) -> str:
        """Detect the main branch of a git repository."""
        try:
            # Try to get the default branch
            result = subprocess.run(
                ['git', '-C', str(project_path), 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Parse "refs/remotes/origin/main" -> "main"
                return result.stdout.strip().split('/')[-1]

            # Fallback: check common branch names
            for branch in ['main', 'master', 'develop']:
                result = subprocess.run(
                    ['git', '-C', str(project_path), 'rev-parse', '--verify', branch],
                    capture_output=True
                )
                if result.returncode == 0:
                    return branch

            # Get current branch as fallback
            result = subprocess.run(
                ['git', '-C', str(project_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()

        except Exception:
            pass

        return "main"  # Default fallback

    def _detect_project_type(self, project_path: Path) -> str:
        """Detect project type based on files in repository."""
        # Check for various project indicators
        checks = [
            # Angular (check before .NET because of project.json confusion)
            (['angular.json', 'package.json', 'ng'], 'angular-frontend'),
            # Angular Library
            (['package.json', 'ng-package.json'], 'angular-library'),
            # Rust
            (['Cargo.toml'], 'rust-simulator'),
            # C++
            (['CMakeLists.txt'], 'cpp-library'),
            # Java/Kotlin (Eclipse RCP)
            (['build.gradle.kts', 'build.gradle', 'MANIFEST.MF'], 'java-desktop'),
            # .NET Web (check for web-specific patterns)
            (['.csproj', 'Program.cs', 'Startup.cs'], 'dotnet-service'),
            (['.csproj', 'Controllers/'], 'dotnet-service'),
            (['.csproj', 'Features/'], 'dotnet-service'),
            # .NET Desktop
            (['.csproj', 'Avalonia'], 'dotnet-desktop'),
            (['.csproj', 'WPF'], 'dotnet-desktop'),
            # .NET Library
            (['.csproj'], 'dotnet-library'),
            # .NET Monolith (check for larger structure)
            (['.sln', 'src/', 'tests/'], 'dotnet-monolith'),
        ]

        for indicators, ptype in checks:
            found_all = True
            for indicator in indicators:
                # Check if it's a file pattern
                if indicator.endswith('/') or indicator.startswith('.'):
                    found = any(
                        str(p).endswith(indicator.rstrip('/')) or
                        indicator in str(p)
                        for p in project_path.rglob('*')
                    )
                else:
                    found = any(
                        indicator in str(p.name) or indicator == p.name
                        for p in project_path.rglob('*')
                    )

                if not found:
                    found_all = False
                    break

            if found_all:
                return ptype

        # Additional checks for .NET project subtypes
        if any(list(project_path.rglob('*.csproj'))):
            # Check if it's a library or service
            csprojs = list(project_path.rglob('*.csproj'))
            for csproj in csprojs:
                try:
                    content = csproj.read_text().lower()
                    if 'microsoft.net.sdk.web' in content:
                        return 'dotnet-service'
                    elif 'avalonia' in content or 'wpf' in content:
                        return 'dotnet-desktop'
                    elif 'microsoft.net.sdk' in content and 'web' not in content:
                        # Check for test project
                        if 'test' in str(csproj).lower():
                            continue
                        return 'dotnet-library'
                except:
                    pass
            return 'dotnet-library'

        return 'unknown'

    def _get_project_description(self, project_path: Path, dir_name: str) -> str:
        """Extract project description from README or guess from directory name."""
        # Try to get from README
        readme_files = ['README.md', 'readme.md', 'Readme.md', 'README.rst']
        for readme_name in readme_files:
            readme_path = project_path / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding='utf-8', errors='ignore')
                    # Get first non-empty line that isn't a heading
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and len(line) > 10:
                            # Truncate to reasonable length
                            desc = line[:80]
                            if len(line) > 80:
                                desc += "..."
                            return desc
                except:
                    pass

        # Try to get from package.json or Cargo.toml
        for config_file, desc_key in [
            ('package.json', 'description'),
            ('Cargo.toml', 'description')
        ]:
            config_path = project_path / config_file
            if config_path.exists():
                try:
                    import json
                    data = json.loads(config_path.read_text())
                    desc = data.get(desc_key, '')
                    if desc:
                        return desc[:80] + ('...' if len(desc) > 80 else '')
                except:
                    pass

        # Fallback: generate from directory name
        name_parts = dir_name.replace('-', ' ').replace('_', ' ').split()
        return f"Project for {dir_name}"

    def _parse_number_input(self, input_str: str, available_items: list) -> list:
        """Parse number ranges like '1 3 5' or '1-5' or '1,3,5'."""
        if not input_str:
            return []

        selected = set()

        # Split by comma, space, or both
        parts = input_str.replace(',', ' ').split()

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for range (e.g., "1-5")
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start_idx = int(start.strip()) - 1
                    end_idx = int(end.strip())

                    if 0 <= start_idx < len(available_items):
                        for i in range(start_idx, min(end_idx, len(available_items))):
                            selected.add(available_items[i])
                except ValueError:
                    continue
            else:
                # Single number
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(available_items):
                        selected.add(available_items[idx])
                except ValueError:
                    continue

        return list(selected)

    def _save_config(self) -> None:
        """Save the updated configuration to JSON file."""
        # Convert projects back to dict
        self.config['projects'] = [
            {
                'directory': p.directory,
                'main_branch': p.main_branch,
                'doc_branch': p.doc_branch,
                'type': p.type,
                'description': p.description
            }
            for p in self.projects
        ]

        # Write to file
        config_path = Path(__file__).parent / 'config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def check_completeness(self) -> None:
        """Check documentation completeness for all projects."""
        print("\nDocumentation Completeness Check:")
        print("=" * 80)

        standard = self.config.get('documentation_standard', {})
        required = standard.get('required_files', [])
        optional = standard.get('optional_files', [])

        for project in self.projects:
            project_doc_dir = self.root_dir / self.doc_config.source_dir / project.directory

            if not project_doc_dir.exists():
                print(f"\n{project.directory}: ❌ No documentation directory")
                continue

            missing_required = []
            present_required = []
            present_optional = []

            for f in required:
                if (project_doc_dir / f).exists():
                    present_required.append(f)
                else:
                    missing_required.append(f)

            for f in optional:
                if (project_doc_dir / f).exists():
                    present_optional.append(f)

            total_files = len(present_required) + len(present_optional)
            expected_files = len(required)

            if len(missing_required) == 0:
                status = "✅ Complete"
            else:
                status = f"⚠️  {len(missing_required)} required files missing"

            print(f"\n{project.directory}: {status}")
            print(f"  Required: {len(present_required)}/{len(required)} files")
            print(f"  Optional: {len(present_optional)}/{len(optional)} files")

            if missing_required:
                print(f"  Missing: {', '.join(missing_required[:3])}{'...' if len(missing_required) > 3 else ''}")

    def create_docs(self, project_name: Optional[str] = None, all_projects: bool = False) -> None:
        """Create documentation for specified project(s)."""
        if all_projects:
            projects_to_process = self.projects
        elif project_name:
            projects_to_process = [p for p in self.projects if p.directory == project_name]
            if not projects_to_process:
                print(f"Error: Project '{project_name}' not found in configuration")
                return
        else:
            print("Error: Specify --project or --all-projects")
            return

        print(f"\nCreating documentation for {len(projects_to_process)} project(s)...")
        print("=" * 80)

        for project in projects_to_process:
            print(f"\n{project.directory}:")
            print("-" * 40)

            # Create documentation directory
            doc_dir = self.root_dir / self.doc_config.source_dir / project.directory
            doc_dir.mkdir(parents=True, exist_ok=True)

            # Generate documentation using project-specific prompt
            self._generate_project_docs(project, doc_dir)

        print(f"\nDocumentation creation complete for {len(projects_to_process)} project(s)")

    def _generate_project_docs(self, project: ProjectConfig, doc_dir: Path) -> None:
        """Generate documentation for a single project."""
        # This would call Claude Code with appropriate prompts
        # For now, we create the command that should be run

        project_path = self.root_dir / project.directory

        if not project_path.exists():
            print(f"  ⚠️  Project directory not found: {project_path}")
            return

        print(f"  📁 Project path: {project_path}")
        print(f"  📄 Doc output: {doc_dir}")
        print(f"  📋 Type: {project.type}")

        # Generate prompt for this project
        prompt = self._generate_documentation_prompt(project, doc_dir)

        # Save prompt to file for reference
        prompt_file = doc_dir / ".documentation-prompt.md"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)

        print(f"  ✏️  Prompt saved to: {prompt_file}")
        print(f"  💡 Run this command with Claude Code to generate docs:")
        print(f"     claude --prompt '{prompt_file}'")

    def _generate_documentation_prompt(self, project: ProjectConfig, doc_dir: Path) -> str:
        """Generate the documentation creation prompt for a project."""
        standard = self.config.get('documentation_standard', {})
        required = standard.get('required_files', [])
        optional = standard.get('optional_files', [])
        diagrams = standard.get('diagram_files', [])

        prompt = f"""# Documentation Generation Task for {project.directory}

Create exhaustive, comprehensive documentation for the {project.directory} project.

## Project Information
- **Name**: {project.directory}
- **Type**: {project.type}
- **Description**: {project.description}
- **Documentation Directory**: {doc_dir}
- **Project Directory**: {self.root_dir / project.directory}

## Required Documentation Files

Create these files in `{doc_dir}`:

"""

        for i, f in enumerate(required, 1):
            prompt += f"{i}. `{f}`\n"

        prompt += "\n## Optional Documentation Files\n\n"
        for i, f in enumerate(optional, 1):
            prompt += f"{i}. `{f}` (if applicable)\n"

        prompt += f"""
## Diagram Files to Create

In `{self.root_dir / self.doc_config.diagrams_dir}/projects/{project.directory}/`:

"""
        for i, f in enumerate(diagrams, 1):
            prompt += f"{i}. `{f}` (Mermaid diagram)\n"

        prompt += """
## Content Guidelines

1. **techstack.md + .yaml**: Complete technology inventory with versions
2. **project-summary.md**: Business context, technical responsibilities, design decisions
3. **architecture.md**: C4 diagrams (Context, Container, Component), data flow
4. **api-reference.md + .yaml**: All endpoints, request/response schemas
5. **domain-model.md + .yaml**: Entities, aggregates, domain events
6. **configuration.md + .yaml**: Config keys, env vars, secrets
7. **design-decisions.md**: ADRs with "Why" callouts
8. **integration-guide.md**: Build, test, deployment instructions
9. **messaging.md + .yaml** (if applicable): Async messaging contracts
10. **protocols.md + .yaml** (if applicable): Protocol specifications

## Requirements

- Use actual type names, field names, and method signatures from source code
- Include extensive "Why" callouts for design decisions
- No emojis
- Tables for structured data
- Follow the structure of docs/projects/config-hub/ for reference
- Be comprehensive - documentation serves both humans and AI agents
- Copy actual names from source - no paraphrasing

## Project-Specific Instructions

"""
        # Add type-specific instructions
        if 'dotnet' in project.type:
            prompt += """For .NET projects:
- Document all public APIs (controllers, services, repositories)
- Include EF Core entities and migrations
- Document Dapr pub/sub topics if applicable
- Include CQRS handlers if using MediatR
"""
        elif 'angular' in project.type:
            prompt += """For Angular projects:
- Document library structure and exports
- Include NgRx state management patterns
- Document component architecture
- Include build configuration
"""
        elif 'java' in project.type:
            prompt += """For Java projects:
- Document module structure
- Include D-Bus interfaces
- Document JNI usage
- Include MQTT protocol details
"""
        elif 'rust' in project.type:
            prompt += """For Rust projects:
- Document async/await patterns
- Include struct and trait definitions
- Document MQTT/WebSocket protocols
- Include Cargo dependencies
"""
        elif 'cpp' in project.type:
            prompt += """For C++ projects:
- Document CMake configuration
- Include header API documentation
- Document D-Bus interfaces
- Include protocol specifications
"""

        return prompt

    def render_diagrams(self, project_name: Optional[str] = None) -> None:
        """Render Mermaid diagrams to PNG."""
        diagrams_dir = self.root_dir / self.doc_config.diagrams_dir

        if not diagrams_dir.exists():
            print(f"Error: Diagrams directory not found: {diagrams_dir}")
            return

        print("\nRendering diagrams to PNG...")
        print("=" * 80)

        # Find all .mmd files
        if project_name:
            mmd_files = list((diagrams_dir / 'projects' / project_name).rglob('*.mmd'))
        else:
            mmd_files = list(diagrams_dir.rglob('*.mmd'))

        if not mmd_files:
            print("No Mermaid diagram files found")
            return

        print(f"Found {len(mmd_files)} diagram files")

        # Render each file
        success_count = 0
        for mmd_file in mmd_files:
            png_file = mmd_file.with_suffix('.png')

            # Skip if PNG is newer than MMD
            if png_file.exists() and png_file.stat().st_mtime > mmd_file.stat().st_mtime:
                print(f"  ⏭️  {mmd_file.name} (up to date)")
                success_count += 1
                continue

            print(f"  🔄 Rendering: {mmd_file.name}")

            # Build mmdc command
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
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print(f"  ✅ {mmd_file.name}")
                    success_count += 1
                else:
                    print(f"  ❌ {mmd_file.name}: {result.stderr[:100]}")
            except Exception as e:
                print(f"  ❌ {mmd_file.name}: {e}")

        print(f"\n{success_count}/{len(mmd_files)} diagrams rendered successfully")

    def commit_and_push(self, project_name: Optional[str] = None, all_projects: bool = False) -> None:
        """Commit documentation and push to origin."""
        if all_projects:
            projects_to_process = self.projects
        elif project_name:
            projects_to_process = [p for p in self.projects if p.directory == project_name]
            if not projects_to_process:
                print(f"Error: Project '{project_name}' not found")
                return
        else:
            print("Error: Specify --project or --all-projects")
            return

        print(f"\nCommitting and pushing documentation for {len(projects_to_process)} project(s)...")
        print("=" * 80)

        behavior = self.config.get('behavior', {})
        commit_msg = behavior.get('commit_message_template', 'docs: update documentation')

        for project in projects_to_process:
            print(f"\n{project.directory}:")
            print("-" * 40)

            project_path = self.root_dir / project.directory

            if not (project_path / '.git').exists():
                print(f"  ⚠️  Not a git repository, skipping")
                continue

            # Check and switch branch
            current_branch = self._get_current_branch(project_path)
            print(f"  Branch: {current_branch}")

            if current_branch != project.doc_branch:
                if behavior.get('auto_switch_branch', True):
                    print(f"  Switching to {project.doc_branch}...")
                    if not self._switch_branch(project_path, project.doc_branch):
                        print(f"  ❌ Failed to switch branch")
                        continue
                else:
                    print(f"  ⚠️  Not on doc branch, skipping")
                    continue

            # Check for changes
            if not self._has_changes(project_path, 'docs/'):
                print(f"  ⏭️  No documentation changes to commit")
                continue

            # Stage changes
            print(f"  Staging docs/ directory...")
            self._git_command(project_path, ['add', 'docs/'])

            # Commit
            print(f"  Committing...")
            result = self._git_command(project_path, ['commit', '-m', commit_msg])
            if result.returncode != 0:
                print(f"  ❌ Commit failed")
                continue

            print(f"  ✅ Committed")

            # Push
            print(f"  Pushing to origin...")
            result = self._git_command(project_path, ['push', 'origin', project.doc_branch])
            if result.returncode == 0:
                print(f"  ✅ Pushed to origin/{project.doc_branch}")
            else:
                print(f"  ❌ Push failed")

        print(f"\nCommit and push complete")

    def _get_current_branch(self, project_path: Path) -> str:
        """Get current git branch."""
        result = subprocess.run(
            ['git', '-C', str(project_path), 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def _switch_branch(self, project_path: Path, branch: str) -> bool:
        """Switch to specified branch, creating if necessary."""
        # Check if branch exists locally
        result = subprocess.run(
            ['git', '-C', str(project_path), 'branch', '--list', branch],
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            # Branch exists locally
            result = subprocess.run(
                ['git', '-C', str(project_path), 'checkout', branch],
                capture_output=True
            )
        else:
            # Check if on remote
            result = subprocess.run(
                ['git', '-C', str(project_path), 'branch', '-r', '--list', f'origin/{branch}'],
                capture_output=True,
                text=True
            )

            if result.stdout.strip():
                # Branch exists on remote
                subprocess.run(
                    ['git', '-C', str(project_path), 'checkout', '-b', branch, f'origin/{branch}'],
                    capture_output=True
                )
            else:
                # Create new branch
                subprocess.run(
                    ['git', '-C', str(project_path), 'checkout', '-b', branch],
                    capture_output=True
                )

        return self._get_current_branch(project_path) == branch

    def _has_changes(self, project_path: Path, path: str) -> bool:
        """Check if specified path has uncommitted changes."""
        result = subprocess.run(
            ['git', '-C', str(project_path), 'status', '--short', path],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())

    def _git_command(self, project_path: Path, args: list) -> subprocess.CompletedProcess:
        """Run git command in project directory."""
        return subprocess.run(
            ['git', '-C', str(project_path)] + args,
            capture_output=True,
            text=True
        )

    def full_workflow(self, project_name: Optional[str] = None, all_projects: bool = False) -> None:
        """Run complete documentation workflow."""
        print("\n" + "=" * 80)
        print("CLAUDE DOCUMENTATION FULL WORKFLOW")
        print("=" * 80)

        # Step 1: Create documentation
        print("\n📋 STEP 1: Creating Documentation")
        print("-" * 80)
        self.create_docs(project_name, all_projects)

        # Step 2: Render diagrams
        print("\n🎨 STEP 2: Rendering Diagrams")
        print("-" * 80)
        self.render_diagrams(project_name)

        # Step 3: Commit and push
        print("\n📤 STEP 3: Committing and Pushing")
        print("-" * 80)
        self.commit_and_push(project_name, all_projects)

        print("\n" + "=" * 80)
        print("FULL WORKFLOW COMPLETE")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Project Documentation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all projects
  %(prog)s --list-projects

  # Interactive setup - add/remove projects from config
  %(prog)s --setup-projects

  # Create docs for single project
  %(prog)s --create-docs --project claiming-service

  # Create docs for all projects
  %(prog)s --create-docs --all-projects

  # Render diagrams
  %(prog)s --render-diagrams

  # Commit and push
  %(prog)s --commit-push --all-projects

  # Full workflow for all projects
  %(prog)s --full-workflow --all-projects
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path(__file__).parent / 'config.json',
        help='Path to configuration JSON file (default: config.json)'
    )

    parser.add_argument(
        '--list-projects', '-l',
        action='store_true',
        help='List all configured projects'
    )

    parser.add_argument(
        '--create-docs',
        action='store_true',
        help='Create documentation for project(s)'
    )

    parser.add_argument(
        '--render-diagrams', '-r',
        action='store_true',
        help='Render Mermaid diagrams to PNG'
    )

    parser.add_argument(
        '--commit-push', '-p',
        action='store_true',
        help='Commit documentation and push to origin'
    )

    parser.add_argument(
        '--check-completeness',
        action='store_true',
        help='Check documentation completeness for all projects'
    )

    parser.add_argument(
        '--full-workflow', '-f',
        action='store_true',
        help='Run complete workflow: create docs, render diagrams, commit/push'
    )

    parser.add_argument(
        '--project', '-n',
        type=str,
        help='Target specific project by directory name'
    )

    parser.add_argument(
        '--all-projects', '-a',
        action='store_true',
        help='Target all projects'
    )

    parser.add_argument(
        '--setup-projects', '-s',
        action='store_true',
        help='Interactive setup: add/remove projects from config.json based on git repositories in root directory'
    )

    args = parser.parse_args()
    load_devenvironment()

    # Initialize manager
    if not args.config.exists():
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    manager = DocumentationManager(args.config)

    # Execute commands
    if args.list_projects:
        manager.list_projects()

    elif args.check_completeness:
        manager.check_completeness()

    elif args.setup_projects:
        manager.setup_projects()

    elif args.create_docs:
        manager.create_docs(args.project, args.all_projects)

    elif args.render_diagrams:
        manager.render_diagrams(args.project)

    elif args.commit_push:
        manager.commit_and_push(args.project, args.all_projects)

    elif args.full_workflow:
        manager.full_workflow(args.project, args.all_projects)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
