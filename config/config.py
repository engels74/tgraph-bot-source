# config/config.py
import argparse
import logging
import os
from typing import Dict, Any, List, Union
from datetime import datetime, time
from ruamel.yaml import YAML
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
config: Dict[str, Any] = {}

def sanitize_color_value(value: str) -> str:
    """
    Sanitize color value to ensure proper format with single set of double quotes.
    
    :param value: The color value to sanitize
    :return: Properly formatted color value
    """
    # Strip any existing quotes and whitespace
    clean_value = value.strip().strip('"\'')
    
    # Ensure the value starts with #
    if not clean_value.startswith('#'):
        clean_value = f'#{clean_value}'
    
    # Return as DoubleQuotedScalarString for proper YAML formatting
    return DoubleQuotedScalarString(clean_value)

def sanitize_time_value(value: str) -> Union[str, DoubleQuotedScalarString]:
    """
    Sanitize time value to ensure proper format (HH:MM or XX:XX).
    
    :param value: The time value to sanitize
    :return: Properly formatted time value
    """
    # Strip any existing quotes and whitespace
    clean_value = value.strip().strip('"\'')
    
    # Handle disabled time (XX:XX)
    if clean_value.upper() == 'XX:XX':
        return DoubleQuotedScalarString('XX:XX')
    
    # Validate time format
    try:
        time_obj = datetime.strptime(clean_value, "%H:%M").time()
        return DoubleQuotedScalarString(time_obj.strftime("%H:%M"))
    except ValueError:
        logging.error(f"Invalid time format: {value}. Using 'XX:XX' as fallback.")
        return DoubleQuotedScalarString('XX:XX')

def load_config(config_path: str = CONFIG_PATH, reload: bool = False, translations: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Load and sanitize configuration from YAML file.
    
    :param config_path: Path to the configuration file
    :param reload: Whether to force reload the configuration
    :param translations: Translation dictionary
    :return: Sanitized configuration dictionary
    """
    global config

    if reload or not config:
        if translations is None:
            translations = load_translations("en")

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096  # Prevent line wrapping

        # Define default configuration with proper formatting
        default_config = {
            "TAUTULLI_API_KEY": "",
            "TAUTULLI_URL": "",
            "DISCORD_TOKEN": "",
            "CHANNEL_ID": 0,
            "UPDATE_DAYS": 7,
            "FIXED_UPDATE_TIME": DoubleQuotedScalarString("XX:XX"),
            "KEEP_DAYS": 7,
            "TIME_RANGE_DAYS": 30,
            "LANGUAGE": "en",
            "CENSOR_USERNAMES": True,
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": True,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_TOP_10_PLATFORMS": True,
            "ENABLE_TOP_10_USERS": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": True,
            "TV_COLOR": DoubleQuotedScalarString("#1f77b4"),
            "MOVIE_COLOR": DoubleQuotedScalarString("#ff7f0e"),
            "ANNOTATION_COLOR": DoubleQuotedScalarString("#ff0000"),
            "ANNOTATE_DAILY_PLAY_COUNT": True,
            "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": True,
            "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ANNOTATE_TOP_10_PLATFORMS": True,
            "ANNOTATE_TOP_10_USERS": True,
            "ANNOTATE_PLAY_COUNT_BY_MONTH": True,
            "MY_STATS_COOLDOWN_MINUTES": 5,
            "MY_STATS_GLOBAL_COOLDOWN_SECONDS": 60,
        }

        # Load existing config or create new one
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                user_config = yaml.load(file)
        else:
            user_config = {}

        # Merge configurations
        merged_config = default_config.copy()
        if user_config:
            for key, value in user_config.items():
                if key in merged_config:
                    merged_config[key] = value

        # Sanitize special values
        merged_config["FIXED_UPDATE_TIME"] = sanitize_time_value(str(merged_config["FIXED_UPDATE_TIME"]))
        for color_key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
            merged_config[color_key] = sanitize_color_value(str(merged_config[color_key]))

        config = merged_config
        save_config(config, config_path)

    return config

def save_config(config: Dict[str, Any], config_path: str = CONFIG_PATH) -> None:
    """
    Save configuration to YAML file while preserving formatting.
    
    :param config: Configuration dictionary to save
    :param config_path: Path to save the configuration file
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096  # Prevent line wrapping
    
    with open(config_path, 'w', encoding='utf-8') as file:
        yaml.dump(config, file)

def update_config(key: str, value: Any, translations: Dict[str, str]) -> str:
    """
    Update configuration value and save to file.
    
    :param key: Configuration key to update
    :param value: New value to set
    :param translations: Translation dictionary
    :return: Response message about the update
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
    
    :return: List of configuration keys that can be modified via Discord
    """
    return CONFIGURABLE_OPTIONS
