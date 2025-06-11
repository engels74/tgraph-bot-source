"""
Configuration command for TGraph Bot.

This module defines the /config slash command group (/config view, /config edit)
for viewing and modifying bot configuration settings with live editing capabilities.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import ValidationError

from config.manager import ConfigManager
from config.schema import TGraphBotConfig
from utils.base_command_cog import BaseCommandCog
from utils.config_utils import ConfigurationHelper
from utils.error_handler import (
    ValidationError as TGraphValidationError,
    ConfigurationError
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConfigCog(BaseCommandCog):
    """Cog for configuration management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the Config cog.

        Args:
            bot: The Discord bot instance
        """
        # Initialize base class (no cooldown needed for config commands)
        super().__init__(bot)

        # Create configuration helper
        self.config_helper: ConfigurationHelper = ConfigurationHelper(self.tgraph_bot.config_manager)

    def _convert_config_value(self, value: str, target_type: type) -> Any:  # pyright: ignore[reportExplicitAny]
        """
        Convert a string value to the appropriate configuration type.

        Args:
            value: The string value to convert
            target_type: The target type to convert to

        Returns:
            The converted value

        Raises:
            ValueError: If the value cannot be converted to the target type
        """
        if target_type == str:
            return value
        elif target_type == int:
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid integer")
        elif target_type == bool:
            lower_value = value.lower()
            if lower_value in ('true', 'yes', '1', 'on', 'enabled'):
                return True
            elif lower_value in ('false', 'no', '0', 'off', 'disabled'):
                return False
            else:
                raise ValueError(f"'{value}' is not a valid boolean (use true/false, yes/no, 1/0, on/off, enabled/disabled)")
        elif target_type == float:
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid number")
        else:
            # For other types, try direct conversion
            try:
                return target_type(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert '{value}' to {target_type.__name__}")

    config_group: app_commands.Group = app_commands.Group(
        name="config",
        description="View or edit bot configuration"
    )
    
    @config_group.command(
        name="view",
        description="View current bot configuration"
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config_view(self, interaction: discord.Interaction) -> None:
        """
        Display current bot configuration.

        Args:
            interaction: The Discord interaction
        """
        try:
            config = self.tgraph_bot.config_manager.get_current_config()

            # Create formatted configuration display
            embed = discord.Embed(
                title="🔧 Bot Configuration",
                description="Current configuration settings",
                color=discord.Color.blue()
            )

            # Essential Settings
            _ = embed.add_field(
                name="📡 Essential Settings",
                value=(
                    f"**Tautulli URL:** {config.TAUTULLI_URL}\n"
                    f"**Channel ID:** {config.CHANNEL_ID}\n"
                    f"**Language:** {config.LANGUAGE}"
                ),
                inline=False
            )

            # Timing Settings
            _ = embed.add_field(
                name="⏰ Timing & Retention",
                value=(
                    f"**Update Days:** {config.UPDATE_DAYS}\n"
                    f"**Fixed Update Time:** {config.FIXED_UPDATE_TIME}\n"
                    f"**Keep Days:** {config.KEEP_DAYS}\n"
                    f"**Time Range Days:** {config.TIME_RANGE_DAYS}"
                ),
                inline=True
            )

            # Graph Options
            graph_options: list[str] = []
            if config.ENABLE_DAILY_PLAY_COUNT:
                graph_options.append("Daily Play Count")
            if config.ENABLE_PLAY_COUNT_BY_DAYOFWEEK:
                graph_options.append("By Day of Week")
            if config.ENABLE_PLAY_COUNT_BY_HOUROFDAY:
                graph_options.append("By Hour of Day")
            if config.ENABLE_TOP_10_PLATFORMS:
                graph_options.append("Top 10 Platforms")
            if config.ENABLE_TOP_10_USERS:
                graph_options.append("Top 10 Users")
            if config.ENABLE_PLAY_COUNT_BY_MONTH:
                graph_options.append("By Month")

            _ = embed.add_field(
                name="📊 Enabled Graphs",
                value="\n".join(f"• {option}" for option in graph_options) if graph_options else "None enabled",
                inline=True
            )

            # Additional Options
            _ = embed.add_field(
                name="⚙️ Options",
                value=(
                    f"**Censor Usernames:** {'Yes' if config.CENSOR_USERNAMES else 'No'}\n"
                    f"**Graph Grid:** {'Enabled' if config.ENABLE_GRAPH_GRID else 'Disabled'}\n"
                    f"**Annotation Outline:** {'Enabled' if config.ENABLE_ANNOTATION_OUTLINE else 'Disabled'}"
                ),
                inline=False
            )

            _ = embed.set_footer(text="Use /config edit to modify settings")

            _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            # Use base class error handling
            await self.handle_command_error(interaction, e, "config_view")
        
    @config_group.command(
        name="edit",
        description="Edit bot configuration"
    )
    @app_commands.describe(
        setting="The configuration setting to modify",
        value="The new value for the setting"
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config_edit(
        self,
        interaction: discord.Interaction,
        setting: str,
        value: str
    ) -> None:
        """
        Edit a bot configuration setting.

        Args:
            interaction: The Discord interaction
            setting: The configuration setting to modify
            value: The new value for the setting
        """
        try:
            # Get current configuration
            current_config = self.tgraph_bot.config_manager.get_current_config()

            # Validate that the setting exists
            if not hasattr(current_config, setting):
                raise TGraphValidationError(
                    f"Configuration setting '{setting}' does not exist",
                    user_message=f"Configuration setting `{setting}` does not exist. Use `/config view` to see all available settings."
                )

            # Get the current value and type
            current_value: Any = getattr(current_config, setting)  # pyright: ignore[reportExplicitAny]

            # Convert the string value to the appropriate type
            try:
                converted_value: Any = self._convert_config_value(value, type(current_value))  # pyright: ignore[reportExplicitAny]
            except ValueError as e:
                raise TGraphValidationError(
                    f"Invalid value for setting '{setting}': {e}",
                    user_message=f"Invalid value for `{setting}`: {e}. Current value: {current_value} (type: {type(current_value).__name__})"
                )

            # Create updated configuration data
            config_data = current_config.model_dump()
            config_data[setting] = converted_value

            # Validate the new configuration
            try:
                new_config = TGraphBotConfig(**config_data)
            except ValidationError as e:
                raise ConfigurationError(
                    f"Configuration validation failed: {e}",
                    user_message=f"Configuration validation failed: {e}"
                )

            # Save the configuration to file
            config_path = Path("config.yml")
            if not config_path.exists():
                raise ConfigurationError(
                    "config.yml file not found",
                    user_message="config.yml file not found. Please ensure it exists."
                )

            ConfigManager.save_config(new_config, config_path)

            # Update runtime configuration
            self.tgraph_bot.config_manager.update_runtime_config(new_config)

            # Success message
            success_embed = discord.Embed(
                title="✅ Configuration Updated",
                description=f"Successfully updated `{setting}`",
                color=discord.Color.green()
            )
            _ = success_embed.add_field(
                name="Previous Value",
                value=str(current_value),
                inline=True
            )
            _ = success_embed.add_field(
                name="New Value",
                value=str(converted_value),
                inline=True
            )
            _ = success_embed.set_footer(text="Configuration saved and applied immediately")

            _ = await interaction.response.send_message(embed=success_embed, ephemeral=True)

        except Exception as e:
            # Use base class error handling with additional context
            additional_context: dict[str, object] = {
                "setting": setting,
                "value": value
            }
            await self.handle_command_error(interaction, e, "config_edit", additional_context)


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(ConfigCog(bot))
