# bot/commands/config.py

"""
Configuration command for TGraph Bot.
Handles viewing and modifying bot configuration settings.
"""

import discord
from discord import app_commands
import logging
from discord.ext import commands
from typing import Optional, Literal

from config.modules.validator import validate_config_value
from config.modules.sanitizer import sanitize_config_value
from config.config import CONFIGURABLE_OPTIONS, RESTART_REQUIRED_KEYS
from config.modules.options import get_option_metadata
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class ConfigCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling bot configuration commands."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        self.bot = bot
        self.config = config
        self.translations = translations
        CommandMixin.__init__(self)  # Initialize command mixin

    @app_commands.command(
        name="config",
        description="View or edit bot configuration"
    )
    @app_commands.describe(
        action="Action to perform (view/edit)",
        key="Configuration key to view or edit",
        value="New value to set (for edit action)"
    )
    async def config(
        self,
        interaction: discord.Interaction,
        action: Literal["view", "edit"],
        key: Optional[str] = None,
        value: Optional[str] = None
    ) -> None:
        """View or edit bot configuration.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        action : Literal["view", "edit"]
            The action to perform (view/edit)
        key : Optional[str]
            Configuration key to view or edit
        value : Optional[str]
            New value to set (for edit action)
        """
        # Add cooldown check since this is a privileged command
        if not await self.check_cooldowns(interaction, 1, 30):  # 1 min user, 30 sec global
            return

        try:
            if action == "view":
                await self._handle_view_config(interaction, key)
            elif action == "edit":
                await self._handle_edit_config(interaction, key, value)

            # Log successful command execution
            await self.log_command(interaction, f"config_{action}")
            
            # Update cooldowns after successful execution
            self.update_cooldowns(str(interaction.user.id), 1, 30)

        except Exception as e:
            # For configuration-specific errors, we want custom handling
            if isinstance(e, (ValueError, KeyError)):
                await interaction.response.send_message(
                    f"Configuration error: {str(e)}", 
                    ephemeral=True
                )
            else:
                # For other errors, let the mixin handle it
                raise e

    @config.autocomplete('key')
    async def key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Provide autocomplete choices for key parameter.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        current : str
            The current input value

        Returns
        -------
        list[app_commands.Choice[str]]
            List of autocomplete choices
        """
        return [
            app_commands.Choice(name=key, value=key)
            for key in CONFIGURABLE_OPTIONS
            if current.lower() in key.lower()
        ][:25]  # Discord limits choices to 25

    async def _handle_view_config(
        self,
        interaction: discord.Interaction,
        key: Optional[str]
    ) -> None:
        """Handle viewing configuration values.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        key : Optional[str]
            Specific key to view, or None for all configurable values
        """
        if key:
            if key in self.config and key in CONFIGURABLE_OPTIONS:
                value = self.config[key]
                display_value = str(value).strip('"\'') if isinstance(value, (str, int, float, bool)) else str(value)
                await interaction.response.send_message(
                    f"{key}: {display_value}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    self.translations["config_view_invalid_key"].format(key=key),
                    ephemeral=True,
                )
        else:
            embed = discord.Embed(title="Bot Configuration", color=0x3498DB)
            for k, v in self.config.items():
                if k in CONFIGURABLE_OPTIONS:
                    display_value = str(v).strip('"\'') if isinstance(v, (str, int, float, bool)) else str(v)
                    embed.add_field(name=k, value=display_value, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_edit_config(
        self,
        interaction: discord.Interaction,
        key: Optional[str],
        value: Optional[str]
    ) -> None:
        """Handle editing configuration values.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        key : Optional[str]
            The key to edit
        value : Optional[str]
            The new value to set
        """
        if key is None:
            await interaction.response.send_message(
                self.translations["config_edit_specify_key"],
                ephemeral=True
            )
            return

        if value is None:
            await interaction.response.send_message(
                self.translations["config_edit_specify_value"],
                ephemeral=True
            )
            return

        if key not in CONFIGURABLE_OPTIONS:
            await interaction.response.send_message(
                self.translations["config_view_invalid_key"].format(key=key),
                ephemeral=True,
            )
            return

        try:
            # Get metadata for the key
            get_option_metadata(key)
            
            # Process the value based on the key type
            if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
                if not value.startswith("#"):
                    await interaction.response.send_message(
                        "Color value must start with '#'. Example: #ff0000", 
                        ephemeral=True
                    )
                    return
            elif key == "FIXED_UPDATE_TIME":
                if value.upper() != "XX:XX":
                    if not self._validate_time_format(value):
                        await interaction.response.send_message(
                            "Invalid time format. Please use HH:MM format (e.g., 14:30) or XX:XX to disable.", 
                            ephemeral=True
                        )
                        return
            elif key in ["UPDATE_DAYS", "KEEP_DAYS", "TIME_RANGE_DAYS", 
                        "MY_STATS_COOLDOWN_MINUTES", "MY_STATS_GLOBAL_COOLDOWN_SECONDS"]:
                try:
                    num_value = int(value)
                    if num_value <= 0:
                        await interaction.response.send_message(
                            f"{key} must be a positive number.", 
                            ephemeral=True
                        )
                        return
                    value = str(num_value)
                except ValueError:
                    await interaction.response.send_message(
                        f"{key} must be a number.", 
                        ephemeral=True
                    )
                    return
            elif key.startswith(("ENABLE_", "ANNOTATE_", "CENSOR_")):
                value = value.lower() in ['true', '1', 'yes', 'on']

            # Validate and sanitize the new value
            if not validate_config_value(key, value):
                await interaction.response.send_message(
                    f"Invalid value for {key}: {value}",
                    ephemeral=True
                )
                return

            # Sanitize the value
            sanitized_value = sanitize_config_value(key, value)
            old_value = self.config.get(key)
            
            # Update config
            self.config[key] = sanitized_value
            
            # Save configuration
            self._save_config()

            # Prepare response message
            if key == "FIXED_UPDATE_TIME" and str(sanitized_value).upper() == "XX:XX":
                response_message = self.translations["config_updated_fixed_time_disabled"].format(key=key)
            elif key in RESTART_REQUIRED_KEYS:
                response_message = self.translations["config_updated_restart"].format(key=key)
            else:
                response_message = self.translations["config_updated"].format(
                    key=key,
                    old_value=old_value,
                    new_value=sanitized_value
                )
            
            await interaction.response.send_message(response_message, ephemeral=True)

            # Special handling for language changes
            if key == "LANGUAGE":
                self.bot.translations = self.translations = self._load_translations(value)
                await self._update_command_descriptions()

        except Exception as e:
            logging.error(f"Error updating config value: {str(e)}")
            await interaction.response.send_message(
                f"Error updating configuration: {str(e)}", 
                ephemeral=True
            )

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time string format (HH:MM).

        Parameters
        ----------
        time_str : str
            The time string to validate

        Returns
        -------
        bool
            True if valid format, False otherwise
        """
        try:
            hours, minutes = map(int, time_str.split(':'))
            return 0 <= hours < 24 and 0 <= minutes < 60
        except (ValueError, TypeError):
            return False

    def _save_config(self) -> None:
        """Save the current configuration to disk."""
        from config.config import save_yaml_config
        save_yaml_config(self.config, self.bot.config_path)

    def _load_translations(self, language: str) -> dict:
        """Load translations for the specified language.

        Parameters
        ----------
        language : str
            The language code to load

        Returns
        -------
        dict
            The loaded translations
        """
        from i18n import load_translations
        return load_translations(language)

    async def _update_command_descriptions(self) -> None:
        """Update command descriptions after language change."""
        for command in self.bot.tree.get_commands():
            translation_key = f"{command.name}_command_description"
            if translation_key in self.translations:
                command.description = self.translations[translation_key]

    async def cog_app_command_error(self, 
                                  interaction: discord.Interaction, 
                                  error: app_commands.AppCommandError) -> None:
        """Custom error handler for configuration commands.
        Extends the mixin's error handler with configuration-specific handling.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        error : app_commands.AppCommandError
            The error that occurred
        """
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            
            # Handle configuration-specific errors
            if isinstance(error, (ValueError, KeyError)):
                await self.send_error_message(
                    interaction,
                    f"Configuration error: {str(error)}"
                )
                return
            
        # For all other errors, use the mixin's error handler
        await super().cog_app_command_error(interaction, error)

async def setup(bot: commands.Bot) -> None:
    """Setup function for the config cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    await bot.add_cog(ConfigCog(bot, bot.config, bot.translations))
