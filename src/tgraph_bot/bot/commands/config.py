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
from ...graphs.graph_modules.config.config_accessor import ConfigAccessor
from ...utils.discord.base_command_cog import BaseCommandCog
from ...utils.core.config_utils import ConfigurationHelper
from ...utils.core.exceptions import (
    ValidationError as TGraphValidationError,
    ConfigurationError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _set_nested_value(data: dict[str, object], path: str, value: object) -> None:
    """
    Set a nested value in a configuration dictionary using dot notation.

    Args:
        data: Configuration dictionary to modify
        path: Dot-separated path (e.g., "automation.scheduling.update_days")
        value: Value to set
    """
    keys = path.split(".")
    current: dict[str, object] = data

    # Navigate to the parent of the target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        if not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]  # pyright: ignore[reportAssignmentType] # We ensure it's a dict above

    # Set the final value
    current[keys[-1]] = value


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
        Get all available configuration keys using nested paths.

        Returns:
            List of nested configuration paths that users can use
        """
        return [
            # Service configuration
            "services.tautulli.api_key",
            "services.tautulli.url",
            "services.discord.token",
            "services.discord.channel_id",
            # Automation configuration
            "automation.scheduling.update_days",
            "automation.scheduling.fixed_update_time",
            "automation.data_retention.keep_days",
            # Data collection configuration
            "data_collection.time_ranges.days",
            "data_collection.time_ranges.months",
            "data_collection.privacy.censor_usernames",
            # System configuration
            "system.localization.language",
            # Graph features configuration
            "graphs.features.enabled_types.daily_play_count",
            "graphs.features.enabled_types.play_count_by_dayofweek",
            "graphs.features.enabled_types.play_count_by_hourofday",
            "graphs.features.enabled_types.top_10_platforms",
            "graphs.features.enabled_types.top_10_users",
            "graphs.features.enabled_types.play_count_by_month",
            "graphs.features.media_type_separation",
            "graphs.features.stacked_bar_charts",
            # Graph appearance configuration
            "graphs.appearance.dimensions.width",
            "graphs.appearance.dimensions.height",
            "graphs.appearance.dimensions.dpi",
            "graphs.appearance.colors.tv",
            "graphs.appearance.colors.movie",
            "graphs.appearance.colors.background",
            "graphs.appearance.grid.enabled",
            # Annotation configuration
            "graphs.appearance.annotations.basic.color",
            "graphs.appearance.annotations.basic.outline_color",
            "graphs.appearance.annotations.basic.enable_outline",
            "graphs.appearance.annotations.enabled_on.daily_play_count",
            "graphs.appearance.annotations.enabled_on.play_count_by_dayofweek",
            "graphs.appearance.annotations.enabled_on.play_count_by_hourofday",
            "graphs.appearance.annotations.enabled_on.top_10_platforms",
            "graphs.appearance.annotations.enabled_on.top_10_users",
            "graphs.appearance.annotations.enabled_on.play_count_by_month",
            # Palette configuration
            "graphs.appearance.palettes.daily_play_count",
            "graphs.appearance.palettes.play_count_by_dayofweek",
            "graphs.appearance.palettes.play_count_by_hourofday",
            "graphs.appearance.palettes.top_10_platforms",
            "graphs.appearance.palettes.top_10_users",
            "graphs.appearance.palettes.play_count_by_month",
        ]

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
            config_accessor = ConfigAccessor(config)

            # If a specific key is requested, show only that key
            if key is not None:
                try:
                    # Use ConfigAccessor to get the value
                    value: object = config_accessor.get_value(key)
                except ConfigurationError:
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
                    await self.send_ephemeral_response(interaction, embed=error_embed)
                    return

                # Provide a generic description for the configuration key
                description = i18n.translate("Configuration setting: {key}", key=key)

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
                await self.send_ephemeral_response(interaction, embed=embed)
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
                    f"**{i18n.translate('Tautulli URL')}:** {config.services.tautulli.url}\n"
                    f"**{i18n.translate('Channel ID')}:** {config.services.discord.channel_id}\n"
                    f"**{i18n.translate('Language')}:** {config.system.localization.language}"
                ),
                inline=False,
            )

            # Timing Settings
            _ = embed.add_field(
                name=i18n.translate("⏰ Timing & Retention"),
                value=(
                    f"**{i18n.translate('Update Days')}:** {config.automation.scheduling.update_days}\n"
                    f"**{i18n.translate('Fixed Update Time')}:** {config.automation.scheduling.fixed_update_time}\n"
                    f"**{i18n.translate('Keep Days')}:** {config.automation.data_retention.keep_days}\n"
                    f"**{i18n.translate('Time Range Days')}:** {config.data_collection.time_ranges.days}\n"
                    f"**{i18n.translate('Time Range Months')}:** {config.data_collection.time_ranges.months}"
                ),
                inline=True,
            )

            # Graph Options
            graph_options: list[str] = []
            if config.graphs.features.enabled_types.daily_play_count:
                graph_options.append(i18n.translate("Daily Play Count"))
            if config.graphs.features.enabled_types.play_count_by_dayofweek:
                graph_options.append(i18n.translate("Play Count by Day of Week"))
            if config.graphs.features.enabled_types.play_count_by_hourofday:
                graph_options.append(i18n.translate("Play Count by Hour of Day"))
            if config.graphs.features.enabled_types.top_10_platforms:
                graph_options.append(i18n.translate("Top 10 Platforms"))
            if config.graphs.features.enabled_types.top_10_users:
                graph_options.append(i18n.translate("Top 10 Users"))
            if config.graphs.features.enabled_types.play_count_by_month:
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
                    f"**{i18n.translate('Censor Usernames')}:** {i18n.translate('Yes') if config.data_collection.privacy.censor_usernames else i18n.translate('No')}\n"
                    f"**{i18n.translate('Graph Grid')}:** {i18n.translate('Enabled') if config.graphs.appearance.grid.enabled else i18n.translate('Disabled')}\n"
                    f"**{i18n.translate('Media Type Separation')}:** {i18n.translate('Enabled') if config.graphs.features.media_type_separation else i18n.translate('Disabled')}\n"
                    f"**{i18n.translate('Annotation Outline')}:** {i18n.translate('Enabled') if config.graphs.appearance.annotations.basic.enable_outline else i18n.translate('Disabled')}"
                ),
                inline=False,
            )

            # Colors
            _ = embed.add_field(
                name=i18n.translate("🎨 Colors"),
                value=(
                    f"**{i18n.translate('TV Color')}:** {config.graphs.appearance.colors.tv}\n"
                    f"**{i18n.translate('Movie Color')}:** {config.graphs.appearance.colors.movie}\n"
                    f"**{i18n.translate('Background')}:** {config.graphs.appearance.colors.background}\n"
                    f"**{i18n.translate('Annotation')}:** {config.graphs.appearance.annotations.basic.color}\n"
                    f"**{i18n.translate('Annotation Outline')}:** {config.graphs.appearance.annotations.basic.outline_color}"
                ),
                inline=True,
            )

            # Annotation Settings
            annotation_graphs: list[str] = []
            if config.graphs.appearance.annotations.enabled_on.daily_play_count:
                annotation_graphs.append(i18n.translate("Daily Play Count"))
            if config.graphs.appearance.annotations.enabled_on.play_count_by_dayofweek:
                annotation_graphs.append(i18n.translate("Play Count by Day of Week"))
            if config.graphs.appearance.annotations.enabled_on.play_count_by_hourofday:
                annotation_graphs.append(i18n.translate("Play Count by Hour of Day"))
            if config.graphs.appearance.annotations.enabled_on.top_10_platforms:
                annotation_graphs.append(i18n.translate("Top 10 Platforms"))
            if config.graphs.appearance.annotations.enabled_on.top_10_users:
                annotation_graphs.append(i18n.translate("Top 10 Users"))
            if config.graphs.appearance.annotations.enabled_on.play_count_by_month:
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
                    f"**{i18n.translate('Enabled')}:** {i18n.translate('Yes') if config.graphs.appearance.annotations.peaks.enabled else i18n.translate('No')}\n"
                    f"**{i18n.translate('Color')}:** {config.graphs.appearance.annotations.peaks.color}\n"
                    f"**{i18n.translate('Text Color')}:** {config.graphs.appearance.annotations.peaks.text_color}\n"
                    f"**{i18n.translate('Font Size')}:** {config.graphs.appearance.annotations.basic.font_size}"
                ),
                inline=False,
            )

            # Cooldown Settings
            _ = embed.add_field(
                name=i18n.translate("⏱️ Command Cooldowns"),
                value=(
                    f"**{i18n.translate('Config command per-user cooldown')}:** {config.rate_limiting.commands.config.user_cooldown_minutes}min\n"
                    f"**{i18n.translate('Config command global cooldown')}:** {config.rate_limiting.commands.config.global_cooldown_seconds}s\n"
                    f"**{i18n.translate('Update graphs command per-user cooldown')}:** {config.rate_limiting.commands.update_graphs.user_cooldown_minutes}min\n"
                    f"**{i18n.translate('Update graphs command global cooldown')}:** {config.rate_limiting.commands.update_graphs.global_cooldown_seconds}s\n"
                    f"**{i18n.translate('My stats command per-user cooldown')}:** {config.rate_limiting.commands.my_stats.user_cooldown_minutes}min\n"
                    f"**{i18n.translate('My stats command global cooldown')}:** {config.rate_limiting.commands.my_stats.global_cooldown_seconds}s"
                ),
                inline=False,
            )

            _ = embed.set_footer(
                text=i18n.translate(
                    "Use `/config edit <key> <value>` to modify settings"
                )
            )

            await self.send_ephemeral_response(interaction, embed=embed)

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
            config_accessor = ConfigAccessor(current_config)

            # Validate that the nested path exists and get current value
            try:
                current_value: object = config_accessor.get_nested_value(key)
            except ConfigurationError:
                raise TGraphValidationError(
                    f"Configuration setting '{key}' does not exist",
                    user_message=f"Configuration setting `{key}` does not exist. Use `/config view` to see all available settings.",
                ) from None

            # Convert the string value to the appropriate type
            try:
                converted_value = self._convert_config_value(value, type(current_value))
            except ValueError as e:
                raise TGraphValidationError(
                    f"Invalid value for setting '{key}': {e}",
                    user_message=f"Invalid value for `{key}`: {e}. Current value: {current_value!r} (type: {type(current_value).__name__})",
                )

            # Create updated configuration data with nested path
            config_data = current_config.model_dump()
            _set_nested_value(config_data, key, converted_value)

            # Validate the new configuration
            try:
                new_config = TGraphBotConfig(**config_data)  # pyright: ignore[reportAny] # dict unpacking
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

            await self.send_ephemeral_response(interaction, embed=success_embed)

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
