# config/modules/defaults.py

"""
Default configuration settings for TGraph Bot.
Provides functions for creating and managing default configuration values.
"""

from typing import Dict, Any
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

def create_default_config() -> CommentedMap:
    """
    Create a default configuration with standard values and structure.
    
    Returns:
        A CommentedMap containing the default configuration
        Using CommentedMap preserves comments and formatting in the YAML file
    """
    cfg = CommentedMap()
    
    # Basic settings
    cfg['TAUTULLI_API_KEY'] = 'your_tautulli_api_key'
    cfg['TAUTULLI_URL'] = 'http://your_tautulli_ip:port/api/v2'
    cfg['DISCORD_TOKEN'] = 'your_discord_bot_token'
    cfg['CHANNEL_ID'] = 'your_channel_id'
    cfg['UPDATE_DAYS'] = 7
    cfg['FIXED_UPDATE_TIME'] = DoubleQuotedScalarString('XX:XX')
    cfg['KEEP_DAYS'] = 7
    cfg['TIME_RANGE_DAYS'] = 30
    cfg['LANGUAGE'] = 'en'
    
    # Graph options
    cfg['CENSOR_USERNAMES'] = True
    cfg['ENABLE_DAILY_PLAY_COUNT'] = True
    cfg['ENABLE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ENABLE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ENABLE_TOP_10_PLATFORMS'] = True
    cfg['ENABLE_TOP_10_USERS'] = True
    cfg['ENABLE_PLAY_COUNT_BY_MONTH'] = True
    
    # Graph colors
    cfg['TV_COLOR'] = DoubleQuotedScalarString('#1f77b4')
    cfg['MOVIE_COLOR'] = DoubleQuotedScalarString('#ff7f0e')
    cfg['ANNOTATION_COLOR'] = DoubleQuotedScalarString('#ff0000')
    
    # Annotation options
    cfg['ANNOTATE_DAILY_PLAY_COUNT'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ANNOTATE_TOP_10_PLATFORMS'] = True
    cfg['ANNOTATE_TOP_10_USERS'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_MONTH'] = True
    
    # Command cooldown options
    cfg['CONFIG_COOLDOWN_MINUTES'] = 1  
    cfg['CONFIG_GLOBAL_COOLDOWN_SECONDS'] = 30 
    cfg['UPDATE_GRAPHS_COOLDOWN_MINUTES'] = 5  
    cfg['UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS'] = 60 
    cfg['MY_STATS_COOLDOWN_MINUTES'] = 5
    cfg['MY_STATS_GLOBAL_COOLDOWN_SECONDS'] = 60
    
    return cfg

def get_default_value(key: str) -> Any:
    """
    Get the default value for a specific configuration key.
    
    Args:
        key: The configuration key to get the default value for
        
    Returns:
        The default value for the specified key
        
    Raises:
        KeyError: If the key doesn't exist in the default configuration
    """
    defaults = create_default_config()
    if key not in defaults:
        raise KeyError(f"No default value found for configuration key: {key}")
    return defaults[key]

def get_section_defaults(section: str) -> Dict[str, Any]:
    """
    Get all default values for a specific configuration section.
    
    Args:
        section: The section name (e.g., 'basic', 'graph_options')
        
    Returns:
        Dictionary of default values for the specified section
        
    Raises:
        ValueError: If the section name is invalid
    """
    from .options import CONFIG_SECTIONS
    
    if section not in CONFIG_SECTIONS:
        raise ValueError(f"Invalid configuration section: {section}")
        
    defaults = create_default_config()
    section_keys = CONFIG_SECTIONS[section]['keys']
    return {key: defaults[key] for key in section_keys}

def is_default_value(key: str, value: Any) -> bool:
    """
    Check if a value matches the default value for a given key.
    
    Args:
        key: The configuration key
        value: The value to check
        
    Returns:
        True if the value matches the default, False otherwise
    """
    try:
        default = get_default_value(key)
        if isinstance(default, DoubleQuotedScalarString):
            return str(value).strip('"\'') == str(default).strip('"\'')
        return value == default
    except KeyError:
        return False

def reset_to_default(config: CommentedMap, key: str) -> None:
    """
    Reset a specific configuration value to its default.
    
    Args:
        config: The current configuration CommentedMap
        key: The key to reset
        
    Raises:
        KeyError: If the key doesn't exist in the default configuration
    """
    default_value = get_default_value(key)
    config[key] = default_value

def merge_with_defaults(user_config: Dict[str, Any]) -> CommentedMap:
    """
    Merge a user configuration with default values, ensuring all required settings exist.
    
    Args:
        user_config: The user's configuration dictionary
        
    Returns:
        A CommentedMap containing the merged configuration
    """
    defaults = create_default_config()
    
    # Start with defaults and update with user values
    merged = CommentedMap()
    for key, value in defaults.items():
        if key in user_config:
            merged[key] = user_config[key]
        else:
            merged[key] = value
            
    return merged
