# config/modules/options.py

"""
Configuration options and metadata for TGraph Bot.
Defines available configuration keys, sections, and their properties.
"""

from typing import Dict, Any, List

# List of keys that can be configured via Discord commands
CONFIGURABLE_OPTIONS = [
    "BASIC_SETTINGS",
    "GRAPH_OPTIONS",
    "GRAPH_COLORS",
    "ANNOTATION_OPTIONS",
    "COOLDOWN_OPTIONS",
]

# Keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = [
    "TAUTULLI_API_KEY",
    "TAUTULLI_URL",
    "DISCORD_TOKEN",
    "CHANNEL_ID",
]

# Configuration option metadata
OPTION_METADATA = {
    # Basic settings
    "BASIC_SETTINGS": {
        "type": dict,
        "description": "Basic configuration settings for TGraph Bot",
        "keys": {
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
                "type": int,
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
                "description": "Fixed time for updates (24-hour format, or None to disable)",
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
        },
    },
    
    # Graph options
    "GRAPH_OPTIONS": {
        "type": dict,
        "description": "Options related to graph generation",
        "keys": {
            "CENSOR_USERNAMES": {
                "type": bool,
                "description": "Whether to censor usernames in graphs",
            },
            "ENABLE_GRAPHS": {
                "type": dict,
                "description": "Enable or disable specific graphs",
                "keys": {
                    "DAILY_PLAY_COUNT": {
                        "type": bool,
                        "description": "Enable daily play count graph",
                    },
                    "PLAY_COUNT_BY_DAYOFWEEK": {
                        "type": bool,
                        "description": "Enable play count by day of week graph",
                    },
                    "PLAY_COUNT_BY_HOUROFDAY": {
                        "type": bool,
                        "description": "Enable play count by hour of day graph",
                    },
                    "TOP_10_PLATFORMS": {
                        "type": bool,
                        "description": "Enable top 10 platforms graph",
                    },
                    "TOP_10_USERS": {
                        "type": bool,
                        "description": "Enable top 10 users graph",
                    },
                    "PLAY_COUNT_BY_MONTH": {
                        "type": bool,
                        "description": "Enable play count by month graph",
                    },
                },
            },
        },
    },
    
    # Graph colors
    "GRAPH_COLORS": {
        "type": dict,
        "description": "Color settings for graphs",
        "keys": {
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
                "description": "Color for graph annotations (default: white)",
            },
        },
    },
    
    # Annotation options
    "ANNOTATION_OPTIONS": {
        "type": dict,
        "description": "Options related to graph annotations",
        "keys": {
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
            "ENABLE_ANNOTATION_OUTLINE": {
                "type": bool,
                "description": "Enable outline around annotation text for better visibility",
            },
            "ANNOTATION_OUTLINE_COLOR": {
                "type": str,
                "format": "hex",
                "description": "Color for annotation text outline (default: black)",
            },
        },
    },
    
    # Cooldown options
    "COOLDOWN_OPTIONS": {
        "type": dict,
        "description": "Cooldown settings for various commands",
        "keys": {
            "CONFIG_COOLDOWN_MINUTES": {
                "type": int,
                "min": 0,
                "description": "Minutes between config command uses per user (0 to disable)",
            },
            "CONFIG_GLOBAL_COOLDOWN_SECONDS": {
                "type": int,
                "min": 0,
                "description": "Seconds between any config command uses (0 to disable)",
            },
            "UPDATE_GRAPHS_COOLDOWN_MINUTES": {
                "type": int,
                "min": 0,
                "description": "Minutes between update_graphs command uses per user (0 to disable)",
            },
            "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS": {
                "type": int,
                "min": 0,
                "description": "Seconds between any update_graphs command uses (0 to disable)",
            },
            "MY_STATS_COOLDOWN_MINUTES": {
                "type": int,
                "min": 0,
                "description": "Minutes between personal stats requests (0 to disable)",
            },
            "MY_STATS_GLOBAL_COOLDOWN_SECONDS": {
                "type": int,
                "min": 0,
                "description": "Seconds between any stats requests (0 to disable)",
            },
        },
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
    # Since we have nested dictionaries, we need to search recursively
    def recursive_search(metadata: Dict[str, Any], target_key: str) -> Any:
        if 'keys' in metadata:
            for k, v in metadata['keys'].items():
                if k == target_key:
                    return v
                elif isinstance(v, dict):
                    result = recursive_search(v, target_key)
                    if result:
                        return result
        return None
    
    result = recursive_search(OPTION_METADATA, key)
    if result:
        return result
    else:
        raise KeyError(f"No metadata found for configuration key: {key}")

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
    section_lower = section.lower()
    for sec in OPTION_METADATA:
        if sec.lower() == section_lower:
            if 'keys' in OPTION_METADATA[sec]:
                return list(OPTION_METADATA[sec]['keys'].keys())
            else:
                return []
    raise KeyError(f"Configuration section not found: {section}")

def is_configurable(key: str) -> bool:
    """
    Check if a configuration option can be modified via Discord commands.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if the key is configurable via Discord, False otherwise
    """
    # Since we have nested configurations, we need to search recursively
    def recursive_search(options: List[str], target_key: str) -> bool:
        for option in options:
            if option == target_key:
                return True
            elif isinstance(option, dict):
                if recursive_search(option.keys(), target_key):
                    return True
        return False
    
    return recursive_search(CONFIGURABLE_OPTIONS, key)

def requires_restart(key: str) -> bool:
    """
    Check if changing a configuration option requires a bot restart.
    
    Args:
        key: The configuration key to check
        
    Returns:
        True if changing the key requires a restart, False otherwise
    """
    return key in RESTART_REQUIRED_KEYS
