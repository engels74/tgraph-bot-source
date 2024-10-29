# i18n.py
import os
import logging
from typing import Dict, List
from ruamel.yaml import YAML

class TranslationKeyError(Exception):
    pass

def load_translations(language: str) -> Dict[str, str]:
    """
    Load translations for the specified language.
    
    :param language: The language code to load translations for
    :return: A dictionary of translations
    :raises TranslationKeyError: If the language file is not found or if there are missing keys
    """
    # Get the directory of the current script (i18n.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to the language file in the i18n subfolder
    file_path = os.path.join(current_dir, "i18n", f"{language}.yml")
    reference_path = os.path.join(current_dir, "i18n", "en.yml")

    yaml = YAML(typ='safe')
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            translations = yaml.load(file)
        
        with open(reference_path, "r", encoding="utf-8") as file:
            reference_translations = yaml.load(file)
        
        # Check for missing keys
        missing_keys = set(reference_translations.keys()) - set(translations.keys())
        if missing_keys:
            raise TranslationKeyError(f"Missing translation keys in {language}.yml: {', '.join(missing_keys)}")
        
        logging.info(f"Loaded translations for language: {language}")
        return translations
    except FileNotFoundError:
        raise TranslationKeyError(f"Translation file for {language} not found. Looked in: {file_path}")
    except yaml.YAMLError as e:
        raise TranslationKeyError(f"Error parsing YAML in {file_path}: {str(e)}")

def get_available_languages() -> List[str]:
    """
    Get a list of available language codes.
    
    :return: A list of available language codes
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    i18n_dir = os.path.join(current_dir, "i18n")
    return [f.split(".")[0] for f in os.listdir(i18n_dir) if f.endswith(".yml")]

def validate_translations(translations: Dict[str, str], reference_lang: str = "en") -> List[str]:
    """
    Validate the completeness of translations against a reference language.
    
    :param translations: The translations to validate
    :param reference_lang: The reference language to compare against (default: "en")
    :return: A list of missing translation keys
    """
    reference_translations = load_translations(reference_lang)
    missing_keys = []
    
    for key in reference_translations:
        if key not in translations:
            missing_keys.append(key)
    
    return missing_keys

def update_translations(bot, language: str) -> None:
    """
    Update bot's translations and command descriptions.
    
    :param bot: The bot instance
    :param language: The language code to update to
    """
    bot.translations = load_translations(language)
    
    # Update command descriptions
    for command in bot.tree.walk_commands():
        translation_key = f"{command.name}_command_description"
        if translation_key in bot.translations:
            command.description = bot.translations[translation_key]
    
    logging.info(f"Updated bot translations and command descriptions to language: {language}")
