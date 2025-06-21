"""
Graph factory for TGraph Bot.

This module provides a factory class that creates instances of specific
graph classes based on the enabled settings in the configuration.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, cast
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
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class GraphFactory:
    """Factory class for creating graph instances based on configuration."""

    def __init__(self, config: "TGraphBotConfig | dict[str, object]") -> None:
        """
        Initialize the graph factory.

        Args:
            config: Configuration object containing graph settings
        """
        self.config: "TGraphBotConfig | dict[str, object]" = config
        
    def create_enabled_graphs(self) -> list[BaseGraph]:
        """
        Create instances of all enabled graph types.

        Returns:
            List of graph instances for enabled graph types
        """
        graphs: list[BaseGraph] = []

        # Check each graph type and create if enabled
        def get_config_value(key: str, default: bool = True) -> bool:
            # Handle both dict and TGraphBotConfig objects
            if isinstance(self.config, dict):
                return bool(self.config.get(key, default))
            else:
                # Use direct attribute access for TGraphBotConfig objects
                if key == 'ENABLE_DAILY_PLAY_COUNT':
                    return self.config.ENABLE_DAILY_PLAY_COUNT
                elif key == 'ENABLE_PLAY_COUNT_BY_DAYOFWEEK':
                    return self.config.ENABLE_PLAY_COUNT_BY_DAYOFWEEK
                elif key == 'ENABLE_PLAY_COUNT_BY_HOUROFDAY':
                    return self.config.ENABLE_PLAY_COUNT_BY_HOUROFDAY
                elif key == 'ENABLE_PLAY_COUNT_BY_MONTH':
                    return self.config.ENABLE_PLAY_COUNT_BY_MONTH
                elif key == 'ENABLE_TOP_10_PLATFORMS':
                    return self.config.ENABLE_TOP_10_PLATFORMS
                elif key == 'ENABLE_TOP_10_USERS':
                    return self.config.ENABLE_TOP_10_USERS
                elif key == 'ENABLE_SAMPLE_GRAPH':
                    # Sample graph is not in the main config schema, default to False
                    return False
                return default

        if get_config_value('ENABLE_DAILY_PLAY_COUNT'):
            logger.debug("Creating daily play count graph")
            graphs.append(DailyPlayCountGraph(config=self.config))

        if get_config_value('ENABLE_PLAY_COUNT_BY_DAYOFWEEK'):
            logger.debug("Creating play count by day of week graph")
            graphs.append(PlayCountByDayOfWeekGraph(config=self.config))

        if get_config_value('ENABLE_PLAY_COUNT_BY_HOUROFDAY'):
            logger.debug("Creating play count by hour of day graph")
            graphs.append(PlayCountByHourOfDayGraph(config=self.config))

        if get_config_value('ENABLE_PLAY_COUNT_BY_MONTH'):
            logger.debug("Creating play count by month graph")
            graphs.append(PlayCountByMonthGraph(config=self.config))

        if get_config_value('ENABLE_TOP_10_PLATFORMS'):
            logger.debug("Creating top 10 platforms graph")
            graphs.append(Top10PlatformsGraph(config=self.config))

        if get_config_value('ENABLE_TOP_10_USERS'):
            logger.debug("Creating top 10 users graph")
            graphs.append(Top10UsersGraph(config=self.config))

        # Sample graph for demonstration (disabled by default)
        if get_config_value('ENABLE_SAMPLE_GRAPH', default=False):
            logger.debug("Creating sample graph")
            graphs.append(SampleGraph(config=self.config))

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
        return graph_class(config=self.config)
        
    def get_enabled_graph_types(self) -> list[str]:
        """
        Get a list of enabled graph type names.

        Returns:
            List of enabled graph type names
        """
        enabled_types: list[str] = []

        def get_config_value(key: str, default: bool = True) -> bool:
            # Handle both dict and TGraphBotConfig objects
            if isinstance(self.config, dict):
                return bool(self.config.get(key, default))
            else:
                # Use direct attribute access for TGraphBotConfig objects
                if key == 'ENABLE_DAILY_PLAY_COUNT':
                    return self.config.ENABLE_DAILY_PLAY_COUNT
                elif key == 'ENABLE_PLAY_COUNT_BY_DAYOFWEEK':
                    return self.config.ENABLE_PLAY_COUNT_BY_DAYOFWEEK
                elif key == 'ENABLE_PLAY_COUNT_BY_HOUROFDAY':
                    return self.config.ENABLE_PLAY_COUNT_BY_HOUROFDAY
                elif key == 'ENABLE_PLAY_COUNT_BY_MONTH':
                    return self.config.ENABLE_PLAY_COUNT_BY_MONTH
                elif key == 'ENABLE_TOP_10_PLATFORMS':
                    return self.config.ENABLE_TOP_10_PLATFORMS
                elif key == 'ENABLE_TOP_10_USERS':
                    return self.config.ENABLE_TOP_10_USERS
                elif key == 'ENABLE_SAMPLE_GRAPH':
                    # Sample graph is not in the main config schema, default to False
                    return False
                return default

        # Check each graph type directly from config attributes
        if get_config_value('ENABLE_DAILY_PLAY_COUNT'):
            enabled_types.append("daily_play_count")

        if get_config_value('ENABLE_PLAY_COUNT_BY_DAYOFWEEK'):
            enabled_types.append("play_count_by_dayofweek")

        if get_config_value('ENABLE_PLAY_COUNT_BY_HOUROFDAY'):
            enabled_types.append("play_count_by_hourofday")

        if get_config_value('ENABLE_PLAY_COUNT_BY_MONTH'):
            enabled_types.append("play_count_by_month")

        if get_config_value('ENABLE_TOP_10_PLATFORMS'):
            enabled_types.append("top_10_platforms")

        if get_config_value('ENABLE_TOP_10_USERS'):
            enabled_types.append("top_10_users")

        # Sample graph (disabled by default)
        if get_config_value('ENABLE_SAMPLE_GRAPH', default=False):
            enabled_types.append("sample_graph")

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

    def generate_all_graphs(self, data: dict[str, object]) -> list[str]:
        """
        Generate all enabled graphs with proper resource management.

        This method creates all enabled graphs in sequence while ensuring
        proper cleanup of matplotlib resources to prevent memory leaks.

        Args:
            data: Dictionary containing the data needed for graph generation
                 Expected structure: {"play_history": {...}, "time_range_days": int}

        Returns:
            List of paths to generated graph files

        Raises:
            Exception: If any graph generation fails
        """
        return self.generate_graphs_with_exclusions(data, exclude_types=[])

    def generate_graphs_with_exclusions(self, data: dict[str, object], exclude_types: list[str]) -> list[str]:
        """
        Generate enabled graphs with exclusions for specific graph types.

        This method creates enabled graphs while excluding specified types,
        useful for context-specific graph generation (e.g., personal stats).

        Args:
            data: Dictionary containing the data needed for graph generation
                 Expected structure: {"play_history": {...}, "time_range_days": int}
            exclude_types: List of graph type names to exclude (e.g., ["top_10_users"])

        Returns:
            List of paths to generated graph files

        Raises:
            Exception: If any graph generation fails
        """
        graphs = self.create_enabled_graphs()
        
        # Filter out excluded graph types
        if exclude_types:
            excluded_classes: list[type[BaseGraph]] = []
            for exclude_type in exclude_types:
                if exclude_type == "top_10_users":
                    excluded_classes.append(Top10UsersGraph)
                elif exclude_type == "top_10_platforms":
                    excluded_classes.append(Top10PlatformsGraph)
                elif exclude_type == "daily_play_count":
                    excluded_classes.append(DailyPlayCountGraph)
                elif exclude_type == "play_count_by_dayofweek":
                    excluded_classes.append(PlayCountByDayOfWeekGraph)
                elif exclude_type == "play_count_by_hourofday":
                    excluded_classes.append(PlayCountByHourOfDayGraph)
                elif exclude_type == "play_count_by_month":
                    excluded_classes.append(PlayCountByMonthGraph)
                elif exclude_type == "sample_graph":
                    excluded_classes.append(SampleGraph)
            
            # Filter graphs list
            original_count = len(graphs)
            graphs = [graph for graph in graphs if not any(isinstance(graph, cls) for cls in excluded_classes)]
            filtered_count = len(graphs)
            
            if original_count > filtered_count:
                logger.info(f"Excluded {original_count - filtered_count} graph(s) from generation: {exclude_types}")

        generated_paths: list[str] = []

        logger.info(f"Starting generation of {len(graphs)} enabled graphs")

        # Pass the full data structure to all graphs - let each graph extract what it needs
        # GraphManager provides: {"play_history": {...}, "monthly_plays": {...}, "time_range_days": int, "time_range_months": int}
        # Different graphs can extract different parts of this data structure
        if not isinstance(data, dict):
            logger.error("Invalid data structure - expected dictionary")
            return generated_paths

        # Type cast to the expected mapping type for type checker
        full_data = cast(Mapping[str, object], data)

        logger.debug(f"Passing full data structure with keys: {list(full_data.keys())}")

        for graph in graphs:
            try:
                # Use context manager for automatic cleanup
                with graph:
                    # Pass the full data structure - each graph will extract what it needs
                    output_path = graph.generate(full_data)
                    generated_paths.append(output_path)
                    logger.debug(f"Generated {graph.__class__.__name__}: {output_path}")

            except Exception as e:
                logger.error(f"Failed to generate {graph.__class__.__name__}: {e}")
                # Continue with other graphs even if one fails
                continue

        # Additional cleanup to ensure no matplotlib state remains
        BaseGraph.cleanup_all_figures()

        logger.info(f"Successfully generated {len(generated_paths)} graphs")
        return generated_paths

    def cleanup_all_graph_resources(self) -> None:
        """
        Perform comprehensive cleanup of all graph-related resources.

        This method ensures all matplotlib figures are closed and
        any remaining graph resources are properly released.
        """
        BaseGraph.cleanup_all_figures()
        logger.debug("Performed comprehensive graph resource cleanup")
