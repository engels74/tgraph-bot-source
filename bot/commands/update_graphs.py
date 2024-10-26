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
from config.config import load_config
from utils.command_utils import CommandMixin, ErrorHandlerMixin

class UpdateGraphsCog(commands.Cog, CommandMixin, ErrorHandlerMixin):
    """Cog for handling graph updates."""
    
    def __init__(self, bot: commands.Bot, config: dict, translations: dict):
        self.bot = bot
        self.config = config
        self.translations = translations
        CommandMixin.__init__(self)

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
        # Check cooldowns since this is a resource-intensive operation
        if not await self.check_cooldowns(interaction, 5, 60):  # 5 min user, 1 min global
            return
            
        try:
            # Defer the response since this operation might take some time
            await interaction.response.defer(ephemeral=True)
            
            # Log the manual update start
            logging.info(self.translations["log_manual_update_started"])

            # Reload config in case of changes
            self.config = self.bot.config = await self.reload_config()
            
            # Update the bot's tracker with new config
            self.bot.update_tracker.update_config(self.config)

            # Get the target channel
            channel = self.bot.get_channel(self.config["CHANNEL_ID"])
            if not channel:
                await interaction.followup.send(
                    self.translations["log_channel_not_found"].format(
                        channel_id=self.config["CHANNEL_ID"]
                    ),
                    ephemeral=True
                )
                return

            # Delete old graph messages
            await self.bot.graph_manager.delete_old_messages(channel)
            
            # Generate new graphs
            graph_files = await self.bot.graph_manager.generate_and_save_graphs()
            
            if not graph_files:
                await interaction.followup.send(
                    self.translations["error_generating_graph"],
                    ephemeral=True
                )
                return

            # Post the new graphs
            await self.bot.graph_manager.post_graphs(channel, graph_files)

            # Update the tracker
            self.bot.update_tracker.update()
            next_update = self.bot.update_tracker.get_next_update_readable()

            # Log completion
            logging.info(self.translations["log_manual_update_completed"])
            
            # Update cooldowns after successful execution
            self.update_cooldowns(str(interaction.user.id), 5, 60)

            # Log the command execution
            await self.log_command(interaction, "update_graphs")
            
            # Send success message
            await interaction.followup.send(
                self.translations["update_graphs_success"].format(
                    next_update=f"<t:{int(self.bot.update_tracker.next_update.timestamp())}:R>"
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
            logging.error(
                self.translations["log_command_error"].format(
                    command="update_graphs",
                    error=str(e)
                )
            )
            raise  # Let the mixin's error handler handle it

    async def reload_config(self) -> dict:
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
