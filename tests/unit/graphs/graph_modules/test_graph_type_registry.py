"""
Tests for the GraphTypeRegistry in TGraph Bot.

This module tests the centralized graph type registry that provides
mappings between graph type names, enable keys, and graph classes.
"""

import pytest

from src.tgraph_bot.graphs.graph_modules import (
    GraphTypeRegistry,
    get_graph_type_registry,
)
from src.tgraph_bot.graphs.graph_modules.core.graph_type_registry import GraphTypeInfo


class TestGraphTypeRegistry:
    """Test cases for the GraphTypeRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test that registry initializes correctly."""
        registry = GraphTypeRegistry()

        # Registry should not be initialized until first access
        assert not registry._initialized  # pyright: ignore[reportPrivateUsage]

        # Accessing any method should initialize it
        type_names = registry.get_all_type_names()
        assert registry._initialized  # pyright: ignore[reportPrivateUsage]
        assert isinstance(type_names, list)
        assert len(type_names) > 0

    def test_get_all_type_names(self) -> None:
        """Test getting all registered graph type names."""
        registry = GraphTypeRegistry()
        type_names = registry.get_all_type_names()

        expected_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            "sample_graph",
        }

        assert set(type_names) == expected_types


    def test_get_graph_class_valid_types(self) -> None:
        """Test getting graph classes for valid type names."""
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
            DailyPlayCountGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
            Top10UsersGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.sample_graph import (
            SampleGraph,
        )

        registry = GraphTypeRegistry()

        assert registry.get_graph_class("daily_play_count") == DailyPlayCountGraph
        assert registry.get_graph_class("top_10_users") == Top10UsersGraph
        assert registry.get_graph_class("sample_graph") == SampleGraph

    def test_get_graph_class_invalid_type(self) -> None:
        """Test that getting graph class for invalid type raises ValueError."""
        registry = GraphTypeRegistry()

        with pytest.raises(ValueError, match="Unknown graph type: invalid_type"):
            _ = registry.get_graph_class("invalid_type")



    def test_get_type_name_from_class(self) -> None:
        """Test getting type name from graph class."""
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
            DailyPlayCountGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
            Top10UsersGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.sample_graph import (
            SampleGraph,
        )

        registry = GraphTypeRegistry()

        assert (
            registry.get_type_name_from_class(DailyPlayCountGraph) == "daily_play_count"
        )
        assert registry.get_type_name_from_class(Top10UsersGraph) == "top_10_users"
        assert registry.get_type_name_from_class(SampleGraph) == "sample_graph"

    def test_get_type_name_from_invalid_class(self) -> None:
        """Test that getting type name from invalid class raises ValueError."""
        registry = GraphTypeRegistry()

        class FakeGraphClass:
            pass

        with pytest.raises(ValueError, match="Unknown graph class"):
            _ = registry.get_type_name_from_class(FakeGraphClass)  # pyright: ignore[reportArgumentType]

    def test_get_default_enabled(self) -> None:
        """Test getting default enabled status for graph types."""
        registry = GraphTypeRegistry()

        # Most graphs should be enabled by default
        assert registry.get_default_enabled("daily_play_count") is True
        assert registry.get_default_enabled("top_10_users") is True

        # Sample graph should be disabled by default
        assert registry.get_default_enabled("sample_graph") is False

    def test_get_default_enabled_invalid_type(self) -> None:
        """Test that getting default enabled for invalid type raises ValueError."""
        registry = GraphTypeRegistry()

        with pytest.raises(ValueError, match="Unknown graph type: invalid_type"):
            _ = registry.get_default_enabled("invalid_type")

    def test_get_type_info(self) -> None:
        """Test getting complete type information."""
        registry = GraphTypeRegistry()

        info = registry.get_type_info("daily_play_count")
        assert isinstance(info, GraphTypeInfo)
        assert info.type_name == "daily_play_count"
        assert info.default_enabled is True
        assert "Daily play count" in info.description

    def test_get_type_info_invalid_type(self) -> None:
        """Test that getting type info for invalid type raises ValueError."""
        registry = GraphTypeRegistry()

        with pytest.raises(ValueError, match="Unknown graph type: invalid_type"):
            _ = registry.get_type_info("invalid_type")

    def test_get_all_type_info(self) -> None:
        """Test getting information about all graph types."""
        registry = GraphTypeRegistry()

        all_info = registry.get_all_type_info()
        assert isinstance(all_info, dict)
        assert len(all_info) == 7  # All registered graph types

        # Check that all expected types are present
        expected_types = {
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
            "sample_graph",
        }
        assert set(all_info.keys()) == expected_types

        # Check that all values are GraphTypeInfo instances
        for info in all_info.values():
            assert isinstance(info, GraphTypeInfo)

    def test_is_valid_type(self) -> None:
        """Test checking if graph type names are valid."""
        registry = GraphTypeRegistry()

        # Valid types
        assert registry.is_valid_type("daily_play_count") is True
        assert registry.is_valid_type("top_10_users") is True
        assert registry.is_valid_type("sample_graph") is True

        # Invalid types
        assert registry.is_valid_type("invalid_type") is False
        assert registry.is_valid_type("") is False
        assert (
            registry.is_valid_type("ENABLE_DAILY_PLAY_COUNT") is False
        )  # This is an enable key, not type name

    def test_get_classes_for_types(self) -> None:
        """Test getting graph classes for a list of type names."""
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
            DailyPlayCountGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.top_10_users_graph import (
            Top10UsersGraph,
        )
        from src.tgraph_bot.graphs.graph_modules.implementations.sample_graph import (
            SampleGraph,
        )

        registry = GraphTypeRegistry()

        type_names = ["daily_play_count", "top_10_users", "sample_graph"]
        classes = registry.get_classes_for_types(type_names)

        expected_classes = [DailyPlayCountGraph, Top10UsersGraph, SampleGraph]
        assert classes == expected_classes

    def test_get_classes_for_types_with_invalid_type(self) -> None:
        """Test that getting classes for list with invalid type raises ValueError."""
        registry = GraphTypeRegistry()

        type_names = ["daily_play_count", "invalid_type", "top_10_users"]

        with pytest.raises(ValueError, match="Unknown graph type: invalid_type"):
            _ = registry.get_classes_for_types(type_names)

    def test_get_classes_for_empty_list(self) -> None:
        """Test getting classes for empty list returns empty list."""
        registry = GraphTypeRegistry()

        classes = registry.get_classes_for_types([])
        assert classes == []

    def test_global_registry_singleton(self) -> None:
        """Test that the global registry function returns the same instance."""
        registry1 = get_graph_type_registry()
        registry2 = get_graph_type_registry()

        assert registry1 is registry2
        assert isinstance(registry1, GraphTypeRegistry)

    def test_registry_consistency(self) -> None:
        """Test that registry data is consistent across different access methods."""
        registry = GraphTypeRegistry()

        # Get all type names and verify each one works with other methods
        type_names = registry.get_all_type_names()

        for type_name in type_names:
            # Each type should have valid graph class
            graph_class = registry.get_graph_class(type_name)
            assert graph_class is not None

            # Reverse lookup should work
            assert registry.get_type_name_from_class(graph_class) == type_name

            # Type should be valid
            assert registry.is_valid_type(type_name) is True

            # Should have default enabled status
            default_enabled = registry.get_default_enabled(type_name)
            assert isinstance(default_enabled, bool)

            # Type info should be complete
            info = registry.get_type_info(type_name)
            assert info.type_name == type_name
            assert info.graph_class == graph_class
            assert info.default_enabled == default_enabled
            assert isinstance(info.description, str)
            assert len(info.description) > 0
