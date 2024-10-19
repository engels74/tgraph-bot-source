# bot/commands/config.py

"""
Configuration command for TGraph Bot.
Handles viewing and modifying bot configuration settings through slash commands.
"""

import discord
from discord import app_commands
import logging
import re
from discord.ext import commands
from typing import Optional, Any, List
from config.modules.validator import validate_config_value
from config.modules.sanitizer import sanitize_config_value, format_value_for_display
from config.config import CONFIGURABLE_OPTIONS, RESTART_REQUIRED_KEYS
from config.modules.constants import CONFIG_CATEGORIES, get_category_keys, get_category_display_name
from config.modules.loader import load_yaml_config, update_config_value, save_yaml_config
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class ConfigCog(commands.GroupCog, CommandMixin, ErrorHandlerMixin, name="config", description="View and edit bot configuration"):
    """
    Cog for handling bot configuration commands.
    Implements configuration viewing and editing functionality.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = bot.config
        self.translations = bot.translations
        # Initialize mixins first
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        # Initialize GroupCog last
        super().__init__()

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        logging.info(self.translations["log_commands_cog_loaded"])

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logging.info(self.translations["log_unloading_command"].format(command_name="config"))

    async def create_config_embed(self) -> discord.Embed:
        """Create an embed showing current configuration."""
        embed = discord.Embed(
            title="Bot Configuration",
            color=discord.Color.blue(),
            description="Current configuration values:"
        )
        
        for category in CONFIG_CATEGORIES:
            category_keys = get_category_keys(category)
            if category_keys:
                configurable_keys = [k for k in category_keys if k in CONFIGURABLE_OPTIONS]
                if configurable_keys:
                    values = []
                    for key in configurable_keys:
                        if key in self.config:
                            value = self.config[key]
                            display_value = format_value_for_display(key, value)
                            values.append(f"**{key}:** {display_value}")
                    
                    if values:
                        embed.add_field(
                            name=get_category_display_name(category),
                            value="\n".join(values),
                            inline=False
                        )

        return embed

    @app_commands.command()
    @app_commands.describe(key="Specific configuration key to view (optional)")
    async def view(
        self,
        interaction: discord.Interaction,
        key: Optional[str] = None
    ) -> None:
        """View configuration settings.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        key : Optional[str]
            Specific configuration key to view
        """
        try:
            if not await self.check_cooldowns(
                interaction,
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            ):
                return

            if key:
                if key in self.config and key in CONFIGURABLE_OPTIONS:
                    value = self.config[key]
                    display_value = format_value_for_display(key, value)
                    await interaction.response.send_message(
                        f"{key}: {display_value}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        self.translations["config_view_invalid_key"].format(key=key),
                        ephemeral=True
                    )
            else:
                embed = await self.create_config_embed()
                await interaction.response.send_message(embed=embed, ephemeral=True)

            await self.log_command(interaction, "config_view")
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            )
            
        except Exception as e:
            await self.handle_command_error(interaction, e, "config_view")

    @app_commands.command()
    @app_commands.describe(
        key="Configuration key to edit",
        value="New value to set"
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        key: str,
        value: str
    ) -> None:
        """Edit a configuration setting.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        key : str
            Configuration key to edit
        value : str
            New value to set
        """
        if not await self.check_cooldowns(
            interaction,
            self.config["CONFIG_COOLDOWN_MINUTES"],
            self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
        ):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if key not in CONFIGURABLE_OPTIONS:
                await interaction.followup.send(
                    self.translations["config_view_invalid_key"].format(key=key),
                    ephemeral=True
                )
                return

            value = await self._process_config_value(interaction, key, value)
            if value is None:
                return

            config = load_yaml_config(self.bot.config_path)
            old_value = config.get(key)
            sanitized_value = sanitize_config_value(key, value)
            update_config_value(config, key, sanitized_value)
            save_yaml_config(config, self.bot.config_path)
            self.config[key] = sanitized_value

            response_message = await self._get_config_update_message(key, old_value, sanitized_value)
            await interaction.followup.send(response_message, ephemeral=True)

            if key == "LANGUAGE":
                await self._update_language(value)

            if key in ["UPDATE_DAYS", "FIXED_UPDATE_TIME"]:
                self.bot.update_tracker.update_config(self.config)

            await self.log_command(interaction, "config_edit")
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            )

        except Exception as e:
            await self.handle_command_error(interaction, e, "config_edit")

    @view.autocomplete('key')
    async def view_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for view command's key parameter."""
        return [
            app_commands.Choice(name=key, value=key)
            for key in CONFIGURABLE_OPTIONS
            if current.lower() in key.lower()
        ][:25]

    @edit.autocomplete('key')
    async def edit_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for edit command's key parameter."""
        return [
            app_commands.Choice(name=key, value=key)
            for key in CONFIGURABLE_OPTIONS
            if current.lower() in key.lower()
        ][:25]

    async def _process_config_value(
        self,
        interaction: discord.Interaction,
        key: str,
        value: str
    ) -> Optional[Any]:
        """Process and validate a configuration value."""
        try:
            if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"]:
                if not self._validate_color_format(value):
                    await interaction.followup.send(
                        "Invalid color format. Use '#' followed by 3 or 6 hex digits. Example: #ff0000 or #f00",
                        ephemeral=True
                    )
                    return None
                    
            elif key == "FIXED_UPDATE_TIME":
                if value.upper() != "XX:XX" and not self._validate_time_format(value):
                    await interaction.followup.send(
                        "Invalid time format. Please use HH:MM format (e.g., 14:30) or XX:XX to disable.",
                        ephemeral=True
                    )
                    return None

            elif key in ["UPDATE_DAYS", "KEEP_DAYS", "TIME_RANGE_DAYS"]:
                num_value = self._validate_positive_int(value)
                if num_value is None:
                    await interaction.followup.send(
                        f"{key} must be a positive number.",
                        ephemeral=True
                    )
                    return None
                value = str(num_value)

            elif key.startswith(("ENABLE_", "ANNOTATE_", "CENSOR_")):
                value = value.lower() in ['true', '1', 'yes', 'on']

            elif key.endswith(("_COOLDOWN_MINUTES", "_COOLDOWN_SECONDS")):
                num_value = self._validate_non_negative_int(value)
                if num_value is None:
                    await interaction.followup.send(
                        f"{key} must be a non-negative number.",
                        ephemeral=True
                    )
                    return None
                value = str(num_value)

            if not validate_config_value(key, value):
                await interaction.followup.send(
                    f"Invalid value for {key}: {value}",
                    ephemeral=True
                )
                return None

            return value

        except Exception as e:
            logging.error(f"Error processing config value: {str(e)}")
            return None

    async def _get_config_update_message(self, key: str, old_value: Any, new_value: Any) -> str:
        """Get appropriate message for configuration update."""
        if key == "FIXED_UPDATE_TIME" and str(new_value).upper() == "XX:XX":
            return self.translations["config_updated_fixed_time_disabled"].format(key=key)
        elif key in RESTART_REQUIRED_KEYS:
            return self.translations["config_updated_restart"].format(key=key)
        else:
            return self.translations["config_updated"].format(
                key=key,
                old_value=old_value,
                new_value=new_value
            )

    async def _update_language(self, language: str) -> None:
        """Update bot language settings."""
        from i18n import load_translations
        self.bot.translations = self.translations = await load_translations(language)
        await self._update_command_descriptions()

    async def _update_command_descriptions(self) -> None:
        """Update command descriptions after language change."""
        try:
            commands = self.bot.tree.get_commands()
            for command in commands:
                if isinstance(command, app_commands.Group):
                    if command.name == "config":
                        for subcmd in command.commands:
                            translation_key = f"config_{subcmd.name}_command_description"
                            if translation_key in self.translations:
                                subcmd.description = self.translations[translation_key]
                else:
                    translation_key = f"{command.name}_command_description"
                    if translation_key in self.translations:
                        command.description = self.translations[translation_key]

            await self.bot.tree.sync()
            logging.info(self.translations["log_command_descriptions_updated"])
        except Exception as e:
            logging.error(f"Failed to update command descriptions: {str(e)}")

    def _validate_color_format(self, value: str) -> bool:
        """Validate color string format (#RGB or #RRGGBB)."""
        return bool(re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value))

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time string format (HH:MM)."""
        if time_str.upper() == "XX:XX":
            return True
        return bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str))

    def _validate_positive_int(self, value: str) -> Optional[int]:
        """Validate and convert positive integer."""
        try:
            num = int(value)
            return num if num > 0 else None
        except ValueError:
            return None

    def _validate_non_negative_int(self, value: str) -> Optional[int]:
        """Validate and convert non-negative integer."""
        try:
            num = int(value)
            return num if num >= 0 else None
        except ValueError:
            return None

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handle application command errors."""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            
            if isinstance(error, (ValueError, KeyError)):
                await interaction.response.send_message(
                    f"Configuration error: {str(error)}",
                    ephemeral=True
                )
                return
            
        await self.handle_error(interaction, error)

async def setup(bot: commands.Bot) -> None:
    """Setup function for the config cog."""
    await bot.add_cog(ConfigCog(bot))
