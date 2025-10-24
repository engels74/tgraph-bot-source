"""Graph factory for creating graph generators.

This module provides the GraphFactory class for creating appropriate graph
generator instances based on graph type.

Requirements: 5.1, 5.6
"""

from dataclasses import dataclass

from tgraph_bot.graphs.protocol import GraphGenerator


@dataclass(slots=True)
class GraphFactory:
    """Factory for creating graph generators.

    Creates appropriate graph generator instances based on graph type.
    Currently returns placeholder implementations as individual graph
    types will be implemented in tasks 17-20.

    Uses dataclass with slots for memory efficiency.

    Requirements:
        - 5.1: Create graph generators for all enabled graph types
        - 5.6: Support all 12 graph types
    """

    def create_generator(self, graph_type: str) -> GraphGenerator:
        """Create appropriate graph generator for type.

        Args:
            graph_type: Type of graph to generate (e.g., "daily_play_count",
                "play_count_by_day_of_week", "top_platforms", etc.)

        Returns:
            GraphGenerator instance for the specified type

        Raises:
            ValueError: If graph_type is not recognized

        Requirements:
            - 5.1: Create generators for all enabled graph types
            - 5.6: Support all graph types (daily play count, day of week,
                hour of day, top platforms, top users, by month, by stream type,
                concurrent streams, source resolution, stream resolution,
                platform and stream type, user and stream type)
        """
        # Map of valid graph types (for now, raise NotImplementedError)
        # Individual graph implementations will be added in tasks 17-20
        valid_types = {
            "daily_play_count",
            "play_count_by_day_of_week",
            "play_count_by_hour_of_day",
            "top_platforms",
            "top_users",
            "play_count_by_month",
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        }

        if graph_type not in valid_types:
            raise ValueError(
                f"Unknown graph type: {graph_type}. "
                f"Valid types are: {', '.join(sorted(valid_types))}"
            )

        # Individual graph generators will be implemented in tasks 17-20
        raise NotImplementedError(
            f"Graph generator for '{graph_type}' will be implemented in tasks 17-20"
        )
