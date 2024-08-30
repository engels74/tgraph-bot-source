# config/config.py
import os
import yaml
import argparse

# Get the CONFIG_DIR from environment variable, default to current directory if not set
CONFIG_DIR = os.environ.get('CONFIG_DIR', os.getcwd())

# Get the config file path from command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--config-file', type=str, default=os.path.join(CONFIG_DIR, 'config.yml'), help='Path to the configuration file')
args, _ = parser.parse_known_args()

CONFIG_PATH = args.config_file

# Define the configuration options that should be configurable via Discord
CONFIGURABLE_OPTIONS = [
    'LANGUAGE', 'UPDATE_DAYS', 'KEEP_DAYS', 'TIME_RANGE_DAYS', 'CENSOR_USERNAMES',
    'ENABLE_DAILY_PLAY_COUNT', 'ENABLE_PLAY_COUNT_BY_DAYOFWEEK', 'ENABLE_PLAY_COUNT_BY_HOUROFDAY',
    'ENABLE_TOP_10_PLATFORMS', 'ENABLE_TOP_10_USERS', 'ENABLE_PLAY_COUNT_BY_MONTH',
    'ANNOTATE_DAILY_PLAY_COUNT', 'ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK', 'ANNOTATE_PLAY_COUNT_BY_HOUROFDAY',
    'ANNOTATE_TOP_10_PLATFORMS', 'ANNOTATE_TOP_10_USERS', 'ANNOTATE_PLAY_COUNT_BY_MONTH',
    'MY_STATS_COOLDOWN_MINUTES', 'MY_STATS_GLOBAL_COOLDOWN_SECONDS',
    'TV_COLOR', 'MOVIE_COLOR', 'ANNOTATION_COLOR'
]

# Global variable to store the configuration
config = None

def format_color_value(value):
    # Remove any existing quotes and spaces
    value = value.strip().strip('"\'')
    # Always wrap the value in double quotes
    return f'"{value}"'

def load_config(config_path=CONFIG_PATH, reload=False):
    global config
    if reload or config is None:
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                config_vars = yaml.safe_load(file)
        else:
            config_vars = {}

        # Function to get the value from config.yml or environment variable
        def get_config(key, default=None):
            value = config_vars.get(key, os.getenv(key, default))
            if key in ['TV_COLOR', 'MOVIE_COLOR']:
                return format_color_value(str(value))
            return value

        config = {
            'DISCORD_TOKEN': get_config('DISCORD_TOKEN', 'your_discord_bot_token'),
            'CHANNEL_ID': int(get_config('CHANNEL_ID', '0')),
            'UPDATE_DAYS': int(get_config('UPDATE_DAYS', 7)),
            'KEEP_DAYS': int(get_config('KEEP_DAYS', 7)),
            'TIME_RANGE_DAYS': int(get_config('TIME_RANGE_DAYS', 30)),
            'TAUTULLI_API_KEY': get_config('TAUTULLI_API_KEY', 'your_tautulli_api_key'),
            'TAUTULLI_URL': get_config('TAUTULLI_URL', 'http://your_tautulli_ip:port/api/v2'),
            'LANGUAGE': get_config('LANGUAGE', 'en'),
            'ENABLE_DAILY_PLAY_COUNT': bool(get_config('ENABLE_DAILY_PLAY_COUNT', True)),
            'ENABLE_PLAY_COUNT_BY_DAYOFWEEK': bool(get_config('ENABLE_PLAY_COUNT_BY_DAYOFWEEK', True)),
            'ENABLE_PLAY_COUNT_BY_HOUROFDAY': bool(get_config('ENABLE_PLAY_COUNT_BY_HOUROFDAY', True)),
            'ENABLE_TOP_10_PLATFORMS': bool(get_config('ENABLE_TOP_10_PLATFORMS', True)),
            'ENABLE_TOP_10_USERS': bool(get_config('ENABLE_TOP_10_USERS', True)),
            'ENABLE_PLAY_COUNT_BY_MONTH': bool(get_config('ENABLE_PLAY_COUNT_BY_MONTH', True)),
            'TV_COLOR': get_config('TV_COLOR', '#1f77b4'),
            'MOVIE_COLOR': get_config('MOVIE_COLOR', '#ff7f0e'),
            'ANNOTATION_COLOR': get_config('ANNOTATION_COLOR', '#ff0000'),
            'ANNOTATE_DAILY_PLAY_COUNT': bool(get_config('ANNOTATE_DAILY_PLAY_COUNT', True)),
            'ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK': bool(get_config('ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK', True)),
            'ANNOTATE_PLAY_COUNT_BY_HOUROFDAY': bool(get_config('ANNOTATE_PLAY_COUNT_BY_HOUROFDAY', True)),
            'ANNOTATE_TOP_10_PLATFORMS': bool(get_config('ANNOTATE_TOP_10_PLATFORMS', True)),
            'ANNOTATE_TOP_10_USERS': bool(get_config('ANNOTATE_TOP_10_USERS', True)),
            'ANNOTATE_PLAY_COUNT_BY_MONTH': bool(get_config('ANNOTATE_PLAY_COUNT_BY_MONTH', True)),
            'MY_STATS_COOLDOWN_MINUTES': int(get_config('MY_STATS_COOLDOWN_MINUTES', 5)),
            'MY_STATS_GLOBAL_COOLDOWN_SECONDS': int(get_config('MY_STATS_GLOBAL_COOLDOWN_SECONDS', 60)),
            'CENSOR_USERNAMES': bool(get_config('CENSOR_USERNAMES', True))
        }

    return config

def save_config(config, config_path=CONFIG_PATH):
    with open(config_path, 'r') as file:
        lines = file.readlines()

    # Update existing lines
    for i, line in enumerate(lines):
        if ':' in line:
            key, _ = line.split(':', 1)
            key = key.strip()
            if key in config:
                value = config[key]
                if key in ['TV_COLOR', 'MOVIE_COLOR']:
                    value = format_color_value(str(value))
                lines[i] = f"{key}: {value}\n"
                del config[key]

    # Append any new keys at the end
    for key, value in config.items():
        if key in ['TV_COLOR', 'MOVIE_COLOR']:
            value = format_color_value(str(value))
        lines.append(f"{key}: {value}\n")

    with open(config_path, 'w') as file:
        file.writelines(lines)

def update_config(key, value):
    global config
    config = load_config(reload=True)
    
    if key in ['TV_COLOR', 'MOVIE_COLOR', 'ANNOTATION_COLOR']:
        value = format_color_value(str(value))
    
    config[key] = value
    save_config(config)
    return config

def sanitize_config_file():
    with open(CONFIG_PATH, 'r') as file:
        lines = file.readlines()

    updated = False
    for i, line in enumerate(lines):
        if 'COLOR:' in line:
            key, value = line.split(':', 1)
            formatted_value = format_color_value(value.strip())
            if formatted_value != value.strip():
                lines[i] = f"{key}: {formatted_value}\n"
                updated = True

    if updated:
        with open(CONFIG_PATH, 'w') as file:
            file.writelines(lines)

    return updated

# List of keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = ['TAUTULLI_API_KEY', 'TAUTULLI_URL', 'DISCORD_TOKEN']

# Function to get configurable options
def get_configurable_options():
    return CONFIGURABLE_OPTIONS
