"""
Tests for i18n string extraction utilities.

This module tests the functionality of the i18n_utils module including
string extraction from Python files, .pot file generation, and .po file updates.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from src.tgraph_bot.utils.i18n.i18n_utils import (
    extract_strings_from_file,
    scan_directory_for_strings,
    generate_pot_file,
    parse_po_file,
    update_po_file,
    generate_pot_header,
    generate_po_header,
    parse_weblate_config,
)


class TestStringExtractor:
    """Test the StringExtractor AST visitor."""

    def test_extract_simple_translation_call(self) -> None:
        """Test extraction of simple _() translation calls."""
        code = """
def test_function():
    message = _("Hello, world!")
    return message
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            strings = extract_strings_from_file(Path(f.name))

        assert len(strings) == 1
        assert strings[0][0] == "Hello, world!"
        assert strings[0][1] == 3  # Line number
        assert strings[0][2] is None  # No context

    def test_extract_translate_function_call(self) -> None:
        """Test extraction of translate() function calls."""
        code = """
from src.tgraph_bot.i18n import translate

def test_function():
    message = translate("Welcome to the bot")
    formatted = translate("Hello, {name}!", name="Alice")
    return message
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            strings = extract_strings_from_file(Path(f.name))

        assert len(strings) == 2
        assert "Welcome to the bot" in [s[0] for s in strings]
        assert "Hello, {name}!" in [s[0] for s in strings]

    def test_extract_with_context(self) -> None:
        """Test extraction of strings with context."""
        code = """
def test_function():
    message = translate("Settings", context="menu_item")
    return message
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            strings = extract_strings_from_file(Path(f.name))

        assert len(strings) == 1
        assert strings[0][0] == "Settings"
        assert strings[0][2] == "menu_item"

    def test_extract_multiple_functions(self) -> None:
        """Test extraction from multiple translation function types."""
        code = """
def test_function():
    msg1 = _("Standard gettext")
    msg2 = translate("Custom translate")
    msg3 = t("Alias t")
    msg4 = ngettext("One item", "Many items", count)
    msg5 = nt("Single", "Plural", n)
    return msg1, msg2, msg3, msg4, msg5
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            strings = extract_strings_from_file(Path(f.name))

        expected_strings = {
            "Standard gettext",
            "Custom translate",
            "Alias t",
            "One item",
            "Many items",
            "Single",
            "Plural",
        }

        extracted_strings = {s[0] for s in strings}
        assert extracted_strings == expected_strings

    def test_ignore_non_translation_calls(self) -> None:
        """Test that non-translation function calls are ignored."""
        code = """
def test_function():
    print("This should not be extracted")
    log.info("Neither should this")
    message = _("But this should be")
    return message
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            strings = extract_strings_from_file(Path(f.name))

        assert len(strings) == 1
        assert strings[0][0] == "But this should be"

    def test_extract_from_invalid_syntax(self) -> None:
        """Test handling of files with invalid Python syntax."""
        code = """
def test_function(
    # Missing closing parenthesis and colon
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            _ = f.write(code)
            f.flush()

            with pytest.raises(SyntaxError):
                _ = extract_strings_from_file(Path(f.name))


class TestDirectoryScanning:
    """Test directory scanning functionality."""

    def test_scan_directory_for_strings(self) -> None:
        """Test scanning a directory for translatable strings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            _ = (temp_path / "file1.py").write_text("""
def func1():
    return _("Message from file1")
""")

            _ = (temp_path / "file2.py").write_text("""
def func2():
    return translate("Message from file2")
""")

            # Create subdirectory
            subdir = temp_path / "subdir"
            subdir.mkdir()
            _ = (subdir / "file3.py").write_text("""
def func3():
    return t("Message from subdir")
""")

            results = scan_directory_for_strings(temp_path)

            assert len(results) == 3
            assert "file1.py" in results
            assert "file2.py" in results
            assert "subdir/file3.py" in results

            # Check extracted strings
            all_strings: list[str] = []
            for strings in results.values():
                all_strings.extend([s[0] for s in strings])

            assert "Message from file1" in all_strings
            assert "Message from file2" in all_strings
            assert "Message from subdir" in all_strings

    def test_exclude_directories(self) -> None:
        """Test excluding specific directories from scanning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files in included directory
            _ = (temp_path / "included.py").write_text('_("Included message")')

            # Create files in excluded directory
            excluded_dir = temp_path / "excluded"
            excluded_dir.mkdir()
            _ = (excluded_dir / "excluded.py").write_text('_("Excluded message")')

            results = scan_directory_for_strings(temp_path, exclude_dirs={"excluded"})

            assert len(results) == 1
            assert "included.py" in results
            assert "excluded/excluded.py" not in results


class TestPotFileGeneration:
    """Test .pot file generation."""

    def test_generate_pot_header(self) -> None:
        """Test generation of .pot file header."""
        header = generate_pot_header()

        assert "TGraph Bot" in header
        assert "msgid" in header
        assert "msgstr" in header
        assert "Project-Id-Version" in header
        assert "POT-Creation-Date" in header

    def test_generate_pot_file(self) -> None:
        """Test generation of complete .pot file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test source file
            _ = (temp_path / "test.py").write_text("""
def test():
    msg1 = _("First message")
    msg2 = translate("Second message")
    return msg1, msg2
""")

            # Generate .pot file
            pot_file = temp_path / "messages.pot"
            generate_pot_file(temp_path, pot_file)

            assert pot_file.exists()

            content = pot_file.read_text()
            assert "First message" in content
            assert "Second message" in content
            assert "#: test.py:" in content
            assert 'msgid "First message"' in content
            assert 'msgstr ""' in content


class TestPoFileHandling:
    """Test .po file parsing and updating."""

    def test_parse_po_file(self) -> None:
        """Test parsing of .po files."""
        po_content = """# Test .po file
msgid ""
msgstr ""
"Project-Id-Version: Test\\n"

msgid "Hello"
msgstr "Hej"

msgid "Goodbye"
msgstr "Farvel"

msgid "Untranslated"
msgstr ""
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".po", delete=False) as f:
            _ = f.write(po_content)
            f.flush()

            translations = parse_po_file(Path(f.name))

        assert len(translations) == 2  # Only translated strings
        assert translations["Hello"] == "Hej"
        assert translations["Goodbye"] == "Farvel"
        assert "Untranslated" not in translations

    def test_generate_po_header(self) -> None:
        """Test generation of .po file header."""
        header = generate_po_header("da")

        assert "Danish translations" in header
        assert "Language: da" in header
        assert "nplurals=2; plural=n != 1;" in header

    def test_update_po_file(self) -> None:
        """Test updating .po file from .pot template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .pot template
            pot_content = """# Template file
msgid ""
msgstr ""

#: test.py:1
msgid "New message"
msgstr ""

#: test.py:2
msgid "Existing message"
msgstr ""
"""
            pot_file = temp_path / "messages.pot"
            _ = pot_file.write_text(pot_content)

            # Create existing .po file with some translations
            po_content = """# Existing translations
msgid ""
msgstr ""

msgid "Existing message"
msgstr "Eksisterende besked"

msgid "Old message"
msgstr "Gammel besked"
"""
            po_file = temp_path / "da" / "LC_MESSAGES" / "messages.po"
            po_file.parent.mkdir(parents=True)
            _ = po_file.write_text(po_content)

            # Update .po file
            update_po_file(pot_file, po_file, preserve_translations=True)

            # Check updated content
            updated_content = po_file.read_text()
            assert "New message" in updated_content
            assert "Existing message" in updated_content
            assert "Eksisterende besked" in updated_content  # Preserved translation
            assert "Old message" not in updated_content  # Removed obsolete string

    def test_update_po_file_no_duplicate_empty_msgid(self) -> None:
        """Test that updating .po file doesn't create duplicate empty msgid entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .pot template with header empty msgid (typical template format)
            pot_content = """# TGraph Bot POT file
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TGraph Bot\\n"
"POT-Creation-Date: 2024-01-01 12:00:00\\n"

#: test.py:1
msgid "Test message"
msgstr ""

#: test.py:2
msgid "Existing message"
msgstr ""
"""
            pot_file = temp_path / "messages.pot"
            _ = pot_file.write_text(pot_content)

            # Create proper .po file with header and existing translation
            po_content = """# Existing .po file
msgid ""
msgstr ""
"Project-Id-Version: Test\\n"

msgid "Existing message"
msgstr "Eksisterende besked"
"""
            po_file = temp_path / "da" / "LC_MESSAGES" / "messages.po"
            po_file.parent.mkdir(parents=True)
            _ = po_file.write_text(po_content)

            # Update .po file
            update_po_file(pot_file, po_file, preserve_translations=True)

            # Check that there's only one empty msgid in the result
            updated_content = po_file.read_text()
            empty_msgid_count = updated_content.count('msgid ""')
            assert empty_msgid_count == 1, (
                f"Expected 1 empty msgid, found {empty_msgid_count}"
            )

            # Verify the content includes expected elements
            assert "Test message" in updated_content
            assert "Eksisterende besked" in updated_content  # Preserved translation
            assert (
                "Danish translations" in updated_content
            )  # Header from generate_po_header


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_extract_from_nonexistent_file(self) -> None:
        """Test handling of non-existent files."""
        with pytest.raises(FileNotFoundError):
            _ = extract_strings_from_file(Path("/nonexistent/file.py"))

    def test_parse_nonexistent_po_file(self) -> None:
        """Test parsing non-existent .po file."""
        translations = parse_po_file(Path("/nonexistent/file.po"))
        assert translations == {}

    def test_update_po_with_nonexistent_pot(self) -> None:
        """Test updating .po file with non-existent .pot template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            po_file = temp_path / "messages.po"

            with pytest.raises(FileNotFoundError):
                update_po_file(Path("/nonexistent.pot"), po_file)


class TestWeblateConfigParsing:
    """Test Weblate configuration parsing functionality."""

    def test_parse_weblate_config_success(self) -> None:
        """Test successful parsing of .weblate configuration file."""
        weblate_content = """[weblate]
url = https://weblate.engels74.net/

[component "tgraph-bot/main"]
name = TGraph Bot Messages
slug = main
repo = https://github.com/engels74/tgraph-bot-source.git
push = git@github.com:engels74/tgraph-bot-source.git
branch = main
filemask = locale/*/LC_MESSAGES/messages.po
template = locale/messages.pot
file_format = po-mono
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".weblate", delete=False
        ) as f:
            _ = f.write(weblate_content)
            f.flush()

            config = parse_weblate_config(Path(f.name))

        assert config is not None
        assert config.url == "https://weblate.engels74.net"
        assert config.project == "tgraph-bot"
        assert config.component == "main"

    def test_parse_weblate_config_missing_file(self) -> None:
        """Test parsing with missing .weblate file."""
        config = parse_weblate_config(Path("/nonexistent/.weblate"))
        assert config is None

    def test_parse_weblate_config_missing_weblate_section(self) -> None:
        """Test parsing with missing [weblate] section."""
        weblate_content = """[component "tgraph-bot/main"]
name = TGraph Bot Messages
slug = main
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".weblate", delete=False
        ) as f:
            _ = f.write(weblate_content)
            f.flush()

            config = parse_weblate_config(Path(f.name))

        assert config is None

    def test_parse_weblate_config_missing_url(self) -> None:
        """Test parsing with missing URL in [weblate] section."""
        weblate_content = """[weblate]
# Missing url field

[component "tgraph-bot/main"]
name = TGraph Bot Messages
slug = main
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".weblate", delete=False
        ) as f:
            _ = f.write(weblate_content)
            f.flush()

            config = parse_weblate_config(Path(f.name))

        assert config is None

    def test_parse_weblate_config_no_components(self) -> None:
        """Test parsing with no component sections."""
        weblate_content = """[weblate]
url = https://weblate.engels74.net/

[some_other_section]
value = test
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".weblate", delete=False
        ) as f:
            _ = f.write(weblate_content)
            f.flush()

            config = parse_weblate_config(Path(f.name))

        assert config is None

    def test_generate_po_header_with_weblate_config(self) -> None:
        """Test that generate_po_header uses dynamic Weblate URLs when config is available."""
        # This test uses the actual .weblate file in the project root
        header = generate_po_header("da")

        # Should contain the correct self-hosted Weblate URL
        assert "https://weblate.engels74.net/projects/tgraph-bot/main/da/" in header
        assert "Danish" in header
        assert "Language: da" in header

    def test_generate_pot_header_with_weblate_config(self) -> None:
        """Test that generate_pot_header uses dynamic Weblate URLs when config is available."""
        # This test uses the actual .weblate file in the project root
        header = generate_pot_header()

        # Should contain the correct self-hosted Weblate URL template
        assert "https://weblate.engels74.net/projects/tgraph-bot/main/LANG/" in header
        assert "LANGUAGE <" in header
