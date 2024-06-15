import os
import pytz

TZ = os.getenv('TZ', 'Etc/UTC')
timezone = pytz.timezone(TZ)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'your_discord_bot_token')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 'your_channel_id'))
UPDATE_DAYS = int(os.getenv('UPDATE_DAYS', 7))
IMG_FOLDER = os.getenv('IMG_FOLDER', 'img')
KEEP_DAYS = int(os.getenv('KEEP_DAYS', 7))
TIME_RANGE_DAYS = int(os.getenv('TIME_RANGE_DAYS', 30))
TAUTULLI_API_KEY = os.getenv('TAUTULLI_API_KEY', 'your_tautulli_api_key')
TAUTULLI_URL = os.getenv('TAUTULLI_URL', 'http://your_tautulli_ip:port/api/v2')