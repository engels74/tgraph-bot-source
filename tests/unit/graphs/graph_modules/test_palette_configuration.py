"""
Test cases for color palette configuration functionality.

This module tests the priority-based palette system to ensure that
user-configured palettes take precedence over automatic media type palettes.
"""

import pytest
from typing import cast
from unittest.mock import patch

from tgraph_bot.config.schema import TGraphBotConfig
from tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_hourofday_graph import (
    PlayCountByHourOfDayGraph,
)
from tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
    Top10UsersGraph,
)


class TestPaletteConfiguration:
    """Test color palette configuration functionality."""

    def test_viridis_palette_configuration(self) -> None:
        """Test that viridis palette is correctly applied."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            ENABLE_MEDIA_TYPE_SEPARATION=True,
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            # This should detect user palette and skip media type palette
            graph.apply_seaborn_style()
            # User palette should be applied via apply_configured_palette
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")

            # Verify that viridis was set as the palette
            mock_set_palette.assert_called_with("viridis")

    def test_plasma_palette_configuration(self) -> None:
        """Test that plasma palette is correctly applied."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            TOP_10_USERS_PALETTE="plasma",
            ENABLE_MEDIA_TYPE_SEPARATION=True,
        )

        graph = Top10UsersGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("TOP_10_USERS_PALETTE")
            mock_set_palette.assert_called_with("plasma")

    def test_inferno_palette_configuration(self) -> None:
        """Test that inferno palette is correctly applied."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="inferno",
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_called_with("inferno")

    def test_magma_palette_configuration(self) -> None:
        """Test that magma palette is correctly applied."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            TOP_10_USERS_PALETTE="magma",
        )

        graph = Top10UsersGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("TOP_10_USERS_PALETTE")
            mock_set_palette.assert_called_with("magma")

    def test_user_palette_takes_precedence_over_media_type(self) -> None:
        """Test that user palette takes precedence by being applied after media type palette."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
            ENABLE_MEDIA_TYPE_SEPARATION=True,
            TV_COLOR="#ff0000",  # Red
            MOVIE_COLOR="#00ff00",  # Green
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            # This should set both palettes with user palette last (taking precedence)
            graph.apply_seaborn_style()

            # Verify that both palettes were set, with user palette last
            assert mock_set_palette.call_count == 2
            # First call should be media type palette (list of colors)
            first_call = mock_set_palette.call_args_list[0]
            assert isinstance(first_call[0][0], list)  # Media type palette is a list of colors
            # Second call should be user palette (string)
            second_call = mock_set_palette.call_args_list[1]
            assert second_call[0][0] == "viridis"  # User palette is the string "viridis"

    def test_media_type_palette_applied_when_no_user_palette(self) -> None:
        """Test that media type palette is applied when no user palette is configured."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="",  # Empty = no user palette
            ENABLE_MEDIA_TYPE_SEPARATION=True,
            TV_COLOR="#ff0000",  # Red
            MOVIE_COLOR="#00ff00",  # Green
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_seaborn_style()

            # Should be called twice: default palette + media type palette
            assert mock_set_palette.call_count == 2
            # Get the actual colors that were passed in the second call (media type palette)
            media_type_palette = cast(list[str], mock_set_palette.call_args_list[1][0][0])
            # Should contain the configured TV and movie colors
            assert "#ff0000" in media_type_palette and "#00ff00" in media_type_palette

    def test_empty_palette_configuration_does_not_apply_palette(self) -> None:
        """Test that empty palette configuration does not apply any palette."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="",  # Empty string
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_not_called()

    def test_whitespace_only_palette_configuration_does_not_apply_palette(self) -> None:
        """Test that whitespace-only palette configuration does not apply any palette."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="   ",  # Whitespace only
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_not_called()

    def test_has_user_configured_palette_detection(self) -> None:
        """Test the _has_user_configured_palette method correctly detects user palettes."""
        # Test with viridis configured
        config_with_palette = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="viridis",
        )

        graph_with_palette = PlayCountByHourOfDayGraph(config=config_with_palette)
        assert graph_with_palette._has_user_configured_palette() is True  # pyright: ignore[reportPrivateUsage]

        # Test with no palette configured
        config_no_palette = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="",
            TOP_10_USERS_PALETTE="",
        )

        graph_no_palette = PlayCountByHourOfDayGraph(config=config_no_palette)
        assert graph_no_palette._has_user_configured_palette() is False  # pyright: ignore[reportPrivateUsage]

    def test_multiple_palette_configurations_detected(self) -> None:
        """Test that multiple palette configurations are correctly detected."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE="",  # Empty
            TOP_10_USERS_PALETTE="plasma",  # Configured
        )

        graph = PlayCountByHourOfDayGraph(config=config)
        # Should return True because TOP_10_USERS_PALETTE is configured
        assert graph._has_user_configured_palette() is True  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.parametrize("palette_name", ["viridis", "plasma", "inferno", "magma"])
    def test_all_supported_palettes(self, palette_name: str) -> None:
        """Test that all supported palette names work correctly."""
        config = TGraphBotConfig(
            DISCORD_TOKEN="test_token",
            TAUTULLI_API_KEY="test_key",
            TAUTULLI_URL="http://test.local",
            CHANNEL_ID=123456789,
            PLAY_COUNT_BY_HOUROFDAY_PALETTE=palette_name,
        )

        graph = PlayCountByHourOfDayGraph(config=config)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_called_with(palette_name)

    def test_dict_config_palette_application(self) -> None:
        """Test palette application with dict-based configuration."""
        config_dict: dict[str, object] = {
            "PLAY_COUNT_BY_HOUROFDAY_PALETTE": "viridis",
            "ENABLE_MEDIA_TYPE_SEPARATION": True,
        }

        graph = PlayCountByHourOfDayGraph(config=config_dict)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_called_with("viridis")

    def test_none_config_does_not_apply_palette(self) -> None:
        """Test that None config does not apply any palette."""
        graph = PlayCountByHourOfDayGraph(config=None)

        with patch("seaborn.set_palette") as mock_set_palette:
            graph.apply_configured_palette("PLAY_COUNT_BY_HOUROFDAY_PALETTE")
            mock_set_palette.assert_not_called()
