# config/modules/constants.py

"""
Constant definitions for TGraph Bot configuration.
Defines the structure and organization of configuration options.
"""

from typing import Dict, List

# Configuration categories
CONFIG_CATEGORIES = {
    "BASIC_SETTINGS": "Basic settings",
    "GRAPH_OPTIONS": "Graph options",
    "GRAPH_COLORS": "Graph colors",
    "ANNOTATION_OPTIONS": "Annotation options",
    "COOLDOWN_OPTIONS": "Cooldown options"
}

# Configuration sections with their headers and keys
CONFIG_SECTIONS = {
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

def get_category_keys(category: str) -> List[str]:
    """
    Get all configuration keys belonging to a specific category.
    
    Args:
        category: The category name (e.g., 'BASIC_SETTINGS')
        
    Returns:
        List of configuration keys in that category
        
    Raises:
        KeyError: If the category doesn't exist
    """
    if category not in CONFIG_CATEGORIES:
        raise KeyError(f"Invalid category: {category}")
    
    keys = []
    for section in CONFIG_SECTIONS.values():
        if section["category"] == category:
            keys.extend(section["keys"])
    return keys

def get_key_category(key: str) -> str:
    """
    Get the category name for a given configuration key.
    
    Args:
        key: The configuration key
        
    Returns:
        The category name
        
    Raises:
        KeyError: If the key doesn't belong to any category
    """
    for section in CONFIG_SECTIONS.values():
        if key in section["keys"]:
            return section["category"]
    raise KeyError(f"Configuration key not found in any category: {key}")

def get_all_keys() -> Dict[str, List[str]]:
    """
    Get all configuration keys organized by category.
    
    Returns:
        Dictionary mapping category names to lists of keys
    """
    categorized_keys = {category: [] for category in CONFIG_CATEGORIES}
    for section in CONFIG_SECTIONS.values():
        categorized_keys[section["category"]].extend(section["keys"])
    return categorized_keys

def get_category_display_name(category: str) -> str:
    """
    Get the display name for a category.
    
    Args:
        category: The category name (e.g., 'BASIC_SETTINGS')
        
    Returns:
        The display name (e.g., 'Basic settings')
        
    Raises:
        KeyError: If the category doesn't exist
    """
    if category not in CONFIG_CATEGORIES:
        raise KeyError(f"Invalid category: {category}")
    return CONFIG_CATEGORIES[category]

# Export public interface
__all__ = [
    'CONFIG_CATEGORIES',
    'CONFIG_SECTIONS',
    'get_category_keys',
    'get_key_category',
    'get_all_keys',
    'get_category_display_name',
]
