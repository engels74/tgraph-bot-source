"""
Tests for the ConfigAccessor utility in TGraph Bot.

This module tests the centralized configuration access utility that handles
TGraphBotConfig objects for graph modules with nested configuration structure.
"""

import pytest

from src.tgraph_bot.graphs.graph_modules import ConfigAccessor
from src.tgraph_bot.utils.core.exceptions import ConfigurationError
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    create_test_config_comprehensive,
)
# Removed unused import: create_test_config_custom


class TestConfigAccessor:
    """Test cases for the ConfigAccessor class."""

    def test_initialization_with_tgraph_config(self) -> None:
        """Test ConfigAccessor initialization with TGraphBotConfig."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)
        assert accessor.config == config

    def test_get_value_with_nested_paths(self) -> None:
        """Test getting values using new nested paths."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test that nested paths work correctly
        assert (
            accessor.get_value("graphs.features.enabled_types.daily_play_count") is True
        )
        assert (
            accessor.get_value("graphs.appearance.colors.tv") == "#2e86ab"
        )  # Colors are normalized to lowercase
        assert accessor.get_value("graphs.appearance.colors.movie") == "#a23b72"

    def test_get_nested_value_with_dot_notation(self) -> None:
        """Test getting values using nested dot notation paths."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test direct nested path access
        assert (
            accessor.get_nested_value("graphs.features.enabled_types.daily_play_count")
            is True
        )
        assert (
            accessor.get_nested_value("graphs.appearance.colors.tv") == "#2e86ab"
        )  # Colors are normalized to lowercase
        assert (
            accessor.get_nested_value("services.tautulli.api_key")
            == "test_api_key_comprehensive"
        )

    def test_get_value_with_defaults(self) -> None:
        """Test getting values with defaults from TGraphBotConfig."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        # Test existing values using nested paths
        assert (
            accessor.get_value("services.tautulli.api_key", "default")
            == "test_api_key_minimal"
        )

        # Test non-existent values with defaults
        assert accessor.get_value("nonexistent.key", "default") == "default"
        assert accessor.get_value("nonexistent.key", 123) == 123

    def test_get_nested_value_with_defaults(self) -> None:
        """Test getting nested values with defaults."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        # Test existing nested path
        assert (
            accessor.get_nested_value("services.tautulli.api_key", "default")
            == "test_api_key_minimal"
        )

        # Test non-existent nested path with default
        assert accessor.get_nested_value("nonexistent.path", "default") == "default"

    def test_missing_key_raises_error(self) -> None:
        """Test that missing keys without defaults raise ConfigurationError."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        with pytest.raises(
            ConfigurationError, match="Configuration path 'nonexistent.path' not found"
        ):
            _ = accessor.get_nested_value("nonexistent.path")

        with pytest.raises(
            ConfigurationError, match="Configuration path 'missing.key' not found"
        ):
            _ = accessor.get_value("missing.key")

    def test_get_bool_value(self) -> None:
        """Test getting boolean values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test nested path access
        assert (
            accessor.get_bool_value("graphs.features.enabled_types.daily_play_count")
            is True
        )
        assert (
            accessor.get_bool_value("data_collection.privacy.censor_usernames") is True
        )
        assert accessor.get_bool_value("graphs.appearance.grid.enabled") is True

        # Test with defaults
        assert accessor.get_bool_value("nonexistent.path", False) is False
        assert accessor.get_bool_value("nonexistent.path", True) is True

    def test_get_int_value(self) -> None:
        """Test getting integer values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test nested path access
        assert accessor.get_int_value("graphs.appearance.dimensions.width", 0) == 14
        assert accessor.get_int_value("graphs.appearance.dimensions.height", 0) == 8
        assert accessor.get_int_value("graphs.appearance.dimensions.dpi", 0) == 100

        # Test with defaults for missing paths
        assert accessor.get_int_value("nonexistent.path", 555) == 555

    def test_graph_type_enabled_comprehensive(self) -> None:
        """Test checking if graph types are enabled using new method."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test direct graph type checking with new method
        assert accessor.is_graph_type_enabled("daily_play_count") is True
        assert accessor.is_graph_type_enabled("play_count_by_dayofweek") is True
        assert accessor.is_graph_type_enabled("play_count_by_hourofday") is True
        assert accessor.is_graph_type_enabled("play_count_by_month") is True
        assert accessor.is_graph_type_enabled("top_10_platforms") is True
        assert accessor.is_graph_type_enabled("top_10_users") is True

    def test_get_graph_dimensions(self) -> None:
        """Test getting graph dimensions from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        dimensions = accessor.get_graph_dimensions()
        assert dimensions == {
            "width": 14,
            "height": 8,
            "dpi": 100,
        }  # Values from comprehensive config

    def test_validate_config(self) -> None:
        """Test configuration validation."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Should not raise any exception for valid config
        accessor.validate_config()

    def test_get_all_enabled_graph_types(self) -> None:
        """Test getting all enabled graph types from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        enabled_types = accessor.get_all_enabled_graph_types()

        # Check that all expected graph types are present and enabled
        expected_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
        ]

        assert set(enabled_types.keys()) == set(expected_types)

        # All should be True in comprehensive config
        for enabled in enabled_types.values():
            assert enabled is True

    def test_is_graph_type_enabled(self) -> None:
        """Test checking if specific graph types are enabled."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test individual graph type checks
        assert accessor.is_graph_type_enabled("daily_play_count") is True
        assert accessor.is_graph_type_enabled("play_count_by_dayofweek") is True
        assert accessor.is_graph_type_enabled("top_10_users") is True

    def test_get_color_value(self) -> None:
        """Test getting color values from configuration."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test color retrieval
        tv_color = accessor.get_color_value("tv")
        movie_color = accessor.get_color_value("movie")
        background_color = accessor.get_color_value("background")

        assert tv_color == "#2e86ab"  # Colors are normalized to lowercase
        assert movie_color == "#a23b72"
        assert background_color == "#f8f9fa"

    def test_get_palette_value(self) -> None:
        """Test getting palette values from configuration."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test palette retrieval (should return empty string for default)
        daily_palette = accessor.get_palette_value("daily_play_count")
        users_palette = accessor.get_palette_value("top_10_users")

        # These should be empty strings for default palettes
        assert isinstance(daily_palette, str)
        assert isinstance(users_palette, str)

    def test_is_annotation_enabled(self) -> None:
        """Test checking if annotations are enabled for graph types."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test annotation checks
        assert accessor.is_annotation_enabled("daily_play_count") is True
        assert accessor.is_annotation_enabled("top_10_users") is True

    def test_get_per_graph_media_type_separation(self) -> None:
        """Test getting per-graph media type separation settings."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test getting per-graph media type separation (these will use the new method once implemented)
        daily_separation = accessor.get_per_graph_media_type_separation(
            "daily_play_count"
        )
        users_separation = accessor.get_per_graph_media_type_separation("top_10_users")

        # Should return boolean values
        assert isinstance(daily_separation, bool)
        assert isinstance(users_separation, bool)

    def test_get_per_graph_stacked_bar_charts(self) -> None:
        """Test getting per-graph stacked bar charts settings."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test getting per-graph stacked bar charts (these will use the new method once implemented)
        daily_stacked = accessor.get_per_graph_stacked_bar_charts("daily_play_count")
        users_stacked = accessor.get_per_graph_stacked_bar_charts("top_10_users")

        # Should return boolean values
        assert isinstance(daily_stacked, bool)
        assert isinstance(users_stacked, bool)

    def test_get_per_graph_settings_with_fallback(self) -> None:
        """Test per-graph settings with fallback to global settings."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        # Test that we get fallback values when per-graph settings are not configured
        separation = accessor.get_per_graph_media_type_separation("daily_play_count")
        stacked = accessor.get_per_graph_stacked_bar_charts("daily_play_count")

        # Should fall back to global or default values
        assert isinstance(separation, bool)
        assert isinstance(stacked, bool)

    def test_get_per_graph_settings_invalid_graph_type(self) -> None:
        """Test per-graph settings with invalid graph type."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        # Test with invalid graph types - should return defaults
        separation = accessor.get_per_graph_media_type_separation("invalid_graph_type")
        stacked = accessor.get_per_graph_stacked_bar_charts("invalid_graph_type")

        # Should return default values
        assert isinstance(separation, bool)
        assert isinstance(stacked, bool)
