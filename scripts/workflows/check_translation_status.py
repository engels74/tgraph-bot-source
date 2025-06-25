#!/usr/bin/env python3
"""
Translation Status Checker for GitHub Actions.

This script checks the completion status of translation files and generates
a report for GitHub Actions workflows.
"""

import json
import sys
from pathlib import Path

import polib


def check_translation_status(locale_dir: Path | None = None) -> tuple[list[str], list[str]]:
    """
    Check the translation status for all languages.

    Args:
        locale_dir: Path to the locale directory containing translation files

    Returns:
        Tuple of (completed_languages, all_languages)
    """
    if locale_dir is None:
        locale_dir = Path('locale')

    completed_langs: list[str] = []
    all_langs: list[str] = []

    for po_file in locale_dir.glob('*/LC_MESSAGES/messages.po'):
        lang = po_file.parent.parent.name
        all_langs.append(lang)
        
        try:
            po = polib.pofile(str(po_file))
            total = len([e for e in po if not e.obsolete])
            translated = len([e for e in po if e.translated() and not e.obsolete])
            percentage = (translated / total * 100) if total > 0 else 0
            
            status_icon = "🟢" if percentage == 100 else "🟡" if percentage >= 80 else "🔴"
            print(f"| {lang} | {percentage:.1f}% | {status_icon} |")
            
            if percentage == 100:
                completed_langs.append(lang)
        except Exception as e:
            print(f"| {lang} | Error | ❌ |")
            print(f"Error processing {lang}: {e}", file=sys.stderr)
    
    return completed_langs, all_langs


def save_status_json(completed_langs: list[str], all_langs: list[str],
                    output_file: Path | None = None) -> None:
    """
    Save translation status to JSON file for GitHub Actions.

    Args:
        completed_langs: List of languages with 100% completion
        all_langs: List of all available languages
        output_file: Path to output JSON file
    """
    if output_file is None:
        output_file = Path('translation_status.json')

    status_data = {
        'completed_languages': completed_langs,
        'all_languages': all_langs
    }

    with open(output_file, 'w') as f:
        json.dump(status_data, f, indent=2)


def main() -> int:
    """Main entry point for the script."""
    try:
        locale_dir = Path('locale')
        if not locale_dir.exists():
            print("Error: locale directory not found", file=sys.stderr)
            return 1
        
        completed_langs, all_langs = check_translation_status(locale_dir)
        save_status_json(completed_langs, all_langs)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
