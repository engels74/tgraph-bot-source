"""
Test suite for locale directory structure and translation file validation.

This module tests that the locale directory structure is properly set up
according to gettext standards and that translation files are correctly formatted.
"""

import pytest
from pathlib import Path
import polib
import i18n


class TestLocaleStructure:
    """Test the locale directory structure and file organization."""

    def test_locale_directory_exists(self) -> None:
        """Test that the locale directory exists."""
        locale_dir = Path("locale")
        assert locale_dir.exists(), "locale directory should exist"
        assert locale_dir.is_dir(), "locale should be a directory"

    def test_messages_pot_exists(self) -> None:
        """Test that the messages.pot template file exists."""
        pot_file = Path("locale/messages.pot")
        assert pot_file.exists(), "messages.pot template file should exist"
        assert pot_file.is_file(), "messages.pot should be a file"

    def test_english_locale_structure(self) -> None:
        """Test that English locale structure is correct."""
        en_dir = Path("locale/en")
        lc_messages_dir = Path("locale/en/LC_MESSAGES")
        po_file = Path("locale/en/LC_MESSAGES/messages.po")
        
        assert en_dir.exists(), "English locale directory should exist"
        assert en_dir.is_dir(), "English locale should be a directory"
        assert lc_messages_dir.exists(), "LC_MESSAGES directory should exist"
        assert lc_messages_dir.is_dir(), "LC_MESSAGES should be a directory"
        assert po_file.exists(), "English messages.po file should exist"
        assert po_file.is_file(), "messages.po should be a file"

    def test_danish_locale_structure(self) -> None:
        """Test that Danish locale structure is correct."""
        da_dir = Path("locale/da")
        lc_messages_dir = Path("locale/da/LC_MESSAGES")
        po_file = Path("locale/da/LC_MESSAGES/messages.po")
        
        assert da_dir.exists(), "Danish locale directory should exist"
        assert da_dir.is_dir(), "Danish locale should be a directory"
        assert lc_messages_dir.exists(), "LC_MESSAGES directory should exist"
        assert lc_messages_dir.is_dir(), "LC_MESSAGES should be a directory"
        assert po_file.exists(), "Danish messages.po file should exist"
        assert po_file.is_file(), "messages.po should be a file"


class TestTranslationFiles:
    """Test the translation file format and content."""

    def test_pot_file_format(self) -> None:
        """Test that the POT file is properly formatted."""
        pot_file = Path("locale/messages.pot")
        
        # Use polib to parse and validate the POT file
        po = polib.pofile(str(pot_file))
        
        # Check metadata
        assert po.metadata['Project-Id-Version'] == 'TGraph Bot 1.0.0'
        assert po.metadata['Content-Type'] == 'text/plain; charset=UTF-8'
        assert 'engels74' in po.metadata['Last-Translator']
        
        # Check that there are translatable strings
        assert len(po) > 0, "POT file should contain translatable strings"
        
        # Check for some expected strings
        expected_strings = [
            "TGraph Bot - Tautulli Discord Graph Generator",
            "Bot is online and ready!",
            "An error occurred while processing your request"
        ]
        
        pot_msgids = [entry.msgid for entry in po]
        for expected in expected_strings:
            assert expected in pot_msgids, f"Expected string '{expected}' not found in POT file"

    def test_english_po_file_format(self) -> None:
        """Test that the English PO file is properly formatted."""
        po_file = Path("locale/en/LC_MESSAGES/messages.po")
        
        # Use polib to parse and validate the PO file
        po = polib.pofile(str(po_file))
        
        # Check metadata
        assert po.metadata['Language'] == 'en'
        assert po.metadata['Content-Type'] == 'text/plain; charset=UTF-8'
        assert 'engels74' in po.metadata['Last-Translator']
        
        # Check that translations exist
        assert len(po) > 0, "English PO file should contain translations"
        
        # Check that English translations are provided (should be same as msgid)
        for entry in po:
            if entry.msgid and not entry.msgid.startswith('#'):
                assert entry.msgstr, f"English translation missing for: {entry.msgid}"

    def test_danish_po_file_format(self) -> None:
        """Test that the Danish PO file is properly formatted."""
        po_file = Path("locale/da/LC_MESSAGES/messages.po")
        
        # Use polib to parse and validate the PO file
        po = polib.pofile(str(po_file))
        
        # Check metadata
        assert po.metadata['Language'] == 'da'
        assert po.metadata['Content-Type'] == 'text/plain; charset=UTF-8'
        assert 'engels74' in po.metadata['Last-Translator']
        
        # Check that translations exist
        assert len(po) > 0, "Danish PO file should contain translations"
        
        # Check that Danish translations are provided
        for entry in po:
            if entry.msgid and not entry.msgid.startswith('#'):
                assert entry.msgstr, f"Danish translation missing for: {entry.msgid}"


class TestI18nIntegration:
    """Test integration between locale structure and i18n module."""

    def test_i18n_loads_english_translations(self) -> None:
        """Test that i18n can load English translations."""
        i18n.setup_i18n("en")
        
        # Test a known translation
        result = i18n.translate("Bot is online and ready!")
        assert result == "Bot is online and ready!"
        
        # Test current language
        assert i18n.get_current_language() == "en"

    def test_i18n_loads_danish_translations(self) -> None:
        """Test that i18n can load Danish translations."""
        i18n.setup_i18n("da")
        
        # Test a known translation
        result = i18n.translate("Bot is online and ready!")
        assert result == "Bot er online og klar!"
        
        # Test current language
        assert i18n.get_current_language() == "da"

    def test_i18n_fallback_to_english(self) -> None:
        """Test that i18n falls back to English for unsupported languages."""
        i18n.setup_i18n("fr")  # French not supported
        
        # Should fallback to English
        result = i18n.translate("Bot is online and ready!")
        assert result == "Bot is online and ready!"

    def test_locale_directory_detection(self) -> None:
        """Test that i18n correctly detects the locale directory."""
        i18n.setup_i18n("en")
        locale_dir = i18n.get_locale_directory()
        
        assert locale_dir is not None
        assert locale_dir.name == "locale"
        assert locale_dir.exists()
