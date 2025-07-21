"""
Consolidated tests for Discord cog base functionality.

This module consolidates common cog testing patterns that were previously
duplicated across multiple cog test files, following DRY principles and
Python 3.13 best practices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.tgraph_bot.bot.commands.config import ConfigCog
from src.tgraph_bot.bot.commands.update_graphs import UpdateGraphsCog
from tests.utils.cog_helpers import assert_cog_initialization, assert_cog_type_validation

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig
    from src.tgraph_bot.main import TGraphBot


class TestCogBaseInitialization:
    """Consolidated tests for cog initialization patterns."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        from tests.utils.cog_helpers import create_mock_bot_with_config
        
        return create_mock_bot_with_config(base_config)

    @pytest.mark.parametrize(
        ("cog_class", "expected_attributes"),
        [
            (ConfigCog, {"config_helper": None}),  # Just check existence
            (UpdateGraphsCog, {"cooldown_config": None, "config_helper": None}),
        ],
    )
    def test_cog_initialization(
        self,
        mock_bot: TGraphBot,
        cog_class: type,
        expected_attributes: dict[str, object],
    ) -> None:
        """Test standard cog initialization using consolidated utility."""
        # Use the consolidated test utility
        _ = assert_cog_initialization(cog_class, mock_bot, expected_attributes=expected_attributes)
        
        # Additional verification for UpdateGraphsCog since it has more attributes
        if cog_class is UpdateGraphsCog:
            cog_instance = cog_class(mock_bot)
            assert cog_instance.cooldown_config is not None
            assert hasattr(cog_instance, "config_helper")

    @pytest.mark.parametrize(
        "cog_class",
        [
            ConfigCog,
            UpdateGraphsCog,
        ],
    )
    def test_cog_type_validation(self, cog_class: type) -> None:
        """Test that cogs properly validate TGraphBot instance type."""
        assert_cog_type_validation(cog_class)


class TestCogCommonFunctionality:
    """Tests for common functionality across all cogs."""

    @pytest.fixture
    def mock_bot(self, base_config: TGraphBotConfig) -> TGraphBot:
        """Create a mock TGraphBot instance."""
        from tests.utils.cog_helpers import create_mock_bot_with_config
        
        return create_mock_bot_with_config(base_config)

    @pytest.mark.parametrize(
        "cog_class",
        [
            ConfigCog,
            UpdateGraphsCog,
        ],
    )
    def test_tgraph_bot_property_access(self, mock_bot: TGraphBot, cog_class: type) -> None:
        """Test that all cogs properly expose tgraph_bot property."""
        cog_instance = cog_class(mock_bot)  # pyright: ignore[reportAny] # Dynamic cog class instantiation
        
        # Should be able to access tgraph_bot property
        tgraph_bot_instance = cog_instance.tgraph_bot  # pyright: ignore[reportAny] # Dynamic cog property access
        assert tgraph_bot_instance is mock_bot
        
        # Should have access to config through tgraph_bot
        config = tgraph_bot_instance.config_manager.get_current_config()  # pyright: ignore[reportAny] # Dynamic bot attribute access
        assert config is not None

    @pytest.mark.parametrize(
        "cog_class",
        [
            ConfigCog,
            UpdateGraphsCog,
        ],
    )
    def test_cog_has_bot_attribute(self, mock_bot: TGraphBot, cog_class: type) -> None:
        """Test that all cogs properly store bot reference."""
        cog_instance = cog_class(mock_bot)  # pyright: ignore[reportAny] # Dynamic cog class instantiation
        
        assert hasattr(cog_instance, "bot")  # pyright: ignore[reportAny] # Dynamic cog instance check
        assert cog_instance.bot is mock_bot  # pyright: ignore[reportAny] # Dynamic cog attribute access