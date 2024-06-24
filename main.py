# main.py
import os
import logging
import sys
import argparse
import asyncio
import discord
from discord.ext import commands
from config.config import load_config, CONFIG_PATH
from i18n import load_translations
from datetime import datetime
from graphs.generate_graphs import update_and_post_graphs
from graphs.generate_graphs_user import generate_user_graphs

# Parse command-line arguments
parser = argparse.ArgumentParser(description='TGraph Bot')
parser.add_argument('--config-file', type=str, default='config/config.yml', help='Path to the configuration file')
parser.add_argument('--log-file', type=str, default='logs/tgraphbot.log', help='Path to the log file')
parser.add_argument('--img-folder', type=str, default='img', help='Path to the image folder')
args = parser.parse_args()

# Load configuration
config = load_config(args.config_file, args.img_folder)

# Load translations
translations = load_translations(config['LANGUAGE'])

# Set up logging
def ensure_folders_exist(log_file, img_folder):
    log_directory = os.path.dirname(log_file)
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
        
    if not os.path.exists(img_folder):
        os.makedirs(img_folder)

ensure_folders_exist(args.log_file, args.img_folder)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(args.log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Function to print log messages with timestamps
def log(message, level=logging.INFO):
    timestamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    logger.log(level, message)

async def main():
    # Define intents
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        global translations
        log(translations['log_bot_logged_in'].format(name=bot.user.name))
        try:
            log(translations['log_loading_bot_commands'])
            await bot.load_extension('bot.commands')
            log(translations['log_bot_commands_loaded'])
            
            log(translations['log_syncing_application_commands'])
            await bot.tree.sync()
            log(translations['log_application_commands_synced'])
            
            # Update and post graphs immediately after logging in
            log(translations['log_updating_posting_graphs_startup'])
            await update_and_post_graphs(bot, translations)
            log(translations['log_graphs_updated_posted_startup'])
        except Exception as e:
            log(translations['log_error_during_startup'].format(error=str(e)))
            raise

    try:
        await bot.start(config['DISCORD_TOKEN'])
    except Exception as e:
        log(translations['log_error_starting_bot'].format(error=str(e)))

def update_translations(new_translations):
    global translations
    translations = new_translations
    # Update translations in other modules
    from graphs import generate_graphs
    generate_graphs.translations = new_translations
    from graphs import generate_graphs_user
    generate_graphs_user.translations = new_translations

if __name__ == "__main__":
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
