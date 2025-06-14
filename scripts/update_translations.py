#!/usr/bin/env python3
"""
Command-line interface for updating translation files from .pot templates.

This script updates existing .po translation files with new strings from
.pot template files while preserving existing translations.

Usage Examples:
    Update all .po files from messages.pot:
        python scripts/update_translations.py

    Update specific language:
        python scripts/update_translations.py --language en

    Use custom .pot file:
        python scripts/update_translations.py --pot-file locale/new_messages.pot

    Don't preserve existing translations:
        python scripts/update_translations.py --no-preserve
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import NamedTuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.i18n_utils import update_po_file, compile_po_to_mo


class UpdateArgs(NamedTuple):
    """Type-safe container for command-line arguments."""
    pot_file: Path
    locale_dir: Path
    language: str | None
    no_preserve: bool
    compile: bool
    verbose: bool
    dry_run: bool


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def find_po_files(locale_dir: Path, language: str | None = None) -> list[Path]:
    """
    Find .po files in the locale directory.

    Args:
        locale_dir: Path to the locale directory
        language: Specific language to find (None for all languages)

    Returns:
        List of .po file paths
    """
    po_files: list[Path] = []

    if language:
        # Look for specific language
        po_file = locale_dir / language / "LC_MESSAGES" / "messages.po"
        if po_file.exists():
            po_files.append(po_file)
    else:
        # Find all .po files
        for po_file in locale_dir.rglob("*.po"):
            if "LC_MESSAGES" in str(po_file):
                po_files.append(po_file)

    return po_files


def parse_arguments() -> UpdateArgs:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments in a type-safe container
    """
    parser = argparse.ArgumentParser(
        description='Update translation files from .pot templates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Update all .po files
  %(prog)s --language en                      # Update only English
  %(prog)s --pot-file locale/new_messages.pot # Use custom .pot file
  %(prog)s --no-preserve                      # Don't preserve translations
  %(prog)s --compile                          # Also compile to .mo files
  %(prog)s --verbose                          # Enable verbose logging
        """
    )

    _ = parser.add_argument(
        '--pot-file',
        type=Path,
        default=Path('locale/messages.pot'),
        help='Path to the .pot template file (default: locale/messages.pot)'
    )

    _ = parser.add_argument(
        '--locale-dir',
        type=Path,
        default=Path('locale'),
        help='Path to the locale directory (default: locale)'
    )

    _ = parser.add_argument(
        '--language',
        type=str,
        help='Update only the specified language (e.g., "en", "da")'
    )

    _ = parser.add_argument(
        '--no-preserve',
        action='store_true',
        help='Do not preserve existing translations (start fresh)'
    )

    _ = parser.add_argument(
        '--compile',
        action='store_true',
        help='Also compile .po files to .mo binary format'
    )

    _ = parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    _ = parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually updating files'
    )

    args = parser.parse_args()

    # Convert to type-safe container - argparse returns Any types
    # Add explicit type annotations to help type checker
    pot_file: Path = args.pot_file
    locale_dir: Path = args.locale_dir
    language: str | None = args.language
    no_preserve: bool = args.no_preserve
    compile_flag: bool = args.compile
    verbose: bool = args.verbose
    dry_run: bool = args.dry_run
    
    return UpdateArgs(
        pot_file=pot_file,
        locale_dir=locale_dir,
        language=language,
        no_preserve=no_preserve,
        compile=compile_flag,
        verbose=verbose,
        dry_run=dry_run
    )


def main() -> int:
    """
    Main entry point for the translation update script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Validate .pot file
        if not args.pot_file.exists():
            logger.error(f"POT template file does not exist: {args.pot_file}")
            return 1

        # Validate locale directory
        if not args.locale_dir.exists():
            logger.error(f"Locale directory does not exist: {args.locale_dir}")
            return 1

        # Find .po files to update
        po_files = find_po_files(args.locale_dir, args.language)

        if not po_files:
            if args.language:
                logger.error(f"No .po file found for language: {args.language}")
            else:
                logger.error(f"No .po files found in: {args.locale_dir}")
            return 1

        logger.info(f"Found {len(po_files)} .po file(s) to update")
        for po_file in po_files:
            logger.info(f"  - {po_file}")

        if args.dry_run:
            logger.info("DRY RUN: Would update the above .po files")
            if args.compile:
                logger.info("DRY RUN: Would also compile .po files to .mo format")
            return 0

        # Update each .po file
        preserve_translations = not args.no_preserve
        updated_files: list[Path] = []

        for po_file in po_files:
            try:
                logger.info(f"Updating {po_file}...")
                update_po_file(
                    pot_file=args.pot_file,
                    po_file=po_file,
                    preserve_translations=preserve_translations
                )
                updated_files.append(po_file)
                logger.info(f"Successfully updated {po_file}")

            except Exception as e:
                logger.error(f"Failed to update {po_file}: {e}")
                if args.verbose:
                    logger.exception("Full traceback:")

        # Compile to .mo files if requested
        if args.compile and updated_files:
            logger.info("Compiling .po files to .mo format...")
            for po_file in updated_files:
                try:
                    compile_po_to_mo(po_file)
                    logger.info(f"Compiled {po_file} to .mo format")
                except Exception as e:
                    logger.warning(f"Failed to compile {po_file}: {e}")

        logger.info(f"Translation update completed! Updated {len(updated_files)} file(s)")

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error during translation update: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
