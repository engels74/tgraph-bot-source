# config/modules/defaults.py

"""
Default configuration settings for TGraph Bot.
Provides functions for creating and managing default configuration values.
"""

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from typing import Dict, Any, List, Set

def create_default_config() -> CommentedMap:
    """
    Create a default configuration with standard values and structure.
    
    Returns:
        A CommentedMap containing the default configuration
    """
    cfg = CommentedMap()
    
    # Basic settings with secure placeholders
    cfg['TAUTULLI_API_KEY'] = '<REQUIRED_TAUTULLI_API_KEY>'
    cfg['TAUTULLI_URL'] = '<REQUIRED_TAUTULLI_URL>'
    cfg['DISCORD_TOKEN'] = '<REQUIRED_DISCORD_TOKEN>'
    cfg['CHANNEL_ID'] = '<REQUIRED_CHANNEL_ID>'
    
    # Time-based settings
    cfg['KEEP_DAYS'] = 7
    cfg['UPDATE_DAYS'] = 7
    cfg['TIME_RANGE_DAYS'] = 30
    cfg['FIXED_UPDATE_TIME'] = DoubleQuotedScalarString('XX:XX')
    cfg['LANGUAGE'] = 'en'
    
    # Graph options
    cfg['CENSOR_USERNAMES'] = True
    cfg['ENABLE_DAILY_PLAY_COUNT'] = True
    cfg['ENABLE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ENABLE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ENABLE_TOP_10_PLATFORMS'] = True
    cfg['ENABLE_TOP_10_USERS'] = True
    cfg['ENABLE_PLAY_COUNT_BY_MONTH'] = True
    cfg['ENABLE_ANNOTATION_OUTLINE'] = True
    
    # Graph colors
    cfg['TV_COLOR'] = DoubleQuotedScalarString('#1f77b4')
    cfg['MOVIE_COLOR'] = DoubleQuotedScalarString('#ff7f0e')
    cfg['ANNOTATION_COLOR'] = DoubleQuotedScalarString('#ffffff')
    cfg['ANNOTATION_OUTLINE_COLOR'] = DoubleQuotedScalarString('#000000')
    
    # Annotation options
    cfg['ANNOTATE_DAILY_PLAY_COUNT'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ANNOTATE_TOP_10_PLATFORMS'] = True
    cfg['ANNOTATE_TOP_10_USERS'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_MONTH'] = True
    
    # Command cooldown options
    cfg['CONFIG_COOLDOWN_MINUTES'] = 0
    cfg['CONFIG_GLOBAL_COOLDOWN_SECONDS'] = 0
    cfg['UPDATE_GRAPHS_COOLDOWN_MINUTES'] = 0
    cfg['UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS'] = 0
    cfg['MY_STATS_COOLDOWN_MINUTES'] = 5
    cfg['MY_STATS_GLOBAL_COOLDOWN_SECONDS'] = 60
    
    return cfg

def merge_with_defaults(user_config: Dict[str, Any]) -> CommentedMap:
    """
    Merge a user configuration with default values, ensuring all required settings exist.
    
    Args:
        user_config: The user's configuration dictionary
        
    Returns:
        A CommentedMap containing the merged configuration
        
    Raises:
        ValueError: If user config contains invalid types
    """
    defaults = create_default_config()
    merged = CommentedMap()
    
    # Track unknown keys
    unknown_keys = set(user_config.keys()) - set(defaults.keys())
    if unknown_keys:
        import logging
        logging.warning(f"Unknown configuration keys: {unknown_keys}")
    
    # Merge user config with defaults
    for key, default_value in defaults.items():
        if key in user_config:
            user_value = user_config[key]
            
            # Type validation
            if not isinstance(user_value, type(default_value)):
                raise ValueError(
                    f"Invalid type for {key}: expected {type(default_value)}, "
                    f"got {type(user_value)}"
                )
            
            merged[key] = user_value
        else:
            merged[key] = default_value
            
    return merged

def is_cooldown_key(key: str) -> bool:
    """
    Check if a configuration key is related to cooldowns.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if the key is a cooldown setting, False otherwise
    """
    return key.endswith(('_COOLDOWN_MINUTES', '_COOLDOWN_SECONDS'))

def get_cooldown_keys() -> List[str]:
    """
    Get a list of all cooldown-related configuration keys.
    
    Returns:
        List of cooldown configuration keys
    """
    defaults = create_default_config()
    return [key for key in defaults.keys() if is_cooldown_key(key)]

def get_default_value(key: str) -> Any:
    """
    Get the default value for a specific configuration key.
    
    Args:
        key: The configuration key
        
    Returns:
        The default value for the key
        
    Raises:
        KeyError: If no default value exists for the key
    """
    defaults = create_default_config()
    if key not in defaults:
        raise KeyError(f"No default value found for configuration key: {key}")
    return defaults[key]

def get_required_keys() -> Set[str]:
    """
    Get a set of required configuration keys.
    
    Returns:
        Set of required configuration keys
    """
    return {
        'TAUTULLI_API_KEY',
        'TAUTULLI_URL',
        'DISCORD_TOKEN',
        'CHANNEL_ID'
    }
