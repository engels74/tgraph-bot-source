"""
Translation compilation utilities for batch processing and automation.

This module provides high-level functions for compiling translation files
with support for version checking, batch processing, and integration with
build systems.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict, override

from ...utils.i18n.i18n_utils import compile_po_to_mo

logger = logging.getLogger(__name__)


class CompilationStatus(TypedDict):
    """Type definition for compilation status dictionary."""

    total_files: int
    needs_compilation: list[str]
    up_to_date: list[str]
    missing_mo: list[str]
    errors: list[dict[str, str]]


class ValidationResult(TypedDict):
    """Type definition for validation result dictionary."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    languages: list[str]
    po_files: int
    mo_files: int


class CompilationResult:
    """Result of a compilation operation."""

    def __init__(self) -> None:
        self.compiled_files: list[Path] = []
        self.skipped_files: list[Path] = []
        self.failed_files: list[tuple[Path, Exception]] = []
        self.total_files: int = 0

    @property
    def success_count(self) -> int:
        """Number of successfully compiled files."""
        return len(self.compiled_files)

    @property
    def skip_count(self) -> int:
        """Number of skipped files."""
        return len(self.skipped_files)

    @property
    def failure_count(self) -> int:
        """Number of failed files."""
        return len(self.failed_files)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_files == 0:
            return 100.0
        return (self.success_count / self.total_files) * 100.0

    @override
    def __str__(self) -> str:
        """String representation of compilation results."""
        return (
            f"Compilation Results: "
            f"{self.success_count} compiled, "
            f"{self.skip_count} skipped, "
            f"{self.failure_count} failed "
            f"({self.success_rate:.1f}% success rate)"
        )


def find_po_files(
    locale_dir: Path, language: str | None = None, recursive: bool = True
) -> list[Path]:
    """
    Find all .po files in the locale directory.

    Args:
        locale_dir: Path to the locale directory
        language: Optional language code to filter by
        recursive: Whether to search recursively

    Returns:
        List of .po file paths sorted alphabetically
    """
    po_files: list[Path] = []

    if not locale_dir.exists():
        logger.warning(f"Locale directory does not exist: {locale_dir}")
        return po_files

    if language:
        # Look for specific language
        lang_dir = locale_dir / language / "LC_MESSAGES"
        if lang_dir.exists():
            po_files.extend(list(lang_dir.glob("*.po")))
    else:
        # Find all .po files in all language directories
        if recursive:
            po_files.extend(list(locale_dir.rglob("*.po")))
        else:
            for lang_dir in locale_dir.iterdir():
                if lang_dir.is_dir() and not lang_dir.name.startswith("."):
                    lc_messages = lang_dir / "LC_MESSAGES"
                    if lc_messages.exists():
                        po_files.extend(list(lc_messages.glob("*.po")))

    return sorted(po_files)


def needs_compilation(po_file: Path, mo_file: Path | None = None) -> bool:
    """
    Check if a .po file needs to be compiled to .mo format.

    Args:
        po_file: Path to the .po file
        mo_file: Path to the .mo file (defaults to same location as .po)

    Returns:
        True if compilation is needed, False otherwise
    """
    if mo_file is None:
        mo_file = po_file.with_suffix(".mo")

    if not mo_file.exists():
        return True

    # Check modification times
    try:
        po_mtime = po_file.stat().st_mtime
        mo_mtime = mo_file.stat().st_mtime
        return po_mtime > mo_mtime
    except OSError as e:
        logger.warning(f"Error checking file times for {po_file}: {e}")
        return True


def compile_translation_file(
    po_file: Path, mo_file: Path | None = None, force: bool = False
) -> bool:
    """
    Compile a single .po file to .mo format.

    Args:
        po_file: Path to the .po file
        mo_file: Path to the .mo file (defaults to same location as .po)
        force: Force compilation even if .mo is newer

    Returns:
        True if compilation was performed, False if skipped

    Raises:
        Exception: If compilation fails
    """
    if mo_file is None:
        mo_file = po_file.with_suffix(".mo")

    if not force and not needs_compilation(po_file, mo_file):
        logger.debug(f"Skipping {po_file} (up to date)")
        return False

    try:
        compile_po_to_mo(po_file, mo_file)
        logger.info(f"Compiled {po_file} -> {mo_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to compile {po_file}: {e}")
        raise


def compile_all_translations(
    locale_dir: Path,
    language: str | None = None,
    force: bool = False,
    fail_fast: bool = False,
) -> CompilationResult:
    """
    Compile all .po files in the locale directory to .mo format.

    Args:
        locale_dir: Path to the locale directory
        language: Optional language code to filter by
        force: Force compilation even if .mo files are newer
        fail_fast: Stop on first compilation error

    Returns:
        CompilationResult with details of the operation
    """
    result = CompilationResult()

    # Find all .po files
    po_files = find_po_files(locale_dir, language)
    result.total_files = len(po_files)

    if not po_files:
        if language:
            logger.warning(f"No .po files found for language: {language}")
        else:
            logger.warning(f"No .po files found in: {locale_dir}")
        return result

    logger.info(f"Found {len(po_files)} .po file(s) to process")

    # Compile each file
    for po_file in po_files:
        try:
            if compile_translation_file(po_file, force=force):
                result.compiled_files.append(po_file)
            else:
                result.skipped_files.append(po_file)
        except Exception as e:
            result.failed_files.append((po_file, e))
            if fail_fast:
                logger.error(f"Stopping compilation due to error in {po_file}")
                break

    # Log summary
    logger.info(str(result))

    if result.failed_files:
        logger.error("Failed files:")
        for po_file, error in result.failed_files:
            logger.error(f"  {po_file}: {error}")

    return result


def get_compilation_status(
    locale_dir: Path, language: str | None = None
) -> CompilationStatus:
    """
    Get the compilation status of all .po files.

    Args:
        locale_dir: Path to the locale directory
        language: Optional language code to filter by

    Returns:
        Dictionary with compilation status information
    """
    po_files = find_po_files(locale_dir, language)

    needs_compilation_list: list[str] = []
    up_to_date_list: list[str] = []
    missing_mo_list: list[str] = []
    errors_list: list[dict[str, str]] = []

    for po_file in po_files:
        mo_file = po_file.with_suffix(".mo")

        try:
            if not mo_file.exists():
                missing_mo_list.append(str(po_file))
            elif needs_compilation(po_file, mo_file):
                needs_compilation_list.append(str(po_file))
            else:
                up_to_date_list.append(str(po_file))
        except Exception as e:
            errors_list.append({"file": str(po_file), "error": str(e)})

    return CompilationStatus(
        total_files=len(po_files),
        needs_compilation=needs_compilation_list,
        up_to_date=up_to_date_list,
        missing_mo=missing_mo_list,
        errors=errors_list,
    )


def validate_locale_structure(locale_dir: Path) -> ValidationResult:
    """
    Validate the locale directory structure for compilation.

    Args:
        locale_dir: Path to the locale directory

    Returns:
        Dictionary with validation results
    """
    errors: list[str] = []
    warnings: list[str] = []
    languages: list[str] = []
    po_files_count = 0
    mo_files_count = 0

    if not locale_dir.exists():
        errors.append(f"Locale directory does not exist: {locale_dir}")
        return ValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            languages=languages,
            po_files=po_files_count,
            mo_files=mo_files_count,
        )

    # Check for language directories
    for item in locale_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            lang_code = item.name
            lc_messages = item / "LC_MESSAGES"

            if not lc_messages.exists():
                warnings.append(f"Language {lang_code} missing LC_MESSAGES directory")
                continue

            languages.append(lang_code)

            # Count .po and .mo files
            po_files = list(lc_messages.glob("*.po"))
            mo_files = list(lc_messages.glob("*.mo"))

            po_files_count += len(po_files)
            mo_files_count += len(mo_files)

            if not po_files:
                warnings.append(f"Language {lang_code} has no .po files")

    if not languages:
        errors.append("No valid language directories found")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        languages=languages,
        po_files=po_files_count,
        mo_files=mo_files_count,
    )
