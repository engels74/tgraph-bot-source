# bot/commands/my_stats.py

"""
My Stats command for TGraph Bot.
Generates and sends personalized Plex statistics to users.
"""

from discord import app_commands
from discord.ext import commands
from typing import Optional, List
from utils.command_utils import CommandMixin, ErrorHandlerMixin
import discord
import logging
import os

class UserStatsError(Exception):
    """Base exception for user statistics related errors."""
    pass

class GraphGenerationError(UserStatsError):
    """Raised when graph generation fails."""
    pass

class DMError(UserStatsError):
    """Raised when there are issues with DM operations."""
    pass

class DataFetchError(UserStatsError):
    """Raised when there are issues fetching user data."""
    pass

class MyStatsCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling user-specific Plex statistics."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        """Initialize the MyStats cog.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : dict
            The configuration dictionary
        translations : dict
            The translations dictionary
        """
        # Initialize Cog first
        super().__init__()
        
        # Set instance attributes
        self.bot = bot
        self.config = config
        self.translations = translations
        
        # Initialize mixins once
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logging.info(self.translations["log_unloading_command"].format(
            command_name="my_stats"
        ))

    async def generate_user_graphs(self, user_id: str) -> Optional[List[str]]:
        """Generate graphs for a specific user with proper error handling.
        
        Parameters
        ----------
        user_id : str
            The user ID to generate graphs for
            
        Returns
        -------
        Optional[List[str]]
            List of generated graph files or None if generation fails
            
        Raises
        ------
        GraphGenerationError
            If graph generation fails
        DataFetchError
            If data fetching fails
        """
        try:
            graph_files = await self.bot.user_graph_manager.generate_user_graphs(user_id)
            
            if not graph_files:
                raise GraphGenerationError("No graphs were generated") from None
                
            return graph_files
            
        except ValueError as e:
            logging.error(f"Invalid user ID or parameters: {e}")
            raise GraphGenerationError("Invalid parameters for graph generation") from e
        except IOError as e:
            logging.error(f"Failed to save generated graphs: {e}")
            raise GraphGenerationError("Failed to save generated graphs") from e
        except Exception as e:
            logging.error(f"Unexpected error during graph generation: {e}")
            raise GraphGenerationError("Failed to generate user graphs") from e

    async def send_graphs_via_dm(
        self,
        user: discord.User,
        graph_files: List[str]
    ) -> None:
        """Send graphs to user via DM with proper error handling.
        
        Parameters
        ----------
        user : discord.User
            The user to send graphs to
        graph_files : List[str]
            List of graph file paths
            
        Raises
        ------
        DMError
            If sending DMs fails
        """
        try:
            dm_channel = await user.create_dm()
            
            for graph_file in graph_files:
                try:
                    # Extract just the filename without the path
                    filename = os.path.basename(graph_file)
                    
                    if not os.path.exists(graph_file):
                        logging.error(f"Graph file not found: {filename}")
                        continue

                    await dm_channel.send(file=discord.File(graph_file))
                    logging.info(
                        self.translations["log_sending_graph_file"].format(
                            file=filename
                        )
                    )
                except discord.HTTPException as e:
                    logging.error(
                        f"Failed to send graph {filename}: {str(e)}"
                    )
                    raise DMError(f"Failed to send graph: {filename}") from e
                    
        except discord.Forbidden as e:
            logging.warning(f"Cannot send DM to user: {str(e)}")
            raise DMError("DMs are disabled") from e
        except Exception as e:
            logging.error(f"Unexpected error while sending DMs: {str(e)}")
            raise DMError("Failed to send graphs via DM") from e

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
            # Validate email input
            if not email or '@' not in email:
                await interaction.followup.send(
                    "Please provide a valid email address.",
                    ephemeral=True
                )
                return

            # Get user ID from email
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

            # Generate graphs
            try:
                graph_files = await self.generate_user_graphs(user_id)
            except GraphGenerationError as e:
                await interaction.followup.send(
                    self.translations["my_stats_generate_failed"],
                    ephemeral=True
                )
                logging.error(f"Graph generation failed: {str(e)}")
                return

            # Send graphs via DM
            try:
                await self.send_graphs_via_dm(interaction.user, graph_files)
            except DMError as e:
                await interaction.followup.send(
                    self.translations["error_dm_disabled"] if "disabled" in str(e)
                    else self.translations["error_dm_send"],
                    ephemeral=True
                )
                return

            # Update cooldowns and log success
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

        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="my_stats",
                    error=str(e)
                )
            )
            await interaction.followup.send(
                self.translations["my_stats_error"],
                ephemeral=True
            )

async def setup(bot: commands.Bot) -> None:
    """Setup function for the my_stats cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    await bot.add_cog(MyStatsCog(bot, bot.config, bot.translations))
