#!/usr/bin/env python3
"""
Release Notes Generator for GitHub Actions.

This script generates release notes based on Git history, categorizing commits
and providing different formats for automatic and manual releases.
"""

import os
import re
import subprocess
import sys

def get_last_tag() -> str | None:
    """Get the last release tag."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since_tag(tag: str | None) -> list[str]:
    """Get commits since the specified tag."""
    if tag:
        cmd = ['git', 'log', f'{tag}..HEAD', '--pretty=format:%H|%s|%an|%b']
    else:
        cmd = ['git', 'log', '--pretty=format:%H|%s|%an|%b']

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def get_pr_numbers(since_tag: str | None) -> list[str]:
    """Extract PR numbers from commit messages."""
    if since_tag:
        cmd = ['git', 'log', f'{since_tag}..HEAD', '--pretty=format:%s']
    else:
        cmd = ['git', 'log', '--pretty=format:%s']

    result = subprocess.run(cmd, capture_output=True, text=True)
    messages = result.stdout.strip().split('\n') if result.stdout else []

    pr_numbers: list[str] = []
    for msg in messages:
        # Match patterns like (#123), #123, PR #123
        matches = re.findall(r'(?:#|PR\s*#)(\d+)', msg)
        pr_numbers.extend(matches)

    return list(set(pr_numbers))  # Remove duplicates


def get_contributors(since_tag: str | None) -> list[str]:
    """Get unique contributors since last tag."""
    if since_tag:
        cmd = ['git', 'log', f'{since_tag}..HEAD', '--pretty=format:%an <%ae>']
    else:
        cmd = ['git', 'log', '--pretty=format:%an <%ae>']

    result = subprocess.run(cmd, capture_output=True, text=True)
    contributors_raw = result.stdout.strip().split('\n') if result.stdout else []
    contributors: set[str] = set(contributors_raw)

    # Remove bot accounts
    contributors_filtered = {c for c in contributors if 'bot' not in c.lower() and c}

    return sorted(contributors_filtered)


def categorize_commits(commits: list[str], is_manual: bool = False) -> tuple[dict[str, list[str | tuple[str, str, str]]], list[str]]:
    """Categorize commits by type."""
    categories: dict[str, list[str | tuple[str, str, str]]] = {}

    if is_manual:
        categories = {
            '✨ Features': [],
            '🐛 Bug Fixes': [],
            '🌐 Translations': [],
            '📚 Documentation': [],
            '🔧 Maintenance': [],
            '⚡ Performance': [],
            '🔒 Security': [],
            '🎨 UI/UX': []
        }
    else:
        categories = {
            'Features': [],
            'Bug Fixes': [],
            'Translations': [],
            'Documentation': [],
            'Other': []
        }

    breaking_changes: list[str] = []

    for commit_line in commits:
        if not commit_line:
            continue

        parts = commit_line.split('|', 3)
        if len(parts) < 3:
            continue

        hash_val = parts[0][:7]
        message = parts[1]
        author = parts[2]
        body = parts[3] if len(parts) > 3 else ''

        # Check for breaking changes
        if 'BREAKING' in message.upper() or 'BREAKING' in body.upper():
            breaking_changes.append(f"{message} ({hash_val})")

        # Categorize based on conventional commits
        if is_manual:
            if message.startswith(('feat:', 'feat(', 'feature:', 'feature(')):
                categories['✨ Features'].append(f"{message} ({hash_val})")
            elif message.startswith(('fix:', 'fix(', 'bugfix:', 'bugfix(')):
                categories['🐛 Bug Fixes'].append(f"{message} ({hash_val})")
            elif any(word in message.lower() for word in ['i18n', 'translation', 'locale']):
                categories['🌐 Translations'].append(f"{message} ({hash_val})")
            elif message.startswith(('docs:', 'doc:', 'documentation:')):
                categories['📚 Documentation'].append(f"{message} ({hash_val})")
            elif message.startswith(('perf:', 'performance:')):
                categories['⚡ Performance'].append(f"{message} ({hash_val})")
            elif message.startswith(('security:', 'sec:')):
                categories['🔒 Security'].append(f"{message} ({hash_val})")
            elif any(word in message.lower() for word in ['ui', 'ux', 'style', 'design']):
                categories['🎨 UI/UX'].append(f"{message} ({hash_val})")
            else:
                categories['🔧 Maintenance'].append(f"{message} ({hash_val})")
        else:
            if message.startswith('feat:') or message.startswith('feat('):
                categories['Features'].append((hash_val, message, author))
            elif message.startswith('fix:') or message.startswith('fix('):
                categories['Bug Fixes'].append((hash_val, message, author))
            elif 'i18n' in message or 'translation' in message.lower() or 'locale' in message:
                categories['Translations'].append((hash_val, message, author))
            elif message.startswith('docs:') or message.startswith('doc:'):
                categories['Documentation'].append((hash_val, message, author))
            else:
                categories['Other'].append((hash_val, message, author))

    return categories, breaking_changes


def generate_automatic_release_notes(version: str, version_type: str, completed_langs: list[str]) -> list[str]:
    """Generate release notes for automatic releases."""
    last_tag = get_last_tag()
    commits = get_commits_since_tag(last_tag)
    categories, _ = categorize_commits(commits, is_manual=False)

    notes: list[str] = []
    notes.append(f"# TGraph Bot v{version}")
    notes.append("")

    if version_type == 'patch' and completed_langs and completed_langs[0]:
        notes.append("## 🌍 Translation Update")
        notes.append("")
        notes.append("This release includes translation updates with the following completed languages:")
        for lang in completed_langs:
            if lang:
                notes.append(f"- ✅ {lang}")
        notes.append("")

    # Add categorized commits
    for category, items in categories.items():
        if items:
            notes.append(f"## {category}")
            notes.append("")
            for hash_val, message, _ in items:
                notes.append(f"- {message} ({hash_val})")
            notes.append("")

    # Footer
    notes.append("---")
    notes.append("")
    notes.append("### Docker Image")
    notes.append("")
    notes.append("The Docker image for this release will be automatically built and published to:")
    notes.append(f"- `ghcr.io/engels74/tgraph-bot:{version}`")
    notes.append("- `ghcr.io/engels74/tgraph-bot:latest`")
    notes.append("")
    notes.append("### Installation")
    notes.append("")
    notes.append("```bash")
    notes.append(f"docker pull ghcr.io/engels74/tgraph-bot:{version}")
    notes.append("```")

    return notes


def generate_manual_release_notes(version: str, bump_type: str, custom_notes: str = "") -> list[str]:
    """Generate release notes for manual releases."""
    last_tag = get_last_tag()
    commits = get_commits_since_tag(last_tag)
    categories, breaking = categorize_commits(commits, is_manual=True)

    notes: list[str] = []
    notes.append(f"# TGraph Bot v{version}")
    notes.append("")

    # Add bump type badge
    if bump_type == 'major':
        notes.append("![Major Release](https://img.shields.io/badge/release-major-red)")
    elif bump_type == 'minor':
        notes.append("![Minor Release](https://img.shields.io/badge/release-minor-yellow)")
    else:
        notes.append("![Patch Release](https://img.shields.io/badge/release-patch-green)")

    notes.append("")

    # Add custom notes if provided
    if custom_notes.strip():
        notes.append("## Release Highlights")
        notes.append("")
        notes.append(custom_notes.strip())
        notes.append("")

    # Add breaking changes if any
    if breaking:
        notes.append("## ⚠️ BREAKING CHANGES")
        notes.append("")
        for change in breaking:
            notes.append(f"- {change}")
        notes.append("")

    # Add categorized commits
    for category, items in categories.items():
        if items:
            notes.append(f"## {category}")
            notes.append("")
            for item in items[:10]:  # Limit to 10 items per category
                notes.append(f"- {item}")
            if len(items) > 10:
                notes.append(f"- ...and {len(items) - 10} more")
            notes.append("")

    # Add PR references
    pr_numbers = get_pr_numbers(last_tag)
    if pr_numbers:
        notes.append("## 🔗 Related Pull Requests")
        notes.append("")
        for pr in pr_numbers[:10]:
            notes.append(f"- #{pr}")
        notes.append("")

    # Add contributors
    contributors = get_contributors(last_tag)
    if contributors:
        notes.append("## 👥 Contributors")
        notes.append("")
        notes.append("Thanks to everyone who contributed to this release:")
        notes.append("")
        for contributor in contributors:
            notes.append(f"- {contributor}")
        notes.append("")

    # Add footer
    notes.append("---")
    notes.append("")
    notes.append("## 📦 Installation")
    notes.append("")
    notes.append("### Docker")
    notes.append("```bash")
    notes.append(f"docker pull ghcr.io/engels74/tgraph-bot:{version}")
    notes.append("```")
    notes.append("")
    notes.append("### From Source")
    notes.append("```bash")
    notes.append("git clone https://github.com/engels74/tgraph-bot-source.git")
    notes.append(f"git checkout v{version}")
    notes.append("```")
    notes.append("")
    notes.append("## 📖 Documentation")
    notes.append("")
    notes.append("- [README](https://github.com/engels74/tgraph-bot-source/blob/main/README.md)")

    return notes


def main() -> int:
    """Main entry point for the script."""
    try:
        # Determine release type based on environment variables
        is_manual = os.environ.get('RELEASE_TYPE') == 'manual'

        if is_manual:
            version = os.environ.get('NEW_VERSION', '')
            bump_type = os.environ.get('BUMP_TYPE', '')
            custom_notes = os.environ.get('CUSTOM_NOTES', '')

            if not version or not bump_type:
                print("Error: NEW_VERSION and BUMP_TYPE must be set for manual releases", file=sys.stderr)
                return 1

            notes = generate_manual_release_notes(version, bump_type, custom_notes)
        else:
            version = os.environ.get('NEW_VERSION', '')
            version_type = os.environ.get('VERSION_TYPE', '')
            completed_langs_str = os.environ.get('COMPLETED_LANGUAGES', '')
            completed_langs = completed_langs_str.split(',') if completed_langs_str else []

            if not version or not version_type:
                print("Error: NEW_VERSION and VERSION_TYPE must be set for automatic releases", file=sys.stderr)
                return 1

            notes = generate_automatic_release_notes(version, version_type, completed_langs)

        # Write to file
        with open('release_notes.md', 'w') as f:
            _ = f.write('\n'.join(notes))

        print("Release notes generated successfully!")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
