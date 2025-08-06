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
        assert minimal_config.automation.scheduling.update_days == 7  # Default value
        assert minimal_config.automation.data_retention.keep_days == 7  # Default value
        assert minimal_config.data_collection.time_ranges.days == 30  # Default value
        assert (
            minimal_config.graphs.features.enabled_types.daily_play_count is True
        )  # Default value
        assert minimal_config.graphs.appearance.colors.tv == "#1f77b4"  # Default value
        assert (
            minimal_config.graphs.appearance.colors.movie == "#ff7f0e"
        )  # Default value

    def test_configuration_access_patterns(self) -> None:
        """Test different patterns of accessing configuration values."""
        config = create_test_config_comprehensive()

        # Test direct access
        assert config.graphs.appearance.colors.tv == "#2e86ab"
        assert config.graphs.appearance.colors.movie == "#a23b72"
        assert config.graphs.features.enabled_types.daily_play_count is True

        # Test through ConfigAccessor
        accessor = ConfigAccessor(config)
        assert accessor.get_value("graphs.appearance.colors.tv") == "#2e86ab"
        assert accessor.get_value("graphs.appearance.colors.movie") == "#a23b72"
        assert (
            accessor.get_value("graphs.features.enabled_types.daily_play_count") is True
        )

        # Test through BaseGraph
        graph = ConfigTestGraph(config=config)
        assert graph.get_config_value("graphs.appearance.colors.tv") == "#2e86ab"
        assert graph.get_config_value("graphs.appearance.colors.movie") == "#a23b72"
        assert (
            graph.get_config_value("graphs.features.enabled_types.daily_play_count")
            is True
        )

    def test_configuration_inheritance_patterns(self) -> None:
        """Test configuration inheritance and override patterns."""
        # Test that graphs inherit configuration properly
        config = create_test_config_comprehensive()
        graph = ConfigTestGraph(config=config)

        # Test inherited values
        assert graph.get_tv_color() == config.graphs.appearance.colors.tv
        assert graph.get_movie_color() == config.graphs.appearance.colors.movie
        assert graph.background_color == config.graphs.appearance.colors.background

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
                # Map parameter names to nested config paths
                config_path_map = {
                    "enable_daily_play_count": "graphs.features.enabled_types.daily_play_count",
                    "enable_play_count_by_dayofweek": "graphs.features.enabled_types.play_count_by_dayofweek",
                    "enable_play_count_by_hourofday": "graphs.features.enabled_types.play_count_by_hourofday",
                    "enable_play_count_by_month": "graphs.features.enabled_types.play_count_by_month",
                    "enable_top_10_platforms": "graphs.features.enabled_types.top_10_platforms",
                    "enable_top_10_users": "graphs.features.enabled_types.top_10_users",
                }
                config_path = config_path_map[key]
                assert graph.get_config_value(config_path) is value

    def test_privacy_configuration_validation(self) -> None:
        """Test privacy-focused configuration validation."""
        privacy_config = create_test_config_privacy_focused()

        # Test privacy settings
        assert privacy_config.data_collection.privacy.censor_usernames is True
        assert privacy_config.graphs.features.enabled_types.top_10_users is False
        assert (
            privacy_config.graphs.appearance.annotations.enabled_on.top_10_users
            is False
        )

        # Test that privacy config works with graphs
        graph = ConfigTestGraph(config=privacy_config)
        assert (
            graph.get_config_value("data_collection.privacy.censor_usernames") is True
        )

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
        assert config.graphs.appearance.annotations.enabled_on.daily_play_count is True
        assert (
            config.graphs.appearance.annotations.enabled_on.play_count_by_dayofweek
            is True
        )
        assert (
            config.graphs.appearance.annotations.enabled_on.play_count_by_hourofday
            is True
        )
        assert config.graphs.appearance.annotations.enabled_on.top_10_platforms is True
        assert config.graphs.appearance.annotations.enabled_on.top_10_users is True
        assert (
            config.graphs.appearance.annotations.enabled_on.play_count_by_month is True
        )

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
        assert config.graphs.features.stacked_bar_charts is True

    def test_graph_customization_configuration_validation(self) -> None:
        """Test validation of graph customization configuration."""
        config = create_test_config_comprehensive()

        # Test grid and background settings
        assert config.graphs.appearance.grid.enabled is True
        assert (
            config.graphs.appearance.colors.background == "#f8f9fa"
        )  # Colors are normalized to lowercase

        # Test user privacy settings
        assert config.data_collection.privacy.censor_usernames is True

        # Test that these settings are accessible through graphs
        graph = ConfigTestGraph(config=config)
        background_color = graph.background_color
        assert background_color == "#f8f9fa"  # Colors are normalized to lowercase

    def test_color_configuration_patterns(self) -> None:
        """Test color configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that color values are properly formatted hex strings
        assert config.graphs.appearance.colors.tv.startswith("#")
        assert len(config.graphs.appearance.colors.tv) in [4, 7]  # #RGB or #RRGGBB
        assert config.graphs.appearance.colors.movie.startswith("#")
        assert len(config.graphs.appearance.colors.movie) in [4, 7]

        # Test color access through graph
        graph = ConfigTestGraph(config=config)
        tv_color = graph.get_tv_color()
        movie_color = graph.get_movie_color()

        assert tv_color == config.graphs.appearance.colors.tv
        assert movie_color == config.graphs.appearance.colors.movie

    def test_boolean_configuration_patterns(self) -> None:
        """Test boolean configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that boolean values are properly typed
        assert isinstance(config.graphs.features.enabled_types.daily_play_count, bool)
        assert isinstance(config.graphs.appearance.grid.enabled, bool)
        assert isinstance(config.data_collection.privacy.censor_usernames, bool)

        # Test boolean access through graph
        graph = ConfigTestGraph(config=config)
        outline_enabled = graph.is_annotation_outline_enabled()
        assert isinstance(outline_enabled, bool)

    def test_integer_configuration_patterns(self) -> None:
        """Test integer configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that integer values are properly typed and within valid ranges
        assert isinstance(config.automation.scheduling.update_days, int)
        assert config.automation.scheduling.update_days > 0

        assert isinstance(config.data_collection.time_ranges.days, int)
        assert config.data_collection.time_ranges.days > 0

        assert isinstance(config.services.discord.channel_id, int)
        assert config.services.discord.channel_id > 0

    def test_string_configuration_patterns(self) -> None:
        """Test string configuration patterns."""
        config = create_test_config_comprehensive()

        # Test that string values are properly typed and non-empty
        assert isinstance(config.services.tautulli.api_key, str)
        assert len(config.services.tautulli.api_key) > 0

        assert isinstance(config.services.discord.token, str)
        assert len(config.services.discord.token) > 0

        assert isinstance(config.services.tautulli.url, str)
        assert config.services.tautulli.url.startswith(("http://", "https://"))
