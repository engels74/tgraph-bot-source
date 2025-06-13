"""
Tests for the internationalization (i18n) module.

This module tests the translation loading, fallback behavior, string formatting,
and language switching functionality of the i18n system.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import i18n


class TestI18nModule:
    """Test cases for the i18n module."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Reset the global translation function to default
        i18n._ = lambda x: x

    def test_setup_i18n_default_language(self) -> None:
        """Test setting up i18n with default English language."""
        # This should not raise an exception even if locale files don't exist
        i18n.setup_i18n()
        
        # The translation function should be available
        assert callable(i18n._)
        
        # Test that we can get the translation function
        translation_func = i18n.get_translation()
        assert callable(translation_func)

    def test_setup_i18n_specific_language(self) -> None:
        """Test setting up i18n with a specific language."""
        # Test with a language that doesn't exist - should fallback gracefully
        i18n.setup_i18n("da")
        
        # The translation function should still be available
        assert callable(i18n._)

    def test_translate_function_basic(self) -> None:
        """Test basic translation functionality."""
        # Test with a simple string
        result = i18n.translate("Hello, world!")
        assert isinstance(result, str)
        assert result == "Hello, world!"  # Should return original if no translation

    def test_translate_function_with_formatting(self) -> None:
        """Test translation with string formatting."""
        # Test with formatting arguments
        result = i18n.translate("Hello, {name}!", name="Alice")
        assert result == "Hello, Alice!"

    def test_translate_function_formatting_error(self) -> None:
        """Test translation with invalid formatting arguments."""
        # Test with missing format argument - should handle gracefully
        result = i18n.translate("Hello, {name}!")
        assert result == "Hello, {name}!"  # Should return unformatted string

    def test_translate_alias(self) -> None:
        """Test that the 't' alias works correctly."""
        result = i18n.t("Test message")
        assert isinstance(result, str)
        assert result == "Test message"

    def test_translate_with_kwargs(self) -> None:
        """Test translation with keyword arguments."""
        result = i18n.t("User {user} has {count} items", user="Bob", count=5)
        assert result == "User Bob has 5 items"

    @patch('i18n.logger')
    def test_setup_i18n_with_exception(self, mock_logger: MagicMock) -> None:
        """Test setup_i18n handles exceptions gracefully."""
        with patch('gettext.translation', side_effect=Exception("Test error")):
            i18n.setup_i18n("invalid")
            
            # Should log a warning
            mock_logger.warning.assert_called()
            mock_logger.info.assert_called_with("Using default English strings")

    @patch('i18n.logger')
    def test_translate_formatting_error_logging(self, mock_logger: MagicMock) -> None:
        """Test that formatting errors are logged properly."""
        # Test with invalid format string
        _ = i18n.translate("Hello, {invalid_key}", valid_key="value")
        
        # Should log a warning about formatting error
        mock_logger.warning.assert_called()
        assert "Translation formatting error" in str(mock_logger.warning.call_args)

    def test_get_translation_returns_callable(self) -> None:
        """Test that get_translation returns a callable function."""
        translation_func = i18n.get_translation()
        assert callable(translation_func)
        
        # Test that the returned function works
        result = translation_func("test")
        assert isinstance(result, str)


class TestI18nWithRealLocaleFiles:
    """Test i18n functionality with actual locale files."""

    def test_with_existing_locale_structure(self) -> None:
        """Test i18n with the existing locale directory structure."""
        # Test that setup works with the existing locale structure
        locale_dir = Path("locale")
        if locale_dir.exists():
            i18n.setup_i18n("en")
            
            # Test translation of a known string from messages.po
            result = i18n.translate("Bot is online and ready!")
            assert isinstance(result, str)
            # Should return the translated string or original if translation not found
            assert len(result) > 0

    def test_fallback_behavior(self) -> None:
        """Test fallback behavior when translation files are missing."""
        # Test with a non-existent language
        i18n.setup_i18n("nonexistent")
        
        # Should still work and return original strings
        result = i18n.translate("Test message")
        assert result == "Test message"


class TestI18nIntegration:
    """Integration tests for i18n module."""

    def test_module_imports_correctly(self) -> None:
        """Test that the i18n module can be imported and used."""
        # Test that all expected functions are available
        assert hasattr(i18n, 'setup_i18n')
        assert hasattr(i18n, 'get_translation')
        assert hasattr(i18n, 'translate')
        assert hasattr(i18n, 't')
        assert hasattr(i18n, '_')
        assert hasattr(i18n, 'ngettext')
        assert hasattr(i18n, 'nt')
        assert hasattr(i18n, 'get_current_language')
        assert hasattr(i18n, 'get_locale_directory')
        assert hasattr(i18n, 'get_domain')
        assert hasattr(i18n, 'install_translation')
        assert hasattr(i18n, 'switch_language')

    def test_global_translation_function(self) -> None:
        """Test that the global _ function works correctly."""
        # Test the global translation function
        result = i18n._("Test string")
        assert isinstance(result, str)

    def test_language_switching(self) -> None:
        """Test switching between languages."""
        # Setup English
        i18n.setup_i18n("en")
        en_func = i18n.get_translation()

        # Setup another language (will fallback to English if not available)
        i18n.setup_i18n("da")
        da_func = i18n.get_translation()

        # Both should be callable
        assert callable(en_func)
        assert callable(da_func)


class TestI18nEnhancedFeatures:
    """Test cases for enhanced i18n features."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Reset to default state
        i18n.setup_i18n("en")

    def test_get_current_language(self) -> None:
        """Test getting the current language."""
        i18n.setup_i18n("en")
        assert i18n.get_current_language() == "en"

        i18n.setup_i18n("da")
        assert i18n.get_current_language() == "da"

    def test_get_locale_directory(self) -> None:
        """Test getting the locale directory."""
        i18n.setup_i18n("en")
        locale_dir = i18n.get_locale_directory()
        assert locale_dir is not None
        assert locale_dir.name == "locale"

    def test_get_domain(self) -> None:
        """Test getting the gettext domain."""
        domain = i18n.get_domain()
        assert domain == "messages"

    def test_switch_language(self) -> None:
        """Test dynamic language switching."""
        # Switch to English
        result = i18n.switch_language("en")
        assert result is True
        assert i18n.get_current_language() == "en"

        # Switch to another language
        result = i18n.switch_language("da")
        assert result is True
        assert i18n.get_current_language() == "da"

    def test_ngettext_singular(self) -> None:
        """Test plural translation with singular form."""
        result = i18n.ngettext("You have {n} message", "You have {n} messages", 1)
        assert result == "You have 1 message"

    def test_ngettext_plural(self) -> None:
        """Test plural translation with plural form."""
        result = i18n.ngettext("You have {n} message", "You have {n} messages", 5)
        assert result == "You have 5 messages"

    def test_ngettext_with_kwargs(self) -> None:
        """Test plural translation with additional formatting."""
        result = i18n.ngettext(
            "User {user} has {n} message",
            "User {user} has {n} messages",
            3,
            user="Alice"
        )
        assert result == "User Alice has 3 messages"

    def test_ngettext_alias(self) -> None:
        """Test that the 'nt' alias works correctly."""
        result = i18n.nt("You have {n} item", "You have {n} items", 2)
        assert result == "You have 2 items"

    @patch('i18n.logger')
    def test_install_translation(self, mock_logger: MagicMock) -> None:
        """Test installing translation globally."""
        # This should not raise an exception
        i18n.install_translation("en")

        # Should log success
        mock_logger.info.assert_called()
        assert "Installed translations globally" in str(mock_logger.info.call_args)
