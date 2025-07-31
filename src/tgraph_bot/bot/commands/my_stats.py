"""
Personal statistics command for TGraph Bot.

This module defines the /my_stats slash command, allowing users to request
their personal Plex statistics (graphs) via DM by providing their Plex email.

Command Design Specifications:
- Name: /my_stats
- Description: Get your personal Plex statistics
- Parameters: email (required) - User's Plex account email address
- Permissions: Available to all users (no restrictions)
- Cooldowns: 5 minutes per-user, 60 seconds global
- Response: Ephemeral acknowledgment, then private DM with graphs
- Error Handling: Comprehensive with user-friendly messages
- Privacy: Email-based user identification for Plex statistics
- File Upload: Automatic DM delivery of personal graph images
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ... import i18n
from ...graphs.user_graph_manager import UserGraphManager
from ...utils.discord.base_command_cog import BaseCommandCog, BaseCooldownConfig
from ...utils.discord.command_utils import (
    create_error_embed,
    create_success_embed,
    create_info_embed,
    create_cooldown_embed,
)
from ...utils.core.config_utils import ConfigurationHelper
from ...utils.core.exceptions import ValidationError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MyStatsCog(BaseCommandCog):
    """
    Cog for personal statistics commands.

    This cog implements the /my_stats slash command with:
    - Email-based user identification for Plex statistics
    - Personal graph generation via UserGraphManager
    - Private DM delivery of generated graphs
    - Configurable cooldowns for rate limiting
    - Comprehensive error handling and user feedback
    - Non-blocking graph generation using async threading
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Initialize the MyStats cog.

        Args:
            bot: The Discord bot instance
        """
        # Configure cooldown settings for this command
        cooldown_config = BaseCooldownConfig(
            user_cooldown_config_key="rate_limiting.commands.my_stats.user_cooldown_minutes",
            global_cooldown_config_key="rate_limiting.commands.my_stats.global_cooldown_seconds",
        )

        # Initialize base class with cooldown configuration
        super().__init__(bot, cooldown_config)

        # Create configuration helper
        self.config_helper: ConfigurationHelper = ConfigurationHelper(
            self.tgraph_bot.config_manager
        )

    @app_commands.command(
        name="my_stats",
        description=i18n.translate("Get your personal Plex statistics via DM"),
    )
    @app_commands.describe(
        email=i18n.translate(
            "Your Plex account email address (used to identify your statistics)"
        )
    )
    async def my_stats(self, interaction: discord.Interaction, email: str) -> None:
        """
        Generate and send personal Plex statistics to the user via DM.

        This command:
        1. Validates the provided email format
        2. Uses UserGraphManager for non-blocking graph generation
        3. Sends generated graphs privately via Discord DM
        4. Provides progress feedback and error handling
        5. Respects configured cooldowns for rate limiting

        Args:
            interaction: The Discord interaction
            email: The user's Plex email address for identification
        """
        try:
            # Check cooldowns first
            is_on_cooldown, retry_after = self.check_cooldowns(interaction)
            if is_on_cooldown:
                cooldown_embed = create_cooldown_embed(
                    i18n.translate("personal statistics"), retry_after
                )
                await self.send_ephemeral_response(interaction, embed=cooldown_embed)
                return

            # Enhanced email validation
            if not email or "@" not in email or "." not in email or len(email) < 5:
                raise ValidationError(
                    f"Invalid email format: {email}",
                    user_message=i18n.translate(
                        "Please provide a valid email address (e.g., user@example.com)."
                    ),
                )

            # Acknowledge the command with informative message
            embed = create_info_embed(
                title=i18n.translate("Personal Statistics Request"),
                description=i18n.translate(
                    "Generating your personal Plex statistics... This may take a moment."
                ),
            )
            _ = embed.add_field(name=i18n.translate("Email"), value=email, inline=True)
            _ = embed.add_field(
                name=i18n.translate("Delivery Method"),
                value=i18n.translate("Direct Message (DM)"),
                inline=True,
            )
            _ = embed.add_field(
                name=i18n.translate("Estimated Time"),
                value=i18n.translate("1-3 minutes"),
                inline=True,
            )

            await self.send_ephemeral_response(interaction, embed=embed)

            # Update cooldowns after successful acknowledgment
            self.update_cooldowns(interaction)

            # Generate personal graphs using user_graph_manager
            async with UserGraphManager(
                self.tgraph_bot.config_manager
            ) as user_graph_manager:
                result_stats = await user_graph_manager.process_user_stats_request(
                    user_id=interaction.user.id, user_email=email, bot=self.bot
                )

                if result_stats and result_stats.get("success", False):
                    # Success - graphs were generated and sent
                    success_embed = create_success_embed(
                        title=i18n.translate("Personal Statistics Complete"),
                        description=i18n.translate(
                            "Your personal Plex statistics have been generated and sent via DM!"
                        ),
                    )

                    # Add statistics from the result
                    graphs_generated = result_stats.get("graphs_generated", 0)
                    processing_time = result_stats.get("processing_time", 0)

                    _ = success_embed.add_field(
                        name=i18n.translate("Graphs Generated"),
                        value=i18n.translate(
                            "{count} personal graphs", count=graphs_generated
                        ),
                        inline=True,
                    )
                    _ = success_embed.add_field(
                        name=i18n.translate("Processing Time"),
                        value=i18n.translate(
                            "{time:.1f} seconds", time=processing_time
                        ),
                        inline=True,
                    )
                    _ = success_embed.add_field(
                        name=i18n.translate("Check Your DMs"),
                        value=i18n.translate("Your graphs have been sent privately"),
                        inline=False,
                    )

                    await self.send_ephemeral_response(interaction, embed=success_embed)
                else:
                    # Error occurred during processing
                    error_embed = create_error_embed(
                        title=i18n.translate("Statistics Generation Failed"),
                        description=i18n.translate(
                            "Unable to generate your personal statistics."
                        ),
                    )
                    _ = error_embed.add_field(
                        name=i18n.translate("Possible Causes"),
                        value=i18n.translate(
                            "• Email not found in Plex server\n• Insufficient data for graphs\n• Temporary server issue"
                        ),
                        inline=False,
                    )
                    _ = error_embed.add_field(
                        name=i18n.translate("Suggested Actions"),
                        value=i18n.translate(
                            "• Verify your email is correct\n• Ensure you have Plex activity\n• Try again in a few minutes"
                        ),
                        inline=False,
                    )

                    await self.send_ephemeral_response(interaction, embed=error_embed)

        except Exception as e:
            # Use base class error handling with additional context
            additional_context: dict[str, object] = {
                "email": email,
                "email_domain": email.split("@")[-1] if "@" in email else None,
            }

            await self.handle_command_error(
                interaction, e, "my_stats", additional_context
            )


async def setup(bot: commands.Bot) -> None:
    """
    Setup function to add the cog to the bot.

    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(MyStatsCog(bot))
