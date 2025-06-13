"""
End-to-end integration tests for graph customization and feature validation.

This module provides comprehensive integration tests that validate the complete
workflow from configuration to graph generation, ensuring all customization
options work correctly in realistic scenarios.
"""

from __future__ import annotations

from config.schema import TGraphBotConfig
from graphs.graph_modules.graph_factory import GraphFactory


class TestEndToEndCustomization:
    """End-to-end integration tests for graph customization features."""

    def test_complete_workflow_with_all_customizations(self) -> None:
        """Test complete workflow with all customization options enabled."""
        # Create a comprehensive configuration with all options
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # Timing and retention
            UPDATE_DAYS=14,
            KEEP_DAYS=21,
            TIME_RANGE_DAYS=60,
            
            # Graph feature toggles
            ENABLE_DAILY_PLAY_COUNT=True,
            ENABLE_PLAY_COUNT_BY_DAYOFWEEK=True,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=True,
            ENABLE_PLAY_COUNT_BY_MONTH=True,
            ENABLE_TOP_10_PLATFORMS=True,
            ENABLE_TOP_10_USERS=True,
            
            # Visual customizations
            TV_COLOR="#2E86AB",
            MOVIE_COLOR="#A23B72",
            GRAPH_BACKGROUND_COLOR="#F8F9FA",
            ANNOTATION_COLOR="#C73E1D",
            ANNOTATION_OUTLINE_COLOR="#FFFFFF",
            
            # Graph options
            ENABLE_GRAPH_GRID=True,
            CENSOR_USERNAMES=True,
            ENABLE_ANNOTATION_OUTLINE=True,
            
            # Annotation controls
            ANNOTATE_DAILY_PLAY_COUNT=True,
            ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK=True,
            ANNOTATE_PLAY_COUNT_BY_HOUROFDAY=True,
            ANNOTATE_TOP_10_PLATFORMS=True,
            ANNOTATE_TOP_10_USERS=True,
            ANNOTATE_PLAY_COUNT_BY_MONTH=True,
        )
        
        # Create factory with comprehensive config
        factory = GraphFactory(config)
        
        # Verify all expected graphs are enabled
        enabled_types = factory.get_enabled_graph_types()
        expected_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users"
        }
        assert set(enabled_types) == expected_types
        
        # Test each graph type can be created with full configuration
        for graph_type in enabled_types:
            graph = factory.create_graph_by_type(graph_type)
            
            # Verify configuration is properly applied (colors are normalized to lowercase)
            assert graph.config is not None
            assert graph.config.TV_COLOR == "#2e86ab"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.MOVIE_COLOR == "#a23b72"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.GRAPH_BACKGROUND_COLOR == "#f8f9fa"  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.ENABLE_GRAPH_GRID is True  # pyright: ignore[reportOptionalMemberAccess]
            assert graph.config.CENSOR_USERNAMES is True  # pyright: ignore[reportOptionalMemberAccess]
            
            # Verify graph properties are set correctly
            assert graph.background_color == "#f8f9fa"
            assert graph.width == 12  # Default width
            assert graph.height == 8  # Default height
            assert graph.dpi == 100  # Default DPI

    def test_minimal_configuration_workflow(self) -> None:
        """Test workflow with minimal configuration using defaults."""
        # Create minimal configuration
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
        )
        
        factory = GraphFactory(config)
        
        # With minimal config, all graphs should be enabled by default
        enabled_types = factory.get_enabled_graph_types()
        assert len(enabled_types) == 6  # All 6 graph types
        
        # Test that default values are applied correctly
        graph = factory.create_graph_by_type("daily_play_count")
        assert graph.config is not None
        assert graph.config.TV_COLOR == "#1f77b4"  # pyright: ignore[reportOptionalMemberAccess] # Default blue
        assert graph.config.MOVIE_COLOR == "#ff7f0e"  # pyright: ignore[reportOptionalMemberAccess] # Default orange
        assert graph.config.CENSOR_USERNAMES is True  # pyright: ignore[reportOptionalMemberAccess] # Default privacy
        assert graph.config.ENABLE_GRAPH_GRID is False  # pyright: ignore[reportOptionalMemberAccess] # Default no grid

    def test_selective_graph_enabling_workflow(self) -> None:
        """Test workflow with selective graph type enabling."""
        # Enable only specific graph types
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # Enable only 3 graph types
            ENABLE_DAILY_PLAY_COUNT=True,
            ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
            ENABLE_PLAY_COUNT_BY_MONTH=True,
            ENABLE_TOP_10_PLATFORMS=False,
            ENABLE_TOP_10_USERS=True,
        )
        
        factory = GraphFactory(config)
        
        # Verify only selected graphs are enabled
        enabled_types = factory.get_enabled_graph_types()
        expected_enabled = {"daily_play_count", "play_count_by_month", "top_10_users"}
        assert set(enabled_types) == expected_enabled
        
        # Verify disabled graphs are not in the list
        assert "play_count_by_dayofweek" not in enabled_types
        assert "play_count_by_hourofday" not in enabled_types
        assert "top_10_platforms" not in enabled_types

    def test_privacy_focused_configuration(self) -> None:
        """Test configuration optimized for privacy."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # Privacy-focused settings
            CENSOR_USERNAMES=True,
            ENABLE_TOP_10_USERS=False,  # Disable user-specific graphs
            
            # Disable user-related annotations
            ANNOTATE_TOP_10_USERS=False,
        )
        
        factory = GraphFactory(config)
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
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # Performance optimizations
            TIME_RANGE_DAYS=7,  # Shorter time range
            
            # Enable only essential graphs
            ENABLE_DAILY_PLAY_COUNT=True,
            ENABLE_PLAY_COUNT_BY_DAYOFWEEK=False,
            ENABLE_PLAY_COUNT_BY_HOUROFDAY=False,
            ENABLE_PLAY_COUNT_BY_MONTH=True,
            ENABLE_TOP_10_PLATFORMS=False,
            ENABLE_TOP_10_USERS=True,
            
            # Disable annotations for faster generation
            ANNOTATE_DAILY_PLAY_COUNT=False,
            ANNOTATE_PLAY_COUNT_BY_MONTH=False,
            ANNOTATE_TOP_10_USERS=False,
        )
        
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()
        
        # Verify only essential graphs are enabled
        assert len(enabled_types) == 3
        expected_types = {"daily_play_count", "play_count_by_month", "top_10_users"}
        assert set(enabled_types) == expected_types
        
        # Verify performance settings are applied
        assert config.TIME_RANGE_DAYS == 7

    def test_high_contrast_theme_configuration(self) -> None:
        """Test configuration with high contrast theme."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # High contrast dark theme
            GRAPH_BACKGROUND_COLOR="#2b2b2b",
            TV_COLOR="#00ff00",
            MOVIE_COLOR="#ff6600",
            ANNOTATION_COLOR="#ffffff",
            ANNOTATION_OUTLINE_COLOR="#000000",
            
            # Enable grid for better readability
            ENABLE_GRAPH_GRID=True,
            ENABLE_ANNOTATION_OUTLINE=True,
        )
        
        factory = GraphFactory(config)
        graph = factory.create_graph_by_type("daily_play_count")
        
        # Verify high contrast colors are applied (colors are normalized to lowercase)
        assert graph.config is not None
        assert graph.config.GRAPH_BACKGROUND_COLOR == "#2b2b2b"  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.TV_COLOR == "#00ff00"  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.MOVIE_COLOR == "#ff6600"  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.ANNOTATION_COLOR == "#ffffff"  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.ENABLE_GRAPH_GRID is True  # pyright: ignore[reportOptionalMemberAccess]

        # Verify graph background is applied
        assert graph.background_color == "#2b2b2b"

    def test_factory_resource_management(self) -> None:
        """Test that factory properly manages resources across multiple operations."""
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
        )
        
        factory = GraphFactory(config)
        
        # Create multiple graphs to test resource management
        graphs = []
        for graph_type in ["daily_play_count", "top_10_users", "play_count_by_hourofday"]:
            graph = factory.create_graph_by_type(graph_type)
            graphs.append(graph)
            
            # Verify each graph is properly configured
            assert graph.config is not None
            assert graph.background_color == "#ffffff"  # Default background
        
        # Test that all graphs are independent instances
        assert len(set(id(graph) for graph in graphs)) == 3
        
        # Test cleanup functionality
        for graph in graphs:
            graph.cleanup()
            assert graph.figure is None
            assert graph.axes is None

    def test_configuration_validation_edge_cases(self) -> None:
        """Test configuration validation with edge case values."""
        # Test with boundary values
        config = TGraphBotConfig(
            TAUTULLI_API_KEY="test_api_key_here",
            TAUTULLI_URL="http://localhost:8181/api/v2",
            DISCORD_TOKEN="test_discord_token_1234567890",
            CHANNEL_ID=123456789,
            
            # Boundary values
            UPDATE_DAYS=1,  # Minimum
            KEEP_DAYS=365,  # Maximum
            TIME_RANGE_DAYS=1,  # Minimum
        )
        
        factory = GraphFactory(config)
        graph = factory.create_graph_by_type("daily_play_count")
        
        # Verify boundary values are accepted
        assert graph.config is not None
        assert graph.config.UPDATE_DAYS == 1  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.KEEP_DAYS == 365  # pyright: ignore[reportOptionalMemberAccess]
        assert graph.config.TIME_RANGE_DAYS == 1  # pyright: ignore[reportOptionalMemberAccess]
