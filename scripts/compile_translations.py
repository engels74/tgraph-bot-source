#!/usr/bin/env python3
"""
Command-line interface for compiling translation files from .po to .mo format.

This script compiles .po translation files to .mo binary format for runtime use.
It includes version checking to only recompile modified files and supports
batch compilation of all language files.

Usage Examples:
    Compile all .po files to .mo:
        python scripts/compile_translations.py

    Compile specific language:
        python scripts/compile_translations.py --language en

    Force recompilation (ignore modification times):
        python scripts/compile_translations.py --force

    Check which files need compilation:
        python scripts/compile_translations.py --check-only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from utils.i18n_utils import compile_po_to_mo


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the script.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def find_po_files(locale_dir: Path, language: str | None = None) -> list[Path]:
    """
    Find all .po files in the locale directory.

    Args:
        locale_dir: Path to the locale directory
        language: Optional language code to filter by

    Returns:
        List of .po file paths
    """
    po_files: list[Path] = []

    if language:
        # Look for specific language
        lang_dir = locale_dir / language / "LC_MESSAGES"
        if lang_dir.exists():
            po_files.extend(list(lang_dir.glob("*.po")))
    else:
        # Find all .po files in all language directories
        for lang_dir in locale_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith('.'):
                lc_messages = lang_dir / "LC_MESSAGES"
                if lc_messages.exists():
                    po_files.extend(list(lc_messages.glob("*.po")))

    return sorted(po_files)


def needs_compilation(po_file: Path, mo_file: Path) -> bool:
    """
    Check if a .po file needs to be compiled to .mo format.

    Args:
        po_file: Path to the .po file
        mo_file: Path to the .mo file

    Returns:
        True if compilation is needed, False otherwise
    """
    if not mo_file.exists():
        return True

    # Check modification times
    po_mtime = po_file.stat().st_mtime
    mo_mtime = mo_file.stat().st_mtime

    return po_mtime > mo_mtime


def compile_file(po_file: Path, force: bool = False, dry_run: bool = False) -> bool:
    """
    Compile a single .po file to .mo format.

    Args:
        po_file: Path to the .po file
        force: Force compilation even if .mo is newer
        dry_run: Show what would be done without actually compiling

    Returns:
        True if compilation was performed or would be performed, False otherwise
    """
    mo_file = po_file.with_suffix('.mo')

    if not force and not needs_compilation(po_file, mo_file):
        logging.debug(f"Skipping {po_file} (up to date)")
        return False

    if dry_run:
        logging.info(f"DRY RUN: Would compile {po_file} -> {mo_file}")
        return True

    try:
        compile_po_to_mo(po_file, mo_file)
        logging.info(f"Compiled {po_file} -> {mo_file}")
        return True
    except Exception as e:
        logging.error(f"Failed to compile {po_file}: {e}")
        raise


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Compile translation files from .po to .mo format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Compile all .po files
  %(prog)s --language en            # Compile only English
  %(prog)s --force                  # Force recompilation
  %(prog)s --check-only             # Check which files need compilation
  %(prog)s --verbose                # Enable verbose logging
        """
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
        help='Compile only the specified language (e.g., "en", "da")'
    )

    _ = parser.add_argument(
        '--force',
        action='store_true',
        help='Force compilation even if .mo files are newer than .po files'
    )

    _ = parser.add_argument(
        '--check-only',
        action='store_true',
        help='Check which files need compilation without actually compiling'
    )

    _ = parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    _ = parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually compiling files'
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the compilation script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Validate locale directory
        if not args.locale_dir.exists():
            logger.error(f"Locale directory does not exist: {args.locale_dir}")
            return 1

        # Find .po files
        po_files = find_po_files(args.locale_dir, args.language)

        if not po_files:
            if args.language:
                logger.warning(f"No .po files found for language: {args.language}")
            else:
                logger.warning(f"No .po files found in: {args.locale_dir}")
            return 0

        logger.info(f"Found {len(po_files)} .po file(s)")

        # Check which files need compilation
        files_to_compile = []
        for po_file in po_files:
            mo_file = po_file.with_suffix('.mo')
            if args.force or needs_compilation(po_file, mo_file):
                files_to_compile.append(po_file)

        if not files_to_compile:
            logger.info("All .mo files are up to date")
            return 0

        logger.info(f"{len(files_to_compile)} file(s) need compilation:")
        for po_file in files_to_compile:
            logger.info(f"  {po_file}")

        if args.check_only:
            logger.info("CHECK ONLY: Use --force or modify .po files to trigger compilation")
            return 0

        if args.dry_run:
            logger.info("DRY RUN: Would compile the above files")
            return 0

        # Compile files
        compiled_count = 0
        for po_file in files_to_compile:
            if compile_file(po_file, args.force, args.dry_run):
                compiled_count += 1

        logger.info(f"Successfully compiled {compiled_count} file(s)")
        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error during compilation: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
