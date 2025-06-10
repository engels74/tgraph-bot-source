"""
Graph factory for TGraph Bot.

This module provides a factory class that creates instances of specific
graph classes based on the enabled settings in the configuration.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Mapping

from .base_graph import BaseGraph
from .utils import cleanup_old_files, ensure_graph_directory
from .daily_play_count_graph import DailyPlayCountGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .play_count_by_month_graph import PlayCountByMonthGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph
from .sample_graph import SampleGraph

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class GraphFactory:
    """Factory class for creating graph instances based on configuration."""
    
    def __init__(self, config: Mapping[str, bool | str | int | None]) -> None:
        """
        Initialize the graph factory.

        Args:
            config: Configuration dictionary containing graph settings
        """
        self.config: Mapping[str, bool | str | int | None] = config
        
    def create_enabled_graphs(self) -> list[BaseGraph]:
        """
        Create instances of all enabled graph types.

        Returns:
            List of graph instances for enabled graph types
        """
        graphs: list[BaseGraph] = []

        # Check each graph type and create if enabled
        if self.config.get("ENABLE_DAILY_PLAY_COUNT", True):
            logger.debug("Creating daily play count graph")
            graphs.append(DailyPlayCountGraph())

        if self.config.get("ENABLE_PLAY_COUNT_BY_DAYOFWEEK", True):
            logger.debug("Creating play count by day of week graph")
            graphs.append(PlayCountByDayOfWeekGraph())

        if self.config.get("ENABLE_PLAY_COUNT_BY_HOUROFDAY", True):
            logger.debug("Creating play count by hour of day graph")
            graphs.append(PlayCountByHourOfDayGraph())

        if self.config.get("ENABLE_PLAY_COUNT_BY_MONTH", True):
            logger.debug("Creating play count by month graph")
            graphs.append(PlayCountByMonthGraph())

        if self.config.get("ENABLE_TOP_10_PLATFORMS", True):
            logger.debug("Creating top 10 platforms graph")
            graphs.append(Top10PlatformsGraph())

        if self.config.get("ENABLE_TOP_10_USERS", True):
            logger.debug("Creating top 10 users graph")
            graphs.append(Top10UsersGraph())

        # Sample graph for demonstration (disabled by default)
        if self.config.get("ENABLE_SAMPLE_GRAPH", False):
            logger.debug("Creating sample graph")
            graphs.append(SampleGraph())

        logger.info(f"Created {len(graphs)} enabled graph instances")
        return graphs
        
    def create_graph_by_type(self, graph_type: str) -> BaseGraph:
        """
        Create a specific graph instance by type name.

        Args:
            graph_type: The type of graph to create

        Returns:
            Graph instance of the specified type

        Raises:
            ValueError: If graph type is not recognized
        """
        graph_type_map = {
            "daily_play_count": DailyPlayCountGraph,
            "play_count_by_dayofweek": PlayCountByDayOfWeekGraph,
            "play_count_by_hourofday": PlayCountByHourOfDayGraph,
            "play_count_by_month": PlayCountByMonthGraph,
            "top_10_platforms": Top10PlatformsGraph,
            "top_10_users": Top10UsersGraph,
            "sample_graph": SampleGraph,
        }

        graph_class = graph_type_map.get(graph_type)
        if graph_class is None:
            raise ValueError(f"Unknown graph type: {graph_type}")

        logger.debug(f"Creating graph of type: {graph_type}")
        return graph_class()
        
    def get_enabled_graph_types(self) -> list[str]:
        """
        Get a list of enabled graph type names.

        Returns:
            List of enabled graph type names
        """
        enabled_types: list[str] = []

        type_config_map: dict[str, str] = {
            "daily_play_count": "ENABLE_DAILY_PLAY_COUNT",
            "play_count_by_dayofweek": "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "play_count_by_hourofday": "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "play_count_by_month": "ENABLE_PLAY_COUNT_BY_MONTH",
            "top_10_platforms": "ENABLE_TOP_10_PLATFORMS",
            "top_10_users": "ENABLE_TOP_10_USERS",
            "sample_graph": "ENABLE_SAMPLE_GRAPH",
        }

        for graph_type, config_key in type_config_map.items():
            if self.config.get(config_key, True):
                enabled_types.append(graph_type)

        return enabled_types

    def setup_graph_environment(self, base_path: str = "graphs") -> Path:
        """
        Setup the graph environment by ensuring directories exist.

        Args:
            base_path: Base path for graph storage

        Returns:
            Path object for the graph directory
        """
        return ensure_graph_directory(base_path)

    def cleanup_old_graphs(self, directory: Path | None = None, keep_days: int = 7) -> int:
        """
        Clean up old graph files from the output directory.

        Args:
            directory: Directory to clean up (defaults to graph directory)
            keep_days: Number of days to keep files

        Returns:
            Number of files deleted
        """
        if directory is None:
            directory = ensure_graph_directory()

        return cleanup_old_files(directory, keep_days)
