# config/config.py
import argparse
import logging
import os
import yaml
from datetime import datetime, time
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
config = None


def format_color_value(value):
    # Remove any existing quotes and spaces
    value = value.strip().strip("\"'")
    # Always wrap the value in double quotes
    return f'"{value}"'


def format_time_value(value):
    # Remove any existing quotes and spaces
    value = str(value).strip().strip("\"'")
    # Always wrap the value in double quotes
    return f'"{value}"'


def parse_time(value, translations):
    if not value:
        return None
    # Remove quotes if present
    value = value.strip("\"'")
    if value.upper() == "XX:XX":
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        logging.error(translations["error_invalid_fixed_time"].format(value=value))
        return None


def load_config(config_path=CONFIG_PATH, reload=False, translations=None):
    global config

    # Define default configuration in the same order as config.yml.sample
    default_config = {
        "TAUTULLI_API_KEY": "your_tautulli_api_key",
        "TAUTULLI_URL": "http://your_tautulli_ip:port/api/v2",
        "DISCORD_TOKEN": "your_discord_bot_token",
        "CHANNEL_ID": 0,
        "UPDATE_DAYS": 7,
        "FIXED_UPDATE_TIME": '"XX:XX"',
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
        "TV_COLOR": '"#1f77b4"',
        "MOVIE_COLOR": '"#ff7f0e"',
        "ANNOTATION_COLOR": '"#ff0000"',
        "ANNOTATE_DAILY_PLAY_COUNT": True,
        "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": True,
        "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": True,
        "ANNOTATE_TOP_10_PLATFORMS": True,
        "ANNOTATE_TOP_10_USERS": True,
        "ANNOTATE_PLAY_COUNT_BY_MONTH": True,
        "MY_STATS_COOLDOWN_MINUTES": 5,
        "MY_STATS_GLOBAL_COOLDOWN_SECONDS": 60,
    }

    # Load existing configuration first
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as file:
                config_vars = yaml.safe_load(file)
        except (IOError, yaml.YAMLError) as e:
            logging.error(f"Error loading configuration: {e}")
            config_vars = {}
    else:
        config_vars = {}

    # Now we can safely get the language
    language = config_vars.get("LANGUAGE", "en")

    if translations is None:
        translations = load_translations(language)

    if reload or config is None:
        # Update config_vars with any missing keys from default_config
        updated = False
        for key, value in default_config.items():
            if key not in config_vars:
                config_vars[key] = value
                updated = True

        # If the configuration was updated, save it back to the file
        if updated:
            save_config(config_vars, config_path, default_config)

        # Function to get the value from config.yml or environment variable
        def get_config(key, default=None):
            value = config_vars.get(key, os.getenv(key, default))
            if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
                return format_color_value(str(value))
            elif key == "FIXED_UPDATE_TIME":
                return parse_time(value, translations)
            return value

        # Build the final configuration dictionary
        config = {key: get_config(key, value) for key, value in default_config.items()}

    return config


def save_config(config, config_path=CONFIG_PATH, default_config=None):
    if default_config is None:
        default_config = config

    # Create a lookup for the order of keys in default_config
    default_order = {key: index for index, key in enumerate(default_config.keys())}

    if os.path.exists(config_path):
        with open(config_path, "r") as file:
            lines = file.readlines()

        # Create a dictionary to store the updated lines and their order
        updated_lines = {}
        existing_keys = []
        for line in lines:
            stripped_line = line.strip()
            if ":" in stripped_line and not stripped_line.startswith("#"):
                key = stripped_line.split(":", 1)[0].strip()
                existing_keys.append(key)
                if key in config:
                    value = config[key]
                    updated_lines[key] = format_value(key, value)
            else:
                # Preserve comments and empty lines
                existing_keys.append(line)
                updated_lines[line] = line

        # Add new keys from config that are not in the existing file
        new_keys = [
            key for key in default_config if key not in existing_keys and key in config
        ]

        # Find the correct position for new keys based on default_config order
        for new_key in new_keys:
            insert_index = len(existing_keys)
            for i, existing_key in enumerate(existing_keys):
                if (
                    existing_key in default_order
                    and default_order[new_key] < default_order[existing_key]
                ):
                    insert_index = i
                    break
            existing_keys.insert(insert_index, new_key)
            updated_lines[new_key] = format_value(new_key, config[new_key])

        # Write the updated config back to the file
        with open(config_path, "w") as file:
            for key in existing_keys:
                file.write(updated_lines[key])
                if not updated_lines[key].endswith("\n"):
                    file.write("\n")
    else:
        # If the file doesn't exist, create it with all config options
        with open(config_path, "w") as file:
            file.write("# config/config.yml\n")
            for key in default_config:
                if key in config:
                    file.write(format_value(key, config[key]))
                    file.write("\n")


def format_value(key, value):
    if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
        return f"{key}: {format_color_value(str(value))}"
    elif key == "FIXED_UPDATE_TIME":
        if isinstance(value, time):
            return f"{key}: {format_time_value(value.strftime('%H:%M'))}"
        elif value is None:
            return f'{key}: "XX:XX"'
        else:
            return f"{key}: {format_time_value(str(value))}"
    else:
        return f"{key}: {value}"


def update_config(key, value, translations):
    global config
    config = load_config(reload=True, translations=translations)

    if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
        value = format_color_value(str(value))
    elif key == "FIXED_UPDATE_TIME":
        if isinstance(value, str):
            if value.upper() == "XX:XX":
                value = None
            else:
                try:
                    value = datetime.strptime(value, "%H:%M").time()
                except ValueError:
                    logging.error(
                        translations["error_invalid_fixed_time"].format(value=value)
                    )
                    return config
        elif not isinstance(value, time) and value is not None:
            logging.error(translations["error_invalid_fixed_time"].format(value=value))
            return config

    config[key] = value
    save_config(config)
    return config


def sanitize_config_file():
    with open(CONFIG_PATH, "r") as file:
        lines = file.readlines()

    updated = False
    for i, line in enumerate(lines):
        if "COLOR:" in line or "FIXED_UPDATE_TIME:" in line:
            key, value = line.split(":", 1)
            if "COLOR" in key:
                formatted_value = format_color_value(value.strip())
            else:  # FIXED_UPDATE_TIME
                formatted_value = format_time_value(value.strip())
            if formatted_value != value.strip():
                lines[i] = f"{key}: {formatted_value}\n"
                updated = True

    if updated:
        with open(CONFIG_PATH, "w") as file:
            file.writelines(lines)

    return updated


# List of keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = ["TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN"]


# Function to get configurable options
def get_configurable_options():
    return CONFIGURABLE_OPTIONS
