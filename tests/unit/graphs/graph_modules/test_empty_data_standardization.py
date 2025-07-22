"""
Test module for empty data handling standardization across all Tautulli graph implementations.

This module tests Phase 2 of the DRY refactoring: standardizing empty data handling
to use the BaseGraph.handle_empty_data_with_message() method consistently.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.daily_play_count_graph import (
    DailyPlayCountGraph,
)
from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_dayofweek_graph import (
    PlayCountByDayOfWeekGraph,
)
from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_hourofday_graph import (
    PlayCountByHourOfDayGraph,
)
from src.tgraph_bot.graphs.graph_modules.implementations.tautulli.play_count_by_month_graph import (
    PlayCountByMonthGraph,
)
from tests.utils.graph_helpers import matplotlib_cleanup


class TestEmptyDataStandardization:
    """Test cases for empty data handling standardization across graph implementations."""

    @pytest.mark.parametrize(
        "graph_class,expected_method_exists",
        [
            (DailyPlayCountGraph, True),
            (PlayCountByDayOfWeekGraph, True),
            (PlayCountByHourOfDayGraph, True),
            (PlayCountByMonthGraph, True),
        ],
    )
    def test_current_empty_data_method_existence(
        self, graph_class: type, expected_method_exists: bool
    ) -> None:
        """Test that graphs currently have custom empty data methods (before standardization)."""
        graph = graph_class()
        
        # Check if custom empty data method exists
        has_custom_method = hasattr(graph, '_handle_empty_data_case')
        assert has_custom_method == expected_method_exists

    @pytest.mark.parametrize(
        "graph_class",
        [
            DailyPlayCountGraph,
            PlayCountByDayOfWeekGraph,
            PlayCountByHourOfDayGraph,
            PlayCountByMonthGraph,
        ],
    )
    def test_base_method_availability(self, graph_class: type) -> None:
        """Test that all graphs have access to the base empty data handling method."""
        graph = graph_class()
        
        # All graphs should have access to the base method
        assert hasattr(graph, 'handle_empty_data_with_message')
        assert callable(graph.handle_empty_data_with_message)

    def test_daily_play_count_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in DailyPlayCountGraph."""
        with matplotlib_cleanup():
            graph = DailyPlayCountGraph()
            _, ax = graph.setup_figure_with_styling()
            
            # Test current custom method
            if hasattr(graph, '_handle_empty_data_case'):
                # Should not raise exception
                graph._handle_empty_data_case(ax)  # pyright: ignore[reportPrivateUsage]
            
            graph.cleanup()

    def test_dayofweek_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByDayOfWeekGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByDayOfWeekGraph()
            _, ax = graph.setup_figure_with_styling()
            
            # Test current custom method
            if hasattr(graph, '_handle_empty_data_case'):
                # Should not raise exception
                graph._handle_empty_data_case(ax)  # pyright: ignore[reportPrivateUsage]
            
            graph.cleanup()

    def test_hourofday_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByHourOfDayGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            _, ax = graph.setup_figure_with_styling()
            
            # This graph already uses the base method correctly
            if hasattr(graph, '_handle_empty_data_case'):
                # Should not raise exception
                graph._handle_empty_data_case(ax)  # pyright: ignore[reportPrivateUsage]
            
            graph.cleanup()

    def test_month_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByMonthGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByMonthGraph()
            _ = graph.setup_figure_with_styling()
            
            # This graph has a different signature (no ax parameter)
            if hasattr(graph, '_handle_empty_data_case'):
                # Should not raise exception
                graph._handle_empty_data_case()  # pyright: ignore[reportPrivateUsage]
            
            graph.cleanup()

    @pytest.mark.parametrize(
        "graph_class",
        [
            DailyPlayCountGraph,
            PlayCountByDayOfWeekGraph,
            PlayCountByHourOfDayGraph,
            PlayCountByMonthGraph,
        ],
    )
    def test_standardized_empty_data_behavior(self, graph_class: type) -> None:
        """Test standardized empty data behavior using base method."""
        with matplotlib_cleanup():
            graph = graph_class()
            _, ax = graph.setup_figure_with_styling()
            
            # Test direct usage of base method (post-standardization behavior)
            graph.handle_empty_data_with_message(ax, "No data available for the selected time range.")
            
            # Test with default message
            graph.handle_empty_data_with_message(ax)
            
            graph.cleanup()

    def test_empty_data_message_consistency(self) -> None:
        """Test that empty data messages are consistent across implementations."""
        expected_message = "No data available for the selected time range."
        
        with matplotlib_cleanup():
            graphs = [
                DailyPlayCountGraph(),
                PlayCountByDayOfWeekGraph(),
                PlayCountByHourOfDayGraph(),
                PlayCountByMonthGraph(),
            ]
            
            for graph in graphs:
                _, ax = graph.setup_figure_with_styling()
                
                # Test that base method works with consistent message
                graph.handle_empty_data_with_message(ax, expected_message)
                
                graph.cleanup()

    def test_custom_methods_delegate_to_base_after_standardization(self) -> None:
        """Test that custom methods delegate to base method after standardization."""
        with matplotlib_cleanup():
            # Test graphs that should delegate to base method
            test_cases = [
                (DailyPlayCountGraph, True),  # Takes ax parameter
                (PlayCountByDayOfWeekGraph, True),  # Takes ax parameter
                (PlayCountByHourOfDayGraph, True),  # Takes ax parameter
                (PlayCountByMonthGraph, False),  # Different signature
            ]
            
            for graph_class, takes_ax_param in test_cases:
                graph = graph_class()
                
                if hasattr(graph, '_handle_empty_data_case'):
                    _, ax = graph.setup_figure_with_styling()
                    
                    with patch.object(graph, 'handle_empty_data_with_message') as mock_base:
                        if takes_ax_param:
                            graph._handle_empty_data_case(ax)  # pyright: ignore[reportPrivateUsage]
                        else:
                            graph._handle_empty_data_case()  # pyright: ignore[reportPrivateUsage]
                        
                        # Should have called the base method
                        mock_base.assert_called()
                    
                    graph.cleanup()

    def test_no_duplicate_empty_data_logic_after_standardization(self) -> None:
        """Test that there's no duplicate empty data logic after standardization."""
        graphs = [
            DailyPlayCountGraph(),
            PlayCountByDayOfWeekGraph(),
            PlayCountByHourOfDayGraph(),
            PlayCountByMonthGraph(),
        ]
        
        for graph in graphs:
            # After standardization, custom methods should be simple delegations
            # or eliminated entirely
            if hasattr(graph, '_handle_empty_data_case'):
                import inspect
                method = getattr(graph, '_handle_empty_data_case')
                source = inspect.getsource(method)
                
                # Should contain a call to the base method
                assert 'handle_empty_data_with_message' in source or 'EmptyDataHandler' in source
                
                # Should not contain complex logic (after standardization)
                lines = [line.strip() for line in source.split('\n') if line.strip()]
                # Filter out comments and docstrings
                code_lines = [
                    line for line in lines 
                    if not line.startswith('#') 
                    and not line.startswith('"""') 
                    and not line.startswith("'''")
                    and 'def ' not in line
                    and 'Args:' not in line
                    and 'Returns:' not in line
                ]
                
                # After standardization, should be simple delegation
                # Allow for some flexibility in implementation
                assert len(code_lines) <= 10  # Should be relatively simple