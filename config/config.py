# config/config.py
import os
import yaml
import pytz

# Load variables from config.yml file
config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
if os.path.exists(config_path):
    with open(config_path, 'r') as file:
        config_vars = yaml.safe_load(file)
else:
    config_vars = {}

# Function to get the value from config.yml or environment variable
def get_config(key, default=None):
    return config_vars.get(key, os.getenv(key, default))

TZ = get_config('TZ', 'Etc/UTC')
timezone = pytz.timezone(TZ)

DISCORD_TOKEN = get_config('DISCORD_TOKEN', 'your_discord_bot_token')
CHANNEL_ID = int(get_config('CHANNEL_ID', 'your_channel_id'))
UPDATE_DAYS = int(get_config('UPDATE_DAYS', 7))
IMG_FOLDER = get_config('IMG_FOLDER', 'img')
KEEP_DAYS = int(get_config('KEEP_DAYS', 7))
TIME_RANGE_DAYS = int(get_config('TIME_RANGE_DAYS', 30))
TAUTULLI_API_KEY = get_config('TAUTULLI_API_KEY', 'your_tautulli_api_key')
TAUTULLI_URL = get_config('TAUTULLI_URL', 'http://your_tautulli_ip:port/api/v2')