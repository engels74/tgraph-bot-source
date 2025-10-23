"""Tests for localization system.

This test suite validates the localization system including:
- Loading English and Danish localization files
- Fallback to English when translation missing
- String formatting with keyword arguments
- Handling missing localization files
- Weblate compatibility (JSON format)

Requirements tested: 14.1, 14.2, 14.4
"""

import json
import tempfile
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from tgraph_bot.localization.localizer import Localizer
from tgraph_bot.utils.errors import LocalizationError


@pytest.fixture
def temp_locales_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for locale files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def english_strings() -> dict[str, str]:
    """Fixture providing English localization strings."""
    return {
        "command_update_graphs_description": "Generate and post new graphs",
        "command_my_stats_description": "View your personal statistics",
        "command_config_description": "View current configuration",
        "error_rate_limited": "Rate limited. Try again in {minutes} minutes.",
        "error_tautulli_connection": "Failed to connect to Tautulli: {error}",
        "success_graphs_generated": "Successfully generated {count} graphs",
        "graph_title_daily_play_count": "Daily Play Count",
        "graph_label_date": "Date",
        "graph_label_count": "Play Count",
        "graph_label_movies": "Movies",
        "graph_label_tv_shows": "TV Shows",
    }


@pytest.fixture
def danish_strings() -> dict[str, str]:
    """Fixture providing Danish localization strings."""
    return {
        "command_update_graphs_description": "Generer og post nye grafer",
        "command_my_stats_description": "Se dine personlige statistikker",
        "command_config_description": "Se nuværende konfiguration",
        "error_rate_limited": "Hastighedsbegrænset. Prøv igen om {minutes} minutter.",
        "error_tautulli_connection": "Kunne ikke oprette forbindelse til Tautulli: {error}",
        "success_graphs_generated": "Genererede {count} grafer med succes",
        "graph_title_daily_play_count": "Daglig afspilningstælling",
        "graph_label_date": "Dato",
        "graph_label_count": "Afspilningstælling",
        "graph_label_movies": "Film",
        "graph_label_tv_shows": "TV-serier",
    }


@pytest.fixture
def partial_danish_strings() -> dict[str, str]:
    """Fixture providing partial Danish localization (missing some keys)."""
    return {
        "command_update_graphs_description": "Generer og post nye grafer",
        "command_my_stats_description": "Se dine personlige statistikker",
        # Missing other keys to test fallback
    }


@pytest.fixture
def create_locale_file(
    temp_locales_dir: Path,
) -> Callable[[str, dict[str, str]], Path]:
    """Factory fixture to create locale JSON files."""

    def _create_file(language: str, strings: dict[str, str]) -> Path:
        """Create a locale file with given strings.

        Args:
            language: Language code (e.g., 'en', 'da')
            strings: Dictionary of localized strings

        Returns:
            Path to the created locale file
        """
        locale_file = temp_locales_dir / f"{language}.json"
        with open(locale_file, "w", encoding="utf-8") as f:
            json.dump(strings, f, ensure_ascii=False, indent=2)
        return locale_file

    return _create_file


class TestLocalizerLoading:
    """Test suite for Localizer loading functionality."""

    def test_load_english_locale(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test loading English locale file.

        Requirements: 14.1, 14.5
        """
        _ = create_locale_file("en", english_strings)

        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        assert localizer.language == "en"
        assert localizer.get("command_update_graphs_description") == english_strings[
            "command_update_graphs_description"
        ]

    def test_load_danish_locale(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
        danish_strings: dict[str, str],
    ) -> None:
        """Test loading Danish locale file.

        Requirements: 14.1, 14.5
        """
        # Create English for fallback
        _ = create_locale_file("en", english_strings)
        _ = create_locale_file("da", danish_strings)

        localizer = Localizer.load("da", locales_dir=temp_locales_dir)

        assert localizer.language == "da"
        assert localizer.get("command_update_graphs_description") == danish_strings[
            "command_update_graphs_description"
        ]

    def test_load_nonexistent_locale_falls_back_to_english(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test fallback to English when requested locale doesn't exist.

        Requirements: 14.4
        """
        # Create only English locale
        _ = create_locale_file("en", english_strings)

        # Request non-existent locale
        localizer = Localizer.load("fr", locales_dir=temp_locales_dir)

        # Should fall back to English
        assert localizer.language == "en"
        assert localizer.get("command_update_graphs_description") == english_strings[
            "command_update_graphs_description"
        ]

    def test_load_missing_english_locale_raises_error(
        self, temp_locales_dir: Path
    ) -> None:
        """Test that missing English locale raises LocalizationError.

        Requirements: 14.4
        """
        # Don't create any locale files
        with pytest.raises(LocalizationError) as exc_info:
            _ = Localizer.load("en", locales_dir=temp_locales_dir)

        assert "English locale file not found" in str(exc_info.value)

    def test_load_invalid_json_raises_error(
        self, temp_locales_dir: Path
    ) -> None:
        """Test that invalid JSON in locale file raises LocalizationError.

        Requirements: 14.1
        """
        # Create invalid JSON file
        locale_file = temp_locales_dir / "en.json"
        with open(locale_file, "w") as f:
            _ = f.write("{ invalid json }")

        with pytest.raises(LocalizationError) as exc_info:
            _ = Localizer.load("en", locales_dir=temp_locales_dir)

        assert "Failed to parse locale file" in str(exc_info.value)


class TestLocalizerStringRetrieval:
    """Test suite for Localizer string retrieval functionality."""

    def test_get_existing_string(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test retrieving an existing localized string.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("command_update_graphs_description")

        assert result == "Generate and post new graphs"

    def test_get_missing_string_returns_key(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test that missing string key returns the key itself.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("nonexistent_key")

        assert result == "nonexistent_key"

    def test_get_with_fallback_to_english(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
        partial_danish_strings: dict[str, str],
    ) -> None:
        """Test fallback to English for missing Danish translations.

        Requirements: 14.4
        """
        _ = create_locale_file("en", english_strings)
        _ = create_locale_file("da", partial_danish_strings)

        localizer = Localizer.load("da", locales_dir=temp_locales_dir)

        # Key exists in Danish
        assert (
            localizer.get("command_update_graphs_description")
            == "Generer og post nye grafer"
        )

        # Key missing in Danish, should fall back to English
        assert (
            localizer.get("error_tautulli_connection")
            == "Failed to connect to Tautulli: {error}"
        )


class TestLocalizerStringFormatting:
    """Test suite for Localizer string formatting functionality."""

    def test_format_string_with_single_argument(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test formatting string with single keyword argument.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("error_rate_limited", minutes=5)

        assert result == "Rate limited. Try again in 5 minutes."

    def test_format_string_with_multiple_arguments(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test formatting string with multiple keyword arguments.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("error_tautulli_connection", error="Connection timeout")

        assert result == "Failed to connect to Tautulli: Connection timeout"

    def test_format_string_with_integer_argument(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test formatting string with integer argument.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("success_graphs_generated", count=12)

        assert result == "Successfully generated 12 graphs"

    def test_format_string_without_placeholders(
        self,
        temp_locales_dir: Path,
        create_locale_file: Callable[[str, dict[str, str]], Path],
        english_strings: dict[str, str],
    ) -> None:
        """Test that strings without placeholders work correctly.

        Requirements: 14.2
        """
        _ = create_locale_file("en", english_strings)
        localizer = Localizer.load("en", locales_dir=temp_locales_dir)

        result = localizer.get("graph_title_daily_play_count")

        assert result == "Daily Play Count"

