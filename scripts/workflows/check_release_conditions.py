#!/usr/bin/env python3
"""
Release Condition Checker for GitHub Actions.

This script determines whether a release should be created based on various
conditions like translation changes, completed languages, and version requirements.
"""

import os
import subprocess
import sys
from pathlib import Path


import polib
import semver
import toml


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    with open('pyproject.toml', 'r') as f:
        data: dict[str, dict[str, str]] = toml.load(f)
        return data['project']['version']


def get_last_release_tag() -> str | None:
    """Get the last release tag."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def check_translation_changes() -> tuple[bool, list[str]]:
    """Check if there are translation changes since last release."""
    last_tag = get_last_release_tag()
    if not last_tag:
        return True, []

    # Get changed files since last tag
    result = subprocess.run(
        ['git', 'diff', '--name-only', f'{last_tag}..HEAD', 'locale/'],
        capture_output=True, text=True
    )

    changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
    return bool(changed_files), changed_files


def get_completed_languages() -> list[str]:
    """Get list of 100% completed languages."""
    completed: list[str] = []
    locale_dir = Path('locale')

    for po_file in locale_dir.glob('*/LC_MESSAGES/messages.po'):
        lang = po_file.parent.parent.name
        try:
            po = polib.pofile(str(po_file))
            total = len([e for e in po if not e.obsolete])
            translated = len([e for e in po if e.translated() and not e.obsolete])

            if total > 0 and translated == total:
                completed.append(lang)
        except Exception:
            pass

    return completed


def determine_version_bump(current_version: str, manual_version: str | None = None) -> tuple[str, str]:
    """Determine the new version."""
    if manual_version:
        # Validate manual version
        try:
            _ = semver.Version.parse(manual_version)
            return manual_version, 'manual'
        except ValueError:
            raise ValueError(f"Invalid version format: {manual_version}")

    # Auto-patch for translation updates
    ver = semver.Version.parse(current_version)
    new_ver = ver.bump_patch()
    return str(new_ver), 'patch'


def set_github_output(key: str, value: str) -> None:
    """Set GitHub Actions output."""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            _ = f.write(f"{key}={value}\n")
    else:
        print(f"::set-output name={key}::{value}")


def main() -> int:
    """Main entry point for the script."""
    try:
        # Main logic
        current_version = get_current_version()
        manual_version = os.environ.get('MANUAL_VERSION', '').strip() or None

        # Check if this is the initial v1.0.0 release
        is_initial_release = current_version == '1.0.0' and not get_last_release_tag()

        if manual_version or is_initial_release:
            # Manual release or initial release
            new_version, version_type = determine_version_bump(
                current_version, manual_version or '1.0.0'
            )
            should_release = True
            completed_langs = get_completed_languages()
        else:
            # Check for translation changes
            has_changes, changed_files = check_translation_changes()

            if not has_changes:
                print("No translation changes detected since last release")
                should_release = False
                new_version = current_version
                version_type = 'none'
                completed_langs = []
            else:
                # Check if we have completed languages
                completed_langs = get_completed_languages()

                # Only release if we have completed languages or significant changes
                if completed_langs or len(changed_files) > 5:
                    new_version, version_type = determine_version_bump(current_version)
                    should_release = True
                else:
                    print("Translation changes detected but no completed languages")
                    should_release = False
                    new_version = current_version
                    version_type = 'none'

        # Output results
        print(f"Current version: {current_version}")
        print(f"New version: {new_version}")
        print(f"Version type: {version_type}")
        print(f"Should release: {should_release}")
        print(f"Completed languages: {', '.join(completed_langs)}")

        # Set GitHub Actions outputs
        set_github_output('should_release', 'true' if should_release else 'false')
        set_github_output('version_type', version_type)
        set_github_output('new_version', new_version)
        set_github_output('completed_languages', ','.join(completed_langs))

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
