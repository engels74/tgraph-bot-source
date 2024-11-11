# config/modules/constants.py

"""
Constant definitions for TGraph Bot configuration.
Defines the structure and organization of configuration options with enhanced error handling.
"""

from typing import Dict, List, Set, Optional, Union
import logging

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
            error_msg = (translations or {}).get(
                'error_invalid_category',
                'Invalid category: {category}'
            ).format(category=category)
            logging.error(error_msg)
            raise CategoryError(error_msg)
            
    except Exception as e:
        if isinstance(e, CategoryError):
            raise
        error_msg = (translations or {}).get(
            'error_category_validation',
            'Error validating category {category}: {error}'
        ).format(category=category, error=str(e))
        logging.error(error_msg)
        raise CategoryError(error_msg) from e

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
                    error_msg = (translations or {}).get(
                        'error_invalid_section_keys',
                        'Invalid keys format in section'
                    )
                    raise KeyError(error_msg)
                keys.extend(section_keys)
        return keys
        
    except (CategoryError, KeyError):
        raise
    except Exception as e:
        error_msg = (translations or {}).get(
            'error_key_retrieval',
            'Error retrieving keys for category {category}: {error}'
        ).format(category=category, error=str(e))
        logging.error(error_msg)
        raise KeyError(error_msg) from e

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
                    error_msg = (translations or {}).get(
                        'error_invalid_category_type',
                        'Invalid category type for key {key}'
                    ).format(key=key)
                    raise KeyError(error_msg)
                return category
                
        error_msg = (translations or {}).get(
            'error_key_not_found',
            'Configuration key not found in any category: {key}'
        ).format(key=key)
        raise KeyError(error_msg)
        
    except Exception as e:
        if isinstance(e, KeyError):
            raise
        error_msg = (translations or {}).get(
            'error_category_lookup',
            'Error looking up category for key {key}: {error}'
        ).format(key=key, error=str(e))
        logging.error(error_msg)
        raise KeyError(error_msg) from e

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
            category: []
            for category in CONFIG_CATEGORIES
        }
        
        for section in CONFIG_SECTIONS.values():
            category = section["category"]
            if not isinstance(category, str) or category not in CONFIG_CATEGORIES:
                error_msg = (translations or {}).get(
                    'error_invalid_section_category',
                    'Invalid category in section: {category}'
                ).format(category=category)
                raise ValidationError(error_msg)
                
            section_keys = section.get("keys", [])
            if not isinstance(section_keys, list):
                error_msg = (translations or {}).get(
                    'error_invalid_keys_format',
                    'Invalid keys format in section with category {category}'
                ).format(category=category)
                raise ValidationError(error_msg)
                
            categorized_keys[category].extend(section_keys)
            
        return categorized_keys
        
    except ValidationError:
        raise
    except Exception as e:
        error_msg = (translations or {}).get(
            'error_key_organization',
            'Error organizing configuration keys: {error}'
        ).format(error=str(e))
        logging.error(error_msg)
        raise ValidationError(error_msg) from e

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
        error_msg = (translations or {}).get(
            'error_display_name',
            'Error getting display name for category {category}: {error}'
        ).format(category=category, error=str(e))
        logging.error(error_msg)
        raise CategoryError(error_msg) from e

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
                error_msg = (translations or {}).get(
                    'error_invalid_section_category',
                    'Invalid or missing category in section'
                )
                raise ValidationError(error_msg)
            used_categories.add(category)
            
        unused_categories = set(CONFIG_CATEGORIES.keys()) - used_categories
        if unused_categories:
            error_msg = (translations or {}).get(
                'error_unused_categories',
                'Unused categories found: {categories}'
            ).format(categories=unused_categories)
            logging.warning(error_msg)
            
        # Validate no key appears in multiple sections
        all_keys: Set[str] = set()
        duplicate_keys: Set[str] = set()
        
        for section in CONFIG_SECTIONS.values():
            section_keys = section.get("keys", [])
            if not isinstance(section_keys, list):
                error_msg = (translations or {}).get(
                    'error_invalid_keys_type',
                    'Invalid keys type in section'
                )
                raise ValidationError(error_msg)
                
            for key in section_keys:
                if key in all_keys:
                    duplicate_keys.add(key)
                all_keys.add(key)
                
        if duplicate_keys:
            error_msg = (translations or {}).get(
                'error_duplicate_keys',
                'Duplicate keys found in configuration: {keys}'
            ).format(keys=duplicate_keys)
            raise ValidationError(error_msg)
            
        logging.info("Configuration structure validation completed successfully")
        
    except ValidationError:
        raise
    except Exception as e:
        error_msg = (translations or {}).get(
            'error_structure_validation',
            'Error validating configuration structure: {error}'
        ).format(error=str(e))
        logging.error(error_msg)
        raise ValidationError(error_msg) from e

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
