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
from config.config import load_config
from datetime import datetime
from discord.ext import commands
from graphs.graph_manager import GraphManager
from graphs.user_graph_manager import UserGraphManager
from i18n import load_translations, TranslationKeyError

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

# Function to create necessary folders
def create_folders(log_file, data_folder, img_folder):
    for folder in [os.path.dirname(log_file), data_folder, img_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

# Create img_folder path
IMG_FOLDER = os.path.join(args.data_folder, "img")

# Create necessary folders before setting up logging
create_folders(args.log_file, args.data_folder, IMG_FOLDER)

# Set up logging - using a simpler, more robust configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(args.log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def log(message, level=logging.INFO):
    logger.log(level, message)

# Load configuration
try:
    config = load_config(args.config_file)
except Exception as e:
    log(f"Failed to load configuration: {e}", logging.ERROR)
    sys.exit(1)

# Load translations
try:
    translations = load_translations(config["LANGUAGE"])
except TranslationKeyError as e:
    log(f"Error loading translations: {e}", logging.ERROR)
    sys.exit(1)

# Log that folders have been created
log(translations["log_ensured_folders_exist"])

# Create UpdateTracker instance
update_tracker = create_update_tracker(args.data_folder, config, translations)

class TGraphBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_folder = kwargs.pop("data_folder", None)
        self.img_folder = os.path.join(self.data_folder, "img")
        self.update_tracker = kwargs.pop("update_tracker", None)
        self.config = kwargs.pop("config", None)
        self.translations = kwargs.pop("translations", None)
        self.graph_manager = GraphManager(self.config, self.translations, self.img_folder)
        self.user_graph_manager = UserGraphManager(self.config, self.translations, self.img_folder)
        log(self.translations["log_tgraphbot_initialized"])

    async def on_error(self, event_method, *args, **kwargs):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if isinstance(exc_value, (ClientConnectorError, ServerDisconnectedError)):
            log(
                self.translations["log_connection_issue"].format(error=str(exc_value)),
                logging.WARNING,
            )
        else:
            log(
                self.translations["log_error_in_event"].format(
                    event=event_method, error=str(exc_value)
                ),
                logging.ERROR,
            )

    async def on_connect(self):
        log(self.translations["log_bot_connected"])

    async def on_disconnect(self):
        log(self.translations["log_bot_disconnected"], logging.WARNING)

    async def on_resume(self):
        log(self.translations["log_bot_resumed"])

async def main():
    log(translations["log_entering_main_function"])
    # Define intents
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True

    bot = TGraphBot(
        command_prefix="!",
        intents=intents,
        data_folder=args.data_folder,
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

            log(bot.translations["log_waiting_before_permission_check"])
            await asyncio.sleep(5)

            log(bot.translations["log_checking_command_permissions"])
            await check_permissions_all_guilds(bot, bot.translations)
            log(bot.translations["log_command_permissions_checked"])

            log(bot.translations["log_updating_posting_graphs_startup"])
            bot.config = load_config(args.config_file, reload=True)
            
            channel = bot.get_channel(bot.config["CHANNEL_ID"])
            if channel:
                await bot.graph_manager.delete_old_messages(channel)
                graph_files = await bot.graph_manager.generate_and_save_graphs()
                if graph_files:
                    await bot.graph_manager.post_graphs(channel, graph_files)
            else:
                log(bot.translations["log_channel_not_found"].format(
                    channel_id=bot.config["CHANNEL_ID"]
                ), logging.ERROR)

            bot.update_tracker.last_update = datetime.now()
            bot.update_tracker.next_update = bot.update_tracker.calculate_next_update(
                bot.update_tracker.last_update
            )
            bot.update_tracker.save_tracker()

            next_update_log = bot.update_tracker.get_next_update_readable()
            log(bot.translations["log_graphs_updated_posted"].format(
                next_update=next_update_log
            ))

            bot.loop.create_task(schedule_updates(bot))
        except Exception as e:
            log(bot.translations["log_error_during_startup"].format(error=str(e)), 
                logging.ERROR)
            raise

    try:
        await bot.start(config["DISCORD_TOKEN"])
    except Exception as e:
        log(bot.translations["log_error_starting_bot"].format(error=str(e)), 
            logging.ERROR)

async def schedule_updates(bot):
    while True:
        if bot.update_tracker.is_update_due():
            log(bot.translations["log_auto_update_started"])
            bot.config = load_config(args.config_file, reload=True)
            
            channel = bot.get_channel(bot.config["CHANNEL_ID"])
            if channel:
                await bot.graph_manager.delete_old_messages(channel)
                graph_files = await bot.graph_manager.generate_and_save_graphs()
                if graph_files:
                    await bot.graph_manager.post_graphs(channel, graph_files)
            else:
                log(bot.translations["log_channel_not_found"].format(
                    channel_id=bot.config["CHANNEL_ID"]
                ), logging.ERROR)
            
            bot.update_tracker.update()
            next_update_log = bot.update_tracker.get_next_update_readable()
            log(bot.translations["log_auto_update_completed"].format(
                next_update=next_update_log
            ))
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log("An error occurred in main", logging.ERROR)
        logger.exception(e)

# TGraph - Tautulli Graph Bot
# <https://github.com/engels74/tgraph-bot-source>
