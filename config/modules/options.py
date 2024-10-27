# config/modules/options.py

"""
Configuration options and metadata for TGraph Bot.
Defines available configuration keys, sections, and their properties.
"""

from typing import Dict, Any, List

# List of keys that can be configured via Discord commands
CONFIGURABLE_OPTIONS = [
    "LANGUAGE",
    "UPDATE_DAYS",
    "FIXED_UPDATE_TIME",
    "KEEP_DAYS",
    "TIME_RANGE_DAYS",
    "CENSOR_USERNAMES",
    "ENABLE_DAILY_PLAY_COUNT",
    "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
    "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
    "ENABLE_TOP_10_PLATFORMS",
    "ENABLE_TOP_10_USERS",
    "ENABLE_PLAY_COUNT_BY_MONTH",
    "ANNOTATE_DAILY_PLAY_COUNT",
    "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK",
    "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
    "ANNOTATE_TOP_10_PLATFORMS",
    "ANNOTATE_TOP_10_USERS",
    "ANNOTATE_PLAY_COUNT_BY_MONTH",
    "MY_STATS_COOLDOWN_MINUTES",
    "MY_STATS_GLOBAL_COOLDOWN_SECONDS",
    "CONFIG_COOLDOWN_MINUTES",             
    "CONFIG_GLOBAL_COOLDOWN_SECONDS",      
    "UPDATE_GRAPHS_COOLDOWN_MINUTES",      
    "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
    "TV_COLOR",
    "MOVIE_COLOR",
    "ANNOTATION_COLOR",
]

# Keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = [
    "TAUTULLI_API_KEY",
    "TAUTULLI_URL",
    "DISCORD_TOKEN"
]

# Configuration sections with their headers and keys
CONFIG_SECTIONS = {
    "basic": {
        "header": "# Basic settings",
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
        "header": "\n# Graph options",
        "keys": [
            "CENSOR_USERNAMES",
            "ENABLE_DAILY_PLAY_COUNT",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "ENABLE_TOP_10_PLATFORMS",
            "ENABLE_TOP_10_USERS",
            "ENABLE_PLAY_COUNT_BY_MONTH",
        ],
    },
    "graph_colors": {
        "header": "\n# Graph colors",
        "keys": [
            "TV_COLOR",
            "MOVIE_COLOR",
            "ANNOTATION_COLOR"
        ],
    },
    "annotation_options": {
        "header": "\n# Annotation options",
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
        "header": "\n# Command cooldown options",
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

# Configuration option metadata
OPTION_METADATA = {
    # Basic settings
    "TAUTULLI_API_KEY": {
        "type": str,
        "required": True,
        "description": "Tautulli API key for authentication",
    },
    "TAUTULLI_URL": {
        "type": str,
        "required": True,
        "description": "URL to your Tautulli instance API",
    },
    "DISCORD_TOKEN": {
        "type": str,
        "required": True,
        "description": "Discord bot token for authentication",
    },
    "CHANNEL_ID": {
        "type": str,
        "required": True,
        "description": "Discord channel ID for posting graphs",
    },
    "UPDATE_DAYS": {
        "type": int,
        "min": 1,
        "description": "Number of days between graph updates",
    },
    "FIXED_UPDATE_TIME": {
        "type": str,
        "format": "HH:MM",
        "description": "Fixed time for updates (24-hour format, or XX:XX to disable)",
    },
    "KEEP_DAYS": {
        "type": int,
        "min": 1,
        "description": "Number of days to keep old graph files",
    },
    "TIME_RANGE_DAYS": {
        "type": int,
        "min": 1,
        "description": "Number of days to include in graphs",
    },
    "LANGUAGE": {
        "type": str,
        "allowed_values": ["en", "da"],
        "description": "Interface language (en/da)",
    },
    
    # Graph options (all boolean)
    "CENSOR_USERNAMES": {
        "type": bool,
        "description": "Whether to censor usernames in graphs",
    },
    "ENABLE_DAILY_PLAY_COUNT": {
        "type": bool,
        "description": "Enable daily play count graph",
    },
    "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": {
        "type": bool,
        "description": "Enable play count by day of week graph",
    },
    "ENABLE_PLAY_COUNT_BY_HOUROFDAY": {
        "type": bool,
        "description": "Enable play count by hour of day graph",
    },
    "ENABLE_TOP_10_PLATFORMS": {
        "type": bool,
        "description": "Enable top 10 platforms graph",
    },
    "ENABLE_TOP_10_USERS": {
        "type": bool,
        "description": "Enable top 10 users graph",
    },
    "ENABLE_PLAY_COUNT_BY_MONTH": {
        "type": bool,
        "description": "Enable play count by month graph",
    },
    
    # Graph colors
    "TV_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for TV show data in graphs",
    },
    "MOVIE_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for movie data in graphs",
    },
    "ANNOTATION_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for annotations in graphs",
    },
    
    # Annotation options (all boolean)
    "ANNOTATE_DAILY_PLAY_COUNT": {
        "type": bool,
        "description": "Show value annotations on daily play count graph",
    },
    "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": {
        "type": bool,
        "description": "Show value annotations on day of week graph",
    },
    "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": {
        "type": bool,
        "description": "Show value annotations on hour of day graph",
    },
    "ANNOTATE_TOP_10_PLATFORMS": {
        "type": bool,
        "description": "Show value annotations on top 10 platforms graph",
    },
    "ANNOTATE_TOP_10_USERS": {
        "type": bool,
        "description": "Show value annotations on top 10 users graph",
    },
    "ANNOTATE_PLAY_COUNT_BY_MONTH": {
        "type": bool,
        "description": "Show value annotations on monthly play count graph",
    },
    
    # Cooldown options
    "CONFIG_COOLDOWN_MINUTES": {
        "type": int,
        "min": 1,
        "description": "Minutes between config command uses per user",
    },
    "CONFIG_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 1,
        "description": "Seconds between any config command uses",
    },
    "UPDATE_GRAPHS_COOLDOWN_MINUTES": {
        "type": int,
        "min": 1,
        "description": "Minutes between update_graphs command uses per user",
    },
    "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 1,
        "description": "Seconds between any update_graphs command uses",
    },
    
    "MY_STATS_COOLDOWN_MINUTES": {
        "type": int,
        "min": 1,
        "description": "Minutes between personal stats requests",
    },
    "MY_STATS_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 1,
        "description": "Seconds between any stats requests",
    },
}

def get_option_metadata(key: str) -> Dict[str, Any]:
    """
    Get metadata for a specific configuration option.
    
    Args:
        key: The configuration key
        
    Returns:
        Dictionary containing the option's metadata
        
    Raises:
        KeyError: If the key doesn't exist in the metadata
    """
    if key not in OPTION_METADATA:
        raise KeyError(f"No metadata found for configuration key: {key}")
    return OPTION_METADATA[key]

def get_section_keys(section: str) -> List[str]:
    """
    Get all configuration keys for a specific section.
    
    Args:
        section: The section name
        
    Returns:
        List of configuration keys in the section
        
    Raises:
        KeyError: If the section doesn't exist
    """
    if section not in CONFIG_SECTIONS:
        raise KeyError(f"Configuration section not found: {section}")
    return CONFIG_SECTIONS[section]["keys"]

def is_configurable(key: str) -> bool:
    """
    Check if a configuration option can be modified via Discord commands.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if the key is configurable via Discord, False otherwise
    """
    return key in CONFIGURABLE_OPTIONS

def requires_restart(key: str) -> bool:
    """
    Check if changing a configuration option requires a bot restart.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if changing the key requires a restart, False otherwise
    """
    return key in RESTART_REQUIRED_KEYS
