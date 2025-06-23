#!/usr/bin/env python3
"""
Development helpers for i18n workflow.

This script provides convenient shortcuts for common i18n operations
during development.

Usage:
    uv run python scripts/i18n/dev-helpers.py extract      # Extract strings
    uv run python scripts/i18n/dev-helpers.py update       # Update all translations
    uv run python scripts/i18n/dev-helpers.py compile      # Compile to .mo files
    uv run python scripts/i18n/dev-helpers.py status       # Show translation status
    uv run python scripts/i18n/dev-helpers.py test         # Test translation loading
    uv run python scripts/i18n/dev-helpers.py fix-english  # Fix English base file for Weblate
    uv run python scripts/i18n/dev-helpers.py full         # Full workflow (extract + update + compile)
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Callable, Literal, cast

CommandChoice = Literal[
    "extract", "update", "compile", "status", "test", "full", "fix-english"
]


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and report success/failure."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        stderr_msg: str | None = e.stderr  # pyright: ignore[reportAny] # subprocess type limitation
        if stderr_msg:
            print(f"   Error: {stderr_msg.strip()}")
        return False


def extract_strings() -> bool:
    """Extract translatable strings to .pot file."""
    return run_command(
        ["uv", "run", "python", "scripts/i18n/extract_strings.py"],
        "Extracting translatable strings",
    )


def update_translations() -> bool:
    """Update all .po files from .pot template."""
    return run_command(
        ["uv", "run", "python", "scripts/i18n/update_translations.py"],
        "Updating translation files",
    )


def compile_translations() -> bool:
    """Compile .po files to .mo binary format."""
    return run_command(
        ["uv", "run", "python", "scripts/i18n/compile_translations.py"],
        "Compiling translation files",
    )


def show_status() -> bool:
    """Show translation status for all languages."""
    print("📊 Translation Status:")
    print()

    locale_dir = Path("locale")
    if not locale_dir.exists():
        print("❌ No locale directory found")
        return False

    # Check template file
    pot_file = locale_dir / "messages.pot"
    if pot_file.exists():
        # Count strings in template
        with open(pot_file, "r", encoding="utf-8") as f:
            content = f.read()
            string_count = content.count('msgid "') - 1  # Subtract header
        print(f"📄 Template: {string_count} translatable strings")
    else:
        print("❌ No messages.pot template found")
        return False

    print()

    # Check each language
    for lang_dir in sorted(locale_dir.iterdir()):
        if lang_dir.is_dir() and lang_dir.name != "__pycache__":
            lang = lang_dir.name
            po_file = lang_dir / "LC_MESSAGES" / "messages.po"
            mo_file = lang_dir / "LC_MESSAGES" / "messages.mo"

            if po_file.exists():
                # Get translation statistics
                try:
                    result = subprocess.run(
                        ["msgfmt", "--statistics", str(po_file)],
                        capture_output=True,
                        text=True,
                    )
                    stats = (
                        result.stderr.strip()
                        if result.stderr
                        else "No statistics available"
                    )
                    mo_status = "✅" if mo_file.exists() else "❌"
                    print(f"🌐 {lang:3}: {stats} | Binary: {mo_status}")
                except FileNotFoundError:
                    print(f"🌐 {lang:3}: msgfmt not available (install gettext)")
            else:
                print(f"🌐 {lang:3}: ❌ No .po file found")

    return True


def test_translations() -> bool:
    """Test that all translations can be loaded correctly."""
    print("🧪 Testing translation loading...")

    try:
        import src.tgraph_bot.i18n as i18n

        locale_dir = Path("locale")
        success = True

        for lang_dir in locale_dir.iterdir():
            if lang_dir.is_dir() and lang_dir.name != "__pycache__":
                lang = lang_dir.name
                try:
                    i18n.setup_i18n(lang)
                    # Test a known string and verify translation works
                    _ = i18n._("Bot is online and ready!")
                    print(f"   ✅ {lang}: Loaded successfully")
                except Exception as e:
                    print(f"   ❌ {lang}: Failed to load - {e}")
                    success = False

        if success:
            print("✅ All translations loaded successfully")
        else:
            print("❌ Some translations failed to load")

        return success

    except ImportError:
        print("❌ Cannot import i18n module")
        return False


def fix_english_base() -> bool:
    """Fix English base language file for monolingual Weblate setup."""
    python_code = (
        "from utils.i18n.i18n_utils import fix_english_base_file; "
        + "from pathlib import Path; "
        + "fix_english_base_file(Path('locale/en/LC_MESSAGES/messages.po'))"
    )
    return run_command(
        ["uv", "run", "python", "-c", python_code], "Fixing English base language file"
    )


def full_workflow() -> bool:
    """Run the complete i18n workflow."""
    print("🚀 Running full i18n workflow...")
    print()

    steps: list[tuple[str, Callable[[], bool]]] = [
        ("extract", extract_strings),
        ("update", update_translations),
        ("compile", compile_translations),
        ("test", test_translations),
    ]

    for step_name, step_func in steps:
        if not step_func():
            print(f"❌ Workflow failed at step: {step_name}")
            return False
        print()

    print("🎉 Full i18n workflow completed successfully!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="i18n development helpers")
    _ = parser.add_argument(
        "command",
        choices=[
            "extract",
            "update",
            "compile",
            "status",
            "test",
            "full",
            "fix-english",
        ],
        help="Command to run",
    )

    args = parser.parse_args()

    commands: dict[CommandChoice, Callable[[], bool]] = {
        "extract": extract_strings,
        "update": update_translations,
        "compile": compile_translations,
        "status": show_status,
        "test": test_translations,
        "full": full_workflow,
        "fix-english": fix_english_base,
    }

    # Type cast is safe because argparse validates the choice
    command = cast(CommandChoice, args.command)
    success = commands[command]()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
