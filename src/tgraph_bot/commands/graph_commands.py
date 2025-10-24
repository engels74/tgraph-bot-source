"""Discord slash commands for graph generation and statistics.

This module implements the GraphCommands cog containing all graph-related
slash commands for the TGraph Bot.

Requirements: 1.2, 1.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5,
              10.1, 10.2, 10.3, 10.4, 10.5, 19.2, 19.4, 22.1, 22.3, 27.1, 27.2
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import nextcord
from nextcord.ext import commands

from tgraph_bot.api.tautulli import TautulliClient
from tgraph_bot.bot import TGraphBot
from tgraph_bot.graphs.factory import GraphFactory
from tgraph_bot.graphs.renderer import GraphRenderer
from tgraph_bot.graphs.styling import GraphStyling
from tgraph_bot.utils.errors import GraphGenerationError, TautulliAPIError
from tgraph_bot.utils.logging import (
    command_name,
    get_logger,
    log_operation_complete,
    log_operation_start,
    mask_sensitive_dict,
    user_id,
)

if TYPE_CHECKING:
    from tgraph_bot.graphs.data import GraphMetadata

logger = get_logger(__name__)

# Discord message character limit
DISCORD_MESSAGE_LIMIT = 2000

# Type aliases using PEP 695 syntax
type GraphMetadataList = list[GraphMetadata]
type MessageChunks = list[str]
type ConfigDict = dict[str, object]


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
        - 22.1, 22.3: Async concurrency with TaskGroup
        - 27.1, 27.2: Error handling with ExceptionGroup
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
    async def update_graphs(self, interaction: nextcord.Interaction[TGraphBot]) -> None:
        """Manually trigger graph generation and posting.

        This command:
        1. Checks rate limiting (user and global cooldowns)
        2. Sends ephemeral "processing" message
        3. Generates all enabled graphs using TaskGroup
        4. Posts graphs to configured channel with timestamp
        5. Deletes or updates the ephemeral message

        Args:
            interaction: The Discord interaction object

        Requirements: 1.2, 8.1, 8.2, 8.3, 8.4, 8.5, 22.1, 22.3, 27.1, 27.2
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
            # Requirement 8.5: Reject command if rate limit is active
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

            # Start operation tracking
            _ = log_operation_start(
                logger,
                "update_graphs_command",
                details={"user_id": interaction.user.id if interaction.user else None},
            )
            start_time = datetime.now(tz=UTC)

            try:
                # Requirement 8.1: Generate all enabled graphs with current data
                # Requirement 22.1: Use TaskGroup for structured concurrency
                metadata_list = await self._generate_and_post_graphs(
                    username_filter=None
                )

                # Calculate duration
                duration_ms = (datetime.now(tz=UTC) - start_time).total_seconds() * 1000

                # Record command usage for rate limiting
                if interaction.user:
                    self.bot.rate_limiter.record_usage(
                        "update_graphs", interaction.user.id
                    )

                # Update the message to indicate completion
                # Requirement 8.3: Update ephemeral message after completion
                if metadata_list:
                    _ = await interaction.edit_original_message(
                        content=f"Successfully generated and posted {len(metadata_list)} graph(s) in {duration_ms / 1000:.1f}s!"
                    )
                else:
                    _ = await interaction.edit_original_message(
                        content="Graph generation completed, but no graphs were enabled or generated."
                    )

                log_operation_complete(
                    logger,
                    "update_graphs_command",
                    success=True,
                    duration_ms=duration_ms,
                    details={"graphs_generated": len(metadata_list)},
                )

            except* TautulliAPIError as eg:
                # Requirement 27.1, 27.2: Handle ExceptionGroup from TaskGroup
                error_msg = "Failed to fetch data from Tautulli"
                for exc in eg.exceptions:
                    logger.error(f"Tautulli API error: {exc}", exc_info=True)
                    error_msg = f"Failed to fetch data from Tautulli: {exc}"

                _ = await interaction.edit_original_message(content=error_msg)

                log_operation_complete(
                    logger,
                    "update_graphs_command",
                    success=False,
                    error=error_msg,
                )

            except* GraphGenerationError as eg:
                # Requirement 27.1, 27.2: Handle multiple graph generation errors
                error_count = len(eg.exceptions)
                error_msg = f"Failed to generate {error_count} graph(s)"

                for exc in eg.exceptions:
                    logger.error(f"Graph generation error: {exc}", exc_info=True)

                _ = await interaction.edit_original_message(
                    content=f"{error_msg}. Check logs for details."
                )

                log_operation_complete(
                    logger,
                    "update_graphs_command",
                    success=False,
                    error=error_msg,
                    details={"error_count": error_count},
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
    async def my_stats(self, interaction: nextcord.Interaction[TGraphBot]) -> None:
        """Generate personal statistics for the requesting user.

        This command:
        1. Checks rate limiting
        2. Generates graphs filtered to user's activity
        3. Sends as ephemeral message (privacy mode)
        4. Handles case where user has no data

        Args:
            interaction: The Discord interaction object

        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 22.1, 22.3, 27.1, 27.2
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
            # Requirement 9.5: Reject command if rate limit is active
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

            # Start operation tracking
            _ = log_operation_start(
                logger,
                "my_stats_command",
                details={"user_id": interaction.user.id if interaction.user else None},
            )
            start_time = datetime.now(tz=UTC)

            try:
                # Get username from Discord user
                username = interaction.user.name if interaction.user else None
                if not username:
                    _ = await interaction.edit_original_message(
                        content="Unable to determine your username."
                    )
                    return

                # Requirement 9.1, 9.3: Generate graphs filtered to user's activity
                metadata_list = await self._generate_personal_stats(username=username)

                # Requirement 9.4: Handle case where user has no data
                if not metadata_list:
                    _ = await interaction.edit_original_message(
                        content=f"No viewing activity found for user '{username}' in the configured time range."
                    )
                    return

                # Calculate duration
                duration_ms = (datetime.now(tz=UTC) - start_time).total_seconds() * 1000

                # Record command usage for rate limiting
                if interaction.user:
                    self.bot.rate_limiter.record_usage("my_stats", interaction.user.id)

                # Send the graphs as ephemeral messages
                # Requirement 9.2: Send as ephemeral message visible only to user
                _ = await interaction.edit_original_message(
                    content=f"Your personal statistics ({len(metadata_list)} graph(s)):"
                )

                # Send each graph as a separate ephemeral message
                for metadata in metadata_list:
                    try:
                        with open(metadata.file_path, "rb") as f:
                            file = nextcord.File(
                                f, filename=Path(metadata.file_path).name
                            )
                            _ = await interaction.followup.send(
                                file=file,
                                ephemeral=True,
                            )
                    except Exception as file_error:
                        logger.error(
                            f"Failed to send graph file: {file_error}",
                            exc_info=True,
                        )

                log_operation_complete(
                    logger,
                    "my_stats_command",
                    success=True,
                    duration_ms=duration_ms,
                    details={"graphs_generated": len(metadata_list)},
                )

            except* TautulliAPIError as eg:
                # Requirement 27.1, 27.2: Handle ExceptionGroup
                error_msg = "Failed to fetch your viewing data from Tautulli"
                for exc in eg.exceptions:
                    logger.error(f"Tautulli API error: {exc}", exc_info=True)

                _ = await interaction.edit_original_message(content=error_msg)

                log_operation_complete(
                    logger,
                    "my_stats_command",
                    success=False,
                    error=error_msg,
                )

            except* GraphGenerationError as eg:
                # Requirement 27.1, 27.2: Handle multiple errors
                error_count = len(eg.exceptions)
                error_msg = f"Failed to generate {error_count} graph(s)"

                for exc in eg.exceptions:
                    logger.error(f"Graph generation error: {exc}", exc_info=True)

                _ = await interaction.edit_original_message(
                    content=f"{error_msg}. Check logs for details."
                )

                log_operation_complete(
                    logger,
                    "my_stats_command",
                    success=False,
                    error=error_msg,
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
    async def config(self, interaction: nextcord.Interaction[TGraphBot]) -> None:
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
            # Requirement 10.5: Reject command if rate limit is active
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

            # Requirement 10.1: Display current configuration values organized by section
            # Requirement 10.2: Mask sensitive values (API keys, tokens)
            config_dict = self.bot.config.model_dump()
            masked_config = mask_sensitive_dict(config_dict)

            # Format configuration as readable text
            config_text = self._format_config_dict(masked_config)

            # Requirement 10.4: Split output if exceeds Discord message limits
            messages = self._split_message(config_text, limit=DISCORD_MESSAGE_LIMIT)

            # Record command usage for rate limiting
            if interaction.user:
                self.bot.rate_limiter.record_usage("config", interaction.user.id)

            # Requirement 10.3: Use ephemeral message that auto-deletes
            delete_after = (
                self.bot.config.services.discord.ephemeral_message_delete_after
            )

            # Send first message as response
            _ = await interaction.response.send_message(
                f"**Current Bot Configuration:**\n```\n{messages[0]}\n```",
                ephemeral=True,
                delete_after=delete_after,
            )

            # Send additional messages as followups if needed
            for msg in messages[1:]:
                _ = await interaction.followup.send(
                    f"```\n{msg}\n```",
                    ephemeral=True,
                    delete_after=delete_after,
                )

            logger.info(
                "Config command executed",
                extra={"message_count": len(messages)},
            )

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

    async def execute_scheduled_update(self) -> None:
        """Execute a scheduled graph update.

        This method implements the UpdateExecutor protocol and is called by
        the TaskScheduler to perform automated graph generation and posting.

        It generates all enabled graphs using TaskGroup for concurrency and
        posts them to the configured Discord channel with a timestamp.

        Requirements: 7.4, 7.5, 22.1
        """
        logger.info("Executing scheduled graph update")
        try:
            _ = await self._generate_and_post_graphs(username_filter=None)
            logger.info("Scheduled graph update completed successfully")
        except Exception as e:
            logger.error(f"Error during scheduled graph update: {e}", exc_info=True)
            raise

    async def _generate_and_post_graphs(
        self, *, username_filter: str | None = None
    ) -> GraphMetadataList:
        """Generate graphs and post them to the configured Discord channel.

        This method:
        1. Creates Tautulli client
        2. Fetches stream data (optionally filtered by username)
        3. Generates all enabled graphs using TaskGroup
        4. Posts graphs to Discord channel

        Args:
            username_filter: Optional username to filter data (for personal stats)

        Returns:
            List of GraphMetadata for generated graphs

        Raises:
            TautulliAPIError: If data fetching fails
            GraphGenerationError: If graph generation fails

        Requirements: 8.3, 22.1, 22.3
        """
        # Create Tautulli client
        tautulli_config = self.bot.config.services.tautulli
        tautulli_client = TautulliClient(
            api_key=tautulli_config.api_key,
            base_url=tautulli_config.url,
        )

        # Fetch stream history
        data_config = self.bot.config.data_collection
        if username_filter:
            # Fetch user-specific data
            history = await tautulli_client.get_user_history(
                username=username_filter,
                days=data_config.history_days,
            )
        else:
            # Fetch all history
            history = await tautulli_client.get_history(
                days=data_config.history_days,
                length=data_config.max_records_per_request,
            )

        # Convert to StreamRecord objects
        from tgraph_bot.graphs.data import transform_tautulli_records

        stream_records = transform_tautulli_records(history)

        if not stream_records:
            logger.warning(
                "No stream records found",
                extra={"username_filter": username_filter},
            )
            return []

        # Generate graphs using renderer
        styling = GraphStyling()
        factory = GraphFactory()
        renderer = GraphRenderer(styling=styling, factory=factory)

        output_dir = Path(self.bot.config.system.output_directory)
        metadata_list = await renderer.render_all_graphs(
            data=stream_records,
            config=self.bot.config.graphs,
            output_dir=output_dir,
        )

        # Post graphs to Discord channel (if not filtered for personal stats)
        if not username_filter:
            await self._post_graphs_to_channel(metadata_list)

        return metadata_list

    async def _generate_personal_stats(self, *, username: str) -> GraphMetadataList:
        """Generate personal statistics graphs for a specific user.

        Args:
            username: Username to filter data for

        Returns:
            List of GraphMetadata for generated graphs

        Requirements: 9.1, 9.3, 9.4
        """
        # Generate graphs with username filter
        return await self._generate_and_post_graphs(username_filter=username)

    async def _post_graphs_to_channel(self, metadata_list: GraphMetadataList) -> None:
        """Post generated graphs to the configured Discord channel.

        Args:
            metadata_list: List of graph metadata with file paths

        Requirement 8.3: Post graphs to configured channel with timestamp
        """
        if not metadata_list:
            return

        channel_id = self.bot.config.services.discord.channel_id
        channel = self.bot.get_channel(channel_id)

        if channel is None or not isinstance(channel, nextcord.TextChannel):
            logger.error(
                f"Channel {channel_id} not found or is not a text channel",
                extra={"channel_id": channel_id},
            )
            return

        # Format timestamp according to configuration
        timestamp_format = self.bot.config.services.discord.timestamp_format
        timestamp = datetime.now(tz=UTC)
        timestamp_unix = int(timestamp.timestamp())
        formatted_timestamp = f"<t:{timestamp_unix}:{timestamp_format}>"

        # Post message with timestamp
        _ = await channel.send(
            f"Generated {len(metadata_list)} graph(s) at {formatted_timestamp}"
        )

        # Post each graph
        # Requirement 22.1: Use TaskGroup for concurrent posting
        try:
            async with asyncio.TaskGroup() as tg:
                for metadata in metadata_list:
                    _ = tg.create_task(self._send_graph_file(channel, metadata))
        except* Exception as eg:
            # Log errors but don't fail the entire operation
            for exc in eg.exceptions:
                logger.error(f"Error posting graph: {exc}", exc_info=True)

    async def _send_graph_file(
        self, channel: nextcord.TextChannel, metadata: GraphMetadata
    ) -> None:
        """Send a single graph file to a Discord channel.

        Args:
            channel: Discord text channel to send to
            metadata: Graph metadata with file path

        Raises:
            Exception: If file cannot be sent
        """
        try:
            with open(metadata.file_path, "rb") as f:
                file = nextcord.File(f, filename=Path(metadata.file_path).name)
                _ = await channel.send(
                    f"**{metadata.graph_type.replace('_', ' ').title()}**",
                    file=file,
                )
        except Exception as e:
            logger.error(
                f"Failed to send graph file: {metadata.file_path}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise GraphGenerationError(
                f"Failed to send graph {metadata.graph_type}: {e}"
            ) from e

    def _format_config_dict(self, config: ConfigDict, *, indent: int = 0) -> str:
        """Format configuration dictionary as readable text.

        Args:
            config: Configuration dictionary to format
            indent: Current indentation level

        Returns:
            Formatted configuration string

        Requirement 10.1: Display configuration organized by section
        """
        lines: list[str] = []
        indent_str = "  " * indent

        for key, value in config.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}{key}:")
                # Type narrowing for recursive call
                dict_value: dict[str, object] = value  # pyright: ignore[reportUnknownVariableType]
                lines.append(self._format_config_dict(dict_value, indent=indent + 1))
            elif isinstance(value, list):
                # Type narrowing for len() call
                list_value: list[object] = value  # pyright: ignore[reportUnknownVariableType]
                lines.append(f"{indent_str}{key}: [{len(list_value)} items]")
            else:
                lines.append(f"{indent_str}{key}: {value}")

        return "\n".join(lines)

    def _split_message(
        self, text: str, *, limit: int = DISCORD_MESSAGE_LIMIT
    ) -> MessageChunks:
        """Split a long message into chunks that fit Discord's message limit.

        Args:
            text: Text to split
            limit: Maximum characters per message (accounting for formatting)

        Returns:
            List of message chunks

        Requirement 10.4: Split output if exceeds message limits
        """
        # Reserve space for markdown code block markers (8 chars)
        effective_limit = limit - 8

        if len(text) <= effective_limit:
            return [text]

        # Split by lines to preserve formatting
        lines = text.split("\n")
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > effective_limit:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        # Add remaining chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks


def setup(bot: TGraphBot) -> None:
    """Set up the GraphCommands cog.

    This function is called by nextcord when loading the cog.

    Args:
        bot: The TGraphBot instance
    """
    bot.add_cog(GraphCommands(bot))
    logger.info("GraphCommands cog loaded")
