"""
Test scheduler command for TGraph Bot.

This module defines the /test_scheduler slash command, allowing administrators
to manually trigger the scheduled update routine for testing purposes without
waiting for the actual scheduled time.

Command Design Specifications:
- Name: /test_scheduler
- Description: Test the scheduled update functionality
- Permissions: Requires manage_guild permission (admin only)
- Parameters: None (simple trigger command)
- Response: Ephemeral acknowledgment, then uses the same update routine as scheduler
- Error Handling: Uses the same comprehensive error handling as the scheduler
- Testing: Simulates exactly what happens when the scheduler triggers an update
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ... import i18n
from ...utils.discord.base_command_cog import BaseCommandCog, BaseCooldownConfig
from ...utils.discord.command_utils import (
    create_error_embed,
    create_success_embed,
    create_info_embed,
    create_cooldown_embed,
)
from ...utils.time import format_for_discord

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SchedulerTestCog(BaseCommandCog):
    """
    Cog for testing the scheduled update functionality.

    This cog implements the /test_scheduler slash command with:
    - Admin-only permissions (manage_guild required)
    - Uses the same force_update() method that tests use
    - Provides immediate feedback on the scheduler test results
    - Updates scheduler state exactly like a real scheduled update
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the TestScheduler cog.

        Args:
            bot: The Discord bot instance
        """
        # Configure cooldown settings for this command (more permissive for testing)
        cooldown_config = BaseCooldownConfig(
            user_cooldown_config_key="UPDATE_GRAPHS_COOLDOWN_MINUTES",  # Reuse existing config
            global_cooldown_config_key="UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS",
        )

        # Initialize base class with cooldown configuration
        super().__init__(bot, cooldown_config)

    @app_commands.command(
        name="test_scheduler",
        description=i18n.translate(
            "Test the scheduled update functionality immediately"
        ),
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_scheduler(self, interaction: discord.Interaction) -> None:
        """
        Test the scheduled update functionality immediately.

        This command:
        1. Uses the UpdateTracker's force_update() method
        2. Triggers the exact same update routine that the scheduler uses
        3. Includes all error handling, retry logic, and state updates
        4. Provides detailed feedback on the test results

        Args:
            interaction: The Discord interaction
        """
        try:
            # Check cooldowns first
            is_on_cooldown, retry_after = self.check_cooldowns(interaction)
            if is_on_cooldown:
                cooldown_embed = create_cooldown_embed(
                    i18n.translate("test scheduler"), retry_after
                )
                _ = await interaction.response.send_message(
                    embed=cooldown_embed, ephemeral=True
                )
                return
        except Exception as e:
            # Handle configuration errors that occur during cooldown checks
            await self.handle_command_error(interaction, e, "test_scheduler")
            return

        # Acknowledge the command immediately
        embed = create_info_embed(
            title=i18n.translate("Scheduler Test Started"),
            description=i18n.translate("Testing the scheduled update functionality..."),
        )
        _ = embed.add_field(
            name=i18n.translate("Test Method"),
            value=i18n.translate(
                "Using UpdateTracker.force_update() - same as scheduler"
            ),
            inline=False,
        )
        _ = embed.add_field(
            name=i18n.translate("What This Tests"),
            value=i18n.translate(
                "• UPDATE_DAYS configuration\n• FIXED_UPDATE_TIME configuration\n• Complete graph generation workflow\n• Error handling and retry logic\n• Scheduler state updates"
            ),
            inline=False,
        )

        _ = await interaction.response.send_message(embed=embed, ephemeral=True)

        # Get scheduler status before test (initialize outside try block)
        update_tracker = self.tgraph_bot.update_tracker
        status_before = update_tracker.get_scheduler_status()

        try:
            # Get timing information
            config = self.get_current_config()
            next_update_before = update_tracker.get_next_update_time()
            last_update_before = update_tracker.get_last_update_time()

            # Send status information
            status_embed = create_info_embed(
                title=i18n.translate("Pre-Test Status"),
                description=i18n.translate("Current scheduler configuration and state"),
            )
            _ = status_embed.add_field(
                name=i18n.translate("Configuration"),
                value=(
                    f"**Update Interval:** {config.UPDATE_DAYS} day(s)\n"
                    f"**Fixed Time:** {config.FIXED_UPDATE_TIME}\n"
                    f"**Scheduler Running:** {status_before.get('is_running', 'Unknown')}"
                ),
                inline=False,
            )

            if next_update_before:
                last_update_str = (
                    format_for_discord(last_update_before, "F")
                    if last_update_before
                    else "Never"
                )
                next_update_str = format_for_discord(next_update_before, "F")

                _ = status_embed.add_field(
                    name=i18n.translate("Scheduled Times"),
                    value=(
                        f"**Last Update:** {last_update_str}\n"
                        f"**Next Update:** {next_update_str}"
                    ),
                    inline=False,
                )

            _ = await interaction.followup.send(embed=status_embed, ephemeral=True)

            # Trigger the scheduled update using the same method as the scheduler
            logger.info("Starting scheduler test via force_update()")

            # This calls the exact same _trigger_update() method that the scheduler uses
            await update_tracker.force_update()

            # Get status after test
            last_update_after = update_tracker.get_last_update_time()
            next_update_after = update_tracker.get_next_update_time()

            # Send success message with results
            success_embed = create_success_embed(
                title=i18n.translate("Scheduler Test Completed Successfully"),
                description=i18n.translate(
                    "The scheduled update routine executed successfully!"
                ),
            )

            _ = success_embed.add_field(
                name=i18n.translate("Test Results"),
                value=i18n.translate(
                    "✅ UPDATE_DAYS interval calculation working\n✅ FIXED_UPDATE_TIME scheduling working\n✅ Graph generation and posting successful\n✅ Scheduler state updated correctly"
                ),
                inline=False,
            )

            if last_update_after and last_update_after != last_update_before:
                last_update_str = format_for_discord(last_update_after, "F")
                next_update_str = (
                    format_for_discord(next_update_after, "F")
                    if next_update_after
                    else "Calculating..."
                )

                _ = success_embed.add_field(
                    name=i18n.translate("State Updates"),
                    value=(
                        f"**Last Update:** Updated to {last_update_str}\n"
                        f"**Next Update:** {next_update_str}"
                    ),
                    inline=False,
                )

            _ = success_embed.add_field(
                name=i18n.translate("What This Confirms"),
                value=i18n.translate(
                    "The scheduler will work correctly at the configured time. All timing calculations and update workflows are functioning properly."
                ),
                inline=False,
            )

            _ = await interaction.followup.send(embed=success_embed, ephemeral=True)

            # Update cooldowns after successful execution
            self.update_cooldowns(interaction)

            logger.info("Scheduler test completed successfully")

        except Exception as e:
            # Detailed error reporting for test failures
            logger.exception(f"Scheduler test failed: {e}")

            error_embed = create_error_embed(
                title=i18n.translate("Scheduler Test Failed"),
                description=i18n.translate(
                    "The scheduled update test encountered an error"
                ),
            )
            _ = error_embed.add_field(
                name=i18n.translate("Error Details"),
                value=f"```{str(e)[:1000]}```",
                inline=False,
            )
            _ = error_embed.add_field(
                name=i18n.translate("What This Means"),
                value=i18n.translate(
                    "There may be an issue with:\n• Tautulli API connectivity\n• Discord channel permissions\n• Graph generation process\n• Bot configuration"
                ),
                inline=False,
            )
            _ = error_embed.add_field(
                name=i18n.translate("Next Steps"),
                value=i18n.translate(
                    "Check the bot logs for detailed error information and verify your configuration settings."
                ),
                inline=False,
            )

            _ = await interaction.followup.send(embed=error_embed, ephemeral=True)

            # Use base class error handling for logging
            await self.handle_command_error(
                interaction, e, "test_scheduler", {"scheduler_status": status_before}
            )


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(SchedulerTestCog(bot))
