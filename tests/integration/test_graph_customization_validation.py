"""
Comprehensive validation tests for graph customization options and feature toggles.

This module systematically tests all customization options including colors,
annotations, grid settings, feature toggles, and username censoring to ensure
they work correctly across all graph types.

"""

from __future__ import annotations

import pytest
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing_extensions import override

from src.tgraph_bot.config.schema import TGraphBotConfig
from src.tgraph_bot.graphs.graph_modules.core.graph_type_registry import (
    GraphTypeRegistry,
)
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    create_test_config_selective,
    create_graph_factory_with_config,
    matplotlib_cleanup,
)
from tests.utils.test_helpers import create_test_config_custom

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig


class TestGraphCustomizationValidation:
    """Test cases for validating all graph customization options."""

    def test_color_customization_validation(
        self, comprehensive_config: TGraphBotConfig
    ) -> None:
        """Test that all color customization options work correctly."""
        with matplotlib_cleanup():
            # Use comprehensive config which has custom colors set
            config = comprehensive_config

            factory = create_graph_factory_with_config(config)

            # Test each graph type with custom colors using GraphTypeRegistry
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)

                # Verify colors are applied to the graph's config
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                # Check the actual colors from comprehensive_config fixture
                assert config_obj.graphs.appearance.colors.tv == "#ff4444"
                assert config_obj.graphs.appearance.colors.movie == "#44ff44"
                assert config_obj.graphs.appearance.colors.background == "#f8f8f8"
                assert config_obj.graphs.appearance.annotations.basic.color == "#4444ff"
                assert (
                    config_obj.graphs.appearance.annotations.basic.outline_color
                    == "#222222"
                )

                # Verify graph can be instantiated with custom colors
                assert graph.background_color == "#f8f8f8"

                # Cleanup
                graph.cleanup()

    def test_feature_toggle_validation(self) -> None:
        """Test that all feature toggles work correctly."""
        with matplotlib_cleanup():
            # Test all graphs disabled
            config_all_disabled = create_test_config_selective(
                enable_daily_play_count=False,
                enable_play_count_by_dayofweek=False,
                enable_play_count_by_hourofday=False,
                enable_play_count_by_month=False,
                enable_top_10_platforms=False,
                enable_top_10_users=False,
            )

            factory = create_graph_factory_with_config(config_all_disabled)
            graphs = factory.create_enabled_graphs()
            assert len(graphs) == 0

            # Test selective enabling
            config_selective = create_test_config_selective(
                enable_daily_play_count=True,
                enable_play_count_by_dayofweek=False,
                enable_play_count_by_hourofday=True,
                enable_play_count_by_month=False,
                enable_top_10_platforms=True,
                enable_top_10_users=False,
            )

            factory = create_graph_factory_with_config(config_selective)
            graphs = factory.create_enabled_graphs()
            try:
                assert len(graphs) == 3

                enabled_types = factory.get_enabled_graph_types()
                expected_enabled = {
                    "daily_play_count",
                    "play_count_by_hourofday",
                    "top_10_platforms",
                }
                assert set(enabled_types) == expected_enabled
            finally:
                # Cleanup all graphs
                for graph in graphs:
                    graph.cleanup()

    def test_annotation_settings_validation(self) -> None:
        """Test that annotation settings work correctly for all graph types."""
        with matplotlib_cleanup():
            # Test with annotations enabled
            config_annotations_enabled = create_test_config_custom(
                services_overrides={
                    "tautulli": {
                        "api_key": "test_api_key_here",
                        "url": "http://localhost:8181/api/v2",
                    },
                    "discord": {
                        "token": "test_discord_token_1234567890",
                        "channel_id": 123456789,
                    },
                },
                graphs_overrides={
                    "appearance": {
                        "annotations": {
                            "enabled_on": {
                                "daily_play_count": True,
                                "play_count_by_dayofweek": True,
                                "play_count_by_hourofday": True,
                                "top_10_platforms": True,
                                "top_10_users": True,
                                "play_count_by_month": True,
                            },
                            "basic": {"enable_outline": True},
                        }
                    }
                },
            )

            factory = create_graph_factory_with_config(config_annotations_enabled)

            # Test each graph type with annotations using GraphTypeRegistry
            registry = GraphTypeRegistry()
            graph_types = registry.get_all_type_names()

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)
                try:
                    # Verify annotation settings are applied
                    assert graph.config is not None
                    # Type guard to ensure we're working with TGraphBotConfig
                    assert not isinstance(graph.config, dict), (
                        "Config should be TGraphBotConfig, not dict"
                    )
                    annotation_config_obj: TGraphBotConfig = graph.config

                    assert (
                        annotation_config_obj.graphs.appearance.annotations.basic.enable_outline
                        is True
                    )
                finally:
                    graph.cleanup()

    def test_grid_settings_validation(self) -> None:
        """Test that grid settings work correctly."""
        with matplotlib_cleanup():
            # Test with grid enabled
            config_grid_enabled = create_test_config_custom(
                services_overrides={
                    "tautulli": {
                        "api_key": "test_api_key_here",
                        "url": "http://localhost:8181/api/v2",
                    },
                    "discord": {
                        "token": "test_discord_token_1234567890",
                        "channel_id": 123456789,
                    },
                },
                graphs_overrides={"appearance": {"grid": {"enabled": True}}},
            )

            factory = create_graph_factory_with_config(config_grid_enabled)
            graph = factory.create_graph_by_type("daily_play_count")
            try:
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config
                assert config_obj.graphs.appearance.grid.enabled is True
            finally:
                graph.cleanup()

            # Test with grid disabled
            config_grid_disabled = create_test_config_custom(
                services_overrides={
                    "tautulli": {
                        "api_key": "test_api_key_here",
                        "url": "http://localhost:8181/api/v2",
                    },
                    "discord": {
                        "token": "test_discord_token_1234567890",
                        "channel_id": 123456789,
                    },
                },
                graphs_overrides={"appearance": {"grid": {"enabled": False}}},
            )

            factory = create_graph_factory_with_config(config_grid_disabled)
            graph = factory.create_graph_by_type("daily_play_count")
            try:
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj_disabled: TGraphBotConfig = graph.config
                assert config_obj_disabled.graphs.appearance.grid.enabled is False
            finally:
                graph.cleanup()

    def test_username_censoring_validation(self) -> None:
        """Test that username censoring works correctly."""
        with matplotlib_cleanup():
            # Test with censoring enabled
            config_censor_enabled = create_test_config_custom(
                services_overrides={
                    "tautulli": {
                        "api_key": "test_api_key_here",
                        "url": "http://localhost:8181/api/v2",
                    },
                    "discord": {
                        "token": "test_discord_token_1234567890",
                        "channel_id": 123456789,
                    },
                },
                data_collection_overrides={"privacy": {"censor_usernames": True}},
            )

            factory = create_graph_factory_with_config(config_censor_enabled)
            graph = factory.create_graph_by_type("top_10_users")
            try:
                assert graph.should_censor_usernames() is True
            finally:
                graph.cleanup()

            # Test with censoring disabled
            config_censor_disabled = create_test_config_custom(
                services_overrides={
                    "tautulli": {
                        "api_key": "test_api_key_here",
                        "url": "http://localhost:8181/api/v2",
                    },
                    "discord": {
                        "token": "test_discord_token_1234567890",
                        "channel_id": 123456789,
                    },
                },
                data_collection_overrides={"privacy": {"censor_usernames": False}},
            )

            factory = create_graph_factory_with_config(config_censor_disabled)
            graph = factory.create_graph_by_type("top_10_users")
            try:
                assert graph.should_censor_usernames() is False
            finally:
                graph.cleanup()

    def test_comprehensive_customization_integration(
        self, comprehensive_config: TGraphBotConfig
    ) -> None:
        """Test all customization options working together."""
        with matplotlib_cleanup():
            factory = create_graph_factory_with_config(comprehensive_config)

            # Verify only enabled graphs are created
            enabled_types = factory.get_enabled_graph_types()

            # Based on comprehensive_config: daily_play_count=True, top_10_users=True, hourofday=True
            # dayofweek=False, platforms=False, month=False
            assert "daily_play_count" in enabled_types
            assert "top_10_users" in enabled_types
            assert "play_count_by_hourofday" in enabled_types
            assert "play_count_by_dayofweek" not in enabled_types
            assert "top_10_platforms" not in enabled_types
            assert "play_count_by_month" not in enabled_types

            # Test each enabled graph with all settings
            for graph_type in enabled_types:
                graph = factory.create_graph_by_type(graph_type)
                try:
                    # Verify all settings are applied
                    assert graph.config is not None
                    # Type guard to ensure we're working with TGraphBotConfig
                    assert not isinstance(graph.config, dict), (
                        "Config should be TGraphBotConfig, not dict"
                    )
                    config_obj: TGraphBotConfig = graph.config

                    assert config_obj.graphs.appearance.colors.tv == "#ff4444"
                    assert config_obj.graphs.appearance.colors.movie == "#44ff44"
                    assert config_obj.graphs.appearance.grid.enabled is True
                    # comprehensive_config has censor_usernames=False
                    assert config_obj.data_collection.privacy.censor_usernames is False
                finally:
                    graph.cleanup()

    def test_invalid_color_format_handling(self) -> None:
        """Test that invalid color formats are handled gracefully."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()

            # Test with invalid color format - should fall back to defaults
            # This tests the color validation in the BaseGraph class
            with pytest.raises(ValueError, match="Invalid background color format"):
                from src.tgraph_bot.graphs.graph_modules.core.base_graph import (
                    BaseGraph,
                )

                # Create a mock graph class to test invalid color handling
                class TestGraph(BaseGraph):
                    @override
                    def generate(self, data: Mapping[str, object]) -> str:
                        return "test.png"

                    @override
                    def get_title(self) -> str:
                        return "Test Graph"

                # This should raise ValueError due to invalid color
                graph = TestGraph(config=config, background_color="invalid_color")
                # Cleanup if it somehow gets created
                if hasattr(graph, "cleanup"):
                    graph.cleanup()

    def test_boolean_flag_customization(self) -> None:
        """Test that boolean flag customizations are properly applied."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Set boolean flags
            config.graphs.appearance.grid.enabled = True
            config.data_collection.privacy.censor_usernames = False
            config.graphs.appearance.annotations.basic.enable_outline = True

            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")

            # Verify boolean flags are applied
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), (
                "Config should be TGraphBotConfig, not dict"
            )
            config_obj: TGraphBotConfig = graph.config

            assert config_obj.graphs.appearance.annotations.basic.enable_outline is True

            # Test methods that use these flags
            assert graph.get_grid_enabled() is True
            assert graph.should_censor_usernames() is False
            assert graph.is_annotation_outline_enabled() is True

    def test_grid_enabling_consistency(self) -> None:
        """Test that grid enabling is consistent across different graph types."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.graphs.appearance.grid.enabled = True

            factory = create_graph_factory_with_config(config)

            # Test various graph types
            graph_types = [
                "daily_play_count",
                "top_10_users",
                "play_count_by_hourofday",
            ]

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)

                # Verify grid is enabled for all graph types
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert config_obj.graphs.appearance.grid.enabled is True
                assert graph.get_grid_enabled() is True

                # Cleanup
                graph.cleanup()

    def test_grid_disabling_consistency(self) -> None:
        """Test that grid disabling is consistent across different graph types."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            config.graphs.appearance.grid.enabled = False

            factory = create_graph_factory_with_config(config)

            # Test various graph types
            graph_types = [
                "daily_play_count",
                "top_10_users",
                "play_count_by_hourofday",
            ]

            for graph_type in graph_types:
                graph = factory.create_graph_by_type(graph_type)

                # Verify grid is disabled for all graph types
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert config_obj.graphs.appearance.grid.enabled is False
                assert graph.get_grid_enabled() is False

                # Cleanup
                graph.cleanup()

    def test_stacked_bar_charts_configuration_validation(self) -> None:
        """Test that stacked bar charts configuration works correctly."""
        with matplotlib_cleanup():
            # Test with stacked bar charts enabled
            config_enabled = create_test_config_minimal()
            config_enabled.graphs.features.media_type_separation = True
            config_enabled.graphs.features.stacked_bar_charts = True

            factory_enabled = create_graph_factory_with_config(config_enabled)

            # Test graphs that support stacked bar charts
            stacked_graph_types = ["play_count_by_dayofweek", "play_count_by_month"]

            for graph_type in stacked_graph_types:
                graph = factory_enabled.create_graph_by_type(graph_type)

                # Verify stacked bar charts are enabled
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert config_obj.graphs.features.stacked_bar_charts is True
                assert graph.get_stacked_bar_charts_enabled() is True
                assert graph.get_media_type_separation_enabled() is True

                # Cleanup
                graph.cleanup()

            # Test with stacked bar charts disabled
            config_disabled = create_test_config_minimal()
            config_disabled.graphs.features.media_type_separation = True
            config_disabled.graphs.features.stacked_bar_charts = False
            
            # Also disable per-graph stacked bar charts (per-graph settings take precedence)
            config_disabled.graphs.per_graph.play_count_by_dayofweek.stacked_bar_charts = False
            config_disabled.graphs.per_graph.play_count_by_month.stacked_bar_charts = False

            factory_disabled = create_graph_factory_with_config(config_disabled)

            for graph_type in stacked_graph_types:
                graph = factory_disabled.create_graph_by_type(graph_type)

                # Verify stacked bar charts are disabled
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj_disabled: TGraphBotConfig = graph.config

                assert config_obj_disabled.graphs.features.stacked_bar_charts is False
                assert graph.get_stacked_bar_charts_enabled() is False
                assert (
                    graph.get_media_type_separation_enabled() is True
                )  # Media separation can still be enabled

                # Cleanup
                graph.cleanup()

    def test_privacy_settings_validation(self) -> None:
        """Test that privacy settings are properly validated and applied."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Enable privacy settings
            config.data_collection.privacy.censor_usernames = True

            factory = create_graph_factory_with_config(config)

            # Test user-related graphs
            user_graphs = ["top_10_users"]
            for graph_type in user_graphs:
                graph = factory.create_graph_by_type(graph_type)

                # Verify privacy settings are applied
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert config_obj.data_collection.privacy.censor_usernames is True
                assert graph.should_censor_usernames() is True

                # Test username formatting
                test_username = "TestUser123"
                censored = graph.format_username(test_username, censor_enabled=True)
                assert censored != test_username  # Should be censored

                uncensored = graph.format_username(test_username, censor_enabled=False)
                assert uncensored == test_username  # Should be unchanged

                # Cleanup
                graph.cleanup()

    def test_comprehensive_customization_validation(self) -> None:
        """Test comprehensive customization settings validation."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Apply comprehensive customizations
            config.graphs.appearance.colors.tv = "#FF6B6B"
            config.graphs.appearance.colors.movie = "#4ECDC4"
            config.graphs.appearance.grid.enabled = True
            config.data_collection.privacy.censor_usernames = True

            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            try:
                # Comprehensive validation
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert (
                    config_obj.graphs.appearance.colors.tv == "#ff6b6b"
                )  # Normalized to lowercase
                assert (
                    config_obj.graphs.appearance.colors.movie == "#4ecdc4"
                )  # Normalized to lowercase
                assert config_obj.graphs.appearance.grid.enabled is True
                assert config_obj.data_collection.privacy.censor_usernames is True

                # Test that graph methods return expected values
                assert graph.get_tv_color() == "#ff6b6b"
                assert graph.get_movie_color() == "#4ecdc4"
                assert graph.get_grid_enabled() is True
                assert graph.should_censor_usernames() is True
            finally:
                # Cleanup
                graph.cleanup()

    def test_annotation_customization_validation(self) -> None:
        """Test that annotation customization settings are properly validated."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()
            # Set annotation customizations with valid colors
            config.graphs.appearance.annotations.basic.color = (
                "#ff0000"  # Valid red color
            )
            config.graphs.appearance.annotations.basic.outline_color = "#000000"
            config.graphs.appearance.annotations.basic.enable_outline = True

            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            try:
                # Verify annotation settings
                assert graph.config is not None
                assert graph.get_annotation_color() == "#ff0000"
                assert graph.get_annotation_outline_color() == "#000000"
                assert graph.is_annotation_outline_enabled() is True
            finally:
                # Cleanup
                graph.cleanup()

    def test_default_values_consistency(self) -> None:
        """Test that default values are consistent when not specified."""
        with matplotlib_cleanup():
            config = create_test_config_minimal()

            factory = create_graph_factory_with_config(config)
            graph = factory.create_graph_by_type("daily_play_count")
            try:
                # Verify default values are applied
                assert graph.get_tv_color() == "#1f77b4"  # Default matplotlib blue
                assert graph.get_movie_color() == "#ff7f0e"  # Default matplotlib orange
                assert graph.get_annotation_color() == "#ff0000"  # Default red
                assert (
                    graph.get_annotation_outline_color() == "#000000"
                )  # Default black
                assert graph.get_grid_enabled() is False  # Default disabled
                assert (
                    graph.should_censor_usernames() is True
                )  # Default privacy enabled
                assert graph.is_annotation_outline_enabled() is True  # Default enabled
            finally:
                # Cleanup
                graph.cleanup()
