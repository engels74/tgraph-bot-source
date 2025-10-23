"""Localization system for TGraph Bot.

This module provides multi-language support for bot messages and graph labels.
It loads localized strings from JSON files and provides fallback to English
when translations are missing.

The system is designed to be compatible with Weblate for collaborative translation.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from tgraph_bot.utils.errors import LocalizationError

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Localizer:
    """Manages localized strings for the bot.

    This class loads localization strings from JSON files and provides
    type-safe access to translated strings with optional formatting.

    Attributes:
        language: Language code (e.g., 'en', 'da')
        strings: Dictionary of localized strings
        fallback_strings: English strings for fallback when translation missing
    """

    language: str
    strings: dict[str, str]
    fallback_strings: dict[str, str] | None = None

    @classmethod
    def load(
        cls,
        language: str,
        *,
        locales_dir: Path | None = None,
    ) -> "Localizer":
        """Load localized strings for the specified language.

        This method loads the requested language file and the English fallback.
        If the requested language is not found, it falls back to English.

        Args:
            language: Language code to load (e.g., 'en', 'da')
            locales_dir: Directory containing locale JSON files.
                        Defaults to src/tgraph_bot/localization/locales

        Returns:
            Localizer instance with loaded strings

        Raises:
            LocalizationError: If English locale file is missing or invalid JSON

        Examples:
            >>> localizer = Localizer.load('en')
            >>> localizer.get('command_update_graphs_description')
            'Generate and post new graphs'
        """
        # Determine locales directory
        if locales_dir is None:
            # Default to package locales directory
            locales_dir = Path(__file__).parent / "locales"

        # Load English as fallback (required)
        english_file = locales_dir / "en.json"
        if not english_file.exists():
            raise LocalizationError(
                "English locale file not found. This is required for fallback.",
                language="en",
                locale_file=str(english_file),
            )

        try:
            with open(english_file, encoding="utf-8") as f:
                english_strings: dict[str, str] = cast(dict[str, str], json.load(f))
        except json.JSONDecodeError as e:
            raise LocalizationError(
                f"Failed to parse locale file: {e}",
                language="en",
                locale_file=str(english_file),
            ) from e

        # If requesting English, return it directly
        if language == "en":
            logger.info("Loaded English locale")
            return cls(language="en", strings=english_strings, fallback_strings=None)

        # Try to load requested language
        locale_file = locales_dir / f"{language}.json"
        if not locale_file.exists():
            logger.warning(
                f"Locale file for '{language}' not found. Falling back to English.",
                extra={"language": language, "locale_file": str(locale_file)},
            )
            return cls(language="en", strings=english_strings, fallback_strings=None)

        try:
            with open(locale_file, encoding="utf-8") as f:
                language_strings: dict[str, str] = cast(dict[str, str], json.load(f))
        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse locale file for '{language}'. Falling back to English.",
                extra={"language": language, "error": str(e)},
            )
            return cls(language="en", strings=english_strings, fallback_strings=None)

        logger.info(f"Loaded {language} locale with English fallback")
        return cls(
            language=language,
            strings=language_strings,
            fallback_strings=english_strings,
        )

    def get(self, key: str, **kwargs: str | int | float) -> str:
        """Get localized string with optional formatting.

        This method retrieves a localized string by key and formats it with
        the provided keyword arguments. If the key is not found in the current
        language, it falls back to English. If not found in English either,
        it returns the key itself.

        Args:
            key: String key to retrieve
            **kwargs: Keyword arguments for string formatting (str, int, or float)

        Returns:
            Localized and formatted string

        Examples:
            >>> localizer.get('error_rate_limited', minutes=5)
            'Rate limited. Try again in 5 minutes.'

            >>> localizer.get('success_graphs_generated', count=12)
            'Successfully generated 12 graphs'
        """
        # Try to get from current language
        template = self.strings.get(key)

        # Fall back to English if not found
        if template is None and self.fallback_strings is not None:
            template = self.fallback_strings.get(key)
            if template is not None:
                logger.debug(
                    f"Using English fallback for key '{key}'",
                    extra={"key": key, "language": self.language},
                )

        # If still not found, return the key itself
        if template is None:
            logger.warning(
                f"Localization key '{key}' not found in {self.language} or English",
                extra={"key": key, "language": self.language},
            )
            return key

        # Format the template with provided arguments
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                logger.error(
                    f"Missing format argument for key '{key}': {e}",
                    extra={"key": key, "template": template, "kwargs": kwargs},
                )
                return template
        else:
            return template

