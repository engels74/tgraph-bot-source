# i18n.py

"""
Internationalization support for TGraph Bot.
Handles loading and management of translations with proper error handling.
"""

from config.modules.sanitizer import sanitize_language_code, ValidationError
from pathlib import Path
from ruamel.yaml import YAML, YAMLError
from threading import Lock
from typing import Dict, List, Optional
import aiofiles
import asyncio
import logging

class TranslationError(Exception):
    """Base exception for translation-related errors."""
    pass

class TranslationKeyError(TranslationError):
    """Raised when there are issues with translation keys."""
    pass

class TranslationFileError(TranslationError):
    """Raised when there are issues with translation files."""
    pass

class TranslationManager:
    """Manages loading and validation of translations.
    
    This class implements a singleton pattern to handle translation operations,
    including loading, caching, and validating language files.

    Attributes:
        default_language (str): The fallback language code (defaults to "en")
        _translations_dir (Path): Path to the translations directory
        _cached_translations (Dict[str, Dict[str, str]]): Cache of loaded translations
    """
    _instance = None
    _translations: Dict[str, str] = {}
    _lock = Lock()
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self._translations_dir: Optional[Path] = None
        self._yaml = YAML(typ='safe')
        self._cached_translations: Dict[str, Dict[str, str]] = {}
        self._cache_lock = Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def get_translation(cls, key: str) -> str:
        """Get a translation string by key.
        
        Args:
            key: The translation key to retrieve
            
        Returns:
            The translation string, or the key if not found
        """
        with cls._lock:
            return cls._translations.get(key, key)

    @classmethod
    def set_translations(cls, translations: Dict[str, str]) -> None:
        """Set the translations dictionary.
        
        Args:
            translations: Dictionary of translation strings
        """
        with cls._lock:
            cls._translations = translations
        
    @property
    def translations_dir(self) -> Path:
        """Get the translations directory path.
        
        Returns:
            Path: The path to the translations directory

        Raises:
            TranslationFileError: If the translations directory doesn't exist
        """
        if self._translations_dir is None:
            current_dir = Path(__file__).parent
            self._translations_dir = current_dir / "i18n"
            
        if not self._translations_dir.exists():
            raise TranslationFileError(
                f"Translation directory not found. Expected at: {self._translations_dir}"
            )
            
        return self._translations_dir

    async def _load_yaml_file(self, file_path: Path) -> Dict[str, str]:
        """Load and parse a YAML file asynchronously."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
                content = await file.read()
                parsed_content = self._yaml.load(content)
                if not isinstance(parsed_content, dict):
                    raise TranslationFileError(
                        f"Invalid translation file format in {file_path}. Expected dictionary."
                    )
                return parsed_content
        except FileNotFoundError as e:
            raise TranslationFileError(f"Translation file not found: {file_path}") from e
        except YAMLError as e:
            raise TranslationFileError(f"Error parsing YAML in {file_path}: {str(e)}") from e
        except Exception as e:
            raise TranslationFileError(f"Unexpected error reading {file_path}: {str(e)}") from e

    async def get_available_languages(self) -> List[str]:
        """Get a list of available language codes asynchronously."""
        try:
            return [
                f.stem for f in self.translations_dir.glob("*.yml")
                if f.is_file() and f.stem
            ]
        except Exception as e:
            raise TranslationFileError(f"Error scanning translation files: {str(e)}") from e

    def _validate_translations(
        self,
        translations: Dict[str, str],
        language: str,
        reference_translations: Dict[str, str]
    ) -> None:
        """Validate translations against reference language."""
        try:
            missing_keys = set(reference_translations.keys()) - set(translations.keys())
            extra_keys = set(translations.keys()) - set(reference_translations.keys())
            
            errors = []
            
            if missing_keys:
                errors.append(f"Missing translation keys: {', '.join(sorted(missing_keys))}")
                
            if extra_keys:
                errors.append(f"Extra translation keys: {', '.join(sorted(extra_keys))}")
                
            if errors:
                raise TranslationKeyError(
                    f"Translation validation failed for {language}.yml:\n" +
                    "\n".join(errors)
                )
        except Exception as e:
            raise TranslationKeyError(
                f"Error validating translations for {language}: {str(e)}"
            ) from e

    async def load_translations(self, language: str) -> Dict[str, str]:
        """Load translations for the specified language asynchronously.
        
        Args:
            language (str): The language code to load translations for

        Returns:
            Dict[str, str]: Dictionary of translation strings

        Raises:
            TranslationError: If translations cannot be loaded
        """
        try:
            async with asyncio.Lock():  # Use asyncio.Lock for async operations
                if language in self._cached_translations:
                    return self._cached_translations[language]
                    
                translations = await self._load_and_validate_translations(language)
                if not translations:
                    # Fallback to default language if translations failed to load
                    translations = await self._load_and_validate_translations(self.default_language)
                    logging.warning(f"Failed to load translations for {language}, using {self.default_language}")
                    
                self._cached_translations[language] = translations
                return translations
            
        except Exception as e:
            logging.error(f"Error loading translations for {language}: {str(e)}")
            # Load default language as fallback
            try:
                return await self._load_and_validate_translations(self.default_language)
            except Exception as fallback_error:
                logging.error(f"Failed to load fallback translations: {str(fallback_error)}")
                raise TranslationError(f"Failed to load translations") from e

    async def _load_and_validate_translations(self, language: str) -> Dict[str, str]:
        """Helper method to load and validate translations asynchronously.
        
        Args:
            language (str): The language code to load and validate

        Returns:
            Dict[str, str]: Dictionary of validated translation strings

        Raises:
            TranslationError: If translations cannot be loaded or validated
            ValidationError: If the language code is invalid
        """
        try:
            # Load reference translations first
            reference_file = self.translations_dir / f"{self.default_language}.yml"
            reference_translations = await self._load_yaml_file(reference_file)

            # If loading default language, no validation needed
            if language == self.default_language:
                return reference_translations

            # Sanitize language code
            try:
                safe_language = sanitize_language_code(language)
            except ValidationError as e:
                raise TranslationError(f"Invalid language code: {str(e)}") from e

            # Load and validate requested language
            language_file = self.translations_dir / f"{safe_language}.yml"
            translations = await self._load_yaml_file(language_file)
            self._validate_translations(translations, language, reference_translations)
            
            return translations
            
        except Exception as e:
            if isinstance(e, TranslationError):
                raise
            raise TranslationError(f"Failed to load translations: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear the translations cache.
        
        Removes all cached translations, forcing them to be reloaded
        on next access.
        """
        with self._cache_lock:
            self._cached_translations.clear()

    async def update_bot_translations(self, bot, language: str) -> None:
        """Update bot's translations and command descriptions asynchronously.
        
        Args:
            bot: The bot instance to update translations for
            language (str): The language code to update to

        Raises:
            TranslationError: If translations cannot be updated or language is not available
        """
        try:
            available_languages = await self.get_available_languages()
            if language not in available_languages:
                raise TranslationError(
                    f"Language '{language}' not available. "
                    f"Available languages: {', '.join(sorted(available_languages))}"
                )

            # Load new translations
            bot.translations = await self.load_translations(language)
            TranslationManager.set_translations(bot.translations)
            
            # Update command descriptions
            for command in bot.tree.walk_commands():
                translation_key = f"{command.name}_command_description"
                try:
                    command.description = bot.translations[translation_key]
                except KeyError:
                    logging.warning(f"Missing translation for command description: {translation_key}")
                    # Keep existing description as fallback
            
            logging.info(f"Updated bot translations and command descriptions to language: {language}")
            
        except Exception as e:
            raise TranslationError(
                f"Failed to update bot translations to {language}"
            ) from e

# Create a global instance for convenience
translation_manager = TranslationManager()

# Backwards compatibility functions
async def load_translations(language: str) -> Dict[str, str]:
    """Load translations for the specified language.
    
    This is a backwards-compatible wrapper around TranslationManager.load_translations.

    Args:
        language (str): The language code to load translations for

    Returns:
        Dict[str, str]: Dictionary of translation strings

    Raises:
        TranslationError: If translations cannot be loaded
    """
    try:
        return await translation_manager.load_translations(language)
    except Exception as e:
        raise TranslationError("Failed to load translations") from e

async def get_available_languages() -> List[str]:
    """Backwards-compatible async function to get available languages."""
    try:
        return await translation_manager.get_available_languages()
    except Exception as e:
        raise TranslationError("Failed to get available languages") from e

async def validate_translations(translations: Dict[str, str], reference_lang: str = "en") -> List[str]:
    """Validate translations against a reference language.
    
    Args:
        translations (Dict[str, str]): The translations to validate
        reference_lang (str, optional): The reference language code. Defaults to "en"

    Returns:
        List[str]: List of validation error messages, empty if validation succeeds
    """
    try:
        reference_translations = await translation_manager.load_translations(reference_lang)
        translation_manager._validate_translations(
            translations,
            "custom",
            reference_translations
        )
        return []
    except TranslationKeyError as e:
        return str(e).split("\n")[1:]  # Return just the error messages

async def update_translations(bot, language: str) -> None:
    """Update bot translations and command descriptions.
    
    This is a backwards-compatible wrapper around TranslationManager.update_bot_translations.

    Args:
        bot: The bot instance to update translations for
        language (str): The language code to update to

    Raises:
        TranslationError: If translations cannot be updated
    """
    try:
        await translation_manager.update_bot_translations(bot, language)
    except Exception as e:
        raise TranslationError("Failed to update translations") from e
