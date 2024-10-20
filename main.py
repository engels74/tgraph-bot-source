# main.py
import argparse
import asyncio
import discord
import logging
import os
import sys
from aiohttp import ClientConnectorError, ServerDisconnectedError
from bot.permission_checker import check_permissions_all_guilds
from bot.update_tracker import create_update_tracker
from config.config import load_config, sanitize_config_file
from datetime import datetime
from discord.ext import commands
from graphs.generate_graphs import update_and_post_graphs
from i18n import load_translations

# Get the CONFIG_DIR from environment variable, default to '/config' if not set
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")

# Parse command-line arguments
parser = argparse.ArgumentParser(description="TGraph Bot")
parser.add_argument(
    "--config-file",
    type=str,
    default=os.path.join(CONFIG_DIR, "config.yml"),
    help="Path to the configuration file",
)
parser.add_argument(
    "--log-file",
    type=str,
    default=os.path.join(CONFIG_DIR, "logs", "tgraphbot.log"),
    help="Path to the log file",
)
parser.add_argument(
    "--data-folder",
    type=str,
    default=os.path.join(CONFIG_DIR, "data"),
    help="Path to the data folder",
)
args = parser.parse_args()

# Sanitize the config file
if sanitize_config_file():
    print("Config file was updated with properly formatted color values.")

# Load configuration
config = load_config(args.config_file)

# Load translations
translations = load_translations(config["LANGUAGE"])

# Set up img_folder
img_folder = os.path.join(args.data_folder, "img")


# Function to create necessary folders
def create_folders(log_file, data_folder, img_folder):
    for folder in [os.path.dirname(log_file), data_folder, img_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)


# Create necessary folders
create_folders(args.log_file, args.data_folder, img_folder)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(args.log_file), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# Function to print log messages with timestamps
def log(message, level=logging.INFO):
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    logger.log(level, f"{timestamp} - {message}")


# Log that folders have been created
log(translations["log_ensured_folders_exist"])

# Create UpdateTracker instance
update_tracker = create_update_tracker(args.data_folder, config, translations)


class TGraphBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_folder = kwargs.pop("data_folder", None)
        self.img_folder = kwargs.pop("img_folder", None)
        self.update_tracker = kwargs.pop("update_tracker", None)
        self.config = kwargs.pop("config", None)
        self.translations = kwargs.pop("translations", None)

    async def on_error(self, event_method, *args, **kwargs):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if isinstance(exc_value, (ClientConnectorError, ServerDisconnectedError)):
            log(
                self.translations["log_connection_issue"].format(error=str(exc_value)),
                level=logging.WARNING,
            )
        else:
            log(
                self.translations["log_error_in_event"].format(
                    event=event_method, error=str(exc_value)
                ),
                level=logging.ERROR,
            )

    async def on_connect(self):
        log(self.translations["log_bot_connected"])

    async def on_disconnect(self):
        log(self.translations["log_bot_disconnected"], level=logging.WARNING)

    async def on_resume(self):
        log(self.translations["log_bot_resumed"])


async def main():
    # Define intents
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True

    bot = TGraphBot(
        command_prefix="!",
        intents=intents,
        data_folder=args.data_folder,
        img_folder=img_folder,
        update_tracker=update_tracker,
        config=config,
        translations=translations,
    )

    @bot.event
    async def on_ready():
        log(bot.translations["log_bot_logged_in"].format(name=bot.user.name))
        try:
            log(bot.translations["log_loading_bot_commands"])
            await bot.load_extension("bot.commands")
            log(bot.translations["log_bot_commands_loaded"])

            log(bot.translations["log_syncing_application_commands"])
            await bot.tree.sync()
            log(bot.translations["log_application_commands_synced"])

            # Delay the permission check
            log(bot.translations["log_waiting_before_permission_check"])
            await asyncio.sleep(5)

            # Check command permissions
            log(bot.translations["log_checking_command_permissions"])
            await check_permissions_all_guilds(bot, bot.translations)
            log(bot.translations["log_command_permissions_checked"])

            # Update and post graphs immediately after logging in
            log(bot.translations["log_updating_posting_graphs_startup"])
            log(bot.translations["log_manual_update_started"])
            bot.config = load_config(
                args.config_file, reload=True
            )  # Reload config here
            await update_and_post_graphs(bot, bot.translations, bot.config)

            # Update the tracker's last_update time and calculate next_update
            bot.update_tracker.last_update = datetime.now()
            bot.update_tracker.next_update = bot.update_tracker.calculate_next_update(
                bot.update_tracker.last_update
            )

            # Save the tracker once after both operations
            bot.update_tracker.save_tracker()

            next_update_log = bot.update_tracker.get_next_update_readable()
            log(bot.translations["log_manual_update_completed"])
            log(
                bot.translations["log_graphs_updated_posted"].format(
                    next_update=next_update_log
                )
            )

            # Schedule regular updates
            bot.loop.create_task(schedule_updates(bot))
        except Exception as e:
            log(bot.translations["log_error_during_startup"].format(error=str(e)))
            raise

    try:
        await bot.start(config["DISCORD_TOKEN"])
    except Exception as e:
        log(bot.translations["log_error_starting_bot"].format(error=str(e)))


async def schedule_updates(bot):
    last_status = False
    last_next_update = None

    while True:
        current_status = bot.update_tracker.is_update_due()
        current_next_update = bot.update_tracker.next_update

        # Log if status changed from not due to due
        if current_status and not last_status:
            logging.info(
                bot.translations["log_update_now_due"].format(
                    current_time=datetime.now()
                )
            )

        # Log if next update time changed
        if current_next_update != last_next_update:
            logging.info(
                bot.translations["log_next_update_changed"].format(
                    next_update=current_next_update
                )
            )

        if current_status:
            logging.info(bot.translations["log_auto_update_started"])
            bot.config = load_config(args.config_file, reload=True)
            await update_and_post_graphs(bot, bot.translations, bot.config)
            bot.update_tracker.update()
            next_update_log = bot.update_tracker.get_next_update_readable()
            logging.info(
                bot.translations["log_auto_update_completed"].format(
                    next_update=next_update_log
                )
            )

        last_status = current_status
        last_next_update = current_next_update

        await asyncio.sleep(60)


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
# Contact: engels74@tuta.io
