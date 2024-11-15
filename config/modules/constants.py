# config/modules/constants.py

"""
Constant definitions for TGraph Bot configuration.
Defines the structure and organization of configuration options with enhanced error handling.
"""

from typing import Dict, List, Set, Optional, Union, NoReturn, TypeVar
import logging

# Type variable for generic exception types
E = TypeVar('E', bound=Exception)

# Custom Exception Hierarchy
class ConstantsError(Exception):
    """Base exception for configuration constants errors."""
    pass

class CategoryError(ConstantsError):
    """Raised when there are issues with configuration categories."""
    pass

class KeyError(ConstantsError):
    """Raised when there are issues with configuration keys."""
    pass

class ValidationError(ConstantsError):
    """Raised when configuration validation fails."""
    pass

# Configuration categories with display names
CONFIG_CATEGORIES: Dict[str, str] = {
    "BASIC_SETTINGS": "Basic settings",
    "GRAPH_OPTIONS": "Graph options",
    "GRAPH_COLORS": "Graph colors",
    "ANNOTATION_OPTIONS": "Annotation options",
    "COOLDOWN_OPTIONS": "Cooldown options"
}

# Configuration sections with their headers, categories, and keys
CONFIG_SECTIONS: Dict[str, Dict[str, Union[str, List[str]]]] = {
    "basic": {
        "header": "Basic settings",
        "category": "BASIC_SETTINGS",
        "keys": [
            "TAUTULLI_API_KEY",
            "TAUTULLI_URL",
            "DISCORD_TOKEN",
            "CHANNEL_ID",
            "UPDATE_DAYS",
            "FIXED_UPDATE_TIME",
            "KEEP_DAYS",
            "TIME_RANGE_DAYS",
            "LANGUAGE",
        ],
    },
    "graph_options": {
        "header": "Graph options",
        "category": "GRAPH_OPTIONS",
        "keys": [
            "CENSOR_USERNAMES",
            "ENABLE_GRAPH_GRID",
            "ENABLE_DAILY_PLAY_COUNT",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "ENABLE_TOP_10_PLATFORMS",
            "ENABLE_TOP_10_USERS",
            "ENABLE_PLAY_COUNT_BY_MONTH",
        ],
    },
    "graph_colors": {
        "header": "Graph colors",
        "category": "GRAPH_COLORS",
        "keys": [
            "TV_COLOR",
            "MOVIE_COLOR",
            "GRAPH_BACKGROUND_COLOR",
            "ANNOTATION_COLOR",
            "ANNOTATION_OUTLINE_COLOR",
            "ENABLE_ANNOTATION_OUTLINE",
        ],
    },
    "annotation_options": {
        "header": "Annotation options",
        "category": "ANNOTATION_OPTIONS",
        "keys": [
            "ANNOTATE_DAILY_PLAY_COUNT",
            "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK",
            "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
            "ANNOTATE_TOP_10_PLATFORMS",
            "ANNOTATE_TOP_10_USERS",
            "ANNOTATE_PLAY_COUNT_BY_MONTH",
        ],
    },
    "cooldown_options": {
        "header": "Command cooldown options",
        "category": "COOLDOWN_OPTIONS",
        "keys": [
            "CONFIG_COOLDOWN_MINUTES",
            "CONFIG_GLOBAL_COOLDOWN_SECONDS",
            "UPDATE_GRAPHS_COOLDOWN_MINUTES",
            "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
            "MY_STATS_COOLDOWN_MINUTES",
            "MY_STATS_GLOBAL_COOLDOWN_SECONDS",
        ],
    },
}

def handle_error(
    error: E,
    translation_key: str,
    fallback_msg: str,
    translations: Optional[Dict[str, str]] = None,
    error_class: Optional[type[E]] = None,
    **format_args
) -> NoReturn:
    """
    Helper function to handle errors with translations.
    
    Args:
        error: The original exception
        translation_key: Key for translation lookup
        fallback_msg: Default message if translation not found
        translations: Optional translations dictionary
        error_class: Optional specific error class to raise
        **format_args: Format arguments for the error message
        
    Raises:
        The specified error class or the original error's class
    """
    error_msg = (translations or {}).get(
        translation_key,
        fallback_msg
    ).format(error=str(error), **format_args)
    
    logging.error(error_msg)
    raise (error_class or type(error))(error_msg) from error

def log_with_translation(
    level: int,
    translation_key: str,
    fallback_msg: str,
    translations: Optional[Dict[str, str]] = None,
    **format_args
) -> None:
    """
    Helper function for logging with translations.
    
    Args:
        level: Logging level
        translation_key: Key for translation lookup
        fallback_msg: Default message if translation not found
        translations: Optional translations dictionary
        **format_args: Format arguments for the message
    """
    msg = (translations or {}).get(
        translation_key,
        fallback_msg
    ).format(**format_args)
    logging.log(level, msg)

def validate_category(category: str, translations: Optional[Dict[str, str]] = None) -> None:
    """
    Validate a category exists and is properly defined.
    
    Args:
        category: The category to validate
        translations: Optional translation dictionary
        
    Raises:
        CategoryError: If category validation fails
    """
    try:
        if category not in CONFIG_CATEGORIES:
            raise CategoryError(f"Invalid category: {category}")
    except Exception as e:
        handle_error(
            e,
            'error_invalid_category',
            'Invalid category: {category}',
            translations,
            CategoryError,
            category=category
        )

def get_category_keys(category: str, translations: Optional[Dict[str, str]] = None) -> List[str]:
    """
    Get all configuration keys belonging to a specific category.
    
    Args:
        category: The category name (e.g., 'BASIC_SETTINGS')
        translations: Optional translation dictionary
        
    Returns:
        List of configuration keys in that category
        
    Raises:
        CategoryError: If the category doesn't exist
        KeyError: If there are issues with key retrieval
    """
    try:
        validate_category(category, translations)
        
        keys: List[str] = []
        for section in CONFIG_SECTIONS.values():
            if section["category"] == category:
                section_keys = section.get("keys", [])
                if not isinstance(section_keys, list):
                    raise KeyError("Invalid keys format in section")
                keys.extend(section_keys)
        return keys
        
    except (CategoryError, KeyError) as e:
        handle_error(
            e,
            'error_key_retrieval',
            'Error retrieving keys for category {category}: {error}',
            translations,
            KeyError if isinstance(e, KeyError) else None,
            category=category
        )
    except Exception as e:
        handle_error(
            e,
            'error_unexpected',
            'Unexpected error retrieving keys for {category}: {error}',
            translations,
            KeyError,
            category=category
        )

def get_key_category(key: str, translations: Optional[Dict[str, str]] = None) -> str:
    """
    Get the category name for a given configuration key.
    
    Args:
        key: The configuration key
        translations: Optional translation dictionary
        
    Returns:
        The category name
        
    Raises:
        KeyError: If the key doesn't belong to any category
    """
    try:
        for section in CONFIG_SECTIONS.values():
            if key in section.get("keys", []):
                category = section["category"]
                if not isinstance(category, str):
                    raise KeyError("Invalid category type")
                return category
                
        raise KeyError(f"Configuration key not found in any category: {key}")
        
    except Exception as e:
        handle_error(
            e,
            'error_category_lookup',
            'Error looking up category for key {key}: {error}',
            translations,
            KeyError,
            key=key
        )

def get_all_keys(translations: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    """
    Get all configuration keys organized by category.
    
    Args:
        translations: Optional translation dictionary
        
    Returns:
        Dictionary mapping category names to lists of keys
        
    Raises:
        ValidationError: If key organization fails
    """
    try:
        categorized_keys: Dict[str, List[str]] = {
            category: [] for category in CONFIG_CATEGORIES
        }
        
        for section in CONFIG_SECTIONS.values():
            category = section["category"]
            if not isinstance(category, str) or category not in CONFIG_CATEGORIES:
                raise ValidationError(f"Invalid category in section: {category}")
                
            section_keys = section.get("keys", [])
            if not isinstance(section_keys, list):
                raise ValidationError(f"Invalid keys format in section with category {category}")
                
            categorized_keys[category].extend(section_keys)
            
        # Log any unused categories
        unused_categories = {
            cat for cat, keys in categorized_keys.items() if not keys
        }
        if unused_categories:
            log_with_translation(
                logging.WARNING,
                'warning_unused_categories',
                'Unused categories found: {categories}',
                translations,
                categories=unused_categories
            )
            
        return categorized_keys
        
    except ValidationError:
        raise
    except Exception as e:
        handle_error(
            e,
            'error_key_organization',
            'Error organizing configuration keys: {error}',
            translations,
            ValidationError
        )

def get_category_display_name(category: str, translations: Optional[Dict[str, str]] = None) -> str:
    """
    Get the display name for a category.
    
    Args:
        category: The category name (e.g., 'BASIC_SETTINGS')
        translations: Optional translation dictionary
        
    Returns:
        The display name (e.g., 'Basic settings')
        
    Raises:
        CategoryError: If the category doesn't exist
    """
    try:
        validate_category(category, translations)
        return CONFIG_CATEGORIES[category]
    except CategoryError:
        raise
    except Exception as e:
        handle_error(
            e,
            'error_display_name',
            'Error getting display name for category {category}: {error}',
            translations,
            CategoryError,
            category=category
        )

def validate_config_structure(translations: Optional[Dict[str, str]] = None) -> None:
    """
    Validate the entire configuration structure for consistency.
    
    Args:
        translations: Optional translation dictionary
        
    Raises:
        ValidationError: If structure validation fails
    """
    try:
        # Check all categories are referenced
        used_categories: Set[str] = set()
        for section in CONFIG_SECTIONS.values():
            category = section.get("category")
            if not isinstance(category, str):
                raise ValidationError("Invalid or missing category in section")
            used_categories.add(category)
            
        # Log unused categories
        unused_categories = set(CONFIG_CATEGORIES.keys()) - used_categories
        if unused_categories:
            log_with_translation(
                logging.WARNING,
                'warning_unused_categories',
                'Unused categories found: {categories}',
                translations,
                categories=unused_categories
            )
            
        # Validate no key appears in multiple sections
        all_keys: Set[str] = set()
        duplicate_keys: Set[str] = set()
        
        for section in CONFIG_SECTIONS.values():
            section_keys = section.get("keys", [])
            if not isinstance(section_keys, list):
                raise ValidationError("Invalid keys type in section")
                
            for key in section_keys:
                if key in all_keys:
                    duplicate_keys.add(key)
                all_keys.add(key)
                
        if duplicate_keys:
            raise ValidationError(f"Duplicate keys found in configuration: {duplicate_keys}")
            
        log_with_translation(
            logging.INFO,
            'info_structure_validated',
            'Configuration structure validation completed successfully',
            translations
        )
        
    except ValidationError:
        raise
    except Exception as e:
        handle_error(
            e,
            'error_structure_validation',
            'Error validating configuration structure: {error}',
            translations,
            ValidationError
        )

# Export public interface
__all__ = [
    'CONFIG_CATEGORIES',
    'CONFIG_SECTIONS',
    'get_category_keys',
    'get_key_category',
    'get_all_keys',
    'get_category_display_name',
    'validate_config_structure',
    'ConstantsError',
    'CategoryError',
    'KeyError',
    'ValidationError',
]

# Validate configuration structure on module import
validate_config_structure()
