# bot/commands/about.py

"""
About command for TGraph Bot.

This module implements the about command as a Cog, providing information about the bot
including description, GitHub repository link, and license details.

Note:
    All responses are ephemeral by default.
"""

from discord import app_commands, Embed, Interaction
from discord.ext import commands
from typing import Any, Dict
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import logging
import discord

class AboutError(Exception):
    """Base exception class for about command errors."""
    pass

class EmbedCreationError(AboutError):
    """Exception raised when embed creation fails.
    
    This exception is raised when there's an error during the creation
    of the about embed, typically due to missing configuration or
    translation values.
    """
    pass

class ConfigurationError(AboutError):
    """Raised when there's an error with configuration values."""
    pass

class TranslationError(AboutError):
    """Raised when required translation strings are missing."""
    pass

class EmbedFieldError(EmbedCreationError):
    """Raised when there's an error adding specific fields to the embed."""
    pass

class AboutCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """A cog that implements the about command.
    
    This cog provides functionality to display information about the bot
    through a formatted embed message.

    Attributes
    ----------
    bot : commands.Bot
        The bot instance
    config : Dict[str, Any]
        Configuration dictionary containing bot settings
    translations : Dict[str, str]
        Dictionary containing translation strings
    """
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        """Initialize the About cog.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : Dict[str, Any]
            Configuration dictionary containing bot settings
        translations : Dict[str, str]
            Dictionary containing translation strings
        """
        # Initialize base classes in proper MRO order
        super().__init__()  # Initialize commands.Cog first
        CommandMixin.__init__(self)  # Then mixins in order
        ErrorHandlerMixin.__init__(self)
        
        # Set instance attributes
        self.bot = bot
        self.config = config
        self.translations = translations

    def create_about_embed(self) -> Embed:
        """Create an embed containing bot information.
        
        Creates a formatted embed containing the bot's description,
        GitHub repository link, and license information using Discord's
        standard blue color.

        Returns
        -------
        discord.Embed
            The formatted embed containing bot information

        Raises
        ------
        TranslationError
            If required translation strings are missing
        EmbedFieldError
            If there's an error adding fields to the embed
        EmbedCreationError
            If there's a general error during embed creation
        """
        try:
            # Validate required translations
            required_translations = ["about_description", "about_github"]
            missing_translations = [
                key for key in required_translations 
                if key not in self.translations
            ]
            if missing_translations:
                raise TranslationError(
                    f"Missing required translations: {', '.join(missing_translations)}"
                )

            # Use Discord blue color directly
            embed = Embed(
                title="TGraph Bot", 
                color=discord.Color.blue()
            )
            
            try:
                embed.add_field(
                    name="Description",
                    value=self.translations["about_description"],
                    inline=False,
                )
            except Exception as e:
                raise EmbedFieldError("Failed to add description field") from e

            try:
                embed.add_field(
                    name=self.translations["about_github"],
                    value=self.config.get(
                        "github_url", 
                        "https://github.com/engels74/tgraph-bot-source"
                    ),
                    inline=False,
                )
            except Exception as e:
                raise EmbedFieldError("Failed to add GitHub field") from e

            try:
                embed.add_field(
                    name=self.translations["about_license"],
                    value="AGPLv3",
                    inline=False,
                )
            except Exception as e:
                raise EmbedFieldError("Failed to add license field") from e
            
            return embed
            
        except (ConfigurationError, TranslationError, EmbedFieldError):
            raise
        except Exception as e:
            raise EmbedCreationError(f"Failed to create about embed: {str(e)}") from e

    @app_commands.command(
        name="about",
        description="Display information about the bot"
    )
    async def about(self, interaction: Interaction) -> None:
        """Display information about the bot in an ephemeral message.

        This command creates and sends an embed containing the bot's description,
        GitHub repository link, and license information.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction that triggered the command

        Note
        ----
        The response is always ephemeral (only visible to the command user).
        """
        try:
            embed = self.create_about_embed()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log the command execution using the mixin's functionality
            await self.log_command(interaction, "about")
            
        except Exception as e:
            # Let the ErrorHandlerMixin handle the error
            await self.handle_command_error(interaction, e, "about")

    async def cog_app_command_error(
        self, 
        interaction: Interaction, 
        error: app_commands.AppCommandError
    ) -> None:
        """Handle errors from application commands in this cog.

        This method extends the ErrorHandlerMixin's error handling with
        specific handling for AboutCog's custom exceptions.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction that triggered the error
        error : app_commands.AppCommandError
            The error that was raised

        Note
        ----
        All error messages are sent as ephemeral messages.
        """
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
            if isinstance(error, EmbedCreationError):
                logging.error(f"About command error: {str(error)}")
                await self.send_error_message(
                    interaction,
                    str(error),
                    ephemeral=True
                )
                return
        
        # Let the mixin handle other types of errors
        await super().cog_app_command_error(interaction, error)

    async def cog_unload(self) -> None:
        """Cleanup resources when cog is unloaded.
        
        Ensures proper cleanup of any resources used by the about command.
        """
        logging.info("About cog is being unloaded")
        # Add any cleanup code here if needed in the future
        await super().cog_unload()

async def setup(bot: commands.Bot) -> None:
    """Set up the About cog.

    This function is called by discord.py when loading the cog.

    Parameters
    ----------
    bot : commands.Bot
        The bot instance to add the cog to
    """
    await bot.add_cog(AboutCog(bot, bot.config, bot.translations))
