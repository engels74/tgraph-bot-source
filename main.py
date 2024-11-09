# main.py
import argparse
import asyncio
import discord
import logging
import os
import sys
from aiohttp import ClientConnectorError, ServerDisconnectedError
from bot.extensions import load_extensions
from bot.permission_checker import check_permissions_all_guilds
from bot.update_tracker import create_update_tracker
from config.config import load_config
from datetime import datetime
from discord.ext import commands
from graphs.graph_manager import GraphManager
from graphs.graph_modules.data_fetcher import DataFetcher
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

# Set up logging
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
        self.config_path = kwargs.pop("config_path", None)
        self.translations = kwargs.pop("translations", None)
        self._initialized_resources = []
        try:
            # Initialize DataFetcher first
            self.data_fetcher = DataFetcher(self.config)
            self._initialized_resources.append(self.data_fetcher)
            
            # Initialize GraphManager with DataFetcher
            self.graph_manager = GraphManager(self.config, self.translations, self.img_folder)
            self._initialized_resources.append(self.graph_manager)
            
            # Initialize UserGraphManager
            self.user_graph_manager = UserGraphManager(self.config, self.translations, self.img_folder)
            self._initialized_resources.append(self.user_graph_manager)
            
            log(self.translations["log_tgraphbot_initialized"])
        except Exception as e:
            log(f"Error during initialization: {e}", logging.ERROR)
            self._cleanup_resources()
            raise

    def _cleanup_resources(self):
        for resource in reversed(self._initialized_resources):
            try:
                if hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                log(f"Error during cleanup of {resource.__class__.__name__}: {e}", logging.ERROR)

    async def setup_hook(self):
        """Initialize the bot's state after login."""
        try:
            # Load command extensions - logging handled by load_extensions
            await load_extensions(self)

            # Sync application commands
            logging.info(self.translations["log_syncing_application_commands"])
            await self.tree.sync()
            logging.info(self.translations["log_application_commands_synced"])

        except commands.ExtensionError as e:
            log(self.translations["log_extension_load_error"].format(error=str(e)), logging.ERROR)
            raise
        except discord.HTTPException as e:
            log(self.translations["log_command_sync_error"].format(error=str(e)), logging.ERROR)
            raise
        except Exception as e:
            log(self.translations["log_unexpected_setup_error"].format(error=str(e)), logging.ERROR)
            raise

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

    async def background_initialization(self):
        """Perform initialization tasks in the background."""
        try:
            # Check permissions after a short delay
            log(self.translations["log_waiting_before_permission_check"])
            await asyncio.sleep(5)

            log(self.translations["log_checking_command_permissions"])
            await check_permissions_all_guilds(self, self.translations)
            log(self.translations["log_command_permissions_checked"])

            # Initial graph update
            log(self.translations["log_updating_posting_graphs_startup"])
            
            try:
                self.config = load_config(self.config_path, reload=True)
            except Exception as e:
                log(self.translations["log_config_reload_error"].format(error=str(e)), logging.ERROR)
                # Use existing config as fallback
                log("Using existing configuration as fallback", logging.WARNING)
            
            channel = self.get_channel(self.config["CHANNEL_ID"])
            if channel:
                await self.graph_manager.delete_old_messages(channel)
                # Pass self.data_fetcher to generate_and_save_graphs
                graph_files = await self.graph_manager.generate_and_save_graphs(self.data_fetcher)
                if graph_files:
                    await self.graph_manager.post_graphs(channel, graph_files, self.update_tracker)
            else:
                log(self.translations["log_channel_not_found"].format(
                    channel_id=self.config["CHANNEL_ID"]
                ), logging.ERROR)

            # Update the tracker
            self.update_tracker.last_update = datetime.now()
            self.update_tracker.next_update = self.update_tracker.calculate_next_update(
                self.update_tracker.last_update
            )
            self.update_tracker.save_tracker()

            next_update_log = self.update_tracker.get_next_update_readable()
            log(self.translations["log_graphs_updated_posted"].format(
                next_update=next_update_log
            ))

        except discord.Forbidden as e:
            log(self.translations["log_permission_error"].format(error=str(e)), logging.ERROR)
            raise
        except discord.NotFound as e:
            log(self.translations["log_channel_not_found_error"].format(error=str(e)), logging.ERROR)
            raise
        except Exception as e:
            log(self.translations["log_error_during_startup"].format(error=str(e)), logging.ERROR)
            raise

    async def on_ready(self):
        """Handle the on_ready event."""
        log(self.translations["log_bot_logged_in"].format(name=self.user.name))
        
        # Start the initialization in a background task
        self.loop.create_task(self.background_initialization())
        
        # Start update scheduling
        self.loop.create_task(schedule_updates(self))

async def schedule_updates(bot):
    """Handle scheduled updates with proper error handling."""
    while True:
        if bot.update_tracker.is_update_due():
            log(bot.translations["log_auto_update_started"])
            try:
                try:
                    bot.config = load_config(bot.config_path, reload=True)
                except Exception as e:
                    log(bot.translations["log_config_reload_error"].format(error=str(e)), logging.ERROR)
                    # Skip this update cycle if config reload fails
                    continue
                
                channel = bot.get_channel(bot.config["CHANNEL_ID"])
                if channel:
                    await bot.graph_manager.delete_old_messages(channel)
                    # Pass bot.data_fetcher to generate_and_save_graphs
                    graph_files = await bot.graph_manager.generate_and_save_graphs(bot.data_fetcher)
                    if graph_files:
                        await bot.graph_manager.post_graphs(channel, graph_files, bot.update_tracker)
                else:
                    log(bot.translations["log_channel_not_found"].format(
                        channel_id=bot.config["CHANNEL_ID"]
                    ), logging.ERROR)
                    continue
                
                bot.update_tracker.update()
                next_update_log = bot.update_tracker.get_next_update_readable()
                log(bot.translations["log_auto_update_completed"].format(
                    next_update=next_update_log
                ))
            except Exception as e:
                log(bot.translations["log_auto_update_error"].format(error=str(e)), logging.ERROR)
        await asyncio.sleep(60)

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
        config_path=args.config_file,
        translations=translations,
    )

    try:
        await bot.start(config["DISCORD_TOKEN"])
    except discord.LoginFailure as e:
        log(translations["log_login_error"].format(error=str(e)), logging.ERROR)
        raise
    except discord.HTTPException as e:
        log(translations["log_connection_error"].format(error=str(e)), logging.ERROR)
        raise
    except Exception as e:
        log(translations["log_error_starting_bot"].format(error=str(e)), logging.ERROR)
        raise
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log(translations["log_shutdown_requested"], logging.INFO)
    except discord.LoginFailure as e:
        log(translations["log_login_error"].format(error=str(e)), logging.ERROR)
        logger.exception(e)
    except Exception as e:
        log(translations["log_unexpected_main_error"].format(error=str(e)), logging.ERROR)
        logger.exception(e)
    finally:
        log(translations["log_shutdown_complete"], logging.INFO)

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
