#!/usr/bin/env python3
"""
Command-line interface for extracting translatable strings from source code.

This script scans Python source files for translatable strings and generates
.pot template files that can be used for internationalization.

Usage Examples:
    Extract strings from current directory:
        python scripts/extract_strings.py

    Extract from specific directory:
        python scripts/extract_strings.py --source-dir bot/

    Specify output file:
        python scripts/extract_strings.py --output locale/messages.pot

    Exclude specific directories:
        python scripts/extract_strings.py --exclude tests --exclude docs
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

from utils.i18n_utils import generate_pot_file, EXCLUDED_DIRS


class ExtractArgs(NamedTuple):
    """Type-safe container for command-line arguments."""
    source_dir: Path
    output: Path
    exclude: list[str]
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


def parse_arguments() -> ExtractArgs:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments in a type-safe container
    """
    parser = argparse.ArgumentParser(
        description='Extract translatable strings from Python source code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Extract from current directory
  %(prog)s --source-dir bot/                  # Extract from bot/ directory
  %(prog)s --output locale/new_messages.pot   # Custom output file
  %(prog)s --exclude tests --exclude docs     # Exclude directories
  %(prog)s --verbose                          # Enable verbose logging
        """
    )

    _ = parser.add_argument(
        '--source-dir',
        type=Path,
        default=Path('.'),
        help='Source directory to scan for translatable strings (default: current directory)'
    )

    _ = parser.add_argument(
        '--output',
        type=Path,
        default=Path('locale/messages.pot'),
        help='Output .pot file path (default: locale/messages.pot)'
    )

    _ = parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Directory names to exclude from scanning (can be used multiple times)'
    )

    _ = parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    _ = parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually creating files'
    )

    args = parser.parse_args()

    # Convert to type-safe container - argparse returns Any types
    return ExtractArgs(
        source_dir=args.source_dir,  # pyright: ignore[reportAny]
        output=args.output,  # pyright: ignore[reportAny]
        exclude=args.exclude or [],  # pyright: ignore[reportAny]
        verbose=args.verbose,  # pyright: ignore[reportAny]
        dry_run=args.dry_run  # pyright: ignore[reportAny]
    )


def main() -> int:
    """
    Main entry point for the string extraction script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    try:
        # Validate source directory
        if not args.source_dir.exists():
            logger.error(f"Source directory does not exist: {args.source_dir}")
            return 1

        if not args.source_dir.is_dir():
            logger.error(f"Source path is not a directory: {args.source_dir}")
            return 1

        # Prepare exclude directories
        exclude_dirs: set[str] = EXCLUDED_DIRS.copy()
        exclude_dirs.update(args.exclude)

        logger.info(f"Scanning source directory: {args.source_dir}")
        logger.info(f"Output file: {args.output}")
        logger.info(f"Excluded directories: {', '.join(sorted(exclude_dirs))}")

        if args.dry_run:
            logger.info("DRY RUN: Would extract strings and generate .pot file")
            logger.info("Use --verbose to see what files would be processed")
            return 0

        # Generate the .pot file
        generate_pot_file(
            source_directory=args.source_dir,
            output_file=args.output,
            exclude_dirs=exclude_dirs
        )

        logger.info("String extraction completed successfully!")
        logger.info(f"Generated .pot file: {args.output}")

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error during string extraction: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
