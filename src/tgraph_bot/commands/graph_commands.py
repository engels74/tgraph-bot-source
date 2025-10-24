"""Discord slash commands for graph generation and statistics.

This module implements the GraphCommands cog containing all graph-related
slash commands for the TGraph Bot.

Requirements: 1.2, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5,
              10.1, 10.2, 10.3, 10.4, 10.5, 19.2, 19.4
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import nextcord
from nextcord.ext import commands

from tgraph_bot.utils.logging import command_name, get_logger, user_id

if TYPE_CHECKING:
    from tgraph_bot.bot import TGraphBot

logger = get_logger(__name__)


class GraphCommands(commands.Cog):
    """Cog containing graph-related slash commands.

    This cog provides slash commands for:
    - Manual graph updates (/update-graphs)
    - Personal statistics viewing (/my-stats)
    - Configuration viewing (/config)

    All commands implement rate limiting and comprehensive error handling.

    Requirements:
        - 1.2: Process commands and respond within 3 seconds
        - 1.5: Support slash commands for configuration, graph updates, stats
        - 8.1-8.5: Manual graph update command
        - 9.1-9.5: Personal statistics command
        - 10.1-10.5: Configuration viewing command
    """

    def __init__(self, bot: TGraphBot) -> None:
        """Initialize the GraphCommands cog.

        Args:
            bot: The TGraphBot instance
        """
        self.bot: TGraphBot = bot
        logger.info("GraphCommands cog initialized")

    @nextcord.slash_command(
        name="update-graphs",
        description="Generate and post new graphs with current data",
    )
    async def update_graphs(self, interaction: nextcord.Interaction[nextcord.Client]) -> None:
        """Manually trigger graph generation and posting.

        This command:
        1. Checks rate limiting (user and global cooldowns)
        2. Sends ephemeral "processing" message
        3. Generates all enabled graphs
        4. Posts graphs to configured channel
        5. Deletes or updates the ephemeral message

        Args:
            interaction: The Discord interaction object

        Requirements: 1.2, 8.1, 8.2, 8.3, 8.4, 8.5
        """
        # Set context variables for logging
        if interaction.user:
            _ = user_id.set(interaction.user.id)
        _ = command_name.set("update_graphs")

        logger.info(
            "Update graphs command invoked",
            extra={
                "user_id": interaction.user.id if interaction.user else None,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
            },
        )

        try:
            # Check rate limiting
            if interaction.user:
                cooldown_info = self.bot.rate_limiter.check_cooldown(
                    "update_graphs", interaction.user.id
                )
                if cooldown_info is not None:
                    # User is on cooldown
                    remaining_minutes = cooldown_info["remaining_seconds"] / 60
                    cooldown_type = (
                        "user" if cooldown_info["is_user_cooldown"] else "global"
                    )

                    _ = await interaction.response.send_message(
                        f"This command is on cooldown. Please wait {remaining_minutes:.1f} minutes before using it again ({cooldown_type} cooldown).",
                        ephemeral=True,
                    )
                    logger.info(
                        f"Command blocked by {cooldown_type} rate limit",
                        extra={"remaining_minutes": remaining_minutes},
                    )
                    return

            # Send initial "processing" message
            # Requirement 8.2: Send ephemeral message indicating processing status
            _ = await interaction.response.send_message(
                "Generating graphs... This may take a few moments.",
                ephemeral=True,
            )

            # TODO: Task 23 will implement actual graph generation
            # For now, just acknowledge the command
            logger.info("Graph generation placeholder - will be implemented in Task 23")

            # Record command usage for rate limiting
            if interaction.user:
                self.bot.rate_limiter.record_usage("update_graphs", interaction.user.id)

            # Update the message to indicate completion
            # Requirement 8.3: Delete ephemeral message after completion
            _ = await interaction.edit_original_message(
                content="Graph update command received. Implementation pending (Task 23)."
            )

        except Exception as e:
            # Requirement 8.4: Send error message with failure details
            logger.error(
                f"Error executing update-graphs command: {e}",
                exc_info=True,
            )
            try:
                if interaction.response.is_done():
                    _ = await interaction.edit_original_message(
                        content=f"An error occurred while generating graphs: {e}"
                    )
                else:
                    _ = await interaction.response.send_message(
                        f"An error occurred while generating graphs: {e}",
                        ephemeral=True,
                    )
            except Exception as followup_error:
                logger.error(
                    f"Failed to send error message: {followup_error}",
                    exc_info=True,
                )

    @nextcord.slash_command(
        name="my-stats",
        description="View your personal viewing statistics",
    )
    async def my_stats(self, interaction: nextcord.Interaction[nextcord.Client]) -> None:
        """Generate personal statistics for the requesting user.

        This command:
        1. Checks rate limiting
        2. Generates graphs filtered to user's activity
        3. Sends as ephemeral message (privacy mode)
        4. Handles case where user has no data

        Args:
            interaction: The Discord interaction object

        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Set context variables for logging
        if interaction.user:
            _ = user_id.set(interaction.user.id)
        _ = command_name.set("my_stats")

        logger.info(
            "My stats command invoked",
            extra={
                "user_id": interaction.user.id if interaction.user else None,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
            },
        )

        try:
            # Check rate limiting
            if interaction.user:
                cooldown_info = self.bot.rate_limiter.check_cooldown(
                    "my_stats", interaction.user.id
                )
                if cooldown_info is not None:
                    remaining_minutes = cooldown_info["remaining_seconds"] / 60
                    cooldown_type = (
                        "user" if cooldown_info["is_user_cooldown"] else "global"
                    )

                    _ = await interaction.response.send_message(
                        f"This command is on cooldown. Please wait {remaining_minutes:.1f} minutes before using it again ({cooldown_type} cooldown).",
                        ephemeral=True,
                    )
                    logger.info(
                        f"Command blocked by {cooldown_type} rate limit",
                        extra={"remaining_minutes": remaining_minutes},
                    )
                    return

            # Send initial message
            # Requirement 9.2: Send personal statistics as ephemeral message
            _ = await interaction.response.send_message(
                "Generating your personal statistics... This may take a few moments.",
                ephemeral=True,
            )

            # TODO: Task 23 will implement actual personal stats generation
            logger.info("Personal stats generation placeholder - will be implemented in Task 23")

            # Record command usage for rate limiting
            if interaction.user:
                self.bot.rate_limiter.record_usage("my_stats", interaction.user.id)

            _ = await interaction.edit_original_message(
                content="Personal stats command received. Implementation pending (Task 23)."
            )

        except Exception as e:
            logger.error(
                f"Error executing my-stats command: {e}",
                exc_info=True,
            )
            try:
                if interaction.response.is_done():
                    _ = await interaction.edit_original_message(
                        content=f"An error occurred while generating your statistics: {e}"
                    )
                else:
                    _ = await interaction.response.send_message(
                        f"An error occurred while generating your statistics: {e}",
                        ephemeral=True,
                    )
            except Exception as followup_error:
                logger.error(
                    f"Failed to send error message: {followup_error}",
                    exc_info=True,
                )

    @nextcord.slash_command(
        name="config",
        description="View current bot configuration",
    )
    async def config(self, interaction: nextcord.Interaction[nextcord.Client]) -> None:
        """Display current bot configuration with sensitive values masked.

        This command:
        1. Checks rate limiting
        2. Retrieves current configuration
        3. Masks sensitive values (API keys, tokens)
        4. Sends as ephemeral message with auto-delete
        5. Splits output if it exceeds message limits

        Args:
            interaction: The Discord interaction object

        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
        """
        # Set context variables for logging
        if interaction.user:
            _ = user_id.set(interaction.user.id)
        _ = command_name.set("config")

        logger.info(
            "Config command invoked",
            extra={
                "user_id": interaction.user.id if interaction.user else None,
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
            },
        )

        try:
            # Check rate limiting
            if interaction.user:
                cooldown_info = self.bot.rate_limiter.check_cooldown(
                    "config", interaction.user.id
                )
                if cooldown_info is not None:
                    remaining_minutes = cooldown_info["remaining_seconds"] / 60
                    cooldown_type = (
                        "user" if cooldown_info["is_user_cooldown"] else "global"
                    )

                    _ = await interaction.response.send_message(
                        f"This command is on cooldown. Please wait {remaining_minutes:.1f} minutes before using it again ({cooldown_type} cooldown).",
                        ephemeral=True,
                    )
                    logger.info(
                        f"Command blocked by {cooldown_type} rate limit",
                        extra={"remaining_minutes": remaining_minutes},
                    )
                    return

            # TODO: Task 23 will implement actual config display
            # For now, send a placeholder message
            # Requirement 10.3: Use ephemeral message that auto-deletes
            _ = await interaction.response.send_message(
                "Configuration display will be implemented in Task 23.",
                ephemeral=True,
                delete_after=self.bot.config.services.discord.ephemeral_message_delete_after,
            )

            # Record command usage for rate limiting
            if interaction.user:
                self.bot.rate_limiter.record_usage("config", interaction.user.id)

            logger.info("Config command placeholder executed")

        except Exception as e:
            logger.error(
                f"Error executing config command: {e}",
                exc_info=True,
            )
            try:
                if interaction.response.is_done():
                    _ = await interaction.edit_original_message(
                        content=f"An error occurred while retrieving configuration: {e}"
                    )
                else:
                    _ = await interaction.response.send_message(
                        f"An error occurred while retrieving configuration: {e}",
                        ephemeral=True,
                    )
            except Exception as followup_error:
                logger.error(
                    f"Failed to send error message: {followup_error}",
                    exc_info=True,
                )


def setup(bot: TGraphBot) -> None:
    """Set up the GraphCommands cog.

    This function is called by nextcord when loading the cog.

    Args:
        bot: The TGraphBot instance
    """
    bot.add_cog(GraphCommands(bot))
    logger.info("GraphCommands cog loaded")
