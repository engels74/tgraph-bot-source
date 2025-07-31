"""
End-to-end integration tests for graph customization and feature validation.

This module provides comprehensive integration tests that validate the complete
workflow from configuration to graph generation, ensuring all customization
options work correctly in realistic scenarios.
"""

from __future__ import annotations

# Removed unused imports - now using utility functions
from tests.utils.graph_helpers import (
    create_test_config_comprehensive,
    create_test_config_minimal,
    create_test_config_selective,
    create_test_config_privacy_focused,
    create_graph_factory_with_config,
    assert_factory_enabled_graphs,
    assert_graph_properties,
    assert_graph_cleanup,
    matplotlib_cleanup,
)

# Import for type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig


class TestEndToEndCustomization:
    """End-to-end integration tests for graph customization features."""

    def test_complete_workflow_with_all_customizations(self) -> None:
        """Test complete workflow with all customization options enabled."""
        with matplotlib_cleanup():
            # Create a comprehensive configuration with all options
            config = create_test_config_comprehensive()

            # Create factory with comprehensive config
            factory = create_graph_factory_with_config(config)

            # Verify all expected graphs are enabled
            expected_types = {
                "daily_play_count",
                "play_count_by_dayofweek",
                "play_count_by_hourofday",
                "play_count_by_month",
                "top_10_platforms",
                "top_10_users",
            }
            assert_factory_enabled_graphs(factory, expected_types)

            # Test each graph type can be created with full configuration
            enabled_types = factory.get_enabled_graph_types()
            for graph_type in enabled_types:
                graph = factory.create_graph_by_type(graph_type)

                # Verify configuration is properly applied (colors are normalized to lowercase)
                assert graph.config is not None
                # Type guard to ensure we're working with TGraphBotConfig
                assert not isinstance(graph.config, dict), (
                    "Config should be TGraphBotConfig, not dict"
                )
                config_obj: TGraphBotConfig = graph.config

                assert config_obj.graphs.appearance.colors.tv == "#2e86ab"
                assert config_obj.graphs.appearance.colors.movie == "#a23b72"
                assert config_obj.graphs.appearance.colors.background == "#f8f9fa"
                assert config_obj.graphs.appearance.grid.enabled is True
                assert config_obj.data_collection.privacy.censor_usernames is True

                # Verify graph properties are set correctly using utility
                assert_graph_properties(graph, expected_background_color="#f8f9fa")

    def test_minimal_configuration_workflow(self) -> None:
        """Test workflow with minimal configuration using defaults."""
        with matplotlib_cleanup():
            # Create minimal configuration
            config = create_test_config_minimal()

            factory = create_graph_factory_with_config(config)

            # With minimal config, all graphs should be enabled by default
            enabled_types = factory.get_enabled_graph_types()
            assert len(enabled_types) == 6  # All 6 graph types

            # Test that default values are applied correctly
            graph = factory.create_graph_by_type("daily_play_count")
            assert graph.config is not None
            # Type guard to ensure we're working with TGraphBotConfig
            assert not isinstance(graph.config, dict), (
                "Config should be TGraphBotConfig, not dict"
            )
            config_obj: TGraphBotConfig = graph.config

            assert config_obj.graphs.appearance.colors.tv == "#1f77b4"  # Default blue
            assert config_obj.graphs.appearance.colors.movie == "#ff7f0e"  # Default orange
            assert config_obj.data_collection.privacy.censor_usernames is True  # Default privacy
            assert config_obj.graphs.appearance.grid.enabled is False  # Default no grid

    def test_selective_graph_enabling_workflow(self) -> None:
        """Test workflow with selective graph type enabling."""
        with matplotlib_cleanup():
            # Enable only specific graph types
            config = create_test_config_selective(
                enable_daily_play_count=True,
                enable_play_count_by_dayofweek=False,
                enable_play_count_by_hourofday=False,
                enable_play_count_by_month=True,
                enable_top_10_platforms=False,
                enable_top_10_users=True,
            )

            factory = create_graph_factory_with_config(config)

            # Verify only selected graphs are enabled
            expected_enabled = {
                "daily_play_count",
                "play_count_by_month",
                "top_10_users",
            }
            assert_factory_enabled_graphs(factory, expected_enabled)

            # Verify disabled graphs are not in the list
            enabled_types = factory.get_enabled_graph_types()
            assert "play_count_by_dayofweek" not in enabled_types
            assert "play_count_by_hourofday" not in enabled_types
            assert "top_10_platforms" not in enabled_types

    def test_privacy_focused_configuration(self) -> None:
        """Test configuration optimized for privacy."""
        with matplotlib_cleanup():
            config = create_test_config_privacy_focused()

            factory = create_graph_factory_with_config(config)
            enabled_types = factory.get_enabled_graph_types()

            # Verify user graphs are disabled
            assert "top_10_users" not in enabled_types

            # Test remaining graphs have privacy settings applied
            for graph_type in enabled_types:
                if graph_type != "top_10_users":  # Skip disabled graph
                    graph = factory.create_graph_by_type(graph_type)
                    assert graph.should_censor_usernames() is True

    def test_performance_optimized_configuration(self) -> None:
        """Test configuration optimized for performance."""
        config = create_test_config_selective(
            enable_daily_play_count=True,
            enable_play_count_by_dayofweek=False,
            enable_play_count_by_hourofday=False,
            enable_play_count_by_month=True,
            enable_top_10_platforms=False,
            enable_top_10_users=True,
        )
        # Override for performance testing
        config.data_collection.time_ranges.days = 7
        config.graphs.appearance.annotations.enabled_on.daily_play_count = False
        config.graphs.appearance.annotations.enabled_on.play_count_by_month = False
        config.graphs.appearance.annotations.enabled_on.top_10_users = False

        factory = create_graph_factory_with_config(config)
        enabled_types = factory.get_enabled_graph_types()

        # Verify only essential graphs are enabled
        assert len(enabled_types) == 3
        expected_types = {"daily_play_count", "play_count_by_month", "top_10_users"}
        assert set(enabled_types) == expected_types

        # Verify performance settings are applied
        assert config.data_collection.time_ranges.days == 7

    def test_high_contrast_theme_configuration(self) -> None:
        """Test configuration with high contrast theme."""
        config = create_test_config_minimal()
        # Override for high contrast theme
        config.graphs.appearance.colors.background = "#2b2b2b"
        config.graphs.appearance.colors.tv = "#00ff00"
        config.graphs.appearance.colors.movie = "#ff6600"
        config.graphs.appearance.annotations.basic.color = "#ffffff"
        config.graphs.appearance.annotations.basic.outline_color = "#000000"
        config.graphs.appearance.grid.enabled = True
        config.graphs.appearance.annotations.basic.enable_outline = True

        factory = create_graph_factory_with_config(config)
        graph = factory.create_graph_by_type("daily_play_count")

        # Verify high contrast colors are applied (colors are normalized to lowercase)
        assert graph.config is not None
        # Type guard to ensure we're working with TGraphBotConfig
        assert not isinstance(graph.config, dict), (
            "Config should be TGraphBotConfig, not dict"
        )
        config_obj: TGraphBotConfig = graph.config

        assert config_obj.graphs.appearance.colors.background == "#2b2b2b"
        assert config_obj.graphs.appearance.colors.tv == "#00ff00"
        assert config_obj.graphs.appearance.colors.movie == "#ff6600"
        assert config_obj.graphs.appearance.annotations.basic.color == "#ffffff"
        assert config_obj.graphs.appearance.grid.enabled is True

        # Verify graph background is applied
        assert graph.background_color == "#2b2b2b"

    def test_factory_resource_management(self) -> None:
        """Test that factory properly manages resources across multiple operations."""
        config = create_test_config_minimal()
        factory = create_graph_factory_with_config(config)

        # Create multiple graphs to test resource management
        graphs: list[object] = []
        for graph_type in [
            "daily_play_count",
            "top_10_users",
            "play_count_by_hourofday",
        ]:
            graph = factory.create_graph_by_type(graph_type)
            graphs.append(graph)

            # Verify each graph is properly configured
            assert graph.config is not None
            assert graph.background_color == "#ffffff"  # Default background

        # Test that all graphs are independent instances
        assert len(set(id(graph) for graph in graphs)) == 3

        # Test cleanup functionality
        for graph in graphs:
            graph.cleanup()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
            assert_graph_cleanup(graph)  # pyright: ignore[reportArgumentType]

    def test_configuration_validation_edge_cases(self) -> None:
        """Test configuration validation with edge case values."""
        # Test with boundary values
        config = create_test_config_minimal()
        # Override for edge case testing
        config.automation.scheduling.update_days = 1  # Minimum
        config.automation.data_retention.keep_days = 365  # Maximum
        config.data_collection.time_ranges.days = 1  # Minimum

        factory = create_graph_factory_with_config(config)
        graph = factory.create_graph_by_type("daily_play_count")

        # Type guard to ensure we're working with TGraphBotConfig
        assert graph.config is not None
        assert not isinstance(graph.config, dict), (
            "Config should be TGraphBotConfig, not dict"
        )
        config_obj: TGraphBotConfig = graph.config

        # Verify boundary values are accepted
        assert config_obj.automation.scheduling.update_days == 1
        assert config_obj.automation.data_retention.keep_days == 365
        assert config_obj.data_collection.time_ranges.days == 1
