# config/config.py
import os
import yaml
import pytz

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yml')

def load_config(config_path=CONFIG_PATH):
    if os.path.exists(config_path):
        with open(config_path, 'r') as file:
            config_vars = yaml.safe_load(file)
    else:
        config_vars = {}

    # Function to get the value from config.yml or environment variable
    def get_config(key, default=None):
        return config_vars.get(key, os.getenv(key, default))

    config = {
        'TZ': get_config('TZ', 'Etc/UTC'),
        'DISCORD_TOKEN': get_config('DISCORD_TOKEN', 'your_discord_bot_token'),
        'CHANNEL_ID': int(get_config('CHANNEL_ID', 'your_channel_id')),
        'UPDATE_DAYS': int(get_config('UPDATE_DAYS', 7)),
        'IMG_FOLDER': get_config('IMG_FOLDER', 'img'),
        'KEEP_DAYS': int(get_config('KEEP_DAYS', 7)),
        'TIME_RANGE_DAYS': int(get_config('TIME_RANGE_DAYS', 30)),
        'TAUTULLI_API_KEY': get_config('TAUTULLI_API_KEY', 'your_tautulli_api_key'),
        'TAUTULLI_URL': get_config('TAUTULLI_URL', 'http://your_tautulli_ip:port/api/v2'),
        'LANGUAGE': get_config('LANGUAGE', 'en'),
        'DAILY_PLAY_COUNT': bool(get_config('DAILY_PLAY_COUNT', True)),
        'PLAY_COUNT_BY_DAYOFWEEK': bool(get_config('PLAY_COUNT_BY_DAYOFWEEK', True)),
        'PLAY_COUNT_BY_HOUROFDAY': bool(get_config('PLAY_COUNT_BY_HOUROFDAY', True)),
        'TOP_10_PLATFORMS': bool(get_config('TOP_10_PLATFORMS', True)),
        'TOP_10_USERS': bool(get_config('TOP_10_USERS', True)),
        'PLAY_COUNT_BY_MONTH': bool(get_config('PLAY_COUNT_BY_MONTH', True)),
        'ANNOTATE_DAILY_PLAY_COUNT': bool(get_config('ANNOTATE_DAILY_PLAY_COUNT', True)),
        'ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK': bool(get_config('ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK', True)),
        'ANNOTATE_PLAY_COUNT_BY_HOUROFDAY': bool(get_config('ANNOTATE_PLAY_COUNT_BY_HOUROFDAY', True)),
        'ANNOTATE_TOP_10_PLATFORMS': bool(get_config('ANNOTATE_TOP_10_PLATFORMS', True)),
        'ANNOTATE_TOP_10_USERS': bool(get_config('ANNOTATE_TOP_10_USERS', True)),
        'ANNOTATE_PLAY_COUNT_BY_MONTH': bool(get_config('ANNOTATE_PLAY_COUNT_BY_MONTH', True))
    }

    config['timezone'] = pytz.timezone(config['TZ'])

    return config

def save_config(config, config_path=CONFIG_PATH):
    # Remove 'timezone' key as it's not part of the original config
    config_to_save = {k: v for k, v in config.items() if k != 'timezone'}
    
    with open(config_path, 'w') as file:
        yaml.dump(config_to_save, file)

def update_config(key, value):
    config = load_config()
    config[key] = value
    save_config(config)
    return config

# List of keys that require a bot restart when changed
RESTART_REQUIRED_KEYS = ['TAUTULLI_API_KEY', 'TAUTULLI_URL', 'DISCORD_TOKEN', 'IMG_FOLDER']
