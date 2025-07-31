"""
Test helper utilities for TGraph Bot tests.

This module provides reusable utility functions and context managers for
common testing patterns, including configuration management, temporary file
handling, mock object creation, and resource cleanup.

All utilities are designed with type safety and proper error handling in mind.
"""

from __future__ import annotations

import tempfile
import yaml
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

__all__ = [
    "create_config_manager_with_config",
    "create_test_config",
    "create_test_config_with_overrides",
    "create_temp_config_file",
    "create_temp_directory",
    "create_mock_discord_bot",
    "create_mock_user",
    "create_mock_guild",
    "create_mock_interaction",
    "create_mock_channel",
    "create_mock_message",
    "assert_graph_output_valid",
    "assert_file_cleanup_successful",
    "assert_config_values_match",
    "assert_mock_called_with_pattern",
]

if TYPE_CHECKING:
    import discord
    from discord.ext import commands

    from src.tgraph_bot.config.manager import ConfigManager
    from src.tgraph_bot.config.schema import TGraphBotConfig


def create_config_manager_with_config(config: TGraphBotConfig) -> ConfigManager:
    """
    Create a ConfigManager instance with a pre-configured TGraphBotConfig.

    This utility function eliminates the common pattern of creating a ConfigManager
    and then setting its current configuration. It provides a clean, type-safe way
    to create a configured manager for testing.

    Args:
        config: The TGraphBotConfig instance to set as the current configuration

    Returns:
        ConfigManager: A configured ConfigManager instance

    Raises:
        ImportError: If ConfigManager cannot be imported
        AttributeError: If ConfigManager doesn't have expected methods

    Example:
        >>> from tests.conftest import base_config
        >>> from tests.utils import create_config_manager_with_config
        >>>
        >>> config = base_config()
        >>> manager = create_config_manager_with_config(config)
        >>> assert manager.get_current_config() == config
    """
    try:
        from src.tgraph_bot.config.manager import ConfigManager
    except ImportError as e:
        msg = f"Failed to import ConfigManager: {e}"
        raise ImportError(msg) from e

    try:
        manager = ConfigManager()
        manager.set_current_config(config)
        return manager
    except AttributeError as e:
        msg = f"ConfigManager missing expected methods: {e}"
        raise AttributeError(msg) from e


def create_test_config(
    *,
    tautulli_api_key: str = "test_api_key",
    tautulli_url: str = "http://localhost:8181",
    discord_token: str = "test_discord_token_1234567890",
    discord_channel_id: int = 123456789012345678,
) -> TGraphBotConfig:
    """
    Create a TGraphBotConfig instance with nested structure for testing.

    This utility function creates a properly structured TGraphBotConfig instance
    using the new nested configuration schema, with sensible defaults for testing.
    It replaces the old flat configuration pattern with the modern nested approach.

    Args:
        tautulli_api_key: API key for Tautulli service
        tautulli_url: URL for Tautulli service
        discord_token: Discord bot token
        discord_channel_id: Discord channel ID

    Returns:
        TGraphBotConfig: A configured instance with the nested structure

    Raises:
        ImportError: If configuration schema classes cannot be imported

    Example:
        >>> # Basic config with defaults
        >>> config = create_test_config()
        >>> assert config.services.tautulli.api_key == "test_api_key"

        >>> # Config with custom values
        >>> config = create_test_config(
        ...     tautulli_api_key="custom_key",
        ...     discord_channel_id=999999999
        ... )
        >>> assert config.services.tautulli.api_key == "custom_key"
    """
    try:
        from src.tgraph_bot.config.schema import (
            TGraphBotConfig,
            ServicesConfig,
            TautulliConfig,
            DiscordConfig,
        )
    except ImportError as e:
        msg = f"Failed to import configuration schema: {e}"
        raise ImportError(msg) from e

    # Create configuration with provided values
    services_config = ServicesConfig(
        tautulli=TautulliConfig(
            api_key=tautulli_api_key,
            url=tautulli_url,
        ),
        discord=DiscordConfig(
            token=discord_token,
            channel_id=discord_channel_id,
        ),
    )

    # Create the main config with services and defaults for other sections
    config = TGraphBotConfig(services=services_config)

    return config


def create_test_config_with_overrides(**kwargs: object) -> TGraphBotConfig:
    """
    Create a TGraphBotConfig with specific overrides for testing.

    This function provides a flexible way to create test configurations
    by accepting old flat parameter names and converting them to the
    new nested structure automatically.

    Args:
        **kwargs: Configuration overrides using old flat names or new nested structure

    Returns:
        TGraphBotConfig: Configured instance

    Example:
        >>> config = create_test_config_with_overrides(
        ...     TAUTULLI_API_KEY="custom_key",
        ...     ENABLE_DAILY_PLAY_COUNT=False,
        ...     TV_COLOR="#ff0000"
        ... )
    """
    try:
        from src.tgraph_bot.config.schema import (
            TGraphBotConfig, ServicesConfig, TautulliConfig, DiscordConfig,
            GraphsConfig, GraphFeaturesConfig, EnabledTypesConfig,
            GraphAppearanceConfig, ColorsConfig, AnnotationsConfig,
            BasicAnnotationsConfig, EnabledOnConfig, GridConfig,
            PalettesConfig, DataCollectionConfig, TimeRangesConfig, PrivacyConfig,
        )
    except ImportError as e:
        msg = f"Failed to import configuration schema: {e}"
        raise ImportError(msg) from e

    # Extract service configuration
    tautulli_api_key = str(kwargs.get("TAUTULLI_API_KEY", "test_api_key"))
    tautulli_url = str(kwargs.get("TAUTULLI_URL", "http://localhost:8181"))
    discord_token = str(kwargs.get("DISCORD_TOKEN", "test_discord_token_1234567890"))
    channel_id_value = kwargs.get("CHANNEL_ID", 123456789012345678)
    discord_channel_id = int(channel_id_value) if isinstance(channel_id_value, (int, str)) else 123456789012345678
    discord_timestamp_format = str(kwargs.get("DISCORD_TIMESTAMP_FORMAT", "R"))

    # Extract graph feature configuration
    enable_daily_play_count = bool(kwargs.get("ENABLE_DAILY_PLAY_COUNT", True))
    enable_play_count_by_dayofweek = bool(kwargs.get("ENABLE_PLAY_COUNT_BY_DAYOFWEEK", True))
    enable_play_count_by_hourofday = bool(kwargs.get("ENABLE_PLAY_COUNT_BY_HOUROFDAY", True))
    enable_play_count_by_month = bool(kwargs.get("ENABLE_PLAY_COUNT_BY_MONTH", True))
    enable_top_10_platforms = bool(kwargs.get("ENABLE_TOP_10_PLATFORMS", True))
    enable_top_10_users = bool(kwargs.get("ENABLE_TOP_10_USERS", True))
    enable_media_type_separation = bool(kwargs.get("ENABLE_MEDIA_TYPE_SEPARATION", True))
    enable_stacked_bar_charts = bool(kwargs.get("ENABLE_STACKED_BAR_CHARTS", True))

    # Extract appearance configuration
    tv_color = str(kwargs.get("TV_COLOR", "#1f77b4"))
    movie_color = str(kwargs.get("MOVIE_COLOR", "#ff7f0e"))
    graph_background_color = str(kwargs.get("GRAPH_BACKGROUND_COLOR", "#ffffff"))
    enable_graph_grid = bool(kwargs.get("ENABLE_GRAPH_GRID", False))

    # Extract annotation configuration
    annotation_color = str(kwargs.get("ANNOTATION_COLOR", "#ff0000"))
    annotation_outline_color = str(kwargs.get("ANNOTATION_OUTLINE_COLOR", "#000000"))
    enable_annotation_outline = bool(kwargs.get("ENABLE_ANNOTATION_OUTLINE", True))
    annotate_daily_play_count = bool(kwargs.get("ANNOTATE_DAILY_PLAY_COUNT", True))
    annotate_play_count_by_dayofweek = bool(kwargs.get("ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK", True))
    annotate_play_count_by_hourofday = bool(kwargs.get("ANNOTATE_PLAY_COUNT_BY_HOUROFDAY", True))
    annotate_play_count_by_month = bool(kwargs.get("ANNOTATE_PLAY_COUNT_BY_MONTH", True))
    annotate_top_10_platforms = bool(kwargs.get("ANNOTATE_TOP_10_PLATFORMS", True))
    annotate_top_10_users = bool(kwargs.get("ANNOTATE_TOP_10_USERS", True))

    # Extract palette configuration
    daily_play_count_palette = str(kwargs.get("DAILY_PLAY_COUNT_PALETTE", ""))
    play_count_by_dayofweek_palette = str(kwargs.get("PLAY_COUNT_BY_DAYOFWEEK_PALETTE", ""))
    play_count_by_hourofday_palette = str(kwargs.get("PLAY_COUNT_BY_HOUROFDAY_PALETTE", ""))
    play_count_by_month_palette = str(kwargs.get("PLAY_COUNT_BY_MONTH_PALETTE", ""))
    top_10_platforms_palette = str(kwargs.get("TOP_10_PLATFORMS_PALETTE", ""))
    top_10_users_palette = str(kwargs.get("TOP_10_USERS_PALETTE", ""))

    # Extract data collection configuration
    time_range_days_value = kwargs.get("TIME_RANGE_DAYS", 30)
    time_range_days = int(time_range_days_value) if isinstance(time_range_days_value, (int, str)) else 30
    time_range_months_value = kwargs.get("TIME_RANGE_MONTHS", 12)
    time_range_months = int(time_range_months_value) if isinstance(time_range_months_value, (int, str)) else 12
    censor_usernames = bool(kwargs.get("CENSOR_USERNAMES", True))

    # Build the configuration
    config = TGraphBotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key=tautulli_api_key,
                url=tautulli_url,
            ),
            discord=DiscordConfig(
                token=discord_token,
                channel_id=discord_channel_id,
                timestamp_format=discord_timestamp_format,  # pyright: ignore[reportArgumentType]
            ),
        ),
        graphs=GraphsConfig(
            features=GraphFeaturesConfig(
                enabled_types=EnabledTypesConfig(
                    daily_play_count=enable_daily_play_count,
                    play_count_by_dayofweek=enable_play_count_by_dayofweek,
                    play_count_by_hourofday=enable_play_count_by_hourofday,
                    play_count_by_month=enable_play_count_by_month,
                    top_10_platforms=enable_top_10_platforms,
                    top_10_users=enable_top_10_users,
                ),
                media_type_separation=enable_media_type_separation,
                stacked_bar_charts=enable_stacked_bar_charts,
            ),
            appearance=GraphAppearanceConfig(
                colors=ColorsConfig(
                    tv=tv_color,
                    movie=movie_color,
                    background=graph_background_color,
                ),
                grid=GridConfig(
                    enabled=enable_graph_grid,
                ),
                annotations=AnnotationsConfig(
                    basic=BasicAnnotationsConfig(
                        color=annotation_color,
                        outline_color=annotation_outline_color,
                        enable_outline=enable_annotation_outline,
                    ),
                    enabled_on=EnabledOnConfig(
                        daily_play_count=annotate_daily_play_count,
                        play_count_by_dayofweek=annotate_play_count_by_dayofweek,
                        play_count_by_hourofday=annotate_play_count_by_hourofday,
                        play_count_by_month=annotate_play_count_by_month,
                        top_10_platforms=annotate_top_10_platforms,
                        top_10_users=annotate_top_10_users,
                    ),
                ),
                palettes=PalettesConfig(
                    daily_play_count=daily_play_count_palette,
                    play_count_by_dayofweek=play_count_by_dayofweek_palette,
                    play_count_by_hourofday=play_count_by_hourofday_palette,
                    play_count_by_month=play_count_by_month_palette,
                    top_10_platforms=top_10_platforms_palette,
                    top_10_users=top_10_users_palette,
                ),
            ),
        ),
        data_collection=DataCollectionConfig(
            time_ranges=TimeRangesConfig(
                days=time_range_days,
                months=time_range_months,
            ),
            privacy=PrivacyConfig(
                censor_usernames=censor_usernames,
            ),
        ),
    )

    return config


@contextmanager
def create_temp_config_file(
    config_data: dict[str, object] | None = None,
    *,
    suffix: str = ".yml",
    encoding: str = "utf-8",
) -> Generator[Path, None, None]:
    """
    Create a temporary configuration file with YAML content.

    This context manager creates a temporary file with configuration data
    in YAML format, yields the file path, and ensures cleanup on exit.
    It standardizes the pattern of creating temporary config files for testing.

    Args:
        config_data: Dictionary of configuration data to write to file.
                    If None, creates a minimal valid configuration.
        suffix: File suffix for the temporary file (default: ".yml")
        encoding: File encoding (default: "utf-8")

    Yields:
        Path: Path to the created temporary configuration file

    Raises:
        OSError: If file creation or writing fails
        yaml.YAMLError: If YAML serialization fails

    Example:
        >>> config_data = {
        ...     'TAUTULLI_API_KEY': 'test_key',
        ...     'TAUTULLI_URL': 'http://localhost:8181/api/v2',
        ...     'DISCORD_TOKEN': 'test_token',
        ...     'CHANNEL_ID': 123456789,
        ... }
        >>> with create_temp_config_file(config_data) as config_path:
        ...     # Use config_path for testing
        ...     assert config_path.exists()
        ...     # File is automatically cleaned up after context
    """
    if config_data is None:
        # Provide minimal valid configuration data
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
        }

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            encoding=encoding,
            delete=False,
        ) as temp_file:
            try:
                yaml.dump(config_data, temp_file, default_flow_style=False)
                temp_path = Path(temp_file.name)
            except yaml.YAMLError as e:
                msg = f"Failed to serialize configuration data to YAML: {e}"
                raise yaml.YAMLError(msg) from e

        try:
            yield temp_path
        finally:
            # Ensure cleanup even if an exception occurs
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                # Ignore cleanup errors - file might already be deleted
                pass

    except OSError as e:
        msg = f"Failed to create temporary configuration file: {e}"
        raise OSError(msg) from e


@contextmanager
def create_temp_directory(
    *,
    prefix: str | None = None,
    suffix: str | None = None,
) -> Generator[Path, None, None]:
    """
    Create a temporary directory with automatic cleanup.

    This context manager creates a temporary directory, yields its path,
    and ensures complete cleanup on exit. It standardizes temporary directory
    creation patterns used across tests.

    Args:
        prefix: Optional prefix for the directory name
        suffix: Optional suffix for the directory name

    Yields:
        Path: Path to the created temporary directory

    Raises:
        OSError: If directory creation fails

    Example:
        >>> with create_temp_directory(prefix="test_graphs_") as temp_dir:
        ...     # Use temp_dir for testing
        ...     assert temp_dir.exists()
        ...     assert temp_dir.is_dir()
        ...     # Directory is automatically cleaned up after context
    """
    try:
        with tempfile.TemporaryDirectory(
            prefix=prefix,
            suffix=suffix,
        ) as temp_dir_str:
            temp_dir_path = Path(temp_dir_str)
            yield temp_dir_path
    except OSError as e:
        msg = f"Failed to create temporary directory: {e}"
        raise OSError(msg) from e


def create_mock_discord_bot(
    *,
    user_id: int = 123456789,
    user_name: str = "TestBot",
    guild_count: int = 2,
    intents: discord.Intents | None = None,
) -> commands.Bot:
    """
    Create a mock Discord bot with configurable attributes.

    This utility function creates a standardized mock Discord bot instance
    that can be used across tests. It provides sensible defaults while
    allowing customization of key attributes.

    Args:
        user_id: The bot user ID (default: 123456789)
        user_name: The bot username (default: "TestBot")
        guild_count: Number of guilds the bot should appear to be in (default: 2)
        intents: Discord intents for the bot (default: None, creates basic intents)

    Returns:
        commands.Bot: A configured mock Discord bot with the specified attributes

    Raises:
        ValueError: If user_id is not positive or guild_count is negative

    Example:
        >>> bot = create_mock_discord_bot(user_name="MyTestBot", guild_count=5)
        >>> assert bot.user.name == "MyTestBot"
        >>> assert len(bot.guilds) == 5
    """
    if user_id <= 0:
        msg = "user_id must be a positive integer"
        raise ValueError(msg)

    if guild_count < 0:
        msg = "guild_count must be non-negative"
        raise ValueError(msg)

    try:
        import discord
        from discord.ext import commands
    except ImportError as e:
        msg = f"Failed to import discord.py: {e}"
        raise ImportError(msg) from e

    # Create mock bot
    mock_bot = MagicMock(spec=commands.Bot)

    # Create mock user
    mock_user = MagicMock(spec=discord.User)
    mock_user.id = user_id
    mock_user.name = user_name
    mock_bot.user = mock_user

    # Create mock guilds
    mock_guilds: list[MagicMock] = []
    for i in range(guild_count):
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.id = 100000000000000000 + i  # Use realistic Discord IDs
        mock_guild.name = f"Test Guild {i + 1}"
        mock_guilds.append(mock_guild)

    mock_bot.guilds = mock_guilds

    # Set up intents
    if intents is None:
        mock_intents = MagicMock(spec=discord.Intents)
        mock_intents.message_content = True
        mock_intents.guilds = True
    else:
        mock_intents = intents

    mock_bot.intents = mock_intents

    # Set common bot attributes
    mock_bot.command_prefix = "!"
    mock_bot.help_command = None

    return cast(commands.Bot, mock_bot)


def create_mock_user(
    *,
    user_id: int = 987654321,
    username: str = "TestUser",
    display_name: str | None = None,
    bot: bool = False,
    guild_permissions: discord.Permissions | None = None,
) -> discord.User:
    """
    Create a mock Discord user with configurable attributes.

    This utility function creates a standardized mock Discord user instance
    that can be used across tests for various user-related scenarios.

    Args:
        user_id: The user ID (default: 987654321)
        username: The username (default: "TestUser")
        display_name: The display name (default: None, uses username)
        bot: Whether the user is a bot (default: False)
        guild_permissions: Guild permissions for the user (default: None)

    Returns:
        discord.User: A configured mock Discord user with the specified attributes

    Raises:
        ValueError: If user_id is not positive

    Example:
        >>> user = create_mock_user(username="TestAdmin", user_id=555)
        >>> assert user.name == "TestAdmin"
        >>> assert user.id == 555
        >>> assert user.bot is False
    """
    if user_id <= 0:
        msg = "user_id must be a positive integer"
        raise ValueError(msg)

    try:
        import discord
    except ImportError as e:
        msg = f"Failed to import discord.py: {e}"
        raise ImportError(msg) from e

    # Create mock user
    mock_user = MagicMock(spec=discord.User)
    mock_user.id = user_id
    mock_user.name = username
    mock_user.display_name = display_name or username
    mock_user.bot = bot

    # Set guild permissions if provided
    if guild_permissions is not None:
        mock_user.guild_permissions = guild_permissions

    return cast(discord.User, mock_user)


def create_mock_guild(
    *,
    guild_id: int = 111222333444555666,
    name: str = "Test Guild",
    owner_id: int = 777888999000111222,
    member_count: int = 100,
) -> discord.Guild:
    """
    Create a mock Discord guild with configurable attributes.

    This utility function creates a standardized mock Discord guild instance
    that can be used across tests for guild-related functionality.

    Args:
        guild_id: The guild ID (default: 111222333444555666)
        name: The guild name (default: "Test Guild")
        owner_id: The guild owner user ID (default: 777888999000111222)
        member_count: The number of members in the guild (default: 100)

    Returns:
        discord.Guild: A configured mock Discord guild with the specified attributes

    Raises:
        ValueError: If guild_id or owner_id is not positive, or member_count is negative

    Example:
        >>> guild = create_mock_guild(name="My Test Server", member_count=50)
        >>> assert guild.name == "My Test Server"
        >>> assert guild.member_count == 50
    """
    if guild_id <= 0:
        msg = "guild_id must be a positive integer"
        raise ValueError(msg)

    if owner_id <= 0:
        msg = "owner_id must be a positive integer"
        raise ValueError(msg)

    if member_count < 0:
        msg = "member_count must be non-negative"
        raise ValueError(msg)

    try:
        import discord
    except ImportError as e:
        msg = f"Failed to import discord.py: {e}"
        raise ImportError(msg) from e

    # Create mock guild
    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.id = guild_id
    mock_guild.name = name
    mock_guild.owner_id = owner_id
    mock_guild.member_count = member_count

    return cast(discord.Guild, mock_guild)


def create_mock_interaction(
    *,
    user_id: int = 987654321,
    username: str = "TestUser",
    guild_id: int | None = 111222333444555666,
    guild_name: str = "Test Guild",
    channel_id: int = 333444555666777888,
    command_name: str = "test_command",
    is_response_done: bool = False,
) -> discord.Interaction:
    """
    Create a mock Discord interaction with configurable attributes.

    This utility function creates a standardized mock Discord interaction instance
    that can be used across tests. It includes properly configured response and
    followup mocks for testing interaction handling.

    Args:
        user_id: The user ID (default: 987654321)
        username: The username (default: "TestUser")
        guild_id: The guild ID (default: 111222333444555666, None for DM)
        guild_name: The guild name (default: "Test Guild")
        channel_id: The channel ID (default: 333444555666777888)
        command_name: The command name (default: "test_command")
        is_response_done: Whether the response has been sent (default: False)

    Returns:
        discord.Interaction: A configured mock Discord interaction with the specified attributes

    Raises:
        ValueError: If any ID is not positive (except guild_id which can be None)

    Example:
        >>> interaction = create_mock_interaction(command_name="config")
        >>> assert interaction.user.id == 987654321
        >>> assert interaction.guild.id == 111222333444555666
        >>> assert not interaction.response.is_done()
    """
    if user_id <= 0:
        msg = "user_id must be a positive integer"
        raise ValueError(msg)

    if guild_id is not None and guild_id <= 0:
        msg = "guild_id must be a positive integer or None"
        raise ValueError(msg)

    if channel_id <= 0:
        msg = "channel_id must be a positive integer"
        raise ValueError(msg)

    try:
        import discord
    except ImportError as e:
        msg = f"Failed to import discord.py: {e}"
        raise ImportError(msg) from e

    # Create mock interaction
    mock_interaction = MagicMock(spec=discord.Interaction)

    # Create mock user
    mock_user = create_mock_user(user_id=user_id, username=username)
    mock_interaction.user = mock_user

    # Create mock guild (or None for DM)
    if guild_id is not None:
        mock_guild = create_mock_guild(guild_id=guild_id, name=guild_name)
        mock_interaction.guild = mock_guild
    else:
        mock_interaction.guild = None

    # Create mock channel
    mock_channel = MagicMock()
    mock_channel.id = channel_id
    mock_interaction.channel = mock_channel

    # Set up command information
    mock_command = MagicMock()
    mock_command.name = command_name
    mock_interaction.command = mock_command

    # Set up response mock
    mock_response = MagicMock()
    mock_response.is_done = MagicMock(return_value=is_response_done)
    mock_response.send_message = AsyncMock()
    mock_interaction.response = mock_response

    # Set up followup mock
    mock_followup = AsyncMock()
    mock_followup.send = AsyncMock()
    mock_interaction.followup = mock_followup

    return cast(discord.Interaction, mock_interaction)


def create_mock_channel(
    *,
    channel_id: int = 333444555666777888,
    name: str = "test-channel",
    channel_type: object | None = None,
    guild_id: int | None = 111222333444555666,
    permissions: dict[str, bool] | None = None,
) -> discord.TextChannel:
    """
    Create a mock Discord text channel with configurable attributes.

    This utility function creates a standardized mock Discord text channel instance
    that can be used across tests to avoid repetitive mock setup code.

    Args:
        channel_id: The channel ID (default: 333444555666777888)
        name: The channel name (default: "test-channel")
        channel_type: The channel type (default: discord.ChannelType.text)
        guild_id: The guild ID (default: 111222333444555666, None for DM)
        permissions: Dict of permission names to boolean values for bot permissions

    Returns:
        discord.TextChannel: A configured mock Discord text channel with the specified attributes

    Example:
        >>> channel = create_mock_channel(name="general", channel_id=123456)
        >>> assert channel.name == "general"
        >>> assert channel.id == 123456
    """
    if channel_id <= 0:
        msg = "channel_id must be a positive integer"
        raise ValueError(msg)

    try:
        import discord
        from unittest.mock import MagicMock
    except ImportError as e:
        msg = f"Required dependencies not available: {e}"
        raise ImportError(msg) from e

    # Create mock channel
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.id = channel_id
    mock_channel.name = name
    mock_channel.type = channel_type or discord.ChannelType.text

    # Set up guild if provided
    if guild_id is not None:
        mock_guild = MagicMock()
        mock_guild.id = guild_id
        mock_channel.guild = mock_guild

        # Set up bot permissions
        mock_guild_member = MagicMock()
        default_permissions = {
            "manage_messages": True,
            "send_messages": True,
            "read_messages": True,
            "embed_links": True,
            "attach_files": True,
        }
        if permissions:
            default_permissions.update(permissions)

        # Create permissions object
        mock_permissions = MagicMock()
        for perm_name, perm_value in default_permissions.items():
            setattr(mock_permissions, perm_name, perm_value)

        permissions_for = mock_guild_member.permissions_for  # pyright: ignore[reportAny]
        permissions_for.return_value = mock_permissions
        mock_guild.me = mock_guild_member
    else:
        mock_channel.guild = None

    return mock_channel


def create_mock_message(
    *,
    message_id: str | int = "123456789",
    author_id: int = 987654321,
    author_name: str = "TestUser",
    content: str = "Test message",
    is_bot: bool = False,
) -> discord.Message:
    """
    Create a mock Discord message with configurable attributes.

    This utility function creates a standardized mock Discord message instance
    that can be used across tests to avoid repetitive mock setup code.

    Args:
        message_id: The message ID (default: "123456789")
        author_id: The author's user ID (default: 987654321)
        author_name: The author's username (default: "TestUser")
        content: The message content (default: "Test message")
        is_bot: Whether the author is a bot (default: False)

    Returns:
        discord.Message: A configured mock Discord message with the specified attributes

    Example:
        >>> message = create_mock_message(content="Hello world", author_name="Alice")
        >>> assert message.content == "Hello world"
        >>> assert message.author.name == "Alice"
    """
    try:
        import discord
        from unittest.mock import MagicMock, AsyncMock
    except ImportError as e:
        msg = f"Required dependencies not available: {e}"
        raise ImportError(msg) from e

    # Create mock message
    mock_message = MagicMock(spec=discord.Message)
    mock_message.id = message_id
    mock_message.content = content

    # Create mock author
    mock_author = MagicMock(spec=discord.User)
    mock_author.id = author_id
    mock_author.name = author_name
    mock_author.bot = is_bot
    mock_message.author = mock_author

    # Add async delete method
    mock_message.delete = AsyncMock()

    return mock_message


def assert_graph_output_valid(
    output_path: str,
    *,
    expected_extension: str = ".png",
    expected_filename_pattern: str | None = None,
    should_exist: bool = True,
) -> None:
    """
    Assert that graph output meets standard validation criteria.

    This utility function consolidates common graph output validation patterns
    to reduce repetitive assertion code across tests.

    Args:
        output_path: The path to the generated graph file
        expected_extension: Expected file extension (default: ".png")
        expected_filename_pattern: Optional pattern that should be in filename
        should_exist: Whether the file should exist (default: True)

    Raises:
        AssertionError: If any validation criteria are not met

    Example:
        >>> output_path = graph.generate(data)
        >>> assert_graph_output_valid(output_path, expected_filename_pattern="daily_play_count")
    """
    from pathlib import Path

    output_file = Path(output_path)

    if should_exist:
        assert output_file.exists(), f"Graph output file should exist: {output_path}"
        assert output_path.endswith(expected_extension), (
            f"Graph output should have {expected_extension} extension: {output_path}"
        )

        if expected_filename_pattern:
            assert expected_filename_pattern in output_path, (
                f"Graph filename should contain '{expected_filename_pattern}': {output_path}"
            )
    else:
        assert not output_file.exists(), (
            f"Graph output file should not exist: {output_path}"
        )


def assert_file_cleanup_successful(file_path: str | Path) -> None:
    """
    Assert that file cleanup was successful.

    This utility function provides a standard way to verify that test files
    have been properly cleaned up after test execution.

    Args:
        file_path: Path to the file that should be cleaned up

    Raises:
        AssertionError: If the file still exists after cleanup

    Example:
        >>> output_path = graph.generate(data)
        >>> Path(output_path).unlink(missing_ok=True)
        >>> assert_file_cleanup_successful(output_path)
    """
    from pathlib import Path

    file_obj = Path(file_path)
    assert not file_obj.exists(), f"File should be cleaned up: {file_path}"


def assert_config_values_match(
    actual_config: object,
    expected_values: dict[str, object],
) -> None:
    """
    Assert that configuration object has expected attribute values.

    This utility function consolidates configuration validation patterns
    to reduce repetitive assertion code across configuration tests.

    Args:
        actual_config: The configuration object to validate
        expected_values: Dictionary of attribute names to expected values

    Raises:
        AssertionError: If any configuration values don't match expectations

    Example:
        >>> config = create_test_config_with_overrides(
                TAUTULLI_API_KEY="test_key", ...,
            )
        >>> assert_config_values_match(config, {
        ...     "TAUTULLI_API_KEY": "test_key",
        ...     "UPDATE_DAYS": 7,
        ... })
    """
    for attr_name, expected_value in expected_values.items():
        actual_value: object = getattr(actual_config, attr_name)  # pyright: ignore[reportAny]
        assert actual_value == expected_value, (
            f"Config attribute {attr_name}: expected {expected_value}, got {actual_value}"
        )


def assert_mock_called_with_pattern(
    mock_obj: object,
    *,
    call_count: int | None = None,
    called_with_args: tuple[object, ...] | None = None,
    called_with_kwargs: dict[str, object] | None = None,
    not_called: bool = False,
) -> None:
    """
    Assert that mock object was called according to specified patterns.

    This utility function consolidates common mock verification patterns
    to reduce repetitive assertion code across tests.

    Args:
        mock_obj: The mock object to verify
        call_count: Expected number of calls (None to skip check)
        called_with_args: Expected positional arguments for last call
        called_with_kwargs: Expected keyword arguments for last call
        not_called: Whether the mock should not have been called

    Raises:
        AssertionError: If mock call patterns don't match expectations

    Example:
        >>> mock_func = MagicMock()
        >>> mock_func("arg1", key="value")
        >>> assert_mock_called_with_pattern(
        ...     mock_func,
        ...     call_count=1,
        ...     called_with_args=("arg1",),
        ...     called_with_kwargs={"key": "value"}
        ... )
    """
    from unittest.mock import MagicMock

    if not isinstance(mock_obj, MagicMock):
        msg = f"Expected MagicMock object, got {type(mock_obj)}"
        raise TypeError(msg)

    if not_called:
        assert not mock_obj.called, "Mock should not have been called"
        return

    if call_count is not None:
        assert mock_obj.call_count == call_count, (
            f"Expected {call_count} calls, got {mock_obj.call_count}"
        )

    if called_with_args is not None or called_with_kwargs is not None:
        if not mock_obj.called:
            msg = "Mock was not called, cannot verify call arguments"
            raise AssertionError(msg)

        last_call = mock_obj.call_args
        if called_with_args is not None:
            actual_args = last_call.args if last_call else ()
            assert actual_args == called_with_args, (
                f"Expected args {called_with_args}, got {actual_args}"
            )

        if called_with_kwargs is not None:
            from typing import cast

            actual_kwargs = cast(
                dict[str, object], last_call.kwargs if last_call else {}
            )
            assert actual_kwargs == called_with_kwargs, (
                f"Expected kwargs {called_with_kwargs}, got {actual_kwargs}"
            )
