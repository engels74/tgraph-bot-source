"""
Update Graphs command for TGraph Bot.

This module implements the functionality to manually update and post server-wide graphs 
through a Discord slash command. It includes robust error handling, resource management,
and proper integration with the bot's configuration and translation systems.
"""

from config.config import load_config
from discord import app_commands
from discord.ext import commands
from typing import Dict, Any
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging

class UpdateGraphsError(Exception):
    """Base exception for update graphs command errors."""
    pass

class ConfigReloadError(UpdateGraphsError):
    """Raised when configuration reload fails."""
    pass

class ChannelError(UpdateGraphsError):
    """Raised when there are channel-related errors."""
    pass

class GraphError(UpdateGraphsError):
    """Raised when graph generation or posting fails."""
    pass

class UpdateGraphsCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """
    A cog that handles manual updates of server-wide graphs.
    
    This cog provides functionality to manually trigger graph updates and posting
    through Discord slash commands. It includes proper error handling, resource
    management, and configuration reloading.

    Attributes:
        bot (commands.Bot): The bot instance
        config (Dict[str, Any]): Configuration dictionary
        translations (Dict[str, str]): Translation strings dictionary
    """
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        """
        Initialize the UpdateGraphs cog.
        
        Args:
            bot: The bot instance to attach the cog to
            config: Configuration dictionary
            translations: Translation strings dictionary
            
        Raises:
            AttributeError: If bot is missing required attributes
        """
        # Initialize parent classes explicitly
        commands.Cog.__init__(self)
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        
        self.bot = bot
        self.config = config
        self.translations = translations
        
        # Verify required bot attributes
        required_attrs = ['update_tracker', 'graph_manager', 'data_fetcher']
        missing_attrs = [attr for attr in required_attrs if not hasattr(bot, attr)]
        if missing_attrs:
            raise AttributeError(
                f"Bot instance missing required attributes: {', '.join(missing_attrs)}"
            )

    def reload_config(self) -> Dict[str, Any]:
        """
        Reload the configuration from disk with proper error handling.
        
        Returns:
            The updated configuration dictionary
            
        Raises:
            ConfigReloadError: If configuration reload fails
        """
        try:
            return load_config(reload=True)
        except Exception as e:
            error_msg = self.translations.get(
                'error_config_reload',
                'Error reloading configuration: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise ConfigReloadError(error_msg) from e

    async def get_target_channel(self, interaction: discord.Interaction) -> discord.TextChannel:
        """
        Get and validate the target channel for posting graphs.
        
        Args:
            interaction: The Discord interaction instance
            
        Returns:
            The target Discord text channel
            
        Raises:
            ChannelError: If channel cannot be found or accessed
        """
        try:
            channel_id = self.config.get("CHANNEL_ID")
            if not channel_id:
                error_msg = self.translations.get(
                    'error_missing_channel_id',
                    'Channel ID not found in configuration.'
                )
                raise ChannelError(error_msg)
                
            try:
                channel_id = int(channel_id)
            except (ValueError, TypeError) as e:
                error_msg = self.translations.get(
                    'error_invalid_channel_id',
                    'Invalid channel ID in configuration: {error}'
                ).format(error=str(e))
                raise ChannelError(error_msg) from e
                
            channel = self.bot.get_channel(channel_id)
            if not channel:
                error_msg = self.translations.get(
                    'error_channel_not_found',
                    'Channel with ID {channel_id} not found'
                ).format(channel_id=channel_id)
                raise ChannelError(error_msg)
                
            return channel
            
        except Exception as e:
            if isinstance(e, ChannelError):
                raise
            error_msg = self.translations.get(
                'error_channel_access',
                'Error accessing target channel: {error}'
            ).format(error=str(e))
            raise ChannelError(error_msg) from e

    @app_commands.command(
        name="update_graphs",
        description="Update and post server-wide graphs"
    )
    async def update_graphs(self, interaction: discord.Interaction) -> None:
        """
        Update and post server-wide graphs command handler.

        This command handler:
        1. Checks cooldowns and permissions
        2. Reloads configuration
        3. Updates tracker configuration
        4. Gets target channel
        5. Deletes old messages
        6. Generates and posts new graphs
        7. Updates tracker with new timing

        Args:
            interaction: The Discord interaction instance
        """
        if not await self.check_cooldowns(
            interaction,
            self.config["UPDATE_GRAPHS_COOLDOWN_MINUTES"],
            self.config["UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS"]
        ):
            return
            
        try:
            # Defer response since this operation takes time
            await interaction.response.defer(ephemeral=True)
            logging.info(self.translations["log_manual_update_started"])

            try:
                # Reload config and update tracker
                self.config = self.bot.config = self.reload_config()
                self.bot.update_tracker.update_config(self.config)
            except ConfigReloadError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

            try:
                # Get and validate target channel
                channel = await self.get_target_channel(interaction)
            except ChannelError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

            try:
                # Delete old messages and generate new graphs
                await self.bot.graph_manager.delete_old_messages(channel)
                graph_files = await self.bot.graph_manager.generate_and_save_graphs(
                    self.bot.data_fetcher
                )
                
                if not graph_files:
                    error_msg = self.translations.get(
                        'error_no_graphs_generated',
                        'No graphs were generated'
                    )
                    raise GraphError(error_msg)
                    
                # Post new graphs
                await self.bot.graph_manager.post_graphs(
                    channel,
                    graph_files,
                    self.bot.update_tracker
                )
                
            except Exception as e:
                error_msg = self.translations.get(
                    'error_graph_operation',
                    'Error during graph operations: {error}'
                ).format(error=str(e))
                raise GraphError(error_msg) from e

            # Update tracker and cooldowns
            self.bot.update_tracker.update()
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["UPDATE_GRAPHS_COOLDOWN_MINUTES"],
                self.config["UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS"]
            )

            # Log command execution
            await self.log_command(interaction, "update_graphs")

            # Send success message
            await interaction.followup.send(
                self.translations["update_graphs_success"].format(
                    next_update=self.bot.update_tracker.get_next_update_discord()
                ),
                ephemeral=True
            )
            
            logging.info(
                self.translations["log_manual_update_completed"].format(
                    next_update=self.bot.update_tracker.get_next_update_readable()
                )
            )

        except Exception as e:
            await self.handle_command_error(interaction, e, "update_graphs")

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        logging.info(self.translations["log_commands_cog_loaded"])

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logging.info(self.translations["log_unloading_command"].format(
            command_name="update_graphs"
        ))

async def setup(bot: commands.Bot) -> None:
    """
    Setup function for the update_graphs cog.
    
    Args:
        bot: The bot instance to add the cog to
        
    Raises:
        AttributeError: If bot is missing required attributes
    """
    # Verify bot has required attributes before adding cog
    required_attrs = ['config', 'translations', 'update_tracker', 'graph_manager', 'data_fetcher']
    missing_attrs = [attr for attr in required_attrs if not hasattr(bot, attr)]
    if missing_attrs:
        raise AttributeError(
            f"Bot instance missing required attributes: {', '.join(missing_attrs)}"
        )
        
    await bot.add_cog(UpdateGraphsCog(bot, bot.config, bot.translations))
