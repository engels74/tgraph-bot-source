# config/config.py
import argparse
import logging
import os
from typing import Dict, Any, List
from datetime import datetime, time
from ruamel.yaml import YAML
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

# Global variable to store the configuration
config: Dict[str, Any] = {}

def format_color_value(value: str) -> str:
    return value.strip().strip('"\'')

def format_time_value(value: str) -> str:
    return value.strip().strip('"\'')

def parse_time(value: str, translations: Dict[str, str]) -> time:
    if not value or value.upper() == "XX:XX":
        return None
    try:
        return datetime.strptime(value.strip("\"'"), "%H:%M").time()
    except ValueError:
        logging.error(translations["error_invalid_fixed_time"].format(value=value))
        return None

def load_config(config_path: str = CONFIG_PATH, reload: bool = False, translations: Dict[str, str] = None) -> Dict[str, Any]:
    global config

    # Define default configuration
    default_config = {
        "TAUTULLI_API_KEY": "your_tautulli_api_key",
        "TAUTULLI_URL": "http://your_tautulli_ip:port/api/v2",
        "DISCORD_TOKEN": "your_discord_bot_token",
        "CHANNEL_ID": 0,
        "UPDATE_DAYS": 7,
        "FIXED_UPDATE_TIME": "XX:XX",
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
        "TV_COLOR": "#1f77b4",
        "MOVIE_COLOR": "#ff7f0e",
        "ANNOTATION_COLOR": "#ff0000",
        "ANNOTATE_DAILY_PLAY_COUNT": True,
        "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": True,
        "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": True,
        "ANNOTATE_TOP_10_PLATFORMS": True,
        "ANNOTATE_TOP_10_USERS": True,
        "ANNOTATE_PLAY_COUNT_BY_MONTH": True,
        "MY_STATS_COOLDOWN_MINUTES": 5,
        "MY_STATS_GLOBAL_COOLDOWN_SECONDS": 60,
    }

    if reload or not config:
        if translations is None:
            translations = load_translations(default_config["LANGUAGE"])

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)

        # Load existing config or use default
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                user_config = yaml.load(file)
        else:
            user_config = {}

        # Merge configurations
        merged_config = default_config.copy()
        merged_config.update(user_config)

        # Process special config values
        for key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
            merged_config[key] = format_color_value(str(merged_config[key]))
        
        if "FIXED_UPDATE_TIME" in merged_config:
            merged_config["FIXED_UPDATE_TIME"] = format_time_value(str(merged_config["FIXED_UPDATE_TIME"]))

        config = merged_config
        save_config(config, config_path)

    return config

def save_config(config: Dict[str, Any], config_path: str = CONFIG_PATH) -> None:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    
    with open(config_path, 'w') as file:
        yaml.dump(config, file)

def update_config(key: str, value: Any, translations: Dict[str, str]) -> str:
    global config
    config = load_config(reload=True, translations=translations)

    if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
        value = format_color_value(str(value))
    elif key == "FIXED_UPDATE_TIME":
        value = format_time_value(str(value))

    old_value = config.get(key, "N/A")
    config[key] = value
    save_config(config)

    if key == "FIXED_UPDATE_TIME":
        if value.upper() == "XX:XX":
            return translations["config_updated_fixed_time_disabled"].format(key=key)
        return translations["config_updated"].format(
            key=key, old_value=old_value, new_value=value
        )
    return translations["config_updated"].format(key=key, old_value=old_value, new_value=value)

def get_configurable_options() -> List[str]:
    return CONFIGURABLE_OPTIONS

# List of keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = ["TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN"]
