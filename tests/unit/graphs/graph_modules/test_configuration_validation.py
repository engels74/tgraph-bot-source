"""
Test module for comprehensive configuration validation.

This module provides comprehensive testing of configuration validation
across all graph modules, ensuring that configuration changes don't
break graph functionality and that valid configurations work correctly.

The tests validate:
- Configuration schema compliance for valid configs
- Configuration access patterns
- Configuration inheritance patterns
- Type safety in configuration access
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, override

import pytest

from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.graphs.graph_modules import (
    BaseGraph,
    ConfigAccessor,
    GraphFactory,
)
from src.tgraph_bot.utils.core.exceptions import ConfigurationError
from tests.utils.graph_helpers import (
    create_test_config_comprehensive,
    create_test_config_minimal,
    create_test_config_privacy_focused,
    create_test_config_selective,
    matplotlib_cleanup,
)

if TYPE_CHECKING:
    pass


class ConfigTestGraph(BaseGraph):
    """Test graph for configuration validation testing."""

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """Generate a simple test graph."""
        try:
            _ = self.setup_figure()

            if self.axes is not None:
                _ = self.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]
                _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                output_path = tmp.name

            return self.save_figure(output_path=output_path)
        finally:
            self.cleanup()

    @override
    def get_title(self) -> str:
        """Get the title for this test graph."""
        return "Configuration Test Graph"


class TestConfigurationValidation:
    """Test cases for comprehensive configuration validation."""

    def test_valid_configuration_schemas(self) -> None:
        """Test that all valid configuration schemas work correctly."""
        valid_configs = [
            create_test_config_minimal(),
            create_test_config_comprehensive(),
            create_test_config_privacy_focused(),
            create_test_config_selective(),
        ]

        for config in valid_configs:
            # Test that config is valid
            assert isinstance(config, TGraphBotConfig)

            # Test that graph can be created with config
            graph = ConfigTestGraph(config=config)
            assert graph.config is config

            # Test that config accessor works
            accessor = ConfigAccessor(config)
            assert accessor.config is config

            # Test that factory can be created with config
            factory = GraphFactory(config)
            assert factory.config is config

    def test_default_value_behavior(self) -> None:
        """Test that default values are applied correctly."""
        minimal_config = create_test_config_minimal()

        # Check that defaults are applied
        assert minimal_config.UPDATE_DAYS == 7  # Default value
        assert minimal_config.KEEP_DAYS == 7  # Default value
        assert minimal_config.TIME_RANGE_DAYS == 30  # Default value
        assert minimal_config.ENABLE_DAILY_PLAY_COUNT is True  # Default value
        assert minimal_config.TV_COLOR == "#1f77b4"  # Default value
        assert minimal_config.MOVIE_COLOR == "#ff7f0e"  # Default value

    def test_configuration_access_patterns(self) -> None:
        """Test different patterns of accessing configuration values."""
        config = create_test_config_comprehensive()

        # Test direct access
        assert config.TV_COLOR == "#2e86ab"
        assert config.MOVIE_COLOR == "#a23b72"
        assert config.ENABLE_DAILY_PLAY_COUNT is True

        # Test through ConfigAccessor
        accessor = ConfigAccessor(config)
        assert accessor.get_value("TV_COLOR") == "#2e86ab"
        assert accessor.get_value("MOVIE_COLOR") == "#a23b72"
        assert accessor.get_value("ENABLE_DAILY_PLAY_COUNT") is True

        # Test through BaseGraph
        graph = ConfigTestGraph(config=config)
        assert graph.get_config_value("TV_COLOR") == "#2e86ab"
        assert graph.get_config_value("MOVIE_COLOR") == "#a23b72"
        assert graph.get_config_value("ENABLE_DAILY_PLAY_COUNT") is True

    def test_configuration_inheritance_patterns(self) -> None:
        """Test configuration inheritance and override patterns."""
        # Test that graphs inherit configuration properly
        config = create_test_config_comprehensive()
        graph = ConfigTestGraph(config=config)

        # Test inherited values
        assert graph.get_tv_color() == config.TV_COLOR
        assert graph.get_movie_color() == config.MOVIE_COLOR
        assert graph.background_color == config.GRAPH_BACKGROUND_COLOR

        # Test that None config uses defaults
        graph_no_config = ConfigTestGraph()
        assert graph_no_config.get_tv_color() == "#1f77b4"  # Default
        assert graph_no_config.get_movie_color() == "#ff7f0e"  # Default

    def test_selective_configuration_combinations(self) -> None:
        """Test various combinations of selective configuration options."""
        # Test different graph type combinations
        combinations = [
            {"enable_daily_play_count": True, "enable_top_10_users": False},
            {"enable_play_count_by_dayofweek": True, "enable_top_10_platforms": False},
            {
                "enable_play_count_by_hourofday": True,
                "enable_play_count_by_month": False,
            },
        ]

        for combination in combinations:
            config = create_test_config_selective(**combination)
            graph = ConfigTestGraph(config=config)

            # Verify configuration is properly applied
            for key, value in combination.items():
                config_key = key.upper()
                assert graph.get_config_value(config_key) is value

    def test_privacy_configuration_validation(self) -> None:
        """Test privacy-focused configuration validation."""
        privacy_config = create_test_config_privacy_focused()

        # Test privacy settings
        assert privacy_config.CENSOR_USERNAMES is True
        assert privacy_config.ENABLE_TOP_10_USERS is False
        assert privacy_config.ANNOTATE_TOP_10_USERS is False

        # Test that privacy config works with graphs
        graph = ConfigTestGraph(config=privacy_config)
        assert graph.get_config_value("CENSOR_USERNAMES") is True

    def test_configuration_edge_cases(self) -> None:
        """Test edge cases in configuration handling."""
        # Test None configuration
        graph_none = ConfigTestGraph(config=None)
        assert graph_none.config is None

        # Should still be able to get default values
        assert graph_none.get_tv_color() == "#1f77b4"
        assert graph_none.get_movie_color() == "#ff7f0e"

    def test_config_accessor_error_handling(self) -> None:
        """Test error handling in configuration access."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        # Test accessing non-existent configuration key
        with pytest.raises(ConfigurationError):
            _ = accessor.get_value("NON_EXISTENT_KEY")

        # Test getting default for non-existent key
        default_value = accessor.get_value("NON_EXISTENT_KEY", default="default")
        assert default_value == "default"

    def test_graph_factory_configuration_validation(self) -> None:
        """Test configuration validation in GraphFactory."""
        # Test with valid configurations
        valid_configs = [
            create_test_config_minimal(),
            create_test_config_comprehensive(),
            create_test_config_privacy_focused(),
        ]

        for config in valid_configs:
            factory = GraphFactory(config)
            assert factory.config is config

            # Test that enabled graph types are correctly determined
            enabled_types = factory.get_enabled_graph_types()
            assert isinstance(enabled_types, list)
            assert all(isinstance(graph_type, str) for graph_type in enabled_types)

    def test_configuration_type_safety(self) -> None:
        """Test type safety in configuration access."""
        config = create_test_config_comprehensive()
        graph = ConfigTestGraph(config=config)

        # Test that type hints are preserved
        tv_color: str = graph.get_tv_color()
        movie_color: str = graph.get_movie_color()
        background_color: str = graph.background_color

        assert isinstance(tv_color, str)
        assert isinstance(movie_color, str)
        assert isinstance(background_color, str)

        # Test boolean configuration values
        outline_enabled: bool = graph.is_annotation_outline_enabled()
        assert isinstance(outline_enabled, bool)

    def test_configuration_validation_with_real_graph_generation(self) -> None:
        """Test configuration validation during actual graph generation."""
        configs_to_test = [
            create_test_config_minimal(),
            create_test_config_comprehensive(),
            create_test_config_privacy_focused(),
        ]

        test_data: dict[str, object] = {"test_key": "test_value"}

        for config in configs_to_test:
            with matplotlib_cleanup():
                graph = ConfigTestGraph(config=config)

                # Test that graph generation works with this configuration
                output_path = graph.generate(test_data)

                # Verify file was created
                assert Path(output_path).exists()
                assert output_path.endswith(".png")

                # Clean up
                Path(output_path).unlink(missing_ok=True)

    def test_annotation_configuration_validation(self) -> None:
        """Test validation of annotation-related configuration."""
        config = create_test_config_comprehensive()
        graph = ConfigTestGraph(config=config)

        # Test annotation color settings
        annotation_color = graph.get_annotation_color()
        annotation_outline_color = graph.get_annotation_outline_color()

        assert annotation_color == "#c73e1d"
        assert annotation_outline_color == "#ffffff"

        # Test annotation enable/disable settings
        assert graph.is_annotation_outline_enabled() is True

        # Test individual graph annotation settings
        assert config.ANNOTATE_DAILY_PLAY_COUNT is True
        assert config.ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK is True
        assert config.ANNOTATE_PLAY_COUNT_BY_HOUROFDAY is True
        assert config.ANNOTATE_TOP_10_PLATFORMS is True
        assert config.ANNOTATE_TOP_10_USERS is True
        assert config.ANNOTATE_PLAY_COUNT_BY_MONTH is True

    def test_media_type_configuration_validation(self) -> None:
        """Test validation of media type-related configuration."""
        config = create_test_config_comprehensive()
        graph = ConfigTestGraph(config=config)

        # Test media type processor configuration
        processor = graph.media_type_processor
        assert processor is not None
        assert processor.get_color_for_type("tv") == "#2e86ab"
        assert processor.get_color_for_type("movie") == "#a23b72"

        # Test stacked bar chart setting
        assert config.ENABLE_STACKED_BAR_CHARTS is True

    def test_graph_customization_configuration_validation(self) -> None:
        """Test validation of graph customization configuration."""
        config = create_test_config_comprehensive()

        # Test grid and background settings
        assert config.ENABLE_GRAPH_GRID is True
        assert (
            config.GRAPH_BACKGROUND_COLOR == "#f8f9fa"
        )  # Colors are normalized to lowercase

        # Test user privacy settings
        assert config.CENSOR_USERNAMES is True

        # Test that these settings are accessible through graphs
        graph = ConfigTestGraph(config=config)
        background_color = graph.background_color
        assert background_color == "#f8f9fa"  # Colors are normalized to lowercase

    def test_color_configuration_patterns(self) -> None:
        """Test color configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that color values are properly formatted hex strings
        assert config.TV_COLOR.startswith("#")
        assert len(config.TV_COLOR) in [4, 7]  # #RGB or #RRGGBB
        assert config.MOVIE_COLOR.startswith("#")
        assert len(config.MOVIE_COLOR) in [4, 7]

        # Test color access through graph
        graph = ConfigTestGraph(config=config)
        tv_color = graph.get_tv_color()
        movie_color = graph.get_movie_color()

        assert tv_color == config.TV_COLOR
        assert movie_color == config.MOVIE_COLOR

    def test_boolean_configuration_patterns(self) -> None:
        """Test boolean configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that boolean values are properly typed
        assert isinstance(config.ENABLE_DAILY_PLAY_COUNT, bool)
        assert isinstance(config.ENABLE_GRAPH_GRID, bool)
        assert isinstance(config.CENSOR_USERNAMES, bool)

        # Test boolean access through graph
        graph = ConfigTestGraph(config=config)
        outline_enabled = graph.is_annotation_outline_enabled()
        assert isinstance(outline_enabled, bool)

    def test_integer_configuration_patterns(self) -> None:
        """Test integer configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that integer values are properly typed and within valid ranges
        assert isinstance(config.UPDATE_DAYS, int)
        assert config.UPDATE_DAYS > 0

        assert isinstance(config.TIME_RANGE_DAYS, int)
        assert config.TIME_RANGE_DAYS > 0

        assert isinstance(config.CHANNEL_ID, int)
        assert config.CHANNEL_ID > 0

    def test_string_configuration_patterns(self) -> None:
        """Test string configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that string values are properly typed and non-empty
        assert isinstance(config.TAUTULLI_API_KEY, str)
        assert len(config.TAUTULLI_API_KEY) > 0

        assert isinstance(config.DISCORD_TOKEN, str)
        assert len(config.DISCORD_TOKEN) > 0

        assert isinstance(config.TAUTULLI_URL, str)
        assert config.TAUTULLI_URL.startswith(("http://", "https://"))
