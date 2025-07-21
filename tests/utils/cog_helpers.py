"""
Cog testing utilities for TGraph Bot tests.

This module provides reusable utility functions for testing Discord cogs,
eliminating redundant test patterns across cog test files. All utilities
follow Python 3.13 best practices and maintain strict type safety.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import discord
import pytest
from discord.ext import commands

if TYPE_CHECKING:
    from src.tgraph_bot.main import TGraphBot
    from src.tgraph_bot.config.schema import TGraphBotConfig
    from src.tgraph_bot.utils.discord.base_command_cog import BaseCommandCog

# Type variable for Discord cog classes that inherit from BaseCommandCog
CogT = TypeVar("CogT", bound="BaseCommandCog")


def assert_cog_initialization(
    cog_class: type[CogT],
    bot: TGraphBot,
    *,
    expected_attributes: dict[str, object] | None = None,
) -> CogT:
    """
    Test standard Discord cog initialization patterns.

    This utility consolidates the common pattern of testing cog initialization
    including bot assignment and TGraphBot type checking.

    Args:
        cog_class: The Discord cog class to test
        bot: TGraphBot instance to pass to the cog
        expected_attributes: Optional dict of attribute names and expected values

    Returns:
        The initialized cog instance for further testing

    Raises:
        AssertionError: If initialization assertions fail

    Example:
        >>> cog = test_cog_initialization(ConfigCog, mock_bot)
        >>> # Cog is ready for further testing
    """
    cog = cog_class(bot)

    # Standard assertions for all TGraph Bot cogs
    assert cog.bot is bot
    # Access tgraph_bot to ensure it returns the correct instance
    tgraph_bot_instance = cog.tgraph_bot
    assert tgraph_bot_instance is bot

    # Test optional expected attributes
    if expected_attributes:
        for attr_name, expected_value in expected_attributes.items():
            if expected_value is not None:
                assert getattr(cog, attr_name) == expected_value
            else:
                # Just check attribute exists
                assert hasattr(cog, attr_name)

    return cog


def assert_cog_type_validation(cog_class: type[CogT]) -> None:
    """
    Test that cog properly validates TGraphBot instance type.

    This utility consolidates the common pattern of testing that cogs
    raise TypeError when passed a regular discord.py Bot instead of TGraphBot.

    Args:
        cog_class: The Discord cog class to test

    Raises:
        AssertionError: If the expected TypeError is not raised

    Example:
        >>> test_cog_type_validation(ConfigCog)
        >>> # Test passes if TypeError is properly raised
    """
    # Create a regular discord.py bot (not TGraphBot)
    regular_bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

    # Should raise TypeError when trying to create cog with wrong bot type
    with pytest.raises(TypeError, match="Expected TGraphBot instance"):
        _ = cog_class(regular_bot)


def create_mock_bot_with_config(base_config: TGraphBotConfig) -> TGraphBot:
    """
    Create a mock TGraphBot instance for testing.

    This utility consolidates the common pattern of creating a TGraphBot
    with a configuration manager for cog testing.

    Args:
        base_config: TGraphBotConfig instance to use for the bot

    Returns:
        TGraphBot instance ready for testing

    Note:
        This function imports create_config_manager_with_config to avoid
        circular imports while maintaining type safety.
    """
    from tests.utils.test_helpers import create_config_manager_with_config
    from src.tgraph_bot.main import TGraphBot

    config_manager = create_config_manager_with_config(base_config)
    return TGraphBot(config_manager)


def create_cog_test_fixtures(cog_class: type[CogT]) -> tuple[object, object]:
    """
    Create standard pytest fixtures for cog testing.

    This utility creates the standard mock_bot and cog fixture pattern
    used across all cog test classes.

    Args:
        cog_class: The Discord cog class to create fixtures for

    Returns:
        Tuple of (mock_bot_fixture, cog_fixture) functions

    Example:
        >>> mock_bot_fixture, config_cog_fixture = create_cog_test_fixtures(ConfigCog)
        >>> # Use fixtures in test class
    """

    def mock_bot_fixture(base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        return create_mock_bot_with_config(base_config)

    def cog_fixture(mock_bot: TGraphBot) -> CogT:
        """Create a cog instance for testing."""
        return cog_class(mock_bot)

    return mock_bot_fixture, cog_fixture


def assert_cog_has_commands(cog: commands.Cog, expected_commands: list[str]) -> None:
    """
    Assert that a cog has the expected slash commands.

    Args:
        cog: The Discord cog instance to check
        expected_commands: List of command names that should exist

    Raises:
        AssertionError: If expected commands are missing
    """
    cog_commands = [cmd.name for cmd in cog.get_commands()]

    for expected_command in expected_commands:
        assert expected_command in cog_commands, (
            f"Command '{expected_command}' not found in cog"
        )


def assert_cog_has_attributes(
    cog: commands.Cog, expected_attributes: list[str]
) -> None:
    """
    Assert that a cog has the expected attributes.

    Args:
        cog: The Discord cog instance to check
        expected_attributes: List of attribute names that should exist

    Raises:
        AssertionError: If expected attributes are missing
    """
    for attr_name in expected_attributes:
        assert hasattr(cog, attr_name), f"Attribute '{attr_name}' not found in cog"
