"""
Internationalization (i18n) support for TGraph Bot.

This module handles loading gettext translation files from the locale directory
and provides functions to retrieve translated strings based on the configured language.

Usage Examples:
    Basic setup:
        >>> import i18n
        >>> i18n.setup_i18n("en")  # Setup English translations
        >>> message = i18n._("Hello, world!")  # Translate a string

    With formatting:
        >>> message = i18n.translate("Hello, {name}!", name="Alice")
        >>> # or using the alias:
        >>> message = i18n.t("Hello, {name}!", name="Alice")

    Language switching:
        >>> i18n.setup_i18n("da")  # Switch to Danish
        >>> i18n.setup_i18n("en")  # Switch back to English

    Getting current translation function:
        >>> translate_func = i18n.get_translation()
        >>> message = translate_func("Hello, world!")
"""

import gettext
import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Global translation function
_: Callable[[str], str] = lambda x: x  # Default fallback

# Global variables for gettext configuration
_current_language: str = "en"
_locale_dir: Optional[Path] = None
_domain: str = "messages"


def setup_i18n(language: str = "en", locale_dir: Optional[Path] = None) -> None:
    """
    Setup internationalization for the specified language.

    This function configures gettext with the appropriate domain, locale directory,
    and language settings. It uses gettext.bindtextdomain() and gettext.textdomain()
    for proper gettext configuration.

    Args:
        language: Language code (e.g., 'en', 'da', 'fr')
        locale_dir: Custom locale directory path. If None, uses default 'locale' directory
    """
    global _, _current_language, _locale_dir, _domain

    try:
        # Set up locale directory
        if locale_dir is None:
            _locale_dir = Path(__file__).parent / "locale"
        else:
            _locale_dir = locale_dir

        # Configure gettext domain and locale directory
        _result = gettext.bindtextdomain(_domain, str(_locale_dir))
        _result = gettext.textdomain(_domain)

        # Try to load the specified language
        translation = gettext.translation(
            _domain,
            localedir=_locale_dir,
            languages=[language],
            fallback=True
        )

        # Install the translation function globally
        _ = translation.gettext
        _current_language = language

        logger.info(f"Loaded translations for language: {language}")
        logger.debug(f"Using locale directory: {_locale_dir}")

    except Exception as e:
        logger.warning(f"Failed to load translations for {language}: {e}")
        logger.info("Using default English strings")
        # Keep the default fallback function
        _current_language = "en"


def get_translation() -> Callable[[str], str]:
    """
    Get the current translation function.

    Returns:
        The translation function for the current language
    """
    return _


def get_current_language() -> str:
    """
    Get the currently configured language.

    Returns:
        The current language code (e.g., 'en', 'da')
    """
    return _current_language


def get_locale_directory() -> Optional[Path]:
    """
    Get the current locale directory path.

    Returns:
        Path to the locale directory, or None if not configured
    """
    return _locale_dir


def get_domain() -> str:
    """
    Get the current gettext domain.

    Returns:
        The gettext domain name (usually 'messages')
    """
    return _domain


def install_translation(language: str = "en") -> None:
    """
    Install translation globally using gettext.install().

    This is an alternative to setup_i18n() that uses gettext.install()
    to make the translation function available as a builtin.

    Args:
        language: Language code to install

    Note:
        This function modifies the builtin namespace. Use setup_i18n()
        for more controlled translation management.
    """
    global _locale_dir, _domain, _current_language

    try:
        if _locale_dir is None:
            _locale_dir = Path(__file__).parent / "locale"

        # Configure gettext
        _result = gettext.bindtextdomain(_domain, str(_locale_dir))
        _result = gettext.textdomain(_domain)

        # Install translation as builtin
        gettext.install(_domain, str(_locale_dir), names=["gettext", "ngettext"])

        _current_language = language
        logger.info(f"Installed translations globally for language: {language}")

    except Exception as e:
        logger.warning(f"Failed to install translations for {language}: {e}")
        logger.info("Translation functions may not be available globally")


def translate(message: str, **kwargs: object) -> str:
    """
    Translate a message with optional formatting.

    Args:
        message: The message to translate
        **kwargs: Format arguments for the translated string

    Returns:
        The translated and formatted message

    Examples:
        >>> translate("Hello, world!")
        "Hello, world!"
        >>> translate("Hello, {name}!", name="Alice")
        "Hello, Alice!"
    """
    translated = _(message)

    if kwargs:
        try:
            return translated.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.warning(f"Translation formatting error for '{message}': {e}")
            return translated

    return translated


def ngettext(singular: str, plural: str, n: int, **kwargs: object) -> str:
    """
    Translate a message with plural forms.

    Args:
        singular: Singular form of the message
        plural: Plural form of the message
        n: Number to determine which form to use
        **kwargs: Format arguments for the translated string

    Returns:
        The translated message in appropriate plural form

    Examples:
        >>> ngettext("You have {n} message", "You have {n} messages", 1, n=1)
        "You have 1 message"
        >>> ngettext("You have {n} message", "You have {n} messages", 5, n=5)
        "You have 5 messages"
    """
    try:
        # Simple plural logic fallback (English rules)
        # In a full implementation, this would use gettext's ngettext
        translated = singular if n == 1 else plural

        if kwargs:
            try:
                return translated.format(n=n, **kwargs)
            except (KeyError, ValueError) as e:
                logger.warning(f"Plural translation formatting error: {e}")
                return translated.format(n=n) if '{n}' in translated else translated

        return translated.format(n=n) if '{n}' in translated else translated

    except Exception as e:
        logger.warning(f"Plural translation error: {e}")
        # Fallback
        result = singular if n == 1 else plural
        return result.format(n=n, **kwargs) if kwargs else result


def switch_language(language: str) -> bool:
    """
    Switch to a different language dynamically.

    Args:
        language: Language code to switch to

    Returns:
        True if language switch was successful, False otherwise
    """
    try:
        setup_i18n(language)
        return True
    except Exception as e:
        logger.error(f"Failed to switch to language {language}: {e}")
        return False


# Convenience aliases
t = translate
nt = ngettext
