# bot/commands/about.py

"""
About command for TGraph Bot.
Provides information about the bot including description,
GitHub repository link, and license details.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Any, Dict

from utils.command_utils import CommandMixin, ErrorHandlerMixin

class AboutCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling the about command."""
    
    def __init__(self, bot: commands.Bot, config: Dict[str, Any], translations: Dict[str, str]):
        self.bot = bot
        self.config = config
        self.translations = translations
        CommandMixin.__init__(self)  # Initialize the command mixin
        ErrorHandlerMixin.__init__(self)  # Initialize the error handler mixin

    @app_commands.command(
        name="about",
        description="Display information about the bot"
    )
    async def about(self, interaction: discord.Interaction) -> None:
        """Display information about the bot.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance.
        """
        try:
            embed = discord.Embed(
                title="TGraph Bot", 
                color=self.config.get("embed_color", 0x3498DB)
            )
            embed.add_field(
                name="Description",
                value=self.translations["about_description"],
                inline=False,
            )
            embed.add_field(
                name=self.translations["about_github"],
                value=self.config.get("github_url", "https://github.com/engels74/tgraph-bot-source"),
                inline=False,
            )
            embed.add_field(
                name=self.translations["about_license"],
                value="AGPLv3",
                inline=False,
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log the successful command execution
            await self.log_command(interaction, "about")
            
        except (discord.HTTPException, discord.Forbidden) as e:
            # The ErrorHandlerMixin will handle this through cog_app_command_error
            raise e
        except Exception as e:
            # Log unexpected errors
            self.bot.logger.error(f"Unexpected error in about command: {e}")
            raise e

async def setup(bot: commands.Bot) -> None:
    """Setup function for the about cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    await bot.add_cog(AboutCog(bot, bot.config, bot.translations))
