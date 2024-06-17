# main.py
import os
import logging
import argparse
import asyncio
import discord
from discord.ext import commands, tasks
from discord import File, Embed
from datetime import datetime
from config.config import load_config
from i18n import load_translations
from graphs.generate_graphs import update_and_post_graphs

# Parse command-line arguments
parser = argparse.ArgumentParser(description='TGraph Bot')
parser.add_argument('--config-file', type=str, default='config/config.yml', help='Path to the configuration file')
parser.add_argument('--log-file', type=str, default='logs/tgraphbot.log', help='Path to the log file')
args = parser.parse_args()

# Load configuration
config = load_config(args.config_file)

# Load translations
translations = load_translations(config['LANGUAGE'])

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

# Task to update graphs
@tasks.loop(seconds=config['UPDATE_DAYS']*24*60*60)  # Convert days to seconds
async def update_graphs_task():
    await update_and_post_graphs(bot)

@bot.event
async def on_ready():
    log(translations['log_bot_logged_in'].format(name=bot.user.name))
    update_graphs_task.start()

async def main():
    async with bot:
        await bot.load_extension('bot.commands')
        await bot.start(config['DISCORD_TOKEN'])

asyncio.run(main())

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
