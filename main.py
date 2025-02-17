# main.py

"""
Standardized main module for TGraph Bot with enhanced error handling.
Manages bot initialization, lifecycle, and background tasks with proper error handling and
resource management.
"""

from aiohttp import ClientConnectorError, ServerDisconnectedError
from bot.extensions import load_extensions
from bot.permission_checker import check_permissions_all_guilds, PermissionError
from bot.update_tracker import UpdateTracker, create_update_tracker, UpdateTrackerError
from config.config import load_config
from datetime import datetime
from discord.ext import commands, tasks
from graphs.graph_manager import GraphManager
from graphs.graph_modules.data_fetcher import DataFetcher
from graphs.graph_modules.utils import cleanup_old_folders
from graphs.user_graph_manager import UserGraphManager
from i18n import load_translations, TranslationManager
from typing import Optional
import argparse
import asyncio
import contextlib
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

# Simplified exception hierarchy
class MainError(Exception):
    """Base exception for main module errors."""
    pass

class InitializationError(MainError):
    """Raised during initialization failures."""
    pass

class ConfigError(MainError):
    """Raised for configuration-related errors."""
    pass

class BackgroundTaskError(MainError):
    """Raised for background task failures."""
    pass

class TranslationError(MainError):
    """Raised for translation-related errors."""
    pass

class DataFetchError(MainError):
    """Raised when data fetching fails."""
    pass

class GraphGenerationError(MainError):
    """Raised when graph generation fails."""
    pass

class PostingError(MainError):
    """Raised when posting graphs fails."""
    pass

class TGraphBot(commands.Bot):
    """Enhanced TGraph Bot with standardized error handling."""
    
    def __init__(self, *args, **kwargs):
        # Initialize intents before super().__init__
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        
        # Pass intents to super().__init__ with updated argument order
        super().__init__(
            *args,
            command_prefix="!",
            intents=intents,
            **kwargs
        )
        
        # Initialize the initialization lock
        self._initialization_lock = asyncio.Lock()
        
        # Initialize other attributes after super().__init__
        self.data_folder = kwargs.pop("data_folder", None)
        self.img_folder = os.path.join(self.data_folder, "img")
        self.update_tracker = kwargs.pop("update_tracker", None)
        self.config = kwargs.pop("config", None)
        self.config_path = kwargs.pop("config_path", None)
        self.translations = kwargs.pop("translations", None)
        
        self._initialized_resources = []  # Initialize the list to keep track of resources
        try:
            self._initialize_resources()
        except Exception as e:
            self._cleanup_resources()  # Now safe to call
            error_msg = f"Failed to initialize TGraphBot: {str(e)}"
            logging.error(error_msg)
            raise InitializationError(error_msg) from e

    def _initialize_resources(self):
        """Initialize bot resources with proper error handling."""
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

    def _cleanup_resources(self) -> None:
        """Clean up initialized resources in reverse order."""
        for resource in reversed(self._initialized_resources):
            try:
                if hasattr(resource, 'cleanup'):
                    logging.debug(f"Cleaning up resource: {resource.__class__.__name__}")
                    resource.cleanup()
            except Exception as e:
                logging.error(f"Error during cleanup of {resource.__class__.__name__}: {e}")

    def _cleanup_old_folders(self) -> None:
        """Clean up old graph folders with error handling.
        
        This is a non-blocking operation - if cleanup fails, it logs the error
        and continues execution.
        """
        try:
            keep_days = self.config.get('KEEP_DAYS')
            if keep_days is None:
                logging.error(self.translations["error_config_missing"].format(key='KEEP_DAYS'))
                return
                
            cleanup_old_folders(self.img_folder, keep_days, self.translations)
            logging.debug(self.translations["log_cleaned_up_old_folders"].format(
                keep_days=keep_days
            ))
        except (OSError, KeyError) as e:
            error_msg = self.translations["error_unexpected"].format(error=str(e))
            logging.error(error_msg)
            # Continue execution even if cleanup fails

    async def setup_hook(self) -> None:
        """Initialize the bot's state after login with enhanced error handling."""
        try:
            async with self._initialization_lock:
                # Clean up old graph folders first
                self._cleanup_old_folders()
                
                # Load command extensions
                await load_extensions(self)

                # Sync application commands with broader error handling
                logging.info(self.translations["log_syncing_application_commands"])
                try:
                    await self.tree.sync()
                    logging.info(self.translations["log_application_commands_synced"])
                except discord.Forbidden as e:
                    error_msg = self.translations["log_command_sync_forbidden"].format(error=str(e))
                    logging.error(error_msg)
                    raise InitializationError(error_msg) from e
                except discord.HTTPException as e:
                    error_msg = self.translations["log_command_sync_error"].format(error=str(e))
                    logging.error(error_msg)
                    raise InitializationError(error_msg) from e
                except Exception as e:
                    error_msg = self.translations["log_command_sync_unexpected"].format(error=str(e))
                    logging.error(error_msg)
                    raise InitializationError(error_msg) from e

        except commands.ExtensionError as e:
            error_msg = self.translations["log_extension_load_error"].format(error=str(e))
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
            raise BackgroundTaskError(error_msg) from e

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
            
            # Sequential initialization steps with proper error handling
            await self._check_permissions()
            await self._reload_config_with_retry()
            channel = await self._validate_channel()
            await self._update_and_post_graphs(channel)
            await self._update_tracker_state()
            
            next_update_log = self.update_tracker.get_next_update_readable()
            log(self.translations["log_graphs_updated_posted"].format(
                next_update=next_update_log
            ))
            
        except Exception as e:
            if isinstance(e, (BackgroundTaskError, ConfigError)):
                raise
            error_msg = f"Background initialization failed: {str(e)}"
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg) from e

    async def _check_permissions(self) -> None:
        """Check bot permissions with error handling."""
        try:
            log(self.translations["log_checking_command_permissions"])
            await check_permissions_all_guilds(self, self.translations)
            log(self.translations["log_command_permissions_checked"])
        except PermissionError as e:
            raise BackgroundTaskError("Permission check failed") from e

    async def _reload_config_with_retry(self, max_retries: int = 3, retry_delay: int = 5) -> None:
        """Reload configuration with retry mechanism and update translations."""
        last_error = None
        for attempt in range(max_retries):
            logging.debug(f"Config reload attempt {attempt + 1}/{max_retries}")
            try:
                # Run load_config in executor to prevent blocking
                self.config = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: load_config(self.config_path, reload=True)
                )
                
                # Reload translations after config update
                await self._reload_translations()
                return
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    log(self.translations["log_config_reload_retry"].format(
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e)
                    ), logging.WARNING)
                    await asyncio.sleep(retry_delay)
                    continue
                error_msg = self.translations["log_config_reload_failed"].format(error=str(e))
                logging.error(error_msg)
                raise ConfigError("Configuration reload failed") from last_error

    async def _validate_channel(self) -> discord.TextChannel:
        """Validate and return the target channel."""
        channel = self.get_channel(self.config["CHANNEL_ID"])
        if not channel:
            error_msg = self.translations["log_channel_not_found"].format(
                channel_id=self.config["CHANNEL_ID"]
            )
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg)
        return channel

    async def _update_and_post_graphs(self, channel: discord.TextChannel) -> None:
        """Generate and post graphs to the specified channel with enhanced error handling."""
        try:
            # First try to delete old messages
            try:
                await self.graph_manager.delete_old_messages(channel)
            except discord.HTTPException as e:
                logging.warning(f"Failed to delete old messages: {str(e)}")
                # Continue execution even if message deletion fails
            
            # Fetch graph data with timeout and error handling
            try:
                async with asyncio.timeout(30):  # 30 second timeout for data fetching
                    graph_data = await self.data_fetcher.fetch_all_graph_data()
                    if not graph_data:
                        error_msg = "No data received from Tautulli API"
                        logging.error(error_msg)
                        raise DataFetchError(error_msg)
                    logging.debug(f"Successfully fetched graph data: {list(graph_data.keys())}")
            except asyncio.TimeoutError as e:
                error_msg = "Timeout while fetching graph data"
                logging.error(error_msg)
                raise DataFetchError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to fetch graph data: {str(e)}"
                logging.error(error_msg)
                raise DataFetchError(error_msg) from e

            # Generate graphs with proper error handling
            try:
                graph_files = await self.graph_manager.generate_and_save_graphs(self.data_fetcher)
                if not graph_files:
                    error_msg = "No graphs were generated"
                    logging.error(error_msg)
                    raise GraphGenerationError(error_msg)
                logging.debug(f"Successfully generated {len(graph_files)} graphs")
            except Exception as e:
                error_msg = f"Failed to generate graphs: {str(e)}"
                logging.error(error_msg)
                raise GraphGenerationError(error_msg) from e

            # Post graphs with timeout and error handling
            try:
                async with asyncio.timeout(30):  # 30 second timeout for posting
                    await self.graph_manager.post_graphs(channel, graph_files, self.update_tracker)
                    logging.info("Successfully posted all graphs")
            except asyncio.TimeoutError as e:
                error_msg = "Timeout while posting graphs"
                logging.error(error_msg)
                raise PostingError(error_msg) from e
            except discord.HTTPException as e:
                error_msg = f"Discord API error while posting graphs: {str(e)}"
                logging.error(error_msg)
                raise PostingError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to post graphs: {str(e)}"
                logging.error(error_msg)
                raise PostingError(error_msg) from e

        except (DataFetchError, GraphGenerationError, PostingError) as e:
            # Re-raise with more context for the calling function
            raise BackgroundTaskError(f"Failed to update and post graphs: {str(e)}") from e
        except Exception as e:
            error_msg = f"Unexpected error in graph update process: {str(e)}"
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg) from e

    async def _update_tracker_state(self) -> None:
        """Update the tracker state with proper error handling."""
        try:
            self.update_tracker.last_update = datetime.now()
            self.update_tracker.next_update = self.update_tracker.calculate_next_update(
                self.update_tracker.last_update
            )
            self.update_tracker.save_tracker()
        except Exception as e:
            raise BackgroundTaskError("Failed to update tracker") from e

    async def _reload_translations(self) -> None:
        """Reload translations based on current configuration."""
        try:
            language = self.config.get("LANGUAGE", "en")
            translations = load_translations(language)
            
            # Update translations across all components
            self.translations = translations
            
            # Update translations for graph-related components
            if hasattr(self, 'graph_manager'):
                self.graph_manager.translations = translations
                self.graph_manager.graph_factory.translations = translations
                
            if hasattr(self, 'user_graph_manager'):
                self.user_graph_manager.translations = translations
                
            if hasattr(self, 'data_fetcher'):
                self.data_fetcher.translations = translations
                
            logging.debug(f"Reloaded translations for language: {language}")
            
        except Exception as e:
            logging.error(f"Failed to reload translations: {str(e)}")
            raise TranslationError(f"Failed to reload translations: {str(e)}") from e

    @tasks.loop(seconds=60)
    async def schedule_updates_task(self):
        """Background task for scheduling updates with proper error handling"""
        try:
            # Add network error handling
            try:
                if self.update_tracker.is_update_due():
                    log(self.translations["log_auto_update_started"])
                    
                    # Handle config reload
                    config_success, consecutive_failures = await _handle_config_reload(
                        self, 0, 3, 600  # Start with 0 failures, max 3 attempts, 10 min delay
                    )
                    if not config_success:
                        await asyncio.sleep(60)  # Add delay before retry
                        return

                    # Handle channel validation
                    channel, channel_check_failures = await _handle_channel_validation(
                        self, 0, 3, 1800  # Start with 0 failures, max 3 attempts, 30 min delay
                    )
                    if not channel:
                        await asyncio.sleep(60)  # Add delay before retry
                        return
                    
                    # Handle graph update
                    if not await _handle_graph_update(self, channel):
                        raise BackgroundTaskError("Failed to update graphs")
            except (ClientConnectorError, ServerDisconnectedError) as e:
                log(self.translations["log_network_error"].format(error=str(e)), logging.WARNING)
                await asyncio.sleep(300)  # 5 minute delay on network errors
                return
        except Exception as e:
            error_msg = f"Error in scheduled update task: {str(e)}"
            logging.error(error_msg)
            # The tasks extension will automatically handle the retry logic

    @schedule_updates_task.before_loop
    async def before_schedule_updates(self):
        """Wait until the bot is ready before starting the task"""
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        """Handle the on_ready event with enhanced error handling."""
        log(self.translations["log_bot_logged_in"].format(name=self.user.name))
        
        try:
            # Start the background task using tasks.loop
            self.schedule_updates_task.start()
            await self.background_initialization()
            
        except Exception as e:
            error_msg = f"Failed to start background tasks: {str(e)}"
            logging.error(error_msg)
            raise BackgroundTaskError(error_msg) from e

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors with comprehensive error handling and user feedback.
        
        Provides detailed error messages for different types of command errors while
        maintaining security by not exposing sensitive details.
        """
        try:
            if isinstance(error, commands.CommandNotFound):
                # Silently ignore command not found errors
                return
            
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send(self.translations["error_missing_permissions"])
            
            elif isinstance(error, commands.BotMissingPermissions):
                await ctx.send(self.translations["error_bot_missing_permissions"].format(
                    permissions=", ".join(error.missing_permissions)
                ))
            
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(self.translations["error_missing_argument"].format(
                    param=error.param.name
                ))
            
            elif isinstance(error, commands.BadArgument):
                await ctx.send(self.translations["error_bad_argument"])
            
            elif isinstance(error, commands.NoPrivateMessage):
                await ctx.send(self.translations["error_no_dm"])
            
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(self.translations["error_cooldown"].format(
                    time=round(error.retry_after, 2)
                ))
            
            elif isinstance(error, commands.DisabledCommand):
                await ctx.send(self.translations["error_command_disabled"])
            
            elif isinstance(error, commands.CheckFailure):
                await ctx.send(self.translations["error_check_failure"])
            
            else:
                # Log unexpected errors with full details
                logging.error(f"Unexpected command error: {str(error)}", exc_info=error)
                
                # Send a generic error message to the user
                await ctx.send(self.translations["error_unexpected"])
            
        except Exception as e:
            # Log any errors that occur during error handling
            logging.error(f"Error in error handler: {str(e)}", exc_info=e)
            with contextlib.suppress(Exception):
                await ctx.send(self.translations["error_handler_failed"])

async def _handle_config_reload(bot: TGraphBot, consecutive_failures: int, max_consecutive_failures: int, failure_delay: int) -> tuple[bool, int]:
    """Handle configuration reload with retry logic.
    
    Args:
        bot: The bot instance
        consecutive_failures: Current number of consecutive failures
        max_consecutive_failures: Maximum allowed consecutive failures
        failure_delay: Delay in seconds before next retry
        
    Returns:
        Tuple of (success status, updated consecutive failures count)
    """
    try:
        bot.config = load_config(bot.config_path, reload=True)
        return True, 0
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
        return False, consecutive_failures

async def _handle_channel_validation(bot: TGraphBot, channel_check_failures: int, max_channel_failures: int, channel_retry_delay: int) -> tuple[Optional[discord.TextChannel], int]:
    """Validate and get the target channel.
    
    Args:
        bot: The bot instance
        channel_check_failures: Current number of channel check failures
        max_channel_failures: Maximum allowed channel check failures
        channel_retry_delay: Delay in seconds before next retry
        
    Returns:
        Tuple of (channel if valid or None, updated channel check failures count)
    """
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
        return None, channel_check_failures
    return channel, 0

async def _handle_graph_update(bot: TGraphBot, channel: discord.TextChannel) -> bool:
    """
    Handle graph generation and posting with enhanced error handling and state management.

    Args:
        bot: The bot instance 
        channel: The target channel for posting

    Returns:
        bool: True if successful, False otherwise
    """
    temp_tracker = None
    previous_state = None
    try:
        # 1. Store current tracker state for rollback
        previous_state = bot.update_tracker.get_state()
        
        # 2. Update tracker state and validate
        bot.update_tracker.update()
        current_update = bot.update_tracker.last_update
        logging.debug(
            "Update sequence started. Current update time: %s, Next scheduled: %s",
            current_update.isoformat() if current_update else "None",
            bot.update_tracker.next_update.isoformat() if bot.update_tracker.next_update else "None"
        )

        # 3. Create temporary tracker with proper initialization
        temp_tracker = UpdateTracker(bot.data_folder, bot.config, bot.translations) 
        temp_tracker.restore_state(bot.update_tracker.get_state())

        # 4. Delete old messages with granular error handling
        try:
            await bot.graph_manager.delete_old_messages(channel)
            logging.debug("Successfully deleted old messages")
        except discord.NotFound:
            logging.warning("Some messages were already deleted")
        except discord.Forbidden as e:
            logging.error("Bot lacks permissions to delete messages: %s", str(e))
            return False
        except discord.HTTPException as e:
            logging.error("Discord API error while deleting messages: %s", str(e))
            # Continue with update even if deletion fails
        except Exception as e:
            logging.error("Unexpected error deleting messages: %s", str(e))
            # Continue with update even if deletion fails

        # 5. Generate new graphs with specific error handling
        try:
            graph_files = await bot.graph_manager.generate_and_save_graphs(bot.data_fetcher)
            if not graph_files:
                raise BackgroundTaskError(bot.translations["error_no_graphs_generated"])
                
            try:
                # Clean up old graph folders
                bot._cleanup_old_folders()
            except Exception as e:
                logging.warning(f"Failed to cleanup old folders: {e}")
                # Continue execution as cleanup failure is non-critical
                
        except BackgroundTaskError as e:
            logging.error("Failed to generate graphs: %s", str(e))
            # Restore previous state before returning
            if previous_state:
                bot.update_tracker.restore_state(previous_state)
            return False
        except Exception as e:
            logging.error("Unexpected error generating graphs: %s", str(e))
            if previous_state:
                bot.update_tracker.restore_state(previous_state)
            return False

        # 6. Post graphs using temporary tracker
        await bot.graph_manager.post_graphs(channel, graph_files, temp_tracker)
        
        # 7. Save state only after successful completion
        bot.update_tracker.save_state()
        
        next_update_log = bot.update_tracker.get_next_update_readable()
        log(bot.translations["log_auto_update_completed"].format(
            next_update=next_update_log
        ))
        return True

    except Exception as e:
        # Restore previous state on failure
        if previous_state:
            bot.update_tracker.restore_state(previous_state)
        error_msg = bot.translations["log_auto_update_error"].format(error=str(e))
        logging.exception(error_msg)
        return False

    finally:
        # Clean up temporary tracker with proper error handling
        if temp_tracker is not None:
            try:
                if hasattr(temp_tracker, 'cleanup'):
                    await temp_tracker.cleanup()
                del temp_tracker
            except Exception as e:
                logging.warning("Failed to cleanup temporary tracker: %s", str(e))

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
            
            # Test write permissions
            test_file = os.path.join(folder, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except IOError as e:
                raise OSError(f"No write permission in {folder}: {e}") from e
    except OSError as e:
        error_msg = f"Failed to create required folders: {str(e)}"
        logging.error(error_msg)
        raise BackgroundTaskError(error_msg) from e

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
        except BackgroundTaskError as e:
            logging.error(f"Failed to create required folders: {e}")
            raise

        logger = logging.getLogger(__name__)

        # Load configuration with error handling
        try:
            config = load_config(args.config_file)
        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            raise ConfigError(error_msg) from e

        # Load translations with fallback handling
        try:
            translations = load_translations(config["LANGUAGE"])
            logging.debug(f"Loaded translations keys: {sorted(translations.keys())}")
            TranslationManager.set_translations(translations)
            if not translations:
                attempted_language = config["LANGUAGE"]
                translations = {"log_ensured_folders_exist": "Ensured folders exist"}
                logging.warning(f"Translations failed to load for language '{attempted_language}', using fallback")
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
            async with TGraphBot(
                data_folder=args.data_folder,
                update_tracker=update_tracker,
                config=config,
                config_path=args.config_file,
                translations=translations,
            ) as bot:
                await bot.start(config["DISCORD_TOKEN"])
        except InitializationError as e:
            logger.error(f"Bot initialization failed: {e}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error during bot initialization: {e}"
            logger.error(error_msg)
            raise InitializationError(error_msg) from e
        finally:
            # Ensure bot is properly closed
            try:
                logger.info("Initiating bot shutdown sequence...")
                
                # Cancel all pending tasks except shutdown tasks
                pending = [t for t in asyncio.all_tasks() 
                        if t is not asyncio.current_task() 
                        and not t.done()]
                
                if pending:
                    logger.info(f"Cancelling {len(pending)} pending tasks...")
                    # Cancel all pending tasks
                    for task in pending:
                        task.cancel()
                    
                    try:
                        # Wait for all tasks to complete with timeout
                        # Return when all tasks are complete or when timeout occurs
                        await asyncio.wait(pending, timeout=5)
                        
                        # Check for tasks that didn't complete in time
                        remaining = [t for t in pending if not t.done()]
                        if remaining:
                            logger.warning(f"{len(remaining)} tasks did not complete in time")
                            
                    except asyncio.CancelledError:
                        logger.info("Shutdown tasks cancelled")
                    except Exception as e:
                        logger.error(f"Error while waiting for tasks to complete: {e}")

                # Close the bot connection
                try:
                    logger.info("Closing bot connection...")
                    await bot.close()
                except Exception as e:
                    logger.error(f"Error closing bot connection: {e}")
                    
                logger.info("Bot shutdown complete")
                
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")

    except Exception as e:
        if not isinstance(e, (InitializationError, ConfigError, BackgroundTaskError)):
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
