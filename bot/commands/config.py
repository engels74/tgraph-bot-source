# bot/commands/config.py

"""
Configuration command for TGraph Bot.
Handles viewing and modifying bot configuration settings.
"""

import discord
from discord import app_commands
import logging
import re
from discord.ext import commands
from typing import Optional, Literal

from config.modules.validator import validate_config_value
from config.modules.sanitizer import sanitize_config_value, format_value_for_display
from config.config import CONFIGURABLE_OPTIONS, RESTART_REQUIRED_KEYS
from config.modules.options import get_option_metadata
from config.modules.loader import load_yaml_config, update_config_value, save_yaml_config
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class ConfigCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling bot configuration commands."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        self.bot = bot
        self.config = config
        self.translations = translations
        super().__init__()

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
        try:
            if not await self.check_cooldowns(
                interaction,
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            ):
                return
        except Exception as e:
            logging.error(f"Error checking cooldowns: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while checking command cooldowns.",
                ephemeral=True
            )
            return

        if action == "view":
            await self._handle_view_config(interaction, key)
        elif action == "edit":
            await self._handle_edit_config(interaction, key, value)

        # Log successful command execution
        await self.log_command(interaction, f"config_{action}")
        
        # Update cooldowns after successful execution
        try:
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            )
        except Exception as e:
            logging.error(f"Error updating cooldowns: {str(e)}")

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
        current_lower = current.lower()
        matches = []
        
        # Try prefix match first (more relevant)
        for key in CONFIGURABLE_OPTIONS:
            if len(matches) >= 25:  # Discord limits choices to 25
                break
            if key.lower().startswith(current_lower):
                matches.append(app_commands.Choice(name=key, value=key))
        
        # If we still have room, try contains match
        if len(matches) < 25:
            for key in CONFIGURABLE_OPTIONS:
                if len(matches) >= 25:
                    break
                if current_lower in key.lower() and not key.lower().startswith(current_lower):
                    matches.append(app_commands.Choice(name=key, value=key))
        
        return matches

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
            # Create embed for all configurable values
            embed = discord.Embed(
                title="Bot Configuration",
                color=discord.Color.blue(),
                description="Current configuration values:"
            )
            
            # Group configuration options by type
            boolean_options = []
            color_options = []
            time_options = []
            other_options = []
            
            for key in CONFIGURABLE_OPTIONS:
                if key in self.config:
                    value = self.config[key]
                    display_value = format_value_for_display(key, value)
                    
                    # Categorize the option
                    if isinstance(value, bool):
                        boolean_options.append((key, display_value))
                    elif key.endswith('_COLOR'):
                        color_options.append((key, display_value))
                    elif key == 'FIXED_UPDATE_TIME':
                        time_options.append((key, display_value))
                    else:
                        other_options.append((key, display_value))
            
            # Add fields for each category if they have values
            if boolean_options:
                bool_text = "\n".join(f"**{k}:** {v}" for k, v in boolean_options)
                embed.add_field(name="Toggles", value=bool_text, inline=False)
            
            if color_options:
                color_text = "\n".join(f"**{k}:** {v}" for k, v in color_options)
                embed.add_field(name="Colors", value=color_text, inline=False)
            
            if time_options:
                time_text = "\n".join(f"**{k}:** {v}" for k, v in time_options)
                embed.add_field(name="Time Settings", value=time_text, inline=False)
            
            if other_options:
                other_text = "\n".join(f"**{k}:** {v}" for k, v in other_options)
                embed.add_field(name="Other Settings", value=other_text, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time string format (HH:MM)."""
        try:
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
                return False
            return True  # Regex already validated the ranges
        except (ValueError, TypeError):
            return False

    def _validate_color_format(self, value: str) -> bool:
        """Validate color string format (#RGB or #RRGGBB)."""
        return bool(re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value))

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
                ephemeral=True
            )
            return

        try:
            # Get metadata for the key
            get_option_metadata(key)
            
            # Process the value based on the key type
            if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR", "ANNOTATION_OUTLINE_COLOR"]:
                if not self._validate_color_format(value):
                    await interaction.response.send_message(
                        "Invalid color format. Use '#' followed by 3 or 6 hex digits. Example: #ff0000 or #f00",
                        ephemeral=True
                    )
                    return
            elif key == "FIXED_UPDATE_TIME":
                if value.upper() != "XX:XX" and not self._validate_time_format(value):
                    await interaction.response.send_message(
                        "Invalid time format. Please use HH:MM format (e.g., 14:30) or XX:XX to disable.",
                        ephemeral=True
                    )
                    return
            elif key in ["UPDATE_DAYS", "KEEP_DAYS", "TIME_RANGE_DAYS"]:
                num_value = self._validate_positive_int(value)
                if num_value is None:
                    await interaction.response.send_message(
                        f"{key} must be a positive number.",
                        ephemeral=True
                    )
                    return
                value = str(num_value)
            elif key.startswith(("ENABLE_", "ANNOTATE_", "CENSOR_")):
                value = value.lower() in ['true', '1', 'yes', 'on']
            elif key.endswith(("_COOLDOWN_MINUTES", "_COOLDOWN_SECONDS")):
                num_value = self._validate_non_negative_int(value)
                if num_value is None:
                    await interaction.response.send_message(
                        f"{key} must be a non-negative number.",
                        ephemeral=True
                    )
                    return
                value = str(num_value)

            # Validate and sanitize the new value
            if not validate_config_value(key, value):
                await interaction.response.send_message(
                    f"Invalid value for {key}: {value}",
                    ephemeral=True
                )
                return

            # Load current config preserving structure
            config = load_yaml_config(self.bot.config_path)
            old_value = config.get(key)
            
            # Sanitize the value
            sanitized_value = sanitize_config_value(key, value)
            
            # Update the specific value while preserving structure
            update_config_value(config, key, sanitized_value)
            
            # Save the updated config
            save_yaml_config(config, self.bot.config_path)
            
            # Update the bot's config reference
            self.config[key] = sanitized_value

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
                self.bot.translations = self.translations = await self._load_translations(value)
                await self._update_command_descriptions()
                
            # Update tracker if needed
            if key in ["UPDATE_DAYS", "FIXED_UPDATE_TIME"]:
                self.bot.update_tracker.update_config(self.config)

        except (ValueError, KeyError) as e:
            logging.error(f"Error updating config value: {str(e)}")
            await interaction.response.send_message(
                f"Error updating configuration: {str(e)}",
                ephemeral=True
            )

    def _validate_positive_int(self, value: str) -> Optional[int]:
        """Validate that the value is a positive integer."""
        try:
            num_value = int(value)
            if num_value <= 0:
                return None
            return num_value
        except ValueError:
            return None

    def _validate_non_negative_int(self, value: str) -> Optional[int]:
        """Validate that the value is a non-negative integer."""
        try:
            num_value = int(value)
            if num_value < 0:
                return None
            return num_value
        except ValueError:
            return None

    async def _load_translations(self, language: str) -> dict:
        """Load translations for the specified language."""
        from i18n import load_translations
        return await load_translations(language)

    async def _update_command_descriptions(self) -> None:
        """Update command descriptions after language change."""
        try:
            for command in self.bot.tree.get_commands():
                translation_key = f"{command.name}_command_description"
                if translation_key in self.translations:
                    command.description = self.translations[translation_key]
            await self.bot.tree.sync()
        except Exception as e:
            logging.error(f"Failed to update command descriptions: {str(e)}")
            # Don't raise the error as this is a non-critical operation

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
                await interaction.response.send_message(
                    f"Configuration error: {str(error)}",
                    ephemeral=True
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
