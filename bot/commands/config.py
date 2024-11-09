# bot/commands/config.py

"""
Configuration command for TGraph Bot.
Handles viewing and modifying bot configuration settings through slash commands.
"""

from config.config import (
    CONFIGURABLE_OPTIONS, 
    RESTART_REQUIRED_KEYS,
    validate_and_format_config_value,
    get_categorized_config
)
from config.modules.constants import get_category_display_name
from config.modules.loader import load_yaml_config, update_config_value, save_yaml_config
from config.modules.sanitizer import format_value_for_display
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging

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
        logging.info(self.translations["log_unloading_command"].format(
            command_name="config"
        ))

    async def create_config_embed(self) -> discord.Embed:
        """Create an embed showing current configuration."""
        embed = discord.Embed(
            title="Bot Configuration",
            color=discord.Color.blue(),
            description="Current configuration values:"
        )
        
        # Use get_categorized_config for organized config display
        categorized_config = get_categorized_config(self.config)
        
        for category, category_config in categorized_config.items():
            category_name = get_category_display_name(category)
            values = []
            for key, value in category_config.items():
                display_value = format_value_for_display(key, value)
                values.append(f"**{key}:** {display_value}")
            
            if values:  # Only add fields for categories with values
                embed.add_field(
                    name=category_name,
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
                    self.translations["config_error_invalid_key"],
                    ephemeral=True
                )
                return

            # Add await here
            formatted_value, error_message = await validate_and_format_config_value(
                key, value, self.translations
            )
            
            if error_message:
                logging.warning(f"Configuration validation error for {key}: {error_message}")
                await interaction.followup.send(
                    self.translations["config_error_validation"].format(error=error_message),
                    ephemeral=True
                )
                return
            
            if formatted_value is None:
                await interaction.followup.send(
                    self.translations["config_invalid_value"],
                    ephemeral=True
                )
                return

            config = load_yaml_config(self.bot.config_path)
            old_value = config.get(key)
            update_config_value(config, key, formatted_value)
            save_yaml_config(config, self.bot.config_path)
            self.config[key] = formatted_value

            # Get appropriate response message
            if key == "FIXED_UPDATE_TIME" and str(formatted_value).upper() == "XX:XX":
                response_message = self.translations["config_updated_fixed_time_disabled"].format(key=key)
            elif key in RESTART_REQUIRED_KEYS:
                response_message = self.translations["config_updated_restart"].format(key=key)
            else:
                response_message = self.translations["config_updated"].format(
                    key=key,
                    old_value=old_value,
                    new_value=formatted_value
                )

            await interaction.followup.send(response_message, ephemeral=True)

            # Handle special cases
            if key == "LANGUAGE":
                await self._update_language(value)
            elif key in ["UPDATE_DAYS", "FIXED_UPDATE_TIME"]:
                self.bot.update_tracker.update_config(self.config)

            await self.log_command(interaction, "config_edit")
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            )

        except Exception as e:
            logging.error(f"Unexpected error in config edit command: {str(e)}")
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

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handle application command errors."""
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            
            if isinstance(error, (ValueError, KeyError)):
                # Log the detailed error
                logging.error(f"Configuration error in {interaction.command.name}: {str(error)}")
                
                # Map specific errors to user-friendly messages
                error_key = "config_error_invalid_value"
                if isinstance(error, KeyError):
                    error_key = "config_error_invalid_key"
                
                # Send translated user-friendly message
                await interaction.response.send_message(
                    self.translations[error_key],
                    ephemeral=True
                )
                return
            
        await self.handle_error(interaction, error)

async def setup(bot: commands.Bot) -> None:
    """Setup function for the config cog."""
    await bot.add_cog(ConfigCog(bot))
