#!/usr/bin/env python3
"""
Weblate API Fetcher for GitHub Actions.

This script fetches translation updates from Weblate and saves them to the
local repository, tracking changes and completion status.
"""

import os
import sys
from pathlib import Path

import httpx


def set_github_output(key: str, value: str) -> None:
    """Set GitHub Actions output."""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            _ = f.write(f"{key}={value}\n")
    else:
        print(f"::set-output name={key}::{value}")


def fetch_component_info(api_url: str, headers: dict[str, str]) -> dict[str, str]:
    """Fetch component information from Weblate API."""
    component_url = f"{api_url}/components/tgraph-bot/main/"
    try:
        resp = httpx.get(component_url, headers=headers)
        _ = resp.raise_for_status()
        return resp.json()  # pyright: ignore[reportAny]
    except Exception as e:
        print(f"Error fetching component: {e}", file=sys.stderr)
        raise


def fetch_translations(api_url: str, headers: dict[str, str]) -> tuple[bool, list[str], list[str]]:
    """
    Fetch translations from Weblate and save them locally.
    
    Returns:
        Tuple of (changes_made, new_languages, completed_languages)
    """
    component = fetch_component_info(api_url, headers)
    
    # Get translations
    translations_url = component['translations_url']
    resp = httpx.get(translations_url, headers=headers)
    _ = resp.raise_for_status()
    translations = resp.json()  # pyright: ignore[reportAny]

    changes_made = False
    new_languages: list[str] = []
    completed_languages: list[str] = []

    for translation in translations:  # pyright: ignore[reportAny]
        lang_code = translation['language_code']  # pyright: ignore[reportAny]
        file_url = translation['file_url']  # pyright: ignore[reportAny]
        translated_percent = translation['translated_percent']  # pyright: ignore[reportAny]

        print(f"Processing {lang_code}: {translated_percent}% translated")

        # Download translation file
        resp = httpx.get(file_url, headers=headers)  # pyright: ignore[reportAny]
        _ = resp.raise_for_status()
        po_content = resp.text

        # Save translation file
        lang_dir = Path(f"locale/{lang_code}/LC_MESSAGES")
        lang_dir.mkdir(parents=True, exist_ok=True)
        po_file = lang_dir / "messages.po"

        # Check if this is a new language
        if not po_file.exists():
            new_languages.append(lang_code)  # pyright: ignore[reportAny]
            changes_made = True
        else:
            # Check if content changed
            existing_content = po_file.read_text(encoding='utf-8')
            if existing_content != po_content:
                changes_made = True

        _ = po_file.write_text(po_content, encoding='utf-8')

        # Track completed translations
        if translated_percent == 100.0:
            completed_languages.append(lang_code)  # pyright: ignore[reportAny]

    return changes_made, new_languages, completed_languages


def main() -> int:
    """Main entry point for the script."""
    try:
        # Get API credentials from environment
        api_token = os.environ.get('WEBLATE_API_TOKEN')
        api_url = os.environ.get('WEBLATE_API_URL')
        
        if not api_token or not api_url:
            print("Error: WEBLATE_API_TOKEN and WEBLATE_API_URL must be set", file=sys.stderr)
            return 1
        
        api_url = api_url.rstrip('/')
        headers = {'Authorization': f'Token {api_token}'}

        # Fetch translations
        changes_made, new_languages, completed_languages = fetch_translations(api_url, headers)

        # Set GitHub Actions outputs
        set_github_output('changes_made', 'true' if changes_made else 'false')
        set_github_output('new_languages', ','.join(new_languages))
        set_github_output('completed_languages', ','.join(completed_languages))

        # Print summary
        if changes_made:
            print("✅ Changes detected!")
            if new_languages:
                print(f"  New languages: {', '.join(new_languages)}")
            if completed_languages:
                print(f"  Completed languages: {', '.join(completed_languages)}")
        else:
            print("ℹ️  No translation changes detected")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
