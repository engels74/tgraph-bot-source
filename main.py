import os
import logging
import argparse
import discord
from discord.ext import commands, tasks
from discord import File, Embed
from datetime import datetime
from config.config import load_config
from graphs.generate_graphs import fetch_all_data, generate_graphs, ensure_folder_exists, cleanup_old_folders

# Parse command-line arguments
parser = argparse.ArgumentParser(description='TGraph Bot')
parser.add_argument('--config-file', type=str, default='config/config.yml', help='Path to the configuration file')
parser.add_argument('--log-file', type=str, default='logs/tgraphbot.log', help='Path to the log file')
args = parser.parse_args()

# Load configuration
config = load_config(args.config_file)

# Set up logging
log_directory = os.path.dirname(args.log_file)
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logging.basicConfig(
    filename=args.log_file,
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %Z'
)

logger = logging.getLogger(__name__)

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Function to print log messages with timestamps
def log(message):
    timestamp = datetime.now(config['timezone']).strftime('%Y-%m-%d %H:%M:%S %Z')
    logger.info(f"{timestamp} - {message}")
    print(f"{timestamp} - {message}")

# Post an embed to Discord with the graphs
async def post_graphs(channel):
    now = datetime.now(config['timezone']).strftime('%Y-%m-%d at %H:%M:%S')
    today = datetime.today().strftime('%Y-%m-%d')
    descriptions = {
        'daily_play_count.png': {
            'title': 'Daily Play Count by Media Type',
            'description': f'Displays the daily play count for different media types over the last {config["TIME_RANGE_DAYS"]} days.'
        },
        'play_count_by_dayofweek.png': {
            'title': 'Play Count by Day of Week',
            'description': f'Shows the play count distribution by day of the week for the last {config["TIME_RANGE_DAYS"]} days.'
        },
        'play_count_by_hourofday.png': {
            'title': 'Play Count by Hour of Day',
            'description': f'Illustrates the play count distribution by hour of the day over the last {config["TIME_RANGE_DAYS"]} days.'
        },
        'top_10_platforms.png': {
            'title': 'Play Count by Top 10 Platforms',
            'description': f'Highlights the play count for the top 10 platforms over the last {config["TIME_RANGE_DAYS"]} days.'
        },
        'top_10_users.png': {
            'title': 'Play Count by Top 10 Users',
            'description': f'Displays the play count for the top 10 users over the last {config["TIME_RANGE_DAYS"]} days.'
        },
        'play_count_by_month.png': {
            'title': 'Total Play Count by Month',
            'description': f'Shows the total play count by month for the last 12 months, excluding months with zero plays.'
        }
    }

    for filename, details in descriptions.items():
        file_path = os.path.join(config['IMG_FOLDER'], today, filename)
        embed = Embed(title=details['title'], description=details['description'], color=0x3498db)
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Posted on {now}")
        with open(file_path, 'rb') as f:
            await channel.send(file=File(f, filename), embed=embed)
            log(f"Posted {filename} to Discord")

# Delete the bot's messages from the channel
async def delete_bot_messages(channel):
    log("Detecting old messages")
    async for message in channel.history(limit=200):
        if message.author == bot.user:
            await message.delete()
            log("Deleted a message")

# Task to update graphs
@tasks.loop(seconds=config['UPDATE_DAYS']*24*60*60)  # Convert days to seconds
async def update_graphs():
    channel = bot.get_channel(config['CHANNEL_ID'])
    await delete_bot_messages(channel)

    ensure_folder_exists(config['IMG_FOLDER'])
    log("Ensured image folder exists")

    today = datetime.today().strftime('%Y-%m-%d')
    dated_folder = os.path.join(config['IMG_FOLDER'], today)
    ensure_folder_exists(dated_folder)
    log(f"Created dated folder: {dated_folder}")

    data = fetch_all_data()
    generate_graphs(data, dated_folder)
    log("Generated graphs")

    await post_graphs(channel)
    cleanup_old_folders(config['IMG_FOLDER'], config['KEEP_DAYS'])
    log("Cleaned up old folders")

@bot.event
async def on_ready():
    log(f'Logged in as {bot.user.name}')
    update_graphs.start()

# Run the bot
bot.run(config['DISCORD_TOKEN'])

# TGraph - Tautulli Graph Bot
# <https://github.com/engels74/tgraph-bot-source>
# This script/bot works by posting Tautulli graphs to Discord webhook 
# Copyright (C) 2024 - engels74
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Contact: engels74@marx.ps
