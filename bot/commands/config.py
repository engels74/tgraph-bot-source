# bot/commands/config.py

"""
Configuration command module for TGraph Bot.

This module implements configuration viewing and editing functionality through Discord
slash commands. It provides a secure and validated interface for managing bot settings
with proper error handling, resource management, and internationalization support.

Classes:
    ConfigCommandError: Base exception for configuration command errors
    ConfigValidationError: Raised when configuration validation fails
    ConfigUpdateError: Raised when configuration update operations fail
    ConfigViewError: Raised when configuration view operations fail
    ConfigEmbedError: Raised when creating config embeds fails
    ConfigCog: Main configuration command handler
"""

from asyncio import Lock
from config.config import (
    CONFIGURABLE_OPTIONS, 
    RESTART_REQUIRED_KEYS,
    validate_and_format_config_value,
    get_categorized_config,
    ConfigError,
    ConfigValidationError as BaseConfigValidationError
)
from config.modules.constants import get_category_display_name
from config.modules.loader import load_yaml_config, update_config_value, save_yaml_config
from config.modules.options import get_option_metadata
from config.modules.sanitizer import format_value_for_display
from discord import app_commands, Embed, Color
from discord.ext import commands
from typing import Optional, List
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging

class ConfigCommandError(Exception):
    """Base exception for configuration command errors."""
    pass

class ConfigValidationError(ConfigCommandError):
    """Raised when configuration validation fails."""
    pass

class ConfigUpdateError(ConfigCommandError):
    """Raised when configuration update operations fail."""
    pass

class ConfigViewError(ConfigCommandError):
    """Raised when configuration view operations fail."""
    pass

class ConfigEmbedError(ConfigCommandError):
    """Raised when creating config embeds fails."""
    pass

class ConfigCog(commands.GroupCog, CommandMixin, ErrorHandlerMixin, name="config"):
    """Configuration management commands for bot settings and preferences"""
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the configuration cog.
        
        Args:
            bot: The bot instance to attach the cog to
            
        Raises:
            ConfigCommandError: If initialization fails
        """
        try:
            self.bot = bot
            self.config = bot.config
            self.translations = bot.translations
            self._config_lock = Lock()
            
            # Initialize mixins first
            CommandMixin.__init__(self)
            ErrorHandlerMixin.__init__(self)
            
            # Initialize GroupCog last
            super().__init__()
            
        except Exception as e:
            error_msg = "Failed to initialize configuration cog"
            logging.error(f"{error_msg}: {str(e)}")
            raise ConfigCommandError(error_msg) from e

    async def create_config_embed(self) -> Embed:
        """
        Create an embed showing current configuration.
        
        Returns:
            discord.Embed: The formatted configuration embed
            
        Raises:
            ConfigEmbedError: If embed creation fails
        """
        try:
            embed = Embed(
                title="Bot Configuration",
                color=Color.blue(),
                description="Current configuration values:"
            )
            
            # Use get_categorized_config for organized display
            categorized_config = get_categorized_config(self.config)
            
            for category, category_config in categorized_config.items():
                category_name = get_category_display_name(category)
                values = []
                
                for key, value in category_config.items():
                    try:
                        display_value = format_value_for_display(key, value)
                        values.append(f"**{key}:** {display_value}")
                    except Exception as e:
                        logging.warning(f"Failed to format value for {key}: {e}")
                        values.append(f"**{key}:** [format error]")
                
                if values:  # Only add fields for categories with values
                    embed.add_field(
                        name=category_name,
                        value="\n".join(values),
                        inline=False
                    )
            
            return embed
            
        except Exception as e:
            error_msg = "Failed to create configuration embed"
            logging.error(f"{error_msg}: {str(e)}")
            raise ConfigEmbedError(error_msg) from e

    @app_commands.command(name="view", description="View configuration settings")
    @app_commands.describe(key="Specific configuration key to view (optional)")
    async def view(
        self,
        interaction: discord.Interaction,
        key: Optional[str] = None
    ) -> None:
        """
        View current configuration settings.

        Args:
            interaction: The Discord interaction
            key: Optional specific key to view
            
        Raises:
            ConfigViewError: If view operation fails
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
                    try:
                        value = self.config[key]
                        display_value = format_value_for_display(key, value)
                        await interaction.response.send_message(
                            f"{key}: {display_value}",
                            ephemeral=True
                        )
                    except Exception as e:
                        error_msg = f"Failed to format configuration value for {key}"
                        logging.error(f"{error_msg}: {str(e)}")
                        raise ConfigViewError(error_msg) from e
                else:
                    await interaction.response.send_message(
                        self.translations["config_view_invalid_key"].format(key=key),
                        ephemeral=True
                    )
            else:
                try:
                    embed = await self.create_config_embed()
                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True
                    )
                except ConfigEmbedError as e:
                    raise ConfigViewError("Failed to create configuration view") from e

            await self.log_command(interaction, "config_view")
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["CONFIG_COOLDOWN_MINUTES"],
                self.config["CONFIG_GLOBAL_COOLDOWN_SECONDS"]
            )

        except Exception as e:
            if not isinstance(e, ConfigViewError):
                error_msg = "Unexpected error viewing configuration"
                logging.error(f"{error_msg}: {str(e)}")
                raise ConfigViewError(error_msg) from e
            await self.handle_command_error(interaction, e, "config_view")

    @app_commands.command(name="edit", description="Edit a configuration setting")
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
        """
        Edit a configuration setting.
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

            # Handle special case where value is "null", "none", or "XX:XX" for FIXED_UPDATE_TIME
            if value and (
                value.lower() in ("null", "none") or
                (key == "FIXED_UPDATE_TIME" and value.upper() == "XX:XX")
            ):
                value = None

            # Validate and format the value
            formatted_value, error_message = await validate_and_format_config_value(
                key, value, self.translations
            )
            
            if error_message:
                await interaction.followup.send(
                    error_message,
                    ephemeral=True
                )
                return
            
            # Check if None is allowed for this key
            metadata = get_option_metadata(key)
            if formatted_value is None:
                if metadata.get("required", False) and key != "FIXED_UPDATE_TIME":
                    raise ConfigValidationError(
                        self.translations.get(
                            "config_error_required_field",
                            "This configuration option cannot be empty or null"
                        )
                    )
                # Special handling for FIXED_UPDATE_TIME
                if key == "FIXED_UPDATE_TIME":
                    formatted_value = "XX:XX"  # Convert None back to XX:XX for storage

            try:
                async with self._config_lock:
                    # Load fresh config
                    config = load_yaml_config(self.bot.config_path)
                    old_value = config.get(key)
                    
                    # Update and save
                    update_config_value(config, key, formatted_value)
                    save_yaml_config(config, self.bot.config_path)
                    self.config[key] = formatted_value
                    
                    # Get appropriate response message
                    if key == "FIXED_UPDATE_TIME" and (formatted_value == "XX:XX" or formatted_value is None):
                        response_message = self.translations["config_updated_fixed_time_disabled"].format(key=key)
                    elif key in RESTART_REQUIRED_KEYS:
                        response_message = self.translations["config_updated_restart"].format(key=key)
                    else:
                        old_display = format_value_for_display(key, old_value)
                        new_display = format_value_for_display(key, formatted_value)
                        response_message = self.translations["config_updated"].format(
                            key=key,
                            old_value=old_display,
                            new_value=new_display
                        )
                    
                    await interaction.followup.send(response_message, ephemeral=True)
                    
            except (ConfigError, BaseConfigValidationError) as e:
                raise ConfigUpdateError(f"Failed to update configuration: {str(e)}") from e

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
            if isinstance(e, (ConfigValidationError, ConfigUpdateError)):
                logging.error(f"Configuration error: {str(e)}")
                raise
            else:
                logging.error(f"Unexpected error updating configuration: {str(e)}")
                raise ConfigUpdateError("Unexpected error updating configuration") from e

    async def _get_key_autocomplete(
        self,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Get autocomplete choices for configuration keys.
        
        This helper method provides filtered and categorized autocomplete suggestions
        for configuration keys. Results are limited to 25 choices and sorted alphabetically.
        
        Parameters
        -----------
        current: str
            The current value entered by the user to filter against
            
        Returns
        --------
        List[app_commands.Choice[str]]
            A list of autocomplete choices, each containing:
            - name: Category » Key format for display
            - value: The actual config key
            
        Note
        -----
        The choices returned are suggestions only. Users may input other values.
        """
        choices = []
        categorized = get_categorized_config(self.config)
        
        for category, category_config in categorized.items():
            category_name = get_category_display_name(category)
            for key in category_config:
                if key in CONFIGURABLE_OPTIONS and current.lower() in key.lower():
                    display_name = f"{category_name} » {key}"
                    choices.append(app_commands.Choice(name=display_name, value=key))
        
        return sorted(choices, key=lambda c: c.name)[:25]

    @view.autocomplete('key')
    async def view_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for the view command's key parameter.
        
        Parameters
        -----------
        interaction: discord.Interaction
            The autocomplete interaction being handled
        current: str
            The current value entered by the user
            
        Returns
        --------
        List[app_commands.Choice[str]]
            The filtered autocomplete choices
        """
        return await self._get_key_autocomplete(current)

    @edit.autocomplete('key')
    async def edit_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for the edit command's key parameter.
        
        Parameters
        -----------
        interaction: discord.Interaction
            The autocomplete interaction being handled
        current: str
            The current value entered by the user
            
        Returns
        --------
        List[app_commands.Choice[str]]
            The filtered autocomplete choices
        """
        return await self._get_key_autocomplete(current)

    async def _update_language(self, language: str) -> None:
        """Update bot language settings.
        
        Args:
            language: New language code to set
            
        Raises:
            ConfigUpdateError: If language update fails
        """
        try:
            from i18n import load_translations
            translations = load_translations(language)
            
            # Update translations across all components
            self.bot.translations = translations
            self.translations = translations
            
            # Update translations for graph-related components
            if hasattr(self.bot, 'graph_manager'):
                self.bot.graph_manager.translations = translations
                self.bot.graph_manager.graph_factory.translations = translations
                
            if hasattr(self.bot, 'user_graph_manager'):
                self.bot.user_graph_manager.translations = translations
                self.bot.user_graph_manager.graph_factory.translations = translations
                
            if hasattr(self.bot, 'data_fetcher'):
                self.bot.data_fetcher.translations = translations
                
            await self._update_command_descriptions()
            
            logging.info(f"Updated language settings to: {language}")
            
        except Exception as e:
            logging.error(f"Failed to update language to {language}: {str(e)}")
            raise ConfigUpdateError(f"Failed to update language to {language}") from e

    async def _update_command_descriptions(self) -> None:
        """
        Update command descriptions after language change.
        
        Raises:
            ConfigUpdateError: If description update fails
        """
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
            raise ConfigUpdateError("Failed to update command descriptions") from e

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handle application command errors.

        Args:
            interaction: The Discord interaction
            error: The error that occurred
        """
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            
            if isinstance(error, ConfigCommandError):
                await self.send_error_message(
                    interaction,
                    str(error),
                    ephemeral=True
                )
                return
            elif isinstance(error, (ValueError, KeyError)):
                logging.error(f"Configuration error in {interaction.command.name}: {str(error)}")
                
                # Map specific errors to user-friendly messages
                error_key = "config_error_invalid_value"
                if isinstance(error, KeyError):
                    error_key = "config_error_invalid_key"
                
                await self.send_error_message(
                    interaction,
                    self.translations[error_key],
                    ephemeral=True
                )
                return
            
        await self.handle_error(interaction, error)

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        logging.debug(self.translations["log_commands_cog_loaded"])

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logging.debug(self.translations["log_unloading_command"].format(
            command_name="config"
        ))

async def setup(bot: commands.Bot) -> None:
    """
    Setup function for the config cog.
    
    Args:
        bot: The bot instance
        
    Raises:
        ConfigCommandError: If cog setup fails
    """
    try:
        await bot.add_cog(ConfigCog(bot))
    except Exception as e:
        error_msg = "Failed to setup configuration cog"
        logging.error(f"{error_msg}: {str(e)}")
        raise ConfigCommandError(error_msg) from e
