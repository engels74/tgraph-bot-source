#!/usr/bin/env python3
"""
CI/CD helper utilities for internationalization workflows.

This module provides utilities for analyzing changes, validating translations,
and generating reports for CI/CD pipelines.

Usage Examples:
    Analyze PR changes:
        python scripts/i18n/ci_helpers.py analyze-pr-changes --base-ref main --head-ref feature-branch

    Validate translation files:
        python scripts/i18n/ci_helpers.py validate-translations --locale-dir locale

    Generate change report:
        python scripts/i18n/ci_helpers.py generate-report --output-file report.md
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ChangeAnalysis(NamedTuple):
    """Result of analyzing changes in a repository."""

    python_files_changed: list[str]
    translation_files_changed: list[str]
    has_translatable_changes: bool
    summary: str


class ValidationResult(NamedTuple):
    """Result of validating translation files."""

    valid: bool
    issues: list[str]
    summary: str


def setup_logging(verbose: bool = False, ci_mode: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose logging
        ci_mode: Enable CI-friendly logging format
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    if ci_mode:
        log_format = "::%(levelname)s::%(message)s" if verbose else "%(message)s"
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_git_command(command: list[str]) -> tuple[str, int]:
    """
    Run a git command and return output and exit code.

    Args:
        command: Git command as list of strings

    Returns:
        Tuple of (output, exit_code)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        logging.error(f"Failed to run git command {' '.join(command)}: {e}")
        return "", 1


def analyze_pr_changes(base_ref: str, head_ref: str) -> ChangeAnalysis:
    """
    Analyze changes in a pull request.

    Args:
        base_ref: Base branch reference
        head_ref: Head branch reference

    Returns:
        Analysis result
    """
    logger = logging.getLogger(__name__)
    
    # Get changed files
    changed_files_cmd = ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"]
    output, exit_code = run_git_command(changed_files_cmd)
    
    if exit_code != 0:
        logger.error(f"Failed to get changed files: {output}")
        return ChangeAnalysis([], [], False, "Error analyzing changes")
    
    changed_files = output.split('\n') if output else []
    
    # Categorize files
    python_files = [f for f in changed_files if f.endswith('.py')]
    translation_files = [f for f in changed_files if 'locale' in f and (f.endswith('.po') or f.endswith('.pot'))]
    
    # Check if Python files contain translatable string changes
    has_translatable_changes = False
    if python_files:
        # Look for added/modified lines with translation functions
        diff_cmd = ["git", "diff", f"{base_ref}...{head_ref}", "--"] + python_files
        diff_output, diff_exit_code = run_git_command(diff_cmd)
        
        if diff_exit_code == 0:
            # Check for lines with translation function calls
            translation_patterns = ['_(', 'translate(', 't(', 'ngettext(', 'nt(']
            for line in diff_output.split('\n'):
                if line.startswith('+') and any(pattern in line for pattern in translation_patterns):
                    has_translatable_changes = True
                    break
    
    # Generate summary
    summary_parts: list[str] = []
    if python_files:
        summary_parts.append(f"{len(python_files)} Python file(s) changed")
    if translation_files:
        summary_parts.append(f"{len(translation_files)} translation file(s) changed")
    if has_translatable_changes:
        summary_parts.append("translatable strings affected")
    
    summary = ", ".join(summary_parts) if summary_parts else "no relevant changes"
    
    logger.info(f"PR analysis: {summary}")
    
    return ChangeAnalysis(
        python_files_changed=python_files,
        translation_files_changed=translation_files,
        has_translatable_changes=has_translatable_changes,
        summary=summary,
    )


def validate_po_file(po_file: Path) -> tuple[bool, list[str]]:
    """
    Validate a single .po file.

    Args:
        po_file: Path to .po file to validate

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues: list[str] = []
    
    if not po_file.exists():
        return False, [f"File does not exist: {po_file}"]
    
    try:
        with open(po_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Basic validation checks
        if not content.strip():
            issues.append("File is empty")
        
        # Check for valid header
        if 'msgid ""' not in content:
            issues.append("Missing header entry")
        
        # Check for unmatched quotes
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith(('msgid', 'msgstr')) and line.count('"') % 2 != 0:
                issues.append(f"Line {i}: Unmatched quotes in {line[:50]}...")
        
        # Check for empty msgstr in non-header entries
        import re
        msgid_pattern = re.compile(r'msgid\s+"([^"]*)"')
        msgstr_pattern = re.compile(r'msgstr\s+""(?!\s*\n\s*")')
        
        msgids: list[str] = msgid_pattern.findall(content)
        empty_msgstrs: list[str] = msgstr_pattern.findall(content)
        
        # Count non-header empty translations
        non_header_empty = sum(1 for msgid in msgids if msgid and msgid in empty_msgstrs)
        if non_header_empty > 0:
            issues.append(f"{non_header_empty} untranslated string(s)")
    
    except UnicodeDecodeError:
        issues.append("File encoding is not UTF-8")
    except Exception as e:
        issues.append(f"Error reading file: {e}")
    
    return len(issues) == 0, issues


def validate_translations(locale_dir: Path) -> ValidationResult:
    """
    Validate all translation files in the locale directory.

    Args:
        locale_dir: Path to locale directory

    Returns:
        Validation result
    """
    logger = logging.getLogger(__name__)
    
    if not locale_dir.exists():
        return ValidationResult(
            valid=False,
            issues=[f"Locale directory does not exist: {locale_dir}"],
            summary="Locale directory not found",
        )
    
    # Find all .po files
    po_files = list(locale_dir.rglob("*.po"))
    
    if not po_files:
        return ValidationResult(
            valid=True,
            issues=[],
            summary="No translation files found (this is okay for new projects)",
        )
    
    all_issues: list[str] = []
    total_files = len(po_files)
    valid_files = 0
    
    for po_file in po_files:
        is_valid, issues = validate_po_file(po_file)
        if is_valid:
            valid_files += 1
        else:
            for issue in issues:
                all_issues.append(f"{po_file.relative_to(locale_dir)}: {issue}")
    
    overall_valid = len(all_issues) == 0
    summary = f"{valid_files}/{total_files} translation files are valid"
    
    if overall_valid:
        logger.info(f"✅ {summary}")
    else:
        logger.warning(f"⚠️  {summary}, {len(all_issues)} issue(s) found")
    
    return ValidationResult(
        valid=overall_valid,
        issues=all_issues,
        summary=summary,
    )


def output_github_actions_format(data: dict[str, str]) -> None:
    """
    Output data in GitHub Actions format.

    Args:
        data: Dictionary of key-value pairs to output
    """
    for key, value in data.items():
        # Escape value for GitHub Actions
        escaped_value = value.replace('\n', '%0A').replace('\r', '%0D')
        print(f"{key}={escaped_value}")


def cmd_analyze_pr_changes(args: argparse.Namespace) -> int:
    """
    Command handler for analyzing PR changes.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    verbose: bool = args.verbose  # pyright: ignore[reportAny]
    ci_mode: bool = args.ci_mode  # pyright: ignore[reportAny]
    base_ref: str = args.base_ref  # pyright: ignore[reportAny]
    head_ref: str = args.head_ref  # pyright: ignore[reportAny]
    output_format: str = args.output_format  # pyright: ignore[reportAny]
    
    setup_logging(verbose, ci_mode)
    
    analysis = analyze_pr_changes(base_ref, head_ref)
    
    if output_format == "github-actions":
        output_github_actions_format({
            "python_files_changed": str(len(analysis.python_files_changed)),
            "translation_files_changed": str(len(analysis.translation_files_changed)),
            "has_translatable_changes": str(analysis.has_translatable_changes).lower(),
            "summary": analysis.summary,
        })
    else:
        print(f"Python files changed: {len(analysis.python_files_changed)}")
        print(f"Translation files changed: {len(analysis.translation_files_changed)}")
        print(f"Has translatable changes: {analysis.has_translatable_changes}")
        print(f"Summary: {analysis.summary}")
    
    return 0


def cmd_validate_translations(args: argparse.Namespace) -> int:
    """
    Command handler for validating translations.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    verbose: bool = args.verbose  # pyright: ignore[reportAny]
    ci_mode: bool = args.ci_mode  # pyright: ignore[reportAny]
    locale_dir_str: str = args.locale_dir  # pyright: ignore[reportAny]
    output_format: str = args.output_format  # pyright: ignore[reportAny]
    
    setup_logging(verbose, ci_mode)
    
    locale_dir = Path(locale_dir_str)
    result = validate_translations(locale_dir)
    
    if output_format == "github-actions":
        output_github_actions_format({
            "valid": str(result.valid).lower(),
            "issues_count": str(len(result.issues)),
            "summary": result.summary,
        })
    else:
        print(f"Valid: {result.valid}")
        print(f"Issues: {len(result.issues)}")
        print(f"Summary: {result.summary}")
        
        if result.issues:
            print("\nIssues found:")
            for issue in result.issues:
                print(f"  - {issue}")
    
    return 0 if result.valid else 1


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="CI/CD helper utilities for i18n workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze PR changes command
    analyze_parser = subparsers.add_parser(
        "analyze-pr-changes",
        help="Analyze changes in a pull request",
    )
    _ = analyze_parser.add_argument(
        "--base-ref",
        required=True,
        help="Base branch reference (e.g., main)",
    )
    _ = analyze_parser.add_argument(
        "--head-ref",
        required=True,
        help="Head branch reference (e.g., feature-branch)",
    )
    _ = analyze_parser.add_argument(
        "--output-format",
        choices=["text", "github-actions"],
        default="text",
        help="Output format",
    )
    _ = analyze_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    _ = analyze_parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI-friendly logging",
    )
    
    # Validate translations command
    validate_parser = subparsers.add_parser(
        "validate-translations",
        help="Validate translation files",
    )
    _ = validate_parser.add_argument(
        "--locale-dir",
        default="locale",
        help="Path to locale directory (default: locale)",
    )
    _ = validate_parser.add_argument(
        "--output-format",
        choices=["text", "github-actions"],
        default="text",
        help="Output format",
    )
    _ = validate_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    _ = validate_parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI-friendly logging",
    )
    
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for CI helpers.

    Returns:
        Exit code
    """
    args = parse_arguments()
    
    command: str | None = args.command  # pyright: ignore[reportAny]
    
    if not command:
        print("Error: No command specified. Use --help for usage information.")
        return 1
    
    try:
        if command == "analyze-pr-changes":
            return cmd_analyze_pr_changes(args)
        elif command == "validate-translations":
            return cmd_validate_translations(args)
        else:
            print(f"Error: Unknown command '{command}'")
            return 1
    except KeyboardInterrupt:
        print("Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())