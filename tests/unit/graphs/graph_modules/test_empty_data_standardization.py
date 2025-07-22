"""
Test module for empty data handling standardization across all Tautulli graph implementations.

This module tests Phase 2 of the DRY refactoring: standardizing empty data handling
to use the BaseGraph.handle_empty_data_with_message() method consistently.
"""

from __future__ import annotations


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
            (DailyPlayCountGraph, False),  # After refactoring: methods removed
            (PlayCountByDayOfWeekGraph, False),  # After refactoring: methods removed
            (PlayCountByHourOfDayGraph, False),  # After refactoring: methods removed
            (PlayCountByMonthGraph, False),  # After refactoring: methods removed
        ],
    )
    def test_current_empty_data_method_existence(
        self,
        graph_class: type[
            DailyPlayCountGraph
            | PlayCountByDayOfWeekGraph
            | PlayCountByHourOfDayGraph
            | PlayCountByMonthGraph
        ],
        expected_method_exists: bool,
    ) -> None:
        """Test that graphs no longer have custom empty data methods (after standardization)."""
        graph = graph_class()

        # Check if custom empty data method exists
        has_custom_method = hasattr(graph, "_handle_empty_data_case")
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
    def test_base_method_availability(
        self,
        graph_class: type[
            DailyPlayCountGraph
            | PlayCountByDayOfWeekGraph
            | PlayCountByHourOfDayGraph
            | PlayCountByMonthGraph
        ],
    ) -> None:
        """Test that all graphs have access to the base empty data handling method."""
        graph = graph_class()

        # All graphs should have access to the base method
        assert hasattr(graph, "handle_empty_data_with_message")
        assert callable(graph.handle_empty_data_with_message)

    def test_daily_play_count_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in DailyPlayCountGraph."""
        with matplotlib_cleanup():
            graph = DailyPlayCountGraph()
            _, ax = graph.setup_figure_with_styling()

            # Test current custom method
            if hasattr(graph, "_handle_empty_data_case"):
                method = getattr(graph, "_handle_empty_data_case")  # pyright: ignore[reportAny]
                if callable(method):  # pyright: ignore[reportAny]
                    # Should not raise exception
                    _ = method(ax)

            graph.cleanup()

    def test_dayofweek_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByDayOfWeekGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByDayOfWeekGraph()
            _, ax = graph.setup_figure_with_styling()

            # Test current custom method
            if hasattr(graph, "_handle_empty_data_case"):
                method = getattr(graph, "_handle_empty_data_case")  # pyright: ignore[reportAny]
                if callable(method):  # pyright: ignore[reportAny]
                    # Should not raise exception
                    _ = method(ax)

            graph.cleanup()

    def test_hourofday_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByHourOfDayGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByHourOfDayGraph()
            _, ax = graph.setup_figure_with_styling()

            # This graph already uses the base method correctly
            if hasattr(graph, "_handle_empty_data_case"):
                method = getattr(graph, "_handle_empty_data_case")  # pyright: ignore[reportAny]
                if callable(method):  # pyright: ignore[reportAny]
                    # Should not raise exception
                    _ = method(ax)

            graph.cleanup()

    def test_month_empty_data_current_behavior(self) -> None:
        """Test current empty data behavior in PlayCountByMonthGraph."""
        with matplotlib_cleanup():
            graph = PlayCountByMonthGraph()
            _, ax = graph.setup_figure_with_styling()

            # This graph has a different signature (no ax parameter)
            if hasattr(graph, "_handle_empty_data_case"):
                method = getattr(graph, "_handle_empty_data_case")  # pyright: ignore[reportAny]
                if callable(method):  # pyright: ignore[reportAny]
                    # Should not raise exception - try both signatures
                    try:
                        _ = method(ax)
                    except TypeError:
                        # If it doesn't take ax parameter, try without
                        _ = method()

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
    def test_standardized_empty_data_behavior(
        self,
        graph_class: type[
            DailyPlayCountGraph
            | PlayCountByDayOfWeekGraph
            | PlayCountByHourOfDayGraph
            | PlayCountByMonthGraph
        ],
    ) -> None:
        """Test standardized empty data behavior using base method."""
        with matplotlib_cleanup():
            graph = graph_class()
            _, ax = graph.setup_figure_with_styling()

            # Test direct usage of base method (post-standardization behavior)
            graph.handle_empty_data_with_message(
                ax, "No data available for the selected time range."
            )

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
        """Test that all classes now use base method directly (no custom wrapper methods)."""
        with matplotlib_cleanup():
            # After refactoring, all graphs should use the base method directly
            # This test verifies that the wrapper methods have been eliminated
            
            graphs = [
                DailyPlayCountGraph(),
                PlayCountByDayOfWeekGraph(), 
                PlayCountByHourOfDayGraph(),
                PlayCountByMonthGraph(),
            ]
            
            for graph in graphs:
                # After standardization, custom empty data methods should not exist
                assert not hasattr(graph, "_handle_empty_data_case"), (
                    f"{graph.__class__.__name__} still has custom empty data method"
                )
                
                # All graphs should have access to the base method
                assert hasattr(graph, "handle_empty_data_with_message"), (
                    f"{graph.__class__.__name__} missing base empty data method"
                )

    def test_no_duplicate_empty_data_logic_after_standardization(self) -> None:
        """Test that there's no duplicate empty data logic after standardization."""
        graphs = [
            DailyPlayCountGraph(),
            PlayCountByDayOfWeekGraph(),
            PlayCountByHourOfDayGraph(),
            PlayCountByMonthGraph(),
        ]

        for graph in graphs:
            # After standardization, custom methods should be eliminated entirely
            assert not hasattr(graph, "_handle_empty_data_case"), (
                f"{graph.__class__.__name__} still has duplicate empty data logic"
            )
            
            # All graphs should use the base method directly
            assert hasattr(graph, "handle_empty_data_with_message"), (
                f"{graph.__class__.__name__} missing base empty data method"
            )
            base_method = graph.handle_empty_data_with_message
            assert callable(base_method), (
                f"{graph.__class__.__name__} base method not callable"
            )
