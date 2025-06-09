"""
Internationalization (i18n) support for TGraph Bot.

This module handles loading gettext translation files from the locale directory
and provides functions to retrieve translated strings based on the configured language.
"""

import gettext
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Global translation function
_: Callable[[str], str] = lambda x: x  # Default fallback


def setup_i18n(language: str = "en") -> None:
    """
    Setup internationalization for the specified language.
    
    Args:
        language: Language code (e.g., 'en', 'da')
    """
    global _
    
    try:
        locale_dir = Path(__file__).parent / "locale"
        
        # Try to load the specified language
        translation = gettext.translation(
            "messages",
            localedir=locale_dir,
            languages=[language],
            fallback=True
        )
        
        # Install the translation function globally
        _ = translation.gettext
        
        logger.info(f"Loaded translations for language: {language}")
        
    except Exception as e:
        logger.warning(f"Failed to load translations for {language}: {e}")
        logger.info("Using default English strings")
        # Keep the default fallback function


def get_translation() -> Callable[[str], str]:
    """
    Get the current translation function.
    
    Returns:
        The translation function for the current language
    """
    return _


def translate(message: str, **kwargs: Any) -> str:
    """
    Translate a message with optional formatting.
    
    Args:
        message: The message to translate
        **kwargs: Format arguments for the translated string
        
    Returns:
        The translated and formatted message
    """
    translated = _(message)
    
    if kwargs:
        try:
            return translated.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.warning(f"Translation formatting error for '{message}': {e}")
            return translated
    
    return translated


# Convenience alias
t = translate
