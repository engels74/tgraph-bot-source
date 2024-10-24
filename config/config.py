# config/config.py
import argparse
import logging
import os
from typing import Dict, Any, List, Union
from datetime import datetime, time
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from i18n import load_translations

# Get the CONFIG_DIR from environment variable, default to '/config' if not set
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")

# Get the config file path from command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    "--config-file",
    type=str,
    default=os.path.join(CONFIG_DIR, "config.yml"),
    help="Path to the configuration file",
)
args, _ = parser.parse_known_args()

CONFIG_PATH = args.config_file

# Define the configuration options that should be configurable via Discord
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
    "TV_COLOR",
    "MOVIE_COLOR",
    "ANNOTATION_COLOR",
]

# List of keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = ["TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN"]

# Global variable to store the configuration
config: CommentedMap = CommentedMap()

def sanitize_color_value(value: str) -> str:
    """
    Sanitize color value to ensure proper format with single set of double quotes.
    """
    clean_value = value.strip().strip('"\'')
    if not clean_value.startswith('#'):
        clean_value = f'#{clean_value}'
    return DoubleQuotedScalarString(clean_value)

def sanitize_time_value(value: str) -> Union[str, DoubleQuotedScalarString]:
    """
    Sanitize time value to ensure proper format (HH:MM or XX:XX).
    """
    clean_value = value.strip().strip('"\'')
    if clean_value.upper() == 'XX:XX':
        return DoubleQuotedScalarString('XX:XX')
    try:
        time_obj = datetime.strptime(clean_value, "%H:%M").time()
        return DoubleQuotedScalarString(time_obj.strftime("%H:%M"))
    except ValueError:
        logging.error(f"Invalid time format: {value}. Using 'XX:XX' as fallback.")
        return DoubleQuotedScalarString('XX:XX')

def create_default_config() -> CommentedMap:
    """
    Create a default configuration with comments and structure.
    """
    cfg = CommentedMap()
    
    # Basic settings with header comment
    cfg.yaml_set_start_comment('config/config.yml.sample\n')
    
    cfg['TAUTULLI_API_KEY'] = 'your_tautulli_api_key'
    cfg['TAUTULLI_URL'] = 'http://your_tautulli_ip:port/api/v2'
    cfg['DISCORD_TOKEN'] = 'your_discord_bot_token'
    cfg['CHANNEL_ID'] = 'your_channel_id'
    cfg['UPDATE_DAYS'] = 7
    cfg['FIXED_UPDATE_TIME'] = DoubleQuotedScalarString('XX:XX')
    cfg['KEEP_DAYS'] = 7
    cfg['TIME_RANGE_DAYS'] = 30
    cfg['LANGUAGE'] = 'en'

    # Add newline and comment before Graph options section
    cfg.yaml_set_comment_before_after_key(
        'CENSOR_USERNAMES', 
        before='\n# Graph options',
        after=None
    )
    cfg['CENSOR_USERNAMES'] = True
    cfg['ENABLE_DAILY_PLAY_COUNT'] = True
    cfg['ENABLE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ENABLE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ENABLE_TOP_10_PLATFORMS'] = True
    cfg['ENABLE_TOP_10_USERS'] = True
    cfg['ENABLE_PLAY_COUNT_BY_MONTH'] = True

    # Add newline and comment before Graph colors section
    cfg.yaml_set_comment_before_after_key(
        'TV_COLOR', 
        before='\n# Graph colors',
        after=None
    )
    cfg['TV_COLOR'] = DoubleQuotedScalarString('#1f77b4')
    cfg['MOVIE_COLOR'] = DoubleQuotedScalarString('#ff7f0e')
    cfg['ANNOTATION_COLOR'] = DoubleQuotedScalarString('#ff0000')

    # Add newline and comment before Annotation options section
    cfg.yaml_set_comment_before_after_key(
        'ANNOTATE_DAILY_PLAY_COUNT', 
        before='\n# Annotation options',
        after=None
    )
    cfg['ANNOTATE_DAILY_PLAY_COUNT'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_HOUROFDAY'] = True
    cfg['ANNOTATE_TOP_10_PLATFORMS'] = True
    cfg['ANNOTATE_TOP_10_USERS'] = True
    cfg['ANNOTATE_PLAY_COUNT_BY_MONTH'] = True

    # Add newline and comment before My Stats command options section
    cfg.yaml_set_comment_before_after_key(
        'MY_STATS_COOLDOWN_MINUTES', 
        before='\n# My Stats command options',
        after=None
    )
    cfg['MY_STATS_COOLDOWN_MINUTES'] = 5
    cfg['MY_STATS_GLOBAL_COOLDOWN_SECONDS'] = 60

    return cfg

def load_config(config_path: str = CONFIG_PATH, reload: bool = False, translations: Dict[str, str] = None) -> CommentedMap:
    """
    Load and sanitize configuration from YAML file.
    """
    global config

    if reload or not config:
        if translations is None:
            translations = load_translations("en")

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096  # Prevent line wrapping

        # Load existing config if it exists
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.load(file)
                
                # If loaded config is None or not a CommentedMap, create new one
                if config is None or not isinstance(config, CommentedMap):
                    config = create_default_config()
        else:
            config = create_default_config()

        # Sanitize special values while preserving the CommentedMap structure
        if isinstance(config, CommentedMap):
            config["FIXED_UPDATE_TIME"] = sanitize_time_value(str(config["FIXED_UPDATE_TIME"]))
            for color_key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
                if color_key in config:
                    config[color_key] = sanitize_color_value(str(config[color_key]))

        save_config(config, config_path)

    return config

def save_config(config: CommentedMap, config_path: str = CONFIG_PATH) -> None:
    """
    Save configuration to YAML file while preserving formatting.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # Prevent line wrapping
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(config, file)

def update_config(key: str, value: Any, translations: Dict[str, str]) -> str:
    """
    Update configuration value and save to file.
    """
    global config
    config = load_config(reload=True, translations=translations)
    
    old_value = config.get(key, "N/A")
    
    # Handle special cases
    if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
        value = sanitize_color_value(str(value))
    elif key == "FIXED_UPDATE_TIME":
        value = sanitize_time_value(str(value))
        if str(value).upper() == "XX:XX":
            config[key] = value
            save_config(config)
            return translations["config_updated_fixed_time_disabled"].format(key=key)
    
    config[key] = value
    save_config(config)
    
    return translations["config_updated"].format(
        key=key, old_value=old_value, new_value=value
    )

def get_configurable_options() -> List[str]:
    """
    Get list of configurable options.
    """
    return CONFIGURABLE_OPTIONS
