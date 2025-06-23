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
            'TAUTULLI_API_KEY': 'test_api_key',
            'TAUTULLI_URL': 'http://localhost:8181/api/v2',
            'DISCORD_TOKEN': 'test_discord_token',
            'CHANNEL_ID': 123456789012345678,
        }
    
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
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
