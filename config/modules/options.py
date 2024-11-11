# config/modules/options.py

"""
Configuration options and metadata for TGraph Bot.
Defines available configuration keys, sections, and their properties with enhanced error handling.
"""

from typing import Dict, Any, List, Optional, TypedDict, Union, Set
import logging

# Custom Exception Hierarchy
class OptionsError(Exception):
    """Base exception for configuration options errors."""
    pass

class MetadataError(OptionsError):
    """Raised when there are issues with option metadata."""
    pass

class ValidationError(OptionsError):
    """Raised when option validation fails."""
    pass

class OptionLookupError(OptionsError):
    """Raised when looking up non-existent options."""
    pass

# Type Definitions
class OptionMetadata(TypedDict, total=False):
    """TypedDict for option metadata structure."""
    type: type
    required: bool
    description: str
    min: Optional[Union[int, float]]
    max: Optional[Union[int, float]]
    format: Optional[str]
    examples: Optional[List[str]]
    normalize: Optional[bool]
    default: Optional[Any]
    allowed_values: Optional[List[str]]
    max_length: Optional[int]

# List of keys that can be configured via Discord commands
CONFIGURABLE_OPTIONS: Set[str] = {
    "UPDATE_DAYS",
    "FIXED_UPDATE_TIME",
    "KEEP_DAYS",
    "TIME_RANGE_DAYS",
    "LANGUAGE",
    "CENSOR_USERNAMES",
    "ENABLE_GRAPH_GRID",
    "ENABLE_DAILY_PLAY_COUNT",
    "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
    "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
    "ENABLE_TOP_10_PLATFORMS",
    "ENABLE_TOP_10_USERS",
    "ENABLE_PLAY_COUNT_BY_MONTH",
    "TV_COLOR",
    "MOVIE_COLOR",
    "GRAPH_BACKGROUND_COLOR",
    "ANNOTATION_COLOR",
    "ANNOTATION_OUTLINE_COLOR",
    "ENABLE_ANNOTATION_OUTLINE",
    "ANNOTATE_DAILY_PLAY_COUNT",
    "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK",
    "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY",
    "ANNOTATE_TOP_10_PLATFORMS",
    "ANNOTATE_TOP_10_USERS",
    "ANNOTATE_PLAY_COUNT_BY_MONTH",
    "CONFIG_COOLDOWN_MINUTES",
    "CONFIG_GLOBAL_COOLDOWN_SECONDS",
    "UPDATE_GRAPHS_COOLDOWN_MINUTES",
    "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
    "MY_STATS_COOLDOWN_MINUTES",
    "MY_STATS_GLOBAL_COOLDOWN_SECONDS",
}

# Keys that require a bot restart when changed
RESTART_REQUIRED_KEYS: Set[str] = {
    "TAUTULLI_API_KEY",
    "TAUTULLI_URL",
    "DISCORD_TOKEN",
    "CHANNEL_ID",
}

# Configuration option metadata with enhanced validation
OPTION_METADATA: Dict[str, OptionMetadata] = {
    # Basic settings
    "TAUTULLI_API_KEY": {
        "type": str,
        "required": True,
        "description": "Tautulli API key for authentication",
        "max_length": 64,
    },
    "TAUTULLI_URL": {
        "type": str,
        "required": True,
        "description": "URL to your Tautulli instance API",
        "max_length": 2048,
    },
    "DISCORD_TOKEN": {
        "type": str,
        "required": True,
        "description": "Discord bot token for authentication",
        "max_length": 100,
    },
    "CHANNEL_ID": {
        "type": int,
        "required": True,
        "description": "Discord channel ID for posting graphs",
    },
    "UPDATE_DAYS": {
        "type": int,
        "min": 1,
        "max": 365,
        "description": "Number of days between graph updates",
    },
    "FIXED_UPDATE_TIME": {
        "type": str,
        "format": "HH:MM",
        "description": "Fixed time for updates (24-hour format, or XX:XX to disable)",
        "examples": ["14:30", "XX:XX"],
    },
    "KEEP_DAYS": {
        "type": int,
        "min": 1,
        "max": 365,
        "description": "Number of days to keep old graph files",
    },
    "TIME_RANGE_DAYS": {
        "type": int,
        "min": 1,
        "max": 365,
        "description": "Number of days to include in graphs",
    },
    "LANGUAGE": {
        "type": str,
        "allowed_values": ["en", "da"],
        "description": "Interface language (en/da)",
    },

    # Graph options
    "CENSOR_USERNAMES": {
        "type": bool,
        "description": "Whether to censor usernames in graphs",
    },
    "ENABLE_GRAPH_GRID": {
        "type": bool,
        "description": "Enable grid lines in graphs",
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

    # Graph colors with enhanced validation
    "TV_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for TV show data in graphs (format: #RGB or #RRGGBB)",
        "examples": ["#ff0000", "#f00"],
        "normalize": True,
        "default": "#1f77b4",
    },
    "MOVIE_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for movie data in graphs (format: #RGB or #RRGGBB)",
        "examples": ["#00ff00", "#0f0"],
        "normalize": True,
        "default": "#ff7f0e",
    },
    "GRAPH_BACKGROUND_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Background color for graphs (format: #RGB or #RRGGBB)",
        "examples": ["#ffffff", "#fff"],
        "normalize": True,
        "default": "#ffffff",
    },
    "ANNOTATION_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for graph annotations (format: #RGB or #RRGGBB)",
        "examples": ["#ffffff", "#fff"],
        "normalize": True,
        "default": "#ffffff",
    },
    "ANNOTATION_OUTLINE_COLOR": {
        "type": str,
        "format": "hex",
        "description": "Color for annotation text outline (format: #RGB or #RRGGBB)",
        "examples": ["#000000", "#000"],
        "normalize": True,
        "default": "#000000",
    },

    # Annotation options
    "ENABLE_ANNOTATION_OUTLINE": {
        "type": bool,
        "description": "Enable outline around annotation text",
    },
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

    # Cooldown options with enhanced validation
    "CONFIG_COOLDOWN_MINUTES": {
        "type": int,
        "min": 0,
        "max": 1440,  # 24 hours
        "description": "Minutes between config command uses per user",
    },
    "CONFIG_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 0,
        "max": 3600,  # 1 hour
        "description": "Seconds between any config command uses",
    },
    "UPDATE_GRAPHS_COOLDOWN_MINUTES": {
        "type": int,
        "min": 0,
        "max": 1440,
        "description": "Minutes between update_graphs command uses per user",
    },
    "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 0,
        "max": 3600,
        "description": "Seconds between any update_graphs command uses",
    },
    "MY_STATS_COOLDOWN_MINUTES": {
        "type": int,
        "min": 0,
        "max": 1440,
        "description": "Minutes between personal stats requests",
    },
    "MY_STATS_GLOBAL_COOLDOWN_SECONDS": {
        "type": int,
        "min": 0,
        "max": 3600,
        "description": "Seconds between any stats requests",
    },
}

def get_option_metadata(key: str, translations: Optional[Dict[str, str]] = None) -> OptionMetadata:
    """
    Get metadata for a specific configuration option with enhanced error handling.
    
    Args:
        key: The configuration key
        translations: Optional translation dictionary for error messages
        
    Returns:
        Dictionary containing the option's metadata
        
    Raises:
        OptionLookupError: If the key doesn't exist in the metadata
        MetadataError: If there are issues accessing metadata
    """
    try:
        if key not in OPTION_METADATA:
            error_msg = (translations or {}).get(
                'error_invalid_option_key',
                'No metadata found for configuration key: {key}'
            ).format(key=key)
            logging.error(error_msg)
            raise OptionLookupError(error_msg)
            
        return OPTION_METADATA[key]
        
    except KeyError as e:
        error_msg = (translations or {}).get(
            'error_metadata_access',
            'Error accessing metadata for key {key}: {error}'
        ).format(key=key, error=str(e))
        logging.error(error_msg)
        raise MetadataError(error_msg) from e
    except Exception as e:
        error_msg = (translations or {}).get(
            'error_unexpected_metadata',
            'Unexpected error getting metadata for {key}: {error}'
        ).format(key=key, error=str(e))
        logging.error(error_msg)
        raise MetadataError(error_msg) from e

def validate_option_metadata() -> None:
    """
    Validate the consistency of option metadata definitions.
    
    Raises:
        MetadataError: If metadata validation fails
    """
    try:
        # Check all configurable options have metadata
        missing_metadata = CONFIGURABLE_OPTIONS - set(OPTION_METADATA.keys())
        if missing_metadata:
            raise MetadataError(f"Missing metadata for configurable options: {missing_metadata}")
            
        # Validate metadata structure
        for key, metadata in OPTION_METADATA.items():
            if "type" not in metadata:
                raise MetadataError(f"Missing required 'type' in metadata for {key}")
                
            if metadata.get("required", False) and "default" in metadata:
                raise MetadataError(
                    f"Required option {key} should not have a default value"
                )
                
            if "min" in metadata and "max" in metadata:
                if metadata["min"] > metadata["max"]:
                    raise MetadataError(
                        f"Invalid range for {key}: min ({metadata['min']}) > max ({metadata['max']})"
                    )
                    
        logging.info("Option metadata validation completed successfully")
        
    except MetadataError:
        raise
    except Exception as e:
        error_msg = f"Unexpected error validating option metadata: {str(e)}"
        logging.error(error_msg)
        raise MetadataError(error_msg) from e

# Export public interface
__all__ = [
    'CONFIGURABLE_OPTIONS',
    'RESTART_REQUIRED_KEYS',
    'OPTION_METADATA',
    'get_option_metadata',
    'validate_option_metadata',
    'OptionsError',
    'MetadataError',
    'ValidationError',
    'OptionLookupError',
]

# Validate metadata on module import
validate_option_metadata()
