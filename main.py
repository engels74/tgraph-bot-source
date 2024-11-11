# main.py

"""
Standardized main module for TGraph Bot with enhanced error handling.
Manages bot initialization, lifecycle, and background tasks with proper error handling and
resource management.
"""

from aiohttp import ClientConnectorError, ServerDisconnectedError
from bot.extensions import load_extensions
from bot.permission_checker import check_permissions_all_guilds, PermissionError
from bot.update_tracker import create_update_tracker, UpdateTrackerError
from config.config import load_config
from datetime import datetime
from discord.ext import commands
from graphs.graph_manager import GraphManager
from graphs.graph_modules.data_fetcher import DataFetcher
from graphs.user_graph_manager import UserGraphManager
from i18n import load_translations, TranslationManager
import argparse
import asyncio
import discord
import logging
import os
import sys

# Set up basic logging immediately after imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],  # Start with just console logging
    force=True  # Force configuration of the root logger
)

# Ensure all loggers inherit the root logger's configuration
logging.getLogger().setLevel(logging.INFO)

# Custom Exception Hierarchy
class MainError(Exception):
    """Base exception for main module errors."""
    pass

class InitializationError(MainError):
    """Raised during initialization failures."""
    pass

class MainConfigError(MainError):
    """Raised for configuration-related errors."""
    pass

class BackgroundTaskError(MainError):
    """Raised for background task failures."""
    pass

class EventHandlingError(MainError):
    """Raised for event handling errors."""
    pass

class SchedulingError(MainError):
    """Raised for update scheduling errors."""
    pass

class ResourceManagementError(MainError):
    """Raised for resource management failures."""
    pass

class CleanupError(MainError):
    """Raised during cleanup failures."""
    pass

class TGraphBot(commands.Bot):
    """Enhanced TGraph Bot with standardized error handling."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_folder = kwargs.pop("data_folder", None)
        self.img_folder = os.path.join(self.data_folder, "img")
        self.update_tracker = kwargs.pop("update_tracker", None)
        self.config = kwargs.pop("config", None)
        self.config_path = kwargs.pop("config_path", None)
        self.translations = kwargs.pop("translations", None)
        self._initialized_resources = []
        self._initialization_lock = asyncio.Lock()
        
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
            self._cleanup_resources()
            error_msg = f"Failed to initialize TGraphBot: {str(e)}"
            logging.error(error_msg)
            raise InitializationError(error_msg) from e

    def _cleanup_resources(self) -> None:
        """Clean up initialized resources in reverse order."""
        for resource in reversed(self._initialized_resources):
            try:
                if hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception as e:
                logging.error(f"Error during cleanup of {resource.__class__.__name__}: {e}")

    async def setup_hook(self) -> None:
        """Initialize the bot's state after login with enhanced error handling."""
        try:
            async with self._initialization_lock:
                # Load command extensions
                await load_extensions(self)

                # Sync application commands
                logging.info(self.translations["log_syncing_application_commands"])
                await self.tree.sync()
                logging.info(self.translations["log_application_commands_synced"])

        except commands.ExtensionError as e:
            error_msg = self.translations["log_extension_load_error"].format(error=str(e))
            logging.error(error_msg)
            raise InitializationError(error_msg) from e
        except discord.HTTPException as e:
            error_msg = self.translations["log_command_sync_error"].format(error=str(e))
            logging.error(error_msg)
            raise InitializationError(error_msg) from e
        except Exception as e:
            error_msg = self.translations["log_unexpected_setup_error"].format(error=str(e))
            logging.error(error_msg)
            raise InitializationError(error_msg) from e

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Enhanced error handling for Discord events."""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        try:
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
        except Exception as e:
            error_msg = f"Error handling event error for {event_method}: {str(e)}"
            logging.error(error_msg)
            raise EventHandlingError(error_msg) from e

    async def on_connect(self) -> None:
        """Handle connection event."""
        log(self.translations["log_bot_connected"])

    async def on_disconnect(self) -> None:
        """Handle disconnection event."""
        log(self.translations["log_bot_disconnected"], logging.WARNING)

    async def on_resume(self) -> None:
        """Handle resume event."""
        log(self.translations["log_bot_resumed"])

    async def background_initialization(self) -> None:
        """Perform initialization tasks in the background with enhanced error handling."""
        try:
            # Check permissions after a short delay
            log(self.translations["log_waiting_before_permission_check"])
            await asyncio.sleep(5)

            # Permissions check with error handling
            try:
                log(self.translations["log_checking_command_permissions"])
                await check_permissions_all_guilds(self, self.translations)
                log(self.translations["log_command_permissions_checked"])
            except PermissionError as e:
                raise BackgroundTaskError("Permission check failed") from e

            # Initial graph update
            log(self.translations["log_updating_posting_graphs_startup"])
            
            # Config reload with retry mechanism
            max_retries = 3
            retry_delay = 5
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    self.config = load_config(self.config_path, reload=True)
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        log(self.translations["log_config_reload_retry"].format(
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error=str(e)
                        ), logging.WARNING)
                        await asyncio.sleep(retry_delay)
                    else:
                        error_msg = self.translations["log_config_reload_failed"].format(error=str(e))
                        logging.error(error_msg)
                        raise MainConfigError("Configuration reload failed") from last_error

            # Channel validation and graph posting
            channel = self.get_channel(self.config["CHANNEL_ID"])
            if not channel:
                error_msg = self.translations["log_channel_not_found"].format(
                    channel_id=self.config["CHANNEL_ID"]
                )
                logging.error(error_msg)
                raise BackgroundTaskError(error_msg)

            try:
                await self.graph_manager.delete_old_messages(channel)
                graph_files = await self.graph_manager.generate_and_save_graphs(self.data_fetcher)
                if graph_files:
                    await self.graph_manager.post_graphs(channel, graph_files, self.update_tracker)
            except Exception as e:
                raise BackgroundTaskError("Failed to generate or post graphs") from e

            # Update tracker management
            try:
                self.update_tracker.last_update = datetime.now()
                self.update_tracker.next_update = self.update_tracker.calculate_next_update(
                    self.update_tracker.last_update
                )
                self.update_tracker.save_tracker()
            except Exception as e:
                raise BackgroundTaskError("Failed to update tracker") from e

            next_update_log = self.update_tracker.get_next_update_readable()
            log(self.translations["log_graphs_updated_posted"].format(
                next_update=next_update_log
            ))

        except Exception as e:
            if isinstance(e, (BackgroundTaskError, MainConfigError)):
                raise
            error_msg = f"Background initialization failed: {str(e)}"
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg) from e

    async def on_ready(self) -> None:
        """Handle the on_ready event with enhanced error handling."""
        log(self.translations["log_bot_logged_in"].format(name=self.user.name))
        
        try:
            # Start the initialization in a background task
            self.loop.create_task(self.background_initialization())
            
            # Start update scheduling
            self.loop.create_task(schedule_updates(self))
        except Exception as e:
            error_msg = f"Failed to start background tasks: {str(e)}"
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg) from e

async def schedule_updates(bot: TGraphBot) -> None:
    """Schedule updates with enhanced error handling and retry mechanisms."""
    channel_retry_delay = 3600  # 1 hour
    channel_check_failures = 0
    max_channel_failures = 3
    max_consecutive_failures = 3
    consecutive_failures = 0
    failure_delay = 300  # 5 minutes

    while True:
        try:
            if bot.update_tracker.is_update_due():
                log(bot.translations["log_auto_update_started"])
                
                try:
                    # Config reload with error handling
                    try:
                        bot.config = load_config(bot.config_path, reload=True)
                        consecutive_failures = 0
                    except Exception as e:
                        consecutive_failures += 1
                        log(bot.translations["log_config_reload_error"].format(
                            error=str(e),
                            attempt=consecutive_failures,
                            max_attempts=max_consecutive_failures
                        ), logging.ERROR)
                        
                        if consecutive_failures >= max_consecutive_failures:
                            log(bot.translations["log_config_reload_critical"], logging.CRITICAL)
                            await asyncio.sleep(failure_delay)
                        continue
                    
                    # Channel validation
                    channel = bot.get_channel(bot.config["CHANNEL_ID"])
                    if not channel:
                        channel_check_failures += 1
                        log(bot.translations["log_channel_not_found"].format(
                            channel_id=bot.config["CHANNEL_ID"],
                            attempt=channel_check_failures,
                            max_attempts=max_channel_failures
                        ), logging.ERROR)
                        
                        if channel_check_failures >= max_channel_failures:
                            log(bot.translations["log_channel_not_found_critical"], logging.CRITICAL)
                            await asyncio.sleep(channel_retry_delay)
                        continue
                    
                    channel_check_failures = 0  # Reset on success
                    
                    # Graph generation and posting
                    graph_files = await bot.graph_manager.generate_and_save_graphs(bot.data_fetcher)
                    if graph_files:
                        await bot.graph_manager.post_graphs(channel, graph_files, bot.update_tracker)
                    else:
                        raise BackgroundTaskError("No graphs were generated")
                    
                    # Update tracker
                    bot.update_tracker.update()
                    next_update_log = bot.update_tracker.get_next_update_readable()
                    log(bot.translations["log_auto_update_completed"].format(
                        next_update=next_update_log
                    ))
                    
                except Exception as e:
                    error_msg = bot.translations["log_auto_update_error"].format(error=str(e))
                    logging.error(error_msg)
                    raise SchedulingError(error_msg) from e
                
        except Exception as e:
            if not isinstance(e, SchedulingError):
                error_msg = f"Unexpected error in update scheduling: {str(e)}"
                logging.error(error_msg)
                
        await asyncio.sleep(60)

def setup_logging(log_file: str) -> None:
    """Set up logging with error handling."""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except Exception as e:
        error_msg = f"Failed to set up logging: {str(e)}"
        print(error_msg)  # Use print since logging isn't set up yet
        raise InitializationError(error_msg) from e

def create_folders(log_file: str, data_folder: str, img_folder: str) -> None:
    """Create necessary folders with error handling."""
    try:
        for folder in [os.path.dirname(log_file), data_folder, img_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
    except OSError as e:
        error_msg = f"Failed to create required folders: {str(e)}"
        logging.error(error_msg)
        raise ResourceManagementError(error_msg) from e

def log(message: str, level: int = logging.INFO) -> None:
    """Centralized logging function."""
    logger = logging.getLogger(__name__)
    logger.log(level, message)

async def main() -> None:
    """Main entry point with comprehensive error handling."""
    # Get the CONFIG_DIR from environment variable, default to '/config' if not set
    CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")

    try:
        # Parse command-line arguments first
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

        # Create log directory and add file handler
        try:
            os.makedirs(os.path.dirname(args.log_file), exist_ok=True)
            # Add file handler to root logger
            file_handler = logging.FileHandler(args.log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            print(f"Failed to set up log file: {e}")  # Use print since console logging still works
            raise InitializationError(f"Failed to set up log file: {e}") from e

        # Create img_folder path
        IMG_FOLDER = os.path.join(args.data_folder, "img")

        # Now create remaining folders
        try:
            create_folders(args.log_file, args.data_folder, IMG_FOLDER)
        except ResourceManagementError as e:
            logging.error(f"Failed to create required folders: {e}")
            raise

        logger = logging.getLogger(__name__)

        # Load configuration with error handling
        try:
            config = load_config(args.config_file)
        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            raise MainConfigError(error_msg) from e

        # Load translations with fallback handling
        try:
            translations = load_translations(config["LANGUAGE"])
            logging.debug(f"Loaded translations keys: {sorted(translations.keys())}")
            TranslationManager.set_translations(translations)
            if not translations:
                translations = {"log_ensured_folders_exist": "Ensured folders exist"}
                logging.warning("Translations failed to load, using fallback")
        except Exception as e:
            error_msg = f"Error loading translations: {e}"
            logger.error(error_msg)
            translations = {"log_ensured_folders_exist": "Ensured folders exist"}
            TranslationManager.set_translations(translations)
            logging.warning("Exception during translation loading, using fallback")

        # Log folder creation success
        logger.info(translations.get(
            "log_ensured_folders_exist",
            "Ensured folders exist"
        ))

        try:
            # Create UpdateTracker instance
            update_tracker = create_update_tracker(args.data_folder, config, translations)
        except UpdateTrackerError as e:
            error_msg = f"Failed to create update tracker: {e}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e

        # Initialize bot with intents
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True

        try:
            bot = TGraphBot(
                command_prefix="!",
                intents=intents,
                data_folder=args.data_folder,
                update_tracker=update_tracker,
                config=config,
                config_path=args.config_file,
                translations=translations,
            )
        except InitializationError as e:
            logger.error(f"Bot initialization failed: {e}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error during bot initialization: {e}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e

        try:
            # Start the bot
            await bot.start(config["DISCORD_TOKEN"])
        except discord.LoginFailure as e:
            error_msg = translations.get(
                "log_login_error",
                "Login error: {error}"
            ).format(error=str(e))
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        except discord.HTTPException as e:
            error_msg = translations.get(
                "log_connection_error",
                "Connection error: {error}"
            ).format(error=str(e))
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        except Exception as e:
            error_msg = translations.get(
                "log_error_starting_bot",
                "Error starting bot: {error}"
            ).format(error=str(e))
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        finally:
            # Ensure bot is properly closed
            try:
                await bot.close()
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")

    except Exception as e:
        if not isinstance(e, (InitializationError, MainConfigError, ResourceManagementError)):
            logging.error(f"Unexpected error in main: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log(TranslationManager.get_translation("log_shutdown_requested"), logging.INFO)
    except discord.LoginFailure as e:
        log(TranslationManager.get_translation("log_login_error").format(error=str(e)), logging.ERROR)
        logging.exception(e)
    except Exception as e:
        log(TranslationManager.get_translation("log_unexpected_main_error").format(error=str(e)), logging.ERROR)
        logging.exception(e)
    finally:
        log(TranslationManager.get_translation("log_shutdown_complete"), logging.INFO)

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
