#!/usr/bin/env python3
"""
Command-line interface for extracting translatable strings from source code.

This script scans Python source files for translatable strings and generates
.pot template files that can be used for internationalization.

Usage Examples:
    Extract strings from current directory:
        uv run python scripts/i18n/extract_strings.py

    Extract from specific directory:
        uv run python scripts/i18n/extract_strings.py --source-dir bot/

    Specify output file:
        uv run python scripts/i18n/extract_strings.py --output locale/messages.pot

    Exclude specific directories:
        uv run python scripts/i18n/extract_strings.py --exclude tests --exclude docs
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import NamedTuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import after path modification to avoid E402
from src.tgraph_bot.utils.i18n.i18n_utils import generate_pot_file, EXCLUDED_DIRS  # noqa: E402


class ExtractArgs(NamedTuple):
    """Type-safe container for command-line arguments."""

    source_dir: Path
    output: Path
    exclude: list[str]
    verbose: bool
    dry_run: bool
    ci_mode: bool
    check: bool


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_arguments() -> ExtractArgs:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments in a type-safe container
    """
    parser = argparse.ArgumentParser(
        description="Extract translatable strings from Python source code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Extract from current directory
  %(prog)s --source-dir bot/                  # Extract from bot/ directory
  %(prog)s --output locale/new_messages.pot   # Custom output file
  %(prog)s --exclude tests --exclude docs     # Exclude directories
  %(prog)s --verbose                          # Enable verbose logging
        """,
    )

    _ = parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("."),
        help="Source directory to scan for translatable strings (default: current directory)",
    )

    _ = parser.add_argument(
        "--output",
        type=Path,
        default=Path("locale/messages.pot"),
        help="Output .pot file path (default: locale/messages.pot)",
    )

    _ = parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory names to exclude from scanning (can be used multiple times)",
    )

    _ = parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )

    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually creating files",
    )

    _ = parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI/CD mode with optimized logging and error handling",
    )

    _ = parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: extract to temporary file and compare with existing .pot",
    )

    args = parser.parse_args()

    # Convert to type-safe container - argparse returns Any types
    return ExtractArgs(
        source_dir=args.source_dir,  # pyright: ignore[reportAny]
        output=args.output,  # pyright: ignore[reportAny]
        exclude=args.exclude or [],  # pyright: ignore[reportAny]
        verbose=args.verbose,  # pyright: ignore[reportAny]
        dry_run=args.dry_run,  # pyright: ignore[reportAny]
        ci_mode=args.ci_mode,  # pyright: ignore[reportAny]
        check=args.check,  # pyright: ignore[reportAny]
    )


def main() -> int:
    """
    Main entry point for the string extraction script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    
    # Setup logging with CI mode considerations
    if args.ci_mode:
        # In CI mode, use structured logging
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format="::%(levelname)s::%(message)s" if args.verbose else "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
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

        if not args.ci_mode:
            logger.info(f"Scanning source directory: {args.source_dir}")
            logger.info(f"Output file: {args.output}")
            logger.info(f"Excluded directories: {', '.join(sorted(exclude_dirs))}")

        # Handle check mode
        if args.check:
            return handle_check_mode(args, exclude_dirs, logger)

        if args.dry_run:
            logger.info("DRY RUN: Would extract strings and generate .pot file")
            if args.verbose:
                logger.info("Use --verbose to see what files would be processed")
            return 0

        # Generate the .pot file
        generate_pot_file(
            source_directory=args.source_dir,
            output_file=args.output,
            exclude_dirs=exclude_dirs,
        )

        if args.ci_mode:
            logger.info(f"✅ String extraction completed: {args.output}")
        else:
            logger.info("String extraction completed successfully!")
            logger.info(f"Generated .pot file: {args.output}")

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        if args.ci_mode:
            logger.error(f"❌ String extraction failed: {e}")
        else:
            logger.error(f"Error during string extraction: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


def handle_check_mode(
    args: ExtractArgs, exclude_dirs: set[str], logger: logging.Logger
) -> int:
    """
    Handle check mode: extract to temporary file and compare with existing.
    
    Args:
        args: Parsed command-line arguments
        exclude_dirs: Set of directories to exclude
        logger: Logger instance
        
    Returns:
        Exit code (0 if no changes needed, 1 if changes needed or error)
    """
    import tempfile
    import hashlib
    
    temp_path: Path | None = None
    
    try:
        # Create temporary file for comparison
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pot', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        # Generate .pot to temporary file
        generate_pot_file(
            source_directory=args.source_dir,
            output_file=temp_path,
            exclude_dirs=exclude_dirs,
        )
        
        # Compare with existing file if it exists
        if args.output.exists():
            # Read both files and compare
            with open(args.output, 'rb') as existing_file:
                existing_hash = hashlib.sha256(existing_file.read()).hexdigest()
            
            with open(temp_path, 'rb') as temp_file:
                new_hash = hashlib.sha256(temp_file.read()).hexdigest()
            
            if existing_hash == new_hash:
                if args.ci_mode:
                    logger.info("✅ Translation template is up to date")
                else:
                    logger.info("No changes needed - .pot file is up to date")
                
                # Clean up temp file
                temp_path.unlink()
                return 0
            else:
                if args.ci_mode:
                    logger.info("⚠️  Translation template needs update")
                else:
                    logger.info("Changes detected - .pot file needs update")
                
                # Copy temp file to actual output location
                import shutil
                _ = shutil.move(str(temp_path), str(args.output))
                return 0
        else:
            # No existing file, move temp file to output location
            import shutil
            _ = shutil.move(str(temp_path), str(args.output))
            
            if args.ci_mode:
                logger.info("📝 Created new translation template")
            else:
                logger.info("Created new .pot file")
            return 0
            
    except Exception as e:
        # Clean up temp file if it exists
        try:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass
        
        if args.ci_mode:
            logger.error(f"❌ Check mode failed: {e}")
        else:
            logger.error(f"Error in check mode: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
