"""
Tests for the graph factory system in TGraph Bot.

This module tests the factory pattern for creating graph instances
based on configuration settings.
"""

import pytest

from graphs.graph_modules.graph_factory import GraphFactory


class TestGraphFactory:
    """Test cases for the GraphFactory class."""
    
    def test_factory_initialization(self) -> None:
        """Test GraphFactory initialization."""
        config = {"ENABLE_DAILY_PLAY_COUNT": True}
        factory = GraphFactory(config)
        assert factory.config == config
    
    def test_create_enabled_graphs_empty_config(self) -> None:
        """Test creating graphs with empty configuration."""
        factory = GraphFactory({})
        graphs = factory.create_enabled_graphs()

        # With empty config, all graphs are enabled by default (True is the default)
        assert isinstance(graphs, list)
        assert len(graphs) == 6  # All 6 graph types should be created
    
    def test_create_enabled_graphs_all_disabled(self) -> None:
        """Test creating graphs with all graph types disabled."""
        config = {
            "ENABLE_DAILY_PLAY_COUNT": False,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": False,
            "ENABLE_PLAY_COUNT_BY_MONTH": False,
            "ENABLE_TOP_10_PLATFORMS": False,
            "ENABLE_TOP_10_USERS": False,
        }
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()
        
        assert isinstance(graphs, list)
        assert len(graphs) == 0
    
    def test_create_enabled_graphs_all_enabled(self) -> None:
        """Test creating graphs with all graph types enabled."""
        config = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": True,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": True,
            "ENABLE_TOP_10_PLATFORMS": True,
            "ENABLE_TOP_10_USERS": True,
        }
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        # All graph types are enabled, so all 6 should be created
        assert isinstance(graphs, list)
        assert len(graphs) == 6
    
    def test_create_enabled_graphs_partial_enabled(self) -> None:
        """Test creating graphs with some graph types enabled."""
        config = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": False,
            "ENABLE_TOP_10_PLATFORMS": True,
            "ENABLE_TOP_10_USERS": False,
        }
        factory = GraphFactory(config)
        graphs = factory.create_enabled_graphs()

        # Only 3 graph types are enabled (daily, hourofday, platforms)
        assert isinstance(graphs, list)
        assert len(graphs) == 3
    
    def test_create_graph_by_type_unknown_type(self) -> None:
        """Test creating graph with unknown type raises ValueError."""
        factory = GraphFactory({})
        
        with pytest.raises(ValueError, match="Unknown graph type: unknown_type"):
            factory.create_graph_by_type("unknown_type")
    
    def test_create_graph_by_type_valid_types(self) -> None:
        """Test creating graph by type with valid type names."""
        factory = GraphFactory({})

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
            assert hasattr(graph, 'generate')
            assert hasattr(graph, 'get_title')

    def test_create_graph_by_type_returns_correct_types(self) -> None:
        """Test that create_graph_by_type returns the correct graph class instances."""
        from graphs.graph_modules.daily_play_count_graph import DailyPlayCountGraph
        from graphs.graph_modules.play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
        from graphs.graph_modules.top_10_users_graph import Top10UsersGraph

        factory = GraphFactory({})

        daily_graph = factory.create_graph_by_type("daily_play_count")
        assert isinstance(daily_graph, DailyPlayCountGraph)

        dayofweek_graph = factory.create_graph_by_type("play_count_by_dayofweek")
        assert isinstance(dayofweek_graph, PlayCountByDayOfWeekGraph)

        users_graph = factory.create_graph_by_type("top_10_users")
        assert isinstance(users_graph, Top10UsersGraph)
    
    def test_get_enabled_graph_types_empty_config(self) -> None:
        """Test getting enabled graph types with empty configuration."""
        factory = GraphFactory({})
        enabled_types = factory.get_enabled_graph_types()
        
        # All types should be enabled by default (True is the default)
        expected_types = [
            "daily_play_count",
            "play_count_by_dayofweek",
            "play_count_by_hourofday",
            "play_count_by_month",
            "top_10_platforms",
            "top_10_users",
        ]
        
        assert set(enabled_types) == set(expected_types)
    
    def test_get_enabled_graph_types_all_disabled(self) -> None:
        """Test getting enabled graph types with all disabled."""
        config = {
            "ENABLE_DAILY_PLAY_COUNT": False,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": False,
            "ENABLE_PLAY_COUNT_BY_MONTH": False,
            "ENABLE_TOP_10_PLATFORMS": False,
            "ENABLE_TOP_10_USERS": False,
        }
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()
        
        assert enabled_types == []
    
    def test_get_enabled_graph_types_partial_enabled(self) -> None:
        """Test getting enabled graph types with some enabled."""
        config = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": False,
            "ENABLE_TOP_10_PLATFORMS": True,
            "ENABLE_TOP_10_USERS": False,
        }
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
        config = {
            "ENABLE_DAILY_PLAY_COUNT": 1,  # Truthy
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": 0,  # Falsy
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": "yes",  # Truthy
            "ENABLE_PLAY_COUNT_BY_MONTH": "",  # Falsy
            "ENABLE_TOP_10_PLATFORMS": None,  # Falsy
            "ENABLE_TOP_10_USERS": "false",  # Truthy (non-empty string)
        }
        factory = GraphFactory(config)
        enabled_types = factory.get_enabled_graph_types()
        
        expected_types = [
            "daily_play_count",
            "play_count_by_hourofday",
            "top_10_users",  # Non-empty string is truthy
        ]
        
        assert set(enabled_types) == set(expected_types)
    
    def test_factory_config_immutability(self) -> None:
        """Test that factory doesn't modify the original config."""
        original_config = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
        }
        config_copy = original_config.copy()
        
        factory = GraphFactory(config_copy)
        _ = factory.get_enabled_graph_types()
        _ = factory.create_enabled_graphs()
        
        # Original config should be unchanged
        assert original_config == config_copy
    
    def test_factory_extensibility(self) -> None:
        """Test that factory design supports extensibility."""
        # This test verifies the factory pattern structure supports
        # adding new graph types without modifying existing code
        
        factory = GraphFactory({})
        
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
        }
        
        # When all are enabled by default, we should get all types
        assert set(enabled_types) == expected_types
