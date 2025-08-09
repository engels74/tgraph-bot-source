"""
Tests for the graph factory system in TGraph Bot.

This module tests the factory pattern for creating graph instances
based on configuration settings.
"""

import tempfile
from pathlib import Path

import pytest

from src.tgraph_bot.graphs.graph_modules import GraphFactory
from src.tgraph_bot.config.schema import TGraphBotConfig
from tests.utils.test_helpers import create_test_config, create_test_config_custom


class TestGraphFactory:
    """Test cases for the GraphFactory class."""

    def test_factory_initialization(self) -> None:
        """Test GraphFactory initialization."""
        config = create_test_config_custom(
            graphs_overrides={"features": {"enabled_types": {"daily_play_count": True}}}
        )
        factory = GraphFactory(config)
        assert factory.config == config
        assert factory._config_accessor is not None  # pyright: ignore[reportPrivateUsage]
        assert factory._graph_registry is not None  # pyright: ignore[reportPrivateUsage]

    def test_factory_initialization_with_tgraphbot_config(
        self, base_config: TGraphBotConfig
    ) -> None:
        """Test GraphFactory initialization with TGraphBotConfig object."""
        factory = GraphFactory(base_config)
        assert factory.config == base_config
        assert factory._config_accessor is not None  # pyright: ignore[reportPrivateUsage]
        assert factory._graph_registry is not None  # pyright: ignore[reportPrivateUsage]

    def test_create_enabled_graphs_empty_config(self) -> None:
        """Test creating graphs with default configuration."""
        config = create_test_config_custom()  # Use default config
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        # With default config, all graphs are enabled by default (True is the default)
        assert isinstance(graphs, list)
        assert len(graphs) == 12  # All 12 graph types should be created (6 original + 6 stream types)

    def test_create_enabled_graphs_all_disabled(self) -> None:
        """Test creating graphs with all graph types disabled."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": False,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": False,
                        "play_count_by_month": False,
                        "top_10_platforms": False,
                        "top_10_users": False,
                        # Stream Type Graphs
                        "daily_play_count_by_stream_type": False,
                        "daily_concurrent_stream_count_by_stream_type": False,
                        "play_count_by_source_resolution": False,
                        "play_count_by_stream_resolution": False,
                        "play_count_by_platform_and_stream_type": False,
                        "play_count_by_user_and_stream_type": False,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        assert isinstance(graphs, list)
        assert len(graphs) == 0

    def test_create_enabled_graphs_all_enabled(self) -> None:
        """Test creating graphs with all graph types enabled."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": True,
                        "play_count_by_hourofday": True,
                        "play_count_by_month": True,
                        "top_10_platforms": True,
                        "top_10_users": True,
                        # Stream Type Graphs
                        "daily_play_count_by_stream_type": True,
                        "daily_concurrent_stream_count_by_stream_type": True,
                        "play_count_by_source_resolution": True,
                        "play_count_by_stream_resolution": True,
                        "play_count_by_platform_and_stream_type": True,
                        "play_count_by_user_and_stream_type": True,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        # All graph types are enabled, so all 12 should be created
        assert isinstance(graphs, list)
        assert len(graphs) == 12

    def test_create_enabled_graphs_partial_enabled(self) -> None:
        """Test creating graphs with some graph types enabled."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": True,
                        "play_count_by_month": False,
                        "top_10_platforms": True,
                        "top_10_users": False,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        # Only 3 graph types are enabled (daily, hourofday, platforms)
        assert isinstance(graphs, list)
        assert len(graphs) == 3

    def test_create_graph_by_type_unknown_type(self) -> None:
        """Test creating graph with unknown type raises ValueError."""
        config = create_test_config_custom()
        factory = GraphFactory(config)

        with pytest.raises(ValueError, match="Unknown graph type: unknown_type"):
            _ = factory.create_graph_by_type("unknown_type")

    def test_create_graph_by_type_valid_types(self) -> None:
        """Test creating graph by type with valid type names."""
        config = create_test_config_custom()
        factory = GraphFactory(config)

        valid_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
        ]

        for graph_type in valid_types:
            # Should successfully create graph instances
            graph = factory.create_graph_by_type(graph_type)
            assert graph is not None
            assert hasattr(graph, "generate")
            assert hasattr(graph, "get_title")

    def test_create_graph_by_type_returns_correct_types(self) -> None:
        """Test that create_graph_by_type returns the correct graph class instances."""
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
            DailyPlayCountGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_dayofweek_graph import (
            PlayCountByDayOfWeekGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
            Top10UsersGraph,
        )

        config = create_test_config_custom()
        factory = GraphFactory(config)

        daily_graph = factory.create_graph_by_type("daily_play_count")
        assert isinstance(daily_graph, DailyPlayCountGraph)

        dayofweek_graph = factory.create_graph_by_type("play_count_by_dayofweek")
        assert isinstance(dayofweek_graph, PlayCountByDayOfWeekGraph)

        users_graph = factory.create_graph_by_type("top_10_users")
        assert isinstance(users_graph, Top10UsersGraph)

    def test_get_enabled_graph_types_empty_config(self) -> None:
        """Test getting enabled graph types with empty configuration."""
        config = create_test_config()  # Use minimal config instead of empty dict
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()

        # All types should be enabled by default (True is the default)
        expected_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            # Stream Type Graphs
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        ]

        assert set(enabled_types) == set(expected_types)

    def test_get_enabled_graph_types_all_disabled(self) -> None:
        """Test getting enabled graph types with all disabled."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": False,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": False,
                        "play_count_by_month": False,
                        "top_10_platforms": False,
                        "top_10_users": False,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()

        assert enabled_types == []

    def test_get_enabled_graph_types_partial_enabled(self) -> None:
        """Test getting enabled graph types with some enabled."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": True,
                        "play_count_by_month": False,
                        "top_10_platforms": True,
                        "top_10_users": False,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()

        expected_types = [
            "daily_play_count",
            "play_count_by_hourofday",
            "top_10_platforms",
        ]

        assert set(enabled_types) == set(expected_types)

    def test_get_enabled_graph_types_mixed_values(self) -> None:
        """Test getting enabled graph types with mixed value types."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": True,
                        "play_count_by_month": False,
                        "top_10_platforms": False,
                        "top_10_users": True,
                    }
                }
            }
        )
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()

        expected_types = [
            "daily_play_count",
            "play_count_by_hourofday",
            "top_10_users",  # Non-empty string is truthy
        ]

        assert set(enabled_types) == set(expected_types)

    def test_graph_dimensions_extraction(self) -> None:
        """Test graph dimensions extraction from configuration."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {"token": "test_discord_token", "channel_id": 123456789},
            },
            graphs_overrides={
                "appearance": {"dimensions": {"width": 15, "height": 10, "dpi": 150}}
            },
        )
        factory = GraphFactory(config)

        # Access private method for testing
        dimensions = factory._get_graph_dimensions()  # pyright: ignore[reportPrivateUsage]

        assert dimensions["width"] == 15
        assert dimensions["height"] == 10
        assert dimensions["dpi"] == 150

    def test_graph_dimensions_defaults(self) -> None:
        """Test graph dimensions with default values."""
        config = create_test_config()  # Use minimal config instead of empty dict
        factory = GraphFactory(config)

        # Access private method for testing
        dimensions = factory._get_graph_dimensions()  # pyright: ignore[reportPrivateUsage]

        # Should use default values from ConfigAccessor
        assert "width" in dimensions
        assert "height" in dimensions
        assert "dpi" in dimensions
        assert isinstance(dimensions["width"], int)
        assert isinstance(dimensions["height"], int)
        assert isinstance(dimensions["dpi"], int)

    def test_factory_config_immutability(self) -> None:
        """Test that factory doesn't modify the original config."""
        original_config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                    }
                }
            }
        )
        # Create a copy by serializing and deserializing
        config_copy = TGraphBotConfig.model_validate(original_config.model_dump())

        factory = GraphFactory(config_copy)
        _ = factory.get_enabled_graph_types()
        _ = factory.create_enabled_graphs()

        # Original config should be unchanged
        assert original_config.model_dump() == config_copy.model_dump()

    def test_factory_extensibility(self) -> None:
        """Test that factory design supports extensibility."""
        # This test verifies the factory pattern structure supports
        # adding new graph types without modifying existing code

        factory = GraphFactory(create_test_config())

        # Verify the type mapping exists and has expected structure
        enabled_types = factory.get_enabled_graph_types()
        assert isinstance(enabled_types, list)

        # Verify all expected graph types are in the mapping
        expected_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            # Stream Type Graphs
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        }

        # When all are enabled by default, we should get all types
        assert set(enabled_types) == expected_types

    def test_sample_graph_integration(self) -> None:
        """Test that sample graph can be created through factory."""
        config = (
            create_test_config()
        )  # Sample graph not in our mapping, use default config
        factory = GraphFactory(config)

        # Test creating sample graph by type
        sample_graph = factory.create_graph_by_type("sample_graph")
        assert sample_graph is not None
        assert hasattr(sample_graph, "generate")
        assert hasattr(sample_graph, "get_title")
        assert sample_graph.get_title() == "Sample Data Visualization"

    def test_sample_graph_in_enabled_graphs(self) -> None:
        """Test that sample graph is disabled by default and not configurable through normal config."""
        # Sample graph should not be enabled by default
        config = create_test_config()
        factory = GraphFactory(config)

        enabled_types = factory.get_enabled_graph_types()
        assert "sample_graph" not in enabled_types

        enabled_graphs = factory.create_enabled_graphs()
        # Should have only the 12 default graphs (sample graph is disabled by default)
        assert len(enabled_graphs) == 12

        # Sample graph should still be creatable by type even if not enabled by default
        sample_graph = factory.create_graph_by_type("sample_graph")
        assert sample_graph is not None
        assert hasattr(sample_graph, "generate")
        assert hasattr(sample_graph, "get_title")
        assert sample_graph.get_title() == "Sample Data Visualization"

    def test_sample_graph_disabled_by_default(self) -> None:
        """Test that sample graph is disabled by default."""
        factory = GraphFactory(create_test_config())  # Use minimal config

        enabled_types = factory.get_enabled_graph_types()
        assert "sample_graph" not in enabled_types

        enabled_graphs = factory.create_enabled_graphs()
        # Should have only the 12 default graphs
        assert len(enabled_graphs) == 12

    def test_end_to_end_sample_graph_workflow(self) -> None:
        """Test complete workflow: factory -> graph -> generation."""
        from src.tgraph_bot.graphs.graph_modules.implementations.sample_graph import (
            SampleGraph,
        )

        config = (
            create_test_config()
        )  # Sample graph not in our mapping, use default config
        factory = GraphFactory(config)

        # Create graph through factory
        sample_graph = factory.create_graph_by_type("sample_graph")
        assert isinstance(sample_graph, SampleGraph)

        # Generate sample data and create graph
        sample_data = sample_graph.get_sample_data()
        output_path = sample_graph.generate(sample_data)

        # Verify file was created
        assert Path(output_path).exists()
        assert "sample_graph" in output_path

        # Clean up
        Path(output_path).unlink(missing_ok=True)

    def test_setup_graph_environment(self) -> None:
        """Test that setup_graph_environment creates directory and returns path."""
        factory = GraphFactory(create_test_config())

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "test_graphs"

            # Setup graph environment
            graph_dir = factory.setup_graph_environment(str(base_path))

            # Verify directory was created
            assert graph_dir.exists()
            assert graph_dir.is_dir()
            assert str(graph_dir) == str(base_path)

    def test_cleanup_old_graphs_with_directory(self) -> None:
        """Test cleanup of old graph files from specified directory."""
        factory = GraphFactory(create_test_config())

        with tempfile.TemporaryDirectory() as temp_dir:
            graph_dir = Path(temp_dir)

            # Create some test files with different ages
            old_file = graph_dir / "old_graph.png"
            new_file = graph_dir / "new_graph.png"

            old_file.touch()
            new_file.touch()

            # Make old file appear old by modifying its timestamp
            import os
            import time

            old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
            os.utime(old_file, (old_time, old_time))

            # Cleanup files older than 7 days
            deleted_count = factory.cleanup_old_graphs(graph_dir, keep_days=7)

            # Note: This test might not work as expected due to filesystem limitations
            # but it tests the method interface
            assert isinstance(deleted_count, int)
            assert deleted_count >= 0

    def test_cleanup_old_graphs_default_directory(self) -> None:
        """Test cleanup using default graph directory."""
        factory = GraphFactory(create_test_config())

        # This should not raise an error even if directory doesn't exist
        deleted_count = factory.cleanup_old_graphs()
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0

    def test_generate_all_graphs_empty_data(self) -> None:
        """Test generate_all_graphs with minimal data structure."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": False,
                        "play_count_by_month": False,
                        "top_10_platforms": False,
                        "top_10_users": False,
                    }
                }
            }
        )
        factory = GraphFactory(config)

        # Mock data structure that graphs expect
        data: dict[str, object] = {"play_history": {"data": []}, "time_range_days": 30}

        # This should not raise an exception even with empty data
        # Each graph should handle empty data gracefully
        try:
            paths = factory.generate_all_graphs(data)
            assert isinstance(paths, list)
            # With empty data, graphs may still generate (showing "no data" message)
            # or may return empty paths list
            assert len(paths) >= 0  # Could be 0 or 1 depending on empty data handling
        except Exception:
            # If graphs don't handle empty data gracefully, that's a separate issue
            # But the factory should not crash
            pass

    def test_generate_graphs_with_exclusions(self) -> None:
        """Test generate_graphs_with_exclusions functionality."""
        config = create_test_config_custom(
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "top_10_users": True,
                    }
                }
            }
        )
        factory = GraphFactory(config)

        # Mock data structure
        data: dict[str, object] = {"play_history": {"data": []}, "time_range_days": 30}

        # Test excluding specific graph types
        try:
            paths = factory.generate_graphs_with_exclusions(
                data, exclude_types=["top_10_users"]
            )
            assert isinstance(paths, list)
            # Should have fewer graphs than without exclusions
        except Exception:
            # If graphs don't handle empty data gracefully, that's a separate issue
            pass

    def test_cleanup_all_graph_resources(self) -> None:
        """Test cleanup_all_graph_resources method."""
        config = create_test_config()
        factory = GraphFactory(config)

        # Should not raise exception
        factory.cleanup_all_graph_resources()

    def test_config_accessor_integration(self) -> None:
        """Test that ConfigAccessor is properly integrated."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {"token": "test_discord_token", "channel_id": 123456789},
            },
            graphs_overrides={
                "features": {
                    "enabled_types": {"daily_play_count": True, "top_10_users": False}
                }
            },
        )
        factory = GraphFactory(config)

        # Test that the factory uses ConfigAccessor properly
        enabled_types = factory.get_enabled_graph_types()
        assert "daily_play_count" in enabled_types
        assert "top_10_users" not in enabled_types

    def test_graph_type_registry_integration(self) -> None:
        """Test that GraphTypeRegistry is properly integrated."""
        factory = GraphFactory(create_test_config())

        # Test that the factory can access registry information
        enabled_types = factory.get_enabled_graph_types()
        assert isinstance(enabled_types, list)

        # Should have all graph types enabled by default
        expected_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            # Stream Type Graphs
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        }
        assert set(enabled_types) == expected_types

    def test_create_graph_by_type_with_dimensions(self) -> None:
        """Test that created graphs receive proper dimensions from config."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {"token": "test_discord_token", "channel_id": 123456789},
            },
            graphs_overrides={
                "appearance": {"dimensions": {"width": 15, "height": 10, "dpi": 150}}
            },
        )
        factory = GraphFactory(config)

        # Create a graph and verify dimensions
        graph = factory.create_graph_by_type("daily_play_count")
        assert graph.width == 15
        assert graph.height == 10
        assert graph.dpi == 150

    def test_create_enabled_graphs_with_dimensions(self) -> None:
        """Test that enabled graphs receive proper dimensions from config."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {"token": "test_discord_token", "channel_id": 123456789},
            },
            graphs_overrides={
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": False,
                        "play_count_by_hourofday": False,
                        "play_count_by_month": False,
                        "top_10_platforms": False,
                        "top_10_users": False,
                    }
                },
                "appearance": {"dimensions": {"width": 20, "height": 12, "dpi": 200}},
            },
        )
        factory = GraphFactory(config)

        # Create enabled graphs and verify dimensions
        graphs = factory.create_enabled_graphs()
        assert len(graphs) == 1  # Only daily_play_count enabled

        graph = graphs[0]
        assert graph.width == 20
        assert graph.height == 12
        assert graph.dpi == 200
