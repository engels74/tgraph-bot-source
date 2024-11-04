# bot/commands/update_graphs.py

"""
Update Graphs command for TGraph Bot.
Handles manual updates of server-wide graphs, including
graph generation and posting to the designated channel.
"""

import discord
from discord import app_commands
import logging
from discord.ext import commands
from typing import Optional
from config.config import load_config
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class UpdateGraphsCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling graph updates."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        """Initialize the UpdateGraphs cog.
        
        Parameters
        ----------
        bot : commands.Bot
            The bot instance
        config : dict
            Configuration dictionary
        translations : dict
            Translation strings dictionary
        """
        # Initialize parent classes first
        super().__init__()
        
        # Set instance attributes
        self.bot = bot
        self.config = config
        self.translations = translations

    async def get_target_channel(self, interaction: discord.Interaction) -> Optional[discord.TextChannel]:
        """Get the target channel for posting graphs.
        
        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
            
        Returns
        -------
        Optional[discord.TextChannel]
            The target channel if found and valid, None otherwise
        """
        try:
            channel_id = self.config.get("CHANNEL_ID")
            if not channel_id:
                await interaction.followup.send(
                    "Channel ID not found in configuration.",
                    ephemeral=True
                )
                return None
                
            # Convert channel_id to integer and handle potential conversion errors
            try:
                channel_id = int(channel_id)
            except (ValueError, TypeError):
                await interaction.followup.send(
                    "Invalid channel ID in configuration.",
                    ephemeral=True
                )
                return None
                
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await interaction.followup.send(
                    self.translations["log_channel_not_found"].format(
                        channel_id=channel_id
                    ),
                    ephemeral=True
                )
                return None
                
            return channel
            
        except Exception as e:
            logging.error(f"Error getting target channel: {e}")
            await interaction.followup.send(
                "Error accessing target channel.",
                ephemeral=True
            )
            return None

    @app_commands.command(
        name="update_graphs",
        description="Update and post server-wide graphs"
    )
    async def update_graphs(self, interaction: discord.Interaction) -> None:
        """Update and post server-wide graphs.

        Parameters
        ----------
        interaction : discord.Interaction
            The interaction instance
        """
        # Check cooldowns using configurable values
        if not await self.check_cooldowns(
            interaction,
            self.config["UPDATE_GRAPHS_COOLDOWN_MINUTES"],
            self.config["UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS"]
        ):
            return
            
        try:
            # Defer the response since this operation might take some time
            await interaction.response.defer(ephemeral=True)
            
            # Log the manual update start
            logging.info(self.translations["log_manual_update_started"])

            # Reload config in case of changes
            self.config = self.bot.config = self.reload_config()
            
            # Update the bot's tracker with new config
            self.bot.update_tracker.update_config(self.config)

            # Get and validate target channel
            channel = await self.get_target_channel(interaction)
            if not channel:
                return

            # Delete old graph messages
            await self.bot.graph_manager.delete_old_messages(channel)
            
            # Generate new graphs - pass the data_fetcher instance
            try:
                graph_files = await self.bot.graph_manager.generate_and_save_graphs(self.bot.data_fetcher)
                
                if not graph_files:
                    await interaction.followup.send(
                        self.translations["error_generating_graph"],
                        ephemeral=True
                    )
                    return
                    
            except Exception as e:
                logging.error(f"Error generating graphs: {e}")
                await interaction.followup.send(
                    self.translations["error_generating_graph"],
                    ephemeral=True
                )
                return

            # Post the new graphs
            try:
                await self.bot.graph_manager.post_graphs(channel, graph_files, self.bot.update_tracker)
            except Exception as e:
                logging.error(f"Error posting graphs: {e}")
                await interaction.followup.send(
                    "Error posting graphs to channel.",
                    ephemeral=True
                )
                return

            # Update the tracker
            self.bot.update_tracker.update()
            next_update = self.bot.update_tracker.get_next_update_readable()

            # Log completion
            logging.info(self.translations["log_manual_update_completed"])
            
            # Update cooldowns after successful execution using configurable values
            self.update_cooldowns(
                str(interaction.user.id),
                self.config["UPDATE_GRAPHS_COOLDOWN_MINUTES"],
                self.config["UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS"]
            )

            # Log the command execution
            await self.log_command(interaction, "update_graphs")
            
            # Send success message
            await interaction.followup.send(
                self.translations["update_graphs_success"].format(
                    next_update=self.bot.update_tracker.get_next_update_discord() 
                ),
                ephemeral=True
            )
            
            # Log the next update time
            logging.info(
                self.translations["log_graphs_updated_posted"].format(
                    next_update=next_update
                )
            )

        except Exception as e:
            logging.exception(
                self.translations["log_command_error"].format(
                    command="update_graphs",
                    error=str(e)
                )
            )
            raise  # Let the mixin's error handler handle it

    def reload_config(self) -> dict:
        """Reload the configuration from disk.

        Returns
        -------
        dict
            The updated configuration
        """
        return load_config(reload=True)

async def setup(bot: commands.Bot) -> None:
    """Setup function for the update_graphs cog.
    
    Parameters
    ----------
    bot : commands.Bot
        The bot instance
    """
    await bot.add_cog(UpdateGraphsCog(bot, bot.config, bot.translations))
