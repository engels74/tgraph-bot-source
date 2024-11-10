# bot/commands/my_stats.py

"""
My Stats command for TGraph Bot.
Generates and sends personalized Plex statistics to users with improved 
file cleanup and validation.
"""

import re
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

class InvalidUserIdError(UserStatsError):
    """Raised when user ID is invalid."""
    pass

class InvalidEmailError(UserStatsError):
    """Raised when email format is invalid."""
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
        # Initialize parent classes explicitly
        super().__init__()
        CommandMixin.__init__(self)
        ErrorHandlerMixin.__init__(self)
        
        self.bot = bot
        self.config = config
        self.translations = translations
        self.email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def validate_email(self, email: str) -> bool:
        """
        Validate email format using regex pattern.
        
        Parameters
        ----------
        email : str
            The email to validate
            
        Returns
        -------
        bool
            True if email is valid, False otherwise
        """
        return bool(re.match(self.email_pattern, email))

    async def cleanup_graph_files(self, graph_files: List[str]) -> None:
        """
        Clean up temporary graph files.
        
        Parameters
        ----------
        graph_files : List[str]
            List of graph file paths to clean up
        """
        for file_path in graph_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.debug(f"Cleaned up temporary file: {file_path}")
            except OSError as e:
                logging.warning(f"Failed to clean up {file_path}: {str(e)}")

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
        InvalidUserIdError
            If user ID is invalid
        """
        try:
            graph_files = await self.bot.user_graph_manager.generate_user_graphs(user_id)
            
            if not graph_files:
                raise GraphGenerationError("No graphs were generated")
                
            return graph_files
            
        except Exception as e:
            logging.error(f"Failed to generate graphs: {str(e)}")
            if isinstance(e, (ValueError, InvalidUserIdError)):
                raise InvalidUserIdError("Invalid user ID format") from e
            elif isinstance(e, DataFetchError):
                raise DataFetchError("Failed to fetch user statistics") from e
            else:
                raise GraphGenerationError("Failed to generate graphs") from e

    async def send_graphs_via_dm(
        self,
        user: discord.User,
        graph_files: List[str]
    ) -> None:
        """Send graphs to user via DM with proper error handling and cleanup.
        
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
                    logging.error(f"Failed to send graph {filename}: {str(e)}")
                    raise DMError(f"Failed to send graph: {filename}") from e
                except IOError as e:
                    logging.error(f"Failed to read graph file {filename}: {str(e)}")
                    raise IOError(f"Failed to read graph file: {filename}") from e

        except discord.Forbidden as e:
            logging.warning(f"Cannot send DM to user: {str(e)}")
            raise DMError("DMs are disabled") from e
        except discord.HTTPException as e:
            logging.error(f"Discord API error while sending DMs: {str(e)}")
            raise DMError("Failed to establish DM channel") from e
        finally:
            # Always attempt to clean up files, even if sending failed
            await self.cleanup_graph_files(graph_files)

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
            # Validate email format
            if not self.validate_email(email):
                await interaction.followup.send(
                    "Please provide a valid email address.",
                    ephemeral=True
                )
                return

            # Get user ID from email
            try:
                user_id = self.bot.data_fetcher.get_user_id_from_email(email)
            except DataFetchError:
                logging.error("Failed to fetch user ID from email")
                await interaction.followup.send(
                    self.translations["my_stats_no_user_found"],
                    ephemeral=True
                )
                return

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
            except (GraphGenerationError, DataFetchError) as e:
                await interaction.followup.send(
                    self.translations["my_stats_generate_failed"],
                    ephemeral=True
                )
                logging.error(
                    self.translations["log_graph_generation_failed"].format(
                        error_type=e.__class__.__name__
                    )
                )
                return
            except InvalidUserIdError:
                await interaction.followup.send(
                    self.translations["my_stats_no_user_found"],
                    ephemeral=True
                )
                return

            # Send graphs via DM and handle cleanup
            try:
                await self.send_graphs_via_dm(interaction.user, graph_files)
            except DMError as e:
                error_msg = (
                    self.translations["error_dm_disabled"] 
                    if "disabled" in str(e)
                    else self.translations["error_dm_send"]
                )
                await interaction.followup.send(error_msg, ephemeral=True)
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
            # Specific error handling with proper messages
            if isinstance(e, discord.Forbidden):
                logging.error("Discord permission error in my_stats command")
                await interaction.followup.send(
                    self.translations["error_dm_disabled"],
                    ephemeral=True
                )
            elif isinstance(e, discord.HTTPException):
                logging.error("Discord API error in my_stats command")
                await interaction.followup.send(
                    self.translations["my_stats_error"],
                    ephemeral=True
                )
            else:
                logging.error(f"Unexpected error in my_stats command: {str(e)}")
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
