"""
Configuration command for TGraph Bot.

This module defines the /config slash command group (/config view, /config edit)
for viewing and modifying bot configuration settings with live editing capabilities.
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from pydantic import ValidationError

from ... import i18n
from ...config.manager import ConfigManager
from ...config.schema import TGraphBotConfig
from ...utils.discord.base_command_cog import BaseCommandCog
from ...utils.core.config_utils import ConfigurationHelper
from ...utils.core.exceptions import (
    ValidationError as TGraphValidationError,
    ConfigurationError,
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
        self.config_helper: ConfigurationHelper = ConfigurationHelper(
            self.tgraph_bot.config_manager
        )

    def _get_config_keys(self) -> list[str]:
        """
        Get all available configuration keys from the schema.

        Returns:
            List of configuration key names
        """
        return list(TGraphBotConfig.model_fields.keys())

    async def _config_key_autocomplete(
        self,
        interaction: discord.Interaction,  # pyright: ignore[reportUnusedParameter]
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """
        Autocomplete function for configuration keys.

        Args:
            interaction: The Discord interaction
            current: Current input from user

        Returns:
            List of autocomplete choices
        """
        config_keys = self._get_config_keys()

        # Filter keys based on current input
        if current:
            filtered_keys = [
                key for key in config_keys if current.lower() in key.lower()
            ]
        else:
            filtered_keys = config_keys

        # Limit to 25 choices (Discord limit) and sort alphabetically
        filtered_keys = sorted(filtered_keys)[:25]

        return [app_commands.Choice(name=key, value=key) for key in filtered_keys]

    def _convert_config_value(self, value: str, target_type: type[object]) -> object:
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
        if target_type is str:
            return value
        elif target_type is int:
            try:
                return int(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid integer")
        elif target_type is bool:
            lower_value = value.lower()
            if lower_value in ("true", "yes", "1", "on", "enabled"):
                return True
            elif lower_value in ("false", "no", "0", "off", "disabled"):
                return False
            else:
                raise ValueError(
                    f"'{value}' is not a valid boolean (use true/false, yes/no, 1/0, on/off, enabled/disabled)"
                )
        elif target_type is float:
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"'{value}' is not a valid number")
        else:
            # For other types, try direct conversion
            try:
                return target_type(value)  # pyright: ignore[reportCallIssue]
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert '{value}' to {target_type.__name__}")

    config_group: app_commands.Group = app_commands.Group(
        name="config", description=i18n.translate("View or edit bot configuration")
    )

    @config_group.command(
        name="view", description=i18n.translate("View current bot configuration")
    )
    @app_commands.describe(
        key=i18n.translate("Optional: View a specific configuration setting")
    )
    @app_commands.autocomplete(key=_config_key_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config_view(
        self, interaction: discord.Interaction, key: str | None = None
    ) -> None:
        """
        Display current bot configuration.

        Args:
            interaction: The Discord interaction
            key: Optional configuration key to view specifically
        """
        try:
            config = self.tgraph_bot.config_manager.get_current_config()

            # If a specific key is requested, show only that key
            if key is not None:
                if not hasattr(config, key):
                    error_embed = discord.Embed(
                        title=i18n.translate("❌ Configuration Key Not Found"),
                        description=i18n.translate(
                            "The configuration key `{key}` does not exist.", key=key
                        ),
                        color=discord.Color.red(),
                    )
                    _ = error_embed.add_field(
                        name=i18n.translate("Available Keys"),
                        value=i18n.translate(
                            "Use `/config view` to see all available configuration keys."
                        ),
                        inline=False,
                    )
                    _ = await interaction.response.send_message(
                        embed=error_embed, ephemeral=True
                    )
                    return

                # Get the value and its type
                value: object = getattr(config, key)  # pyright: ignore[reportAny]
                field_info = TGraphBotConfig.model_fields.get(key)
                description = (
                    field_info.description
                    if field_info
                    else i18n.translate("No description available")
                )

                # Create embed for specific key
                embed = discord.Embed(
                    title=i18n.translate("🔧 Configuration: {key}", key=key),
                    description=description,
                    color=discord.Color.blue(),
                )
                _ = embed.add_field(
                    name=i18n.translate("Current Value"),
                    value=f"`{value}`",
                    inline=True,
                )
                _ = embed.add_field(
                    name=i18n.translate("Type"),
                    value=f"`{type(value).__name__}`",
                    inline=True,
                )
                _ = embed.set_footer(
                    text=i18n.translate(
                        "Use `/config edit {key} <value>` to modify this setting",
                        key=key,
                    )
                )
                _ = await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create formatted configuration display for all settings
            embed = discord.Embed(
                title=i18n.translate("🔧 Bot Configuration"),
                description=i18n.translate("Current bot configuration settings"),
                color=discord.Color.blue(),
            )

            # Essential Settings
            _ = embed.add_field(
                name=i18n.translate("📡 Essential Settings"),
                value=(
                    f"**{i18n.translate('Tautulli URL')}:** {config.TAUTULLI_URL}\n"
                    f"**{i18n.translate('Channel ID')}:** {config.CHANNEL_ID}\n"
                    f"**{i18n.translate('Language')}:** {config.LANGUAGE}"
                ),
                inline=False,
            )

            # Timing Settings
            _ = embed.add_field(
                name=i18n.translate("⏰ Timing & Retention"),
                value=(
                    f"**{i18n.translate('Update Days')}:** {config.UPDATE_DAYS}\n"
                    f"**{i18n.translate('Fixed Update Time')}:** {config.FIXED_UPDATE_TIME}\n"
                    f"**{i18n.translate('Keep Days')}:** {config.KEEP_DAYS}\n"
                    f"**{i18n.translate('Time Range Days')}:** {config.TIME_RANGE_DAYS}\n"
                    f"**{i18n.translate('Time Range Months')}:** {config.TIME_RANGE_MONTHS}"
                ),
                inline=True,
            )

            # Graph Options
            graph_options: list[str] = []
            if config.ENABLE_DAILY_PLAY_COUNT:
                graph_options.append(i18n.translate("Daily Play Count"))
            if config.ENABLE_PLAY_COUNT_BY_DAYOFWEEK:
                graph_options.append(i18n.translate("Play Count by Day of Week"))
            if config.ENABLE_PLAY_COUNT_BY_HOUROFDAY:
                graph_options.append(i18n.translate("Play Count by Hour of Day"))
            if config.ENABLE_TOP_10_PLATFORMS:
                graph_options.append(i18n.translate("Top 10 Platforms"))
            if config.ENABLE_TOP_10_USERS:
                graph_options.append(i18n.translate("Top 10 Users"))
            if config.ENABLE_PLAY_COUNT_BY_MONTH:
                graph_options.append(i18n.translate("Play Count by Month"))

            _ = embed.add_field(
                name=i18n.translate("📊 Enabled Graphs"),
                value="\n".join(f"• {option}" for option in graph_options)
                if graph_options
                else i18n.translate("No graphs enabled"),
                inline=True,
            )

            # Graph Options
            _ = embed.add_field(
                name=i18n.translate("⚙️ Graph Options"),
                value=(
                    f"**{i18n.translate('Censor Usernames')}:** {i18n.translate('Yes') if config.CENSOR_USERNAMES else i18n.translate('No')}\n"
                    f"**{i18n.translate('Graph Grid')}:** {i18n.translate('Enabled') if config.ENABLE_GRAPH_GRID else i18n.translate('Disabled')}\n"
                    f"**{i18n.translate('Media Type Separation')}:** {i18n.translate('Enabled') if config.ENABLE_MEDIA_TYPE_SEPARATION else i18n.translate('Disabled')}\n"
                    f"**{i18n.translate('Annotation Outline')}:** {i18n.translate('Enabled') if config.ENABLE_ANNOTATION_OUTLINE else i18n.translate('Disabled')}"
                ),
                inline=False,
            )

            # Colors
            _ = embed.add_field(
                name=i18n.translate("🎨 Colors"),
                value=(
                    f"**{i18n.translate('TV Color')}:** {config.TV_COLOR}\n"
                    f"**{i18n.translate('Movie Color')}:** {config.MOVIE_COLOR}\n"
                    f"**{i18n.translate('Background')}:** {config.GRAPH_BACKGROUND_COLOR}\n"
                    f"**{i18n.translate('Annotation')}:** {config.ANNOTATION_COLOR}\n"
                    f"**{i18n.translate('Annotation Outline')}:** {config.ANNOTATION_OUTLINE_COLOR}"
                ),
                inline=True,
            )

            # Annotation Settings
            annotation_graphs: list[str] = []
            if config.ANNOTATE_DAILY_PLAY_COUNT:
                annotation_graphs.append(i18n.translate("Daily Play Count"))
            if config.ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK:
                annotation_graphs.append(i18n.translate("Play Count by Day of Week"))
            if config.ANNOTATE_PLAY_COUNT_BY_HOUROFDAY:
                annotation_graphs.append(i18n.translate("Play Count by Hour of Day"))
            if config.ANNOTATE_TOP_10_PLATFORMS:
                annotation_graphs.append(i18n.translate("Top 10 Platforms"))
            if config.ANNOTATE_TOP_10_USERS:
                annotation_graphs.append(i18n.translate("Top 10 Users"))
            if config.ANNOTATE_PLAY_COUNT_BY_MONTH:
                annotation_graphs.append(i18n.translate("Play Count by Month"))

            _ = embed.add_field(
                name=i18n.translate("📝 Annotations Enabled"),
                value="\n".join(f"• {option}" for option in annotation_graphs)
                if annotation_graphs
                else i18n.translate("No annotations enabled"),
                inline=True,
            )

            # Peak Annotations
            _ = embed.add_field(
                name=i18n.translate("🏔️ Peak Annotations"),
                value=(
                    f"**{i18n.translate('Enabled')}:** {i18n.translate('Yes') if config.ENABLE_PEAK_ANNOTATIONS else i18n.translate('No')}\n"
                    f"**{i18n.translate('Color')}:** {config.PEAK_ANNOTATION_COLOR}\n"
                    f"**{i18n.translate('Text Color')}:** {config.PEAK_ANNOTATION_TEXT_COLOR}\n"
                    f"**{i18n.translate('Font Size')}:** {config.ANNOTATION_FONT_SIZE}"
                ),
                inline=False,
            )

            # Cooldown Settings
            _ = embed.add_field(
                name=i18n.translate("⏱️ Command Cooldowns"),
                value=(
                    f"**{i18n.translate('Config command per-user cooldown')}:** {config.CONFIG_COOLDOWN_MINUTES}min\n"
                    f"**{i18n.translate('Config command global cooldown')}:** {config.CONFIG_GLOBAL_COOLDOWN_SECONDS}s\n"
                    f"**{i18n.translate('Update graphs command per-user cooldown')}:** {config.UPDATE_GRAPHS_COOLDOWN_MINUTES}min\n"
                    f"**{i18n.translate('Update graphs command global cooldown')}:** {config.UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS}s\n"
                    f"**{i18n.translate('My stats command per-user cooldown')}:** {config.MY_STATS_COOLDOWN_MINUTES}min\n"
                    f"**{i18n.translate('My stats command global cooldown')}:** {config.MY_STATS_GLOBAL_COOLDOWN_SECONDS}s"
                ),
                inline=False,
            )

            _ = embed.set_footer(
                text=i18n.translate(
                    "Use `/config edit <key> <value>` to modify settings"
                )
            )

            _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            # Use base class error handling
            await self.handle_command_error(interaction, e, "config_view")

    @config_group.command(
        name="edit", description=i18n.translate("Edit bot configuration")
    )
    @app_commands.describe(
        key=i18n.translate("The configuration setting to modify"),
        value=i18n.translate("The new value for the setting"),
    )
    @app_commands.autocomplete(key=_config_key_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config_edit(
        self, interaction: discord.Interaction, key: str, value: str
    ) -> None:
        """
        Edit a bot configuration setting.

        Args:
            interaction: The Discord interaction
            key: The configuration setting to modify
            value: The new value for the setting
        """
        try:
            # Get current configuration
            current_config = self.tgraph_bot.config_manager.get_current_config()

            # Validate that the setting exists
            if not hasattr(current_config, key):
                raise TGraphValidationError(
                    f"Configuration setting '{key}' does not exist",
                    user_message=f"Configuration setting `{key}` does not exist. Use `/config view` to see all available settings.",
                )

            # Get the current value and type
            current_value: object = getattr(current_config, key)  # pyright: ignore[reportAny]

            # Convert the string value to the appropriate type
            try:
                converted_value = self._convert_config_value(value, type(current_value))
            except ValueError as e:
                raise TGraphValidationError(
                    f"Invalid value for setting '{key}': {e}",
                    user_message=f"Invalid value for `{key}`: {e}. Current value: {current_value!r} (type: {type(current_value).__name__})",
                )

            # Create updated configuration data
            config_data = current_config.model_dump()
            config_data[key] = converted_value

            # Validate the new configuration
            try:
                new_config = TGraphBotConfig(**config_data)  # pyright: ignore[reportAny]
            except ValidationError as e:
                raise ConfigurationError(
                    f"Configuration validation failed: {e}",
                    user_message=f"Configuration validation failed: {e}",
                )

            # Save the configuration to file
            config_path = self.tgraph_bot.config_manager.config_file_path
            if config_path is None or not config_path.exists():
                raise ConfigurationError(
                    "Configuration file not found",
                    user_message="Configuration file not found. Please ensure it exists.",
                )

            ConfigManager.save_config(new_config, config_path)

            # Update runtime configuration
            self.tgraph_bot.config_manager.update_runtime_config(new_config)

            # Success message
            success_embed = discord.Embed(
                title=i18n.translate("✅ Configuration Updated"),
                description=i18n.translate("Successfully updated `{key}`", key=key),
                color=discord.Color.green(),
            )
            _ = success_embed.add_field(
                name=i18n.translate("Previous Value"),
                value=str(current_value),
                inline=True,
            )
            _ = success_embed.add_field(
                name=i18n.translate("New Value"),
                value=str(converted_value),
                inline=True,
            )
            _ = success_embed.set_footer(
                text=i18n.translate(
                    "Configuration changes require bot restart to take effect"
                )
            )

            _ = await interaction.response.send_message(
                embed=success_embed, ephemeral=True
            )

        except Exception as e:
            # Use base class error handling with additional context
            additional_context: dict[str, object] = {"key": key, "value": value}
            await self.handle_command_error(
                interaction, e, "config_edit", additional_context
            )


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(ConfigCog(bot))
