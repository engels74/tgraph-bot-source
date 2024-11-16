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
import logging

class TranslationError(Exception):
    """Base exception class for translation-related errors."""
    pass

class TranslationKeyError(TranslationError):
    """Raised when there are issues with translation keys."""
    pass

class TranslationFileError(TranslationError):
    """Raised when there are issues with translation files."""
    pass

class TranslationManager:
    """Manages loading and validation of translations."""
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
        """Get the translations directory path."""
        if self._translations_dir is None:
            current_dir = Path(__file__).parent
            self._translations_dir = current_dir / "i18n"
            
        if not self._translations_dir.exists():
            raise TranslationFileError(
                f"Translation directory not found. Expected at: {self._translations_dir}"
            )
            
        return self._translations_dir

    def _load_yaml_file(self, file_path: Path) -> Dict[str, str]:
        """Load and parse a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Dictionary containing the parsed YAML content
            
        Raises:
            TranslationFileError: If the file cannot be read or parsed
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = self._yaml.load(file)
                if not isinstance(content, dict):
                    raise TranslationFileError(
                        f"Invalid translation file format in {file_path}. Expected dictionary."
                    )
                return content
        except FileNotFoundError as e:
            raise TranslationFileError(f"Translation file not found: {file_path}") from e
        except YAMLError as e:
            raise TranslationFileError(f"Error parsing YAML in {file_path}: {str(e)}") from e
        except Exception as e:
            raise TranslationFileError(f"Unexpected error reading {file_path}: {str(e)}") from e

    def get_available_languages(self) -> List[str]:
        """Get a list of available language codes.
        
        Returns:
            List of available language codes
            
        Raises:
            TranslationFileError: If the translations directory cannot be accessed
        """
        try:
            return [
                f.stem for f in self.translations_dir.glob("*.yml")
                if f.is_file() and f.stem
            ]
        except Exception as e:
            raise TranslationFileError(f"Error scanning translation files: {str(e)}") from e

    def validate_translations(
        self,
        translations: Dict[str, str],
        language: str,
        reference_translations: Dict[str, str]
    ) -> None:
        """Validate translations against reference language.
        
        Args:
            translations: The translations to validate
            language: The language code being validated
            reference_translations: The reference translations to validate against
            
        Raises:
            TranslationKeyError: If translations are missing required keys
        """
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

    def load_translations(self, language: str) -> Dict[str, str]:
        """Load translations for the specified language.
        
        Args:
            language: The language code to load translations for
            
        Returns:
            Dictionary containing the translations
            
        Raises:
            TranslationError: If translations cannot be loaded or validated
        """
        try:
            with self._cache_lock:
                if language not in self._cached_translations:
                    translations = self._load_and_validate_translations(language)
                    self._cached_translations[language] = translations
                return self._cached_translations[language]
            
        except Exception as e:
            logging.error(f"Error loading translations for {language}: {str(e)}")
            raise TranslationError(f"Failed to load translations for {language}") from e

    def _load_and_validate_translations(self, language: str) -> Dict[str, str]:
        """Helper method to load and validate translations."""
        try:
            # Load reference translations first
            reference_file = self.translations_dir / f"{self.default_language}.yml"
            reference_translations = self._load_yaml_file(reference_file)

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
            translations = self._load_yaml_file(language_file)
            self._validate_translations(translations, language, reference_translations)
            
            return translations
            
        except Exception as e:
            if isinstance(e, TranslationError):
                raise
            raise TranslationError(f"Failed to load translations: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear the translations cache."""
        with self._cache_lock:
            self._cached_translations.clear()

    def update_bot_translations(self, bot, language: str) -> None:
        """Update bot's translations and command descriptions.
        
        Args:
            bot: The bot instance
            language: The language code to update to
            
        Raises:
            TranslationError: If the language is not available or translations fail
        """
        try:
            available_languages = self.get_available_languages()
            if language not in available_languages:
                raise TranslationError(
                    f"Language '{language}' not available. "
                    f"Available languages: {', '.join(sorted(available_languages))}"
                )

            # Load new translations
            bot.translations = self.load_translations(language)
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
def load_translations(language: str) -> Dict[str, str]:
    """Backwards-compatible function to load translations."""
    try:
        return translation_manager.load_translations(language)
    except Exception as e:
        raise TranslationError("Failed to load translations") from e

def get_available_languages() -> List[str]:
    """Backwards-compatible function to get available languages."""
    try:
        return translation_manager.get_available_languages()
    except Exception as e:
        raise TranslationError("Failed to get available languages") from e

def validate_translations(translations: Dict[str, str], reference_lang: str = "en") -> List[str]:
    """Backwards-compatible function to validate translations."""
    try:
        translation_manager.validate_translations(
            translations,
            "custom",
            translation_manager.load_translations(reference_lang)
        )
        return []
    except TranslationKeyError as e:
        return str(e).split("\n")[1:]  # Return just the error messages

def update_translations(bot, language: str) -> None:
    """Backwards-compatible function to update bot translations."""
    try:
        translation_manager.update_bot_translations(bot, language)
    except Exception as e:
        raise TranslationError("Failed to update translations") from e
