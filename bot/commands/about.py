# bot/commands/about.py

"""
About command for TGraph Bot.
Provides information about the bot including description,
GitHub repository link, and license details with enhanced error handling.
"""

from discord import app_commands, Embed, Interaction, Forbidden, HTTPException
from discord.ext import commands
from typing import Any, Dict
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class AboutCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """
    Cog for handling the about command with enhanced error handling and logging.
    Implements the about command to display bot information.
    """
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        """
        Initialize the About cog.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : Dict[str, Any]
            Configuration dictionary
        translations : Dict[str, str]
            Translation strings dictionary
        """
        self.bot = bot
        self.config = config
        self.translations = translations
        CommandMixin.__init__(self)  # Initialize the command mixin
        ErrorHandlerMixin.__init__(self)  # Initialize the error handler mixin
        super().__init__()  # Initialize Cog

    def create_about_embed(self) -> Embed:
        """
        Create the about embed with bot information.
        
        Returns
        -------
        discord.Embed
            The formatted embed containing bot information
        """
        embed = Embed(
            title="TGraph Bot", 
            color=self.config.get("embed_color", 0x3498DB)
        )
        
        # Add embed fields
        embed.add_field(
            name="Description",
            value=self.translations["about_description"],
            inline=False,
        )
        embed.add_field(
            name=self.translations["about_github"],
            value=self.config.get(
                "github_url", 
                "https://github.com/engels74/tgraph-bot-source"
            ),
            inline=False,
        )
        embed.add_field(
            name=self.translations["about_license"],
            value="AGPLv3",
            inline=False,
        )
        
        return embed

    async def handle_response(self, interaction: Interaction, embed: Embed) -> None:
        """
        Handle sending the response with proper error handling.
        
        Parameters
        ----------
        interaction : discord.Interaction
            The interaction to respond to
        embed : discord.Embed
            The embed to send
            
        Raises
        ------
        discord.Forbidden
            If the bot lacks permissions to respond
        discord.HTTPException
            If there's an error sending the response
        """
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Forbidden as e:
            self.bot.logger.error(f"Permission error in about command: {e}")
            raise
        except HTTPException as e:
            self.bot.logger.error(f"HTTP error in about command: {e}")
            raise

    @app_commands.command(
        name="about",
        description="Display information about the bot"
    )
    async def about(self, interaction: Interaction) -> None:
        """
        Display information about the bot.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        """
        try:
            embed = self.create_about_embed()
            await self.handle_response(interaction, embed)
            await self.log_command(interaction, "about")
        except Exception as e:
            await self.handle_command_error(interaction, e, "about")

    async def cog_unload(self) -> None:
        """Called when the cog is being unloaded."""
        self.bot.logger.info(self.translations["log_unloading_command"].format(
            command_name="about"
        ))

async def setup(bot: commands.Bot) -> None:
    """
    Setup function for the about cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance to add the cog to
    """
    await bot.add_cog(AboutCog(bot, bot.config, bot.translations))
