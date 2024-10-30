# bot/commands/my_stats.py

"""
My Stats command for TGraph Bot.
Generates and sends personalized Plex statistics to users.
"""

import discord
from discord import app_commands
import logging
from discord.ext import commands
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class MyStatsCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling user-specific Plex statistics."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        self.bot = bot
        self.config = config
        self.translations = translations
        super().__init__()  # Initialize both CommandMixin and ErrorHandlerMixin

    @app_commands.command(
        name="my_stats",
        description="Get your personal Plex statistics"
    )
    @app_commands.describe(email="Your Plex email address")
    async def my_stats(self, interaction: discord.Interaction, email: str) -> None:
        """Get your personal Plex statistics.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        email : str
            The user's Plex email address
        """
        if not await self.check_cooldowns(
            interaction,
            self.config["MY_STATS_COOLDOWN_MINUTES"],
            self.config["MY_STATS_GLOBAL_COOLDOWN_SECONDS"]
        ):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            user_id = self.bot.data_fetcher.get_user_id_from_email(email)

            if not user_id:
                await interaction.followup.send(
                    self.translations["my_stats_no_user_found"],
                    ephemeral=True
                )
                return

            logging.info(
                self.translations["log_generating_user_graphs"].format(
                    user_id=user_id
                )
            )

            graph_files = await self.bot.user_graph_manager.generate_user_graphs(user_id)
            
            logging.info(
                self.translations["log_generated_graph_files"].format(
                    count=len(graph_files)
                )
            )

            if not graph_files:
                logging.warning(self.translations["my_stats_generate_failed"])
                await interaction.followup.send(
                    self.translations["my_stats_generate_failed"],
                    ephemeral=True
                )
                return

            logging.info(self.translations["log_sending_graphs_pm"])
            
            try:
                dm_channel = await interaction.user.create_dm()
                
                for graph_file in graph_files:
                    try:
                        await dm_channel.send(file=discord.File(graph_file))
                        logging.info(
                            self.translations["log_sending_graph_file"].format(file=graph_file)
                        )
                    except discord.HTTPException as e:
                        logging.error(f"Failed to send graph file: {str(e)}")
                        raise

                self.update_cooldowns(
                    str(interaction.user.id),
                    self.config["MY_STATS_COOLDOWN_MINUTES"],
                    self.config["MY_STATS_GLOBAL_COOLDOWN_SECONDS"]
                )

                await self.log_command(interaction, "my_stats")
                await interaction.followup.send(
                    self.translations["my_stats_success"],
                    ephemeral=True
                )

            except discord.Forbidden:
                logging.warning("Failed to send DM to user; DMs may be disabled.")
                await interaction.followup.send(
                    self.translations["error_dm_disabled"],
                    ephemeral=True
                )
            except Exception as e:
                logging.error(f"Unexpected error when sending DM: {e}")
                await interaction.followup.send(
                    self.translations["error_dm_send"],
                    ephemeral=True
                )

        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="my_stats",
                    error=str(e)
                )
            )
            raise

def setup(bot: commands.Bot) -> None:
    """Setup function for the my_stats cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    bot.add_cog(MyStatsCog(bot, bot.config, bot.translations))
