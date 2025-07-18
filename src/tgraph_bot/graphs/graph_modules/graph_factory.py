"""
Graph factory for TGraph Bot.

This module provides a factory class that creates instances of specific
graph classes based on the enabled settings in the configuration.
"""

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

from .base_graph import BaseGraph
from .config_accessor import ConfigAccessor
from .graph_type_registry import GraphTypeRegistry, get_graph_type_registry
from .utils import cleanup_old_files, ensure_graph_directory

if TYPE_CHECKING:
    from ...config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class GraphDimensions(TypedDict):
    """Type definition for graph dimensions dictionary."""

    width: int
    height: int
    dpi: int


class GraphFactory:
    """Factory class for creating graph instances based on configuration."""

    def __init__(self, config: "TGraphBotConfig | dict[str, object]") -> None:
        """
        Initialize the graph factory.

        Args:
            config: Configuration object containing graph settings
        """
        self.config: "TGraphBotConfig | dict[str, object]" = config
        self._config_accessor: ConfigAccessor = ConfigAccessor(config)
        self._graph_registry: GraphTypeRegistry = get_graph_type_registry()

    def _get_graph_dimensions(self) -> GraphDimensions:
        """
        Extract graph dimensions from configuration.

        Returns:
            Dictionary containing width, height, and dpi values
        """
        dimensions = self._config_accessor.get_graph_dimensions()
        return GraphDimensions(
            width=dimensions["width"],
            height=dimensions["height"],
            dpi=dimensions["dpi"],
        )

    def create_enabled_graphs(self) -> list[BaseGraph]:
        """
        Create instances of all enabled graph types.

        Returns:
            List of graph instances for enabled graph types
        """
        graphs: list[BaseGraph] = []

        # Get dimension parameters from config
        dimensions = self._get_graph_dimensions()

        # Get all graph types and check which ones are enabled
        for type_name in self._graph_registry.get_all_type_names():
            type_info = self._graph_registry.get_type_info(type_name)

            # Check if this graph type is enabled
            is_enabled = self._config_accessor.get_graph_enable_value(
                type_info.enable_key, default=type_info.default_enabled
            )

            if is_enabled:
                logger.debug(f"Creating {type_name} graph")
                graph_class = type_info.graph_class
                graph_instance = graph_class(config=self.config, **dimensions)
                graphs.append(graph_instance)

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
        # Use the registry to get the graph class
        graph_class = self._graph_registry.get_graph_class(graph_type)

        # Get dimension parameters from config
        dimensions = self._get_graph_dimensions()

        logger.debug(f"Creating graph of type: {graph_type}")
        return graph_class(config=self.config, **dimensions)

    def get_enabled_graph_types(self) -> list[str]:
        """
        Get a list of enabled graph type names.

        Returns:
            List of enabled graph type names
        """
        enabled_types: list[str] = []

        # Check each graph type using the registry
        for type_name in self._graph_registry.get_all_type_names():
            type_info = self._graph_registry.get_type_info(type_name)

            # Check if this graph type is enabled
            is_enabled = self._config_accessor.get_graph_enable_value(
                type_info.enable_key, default=type_info.default_enabled
            )

            if is_enabled:
                enabled_types.append(type_name)

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

    def cleanup_old_graphs(
        self, directory: Path | None = None, keep_days: int = 7
    ) -> int:
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

    def generate_graphs_with_exclusions(
        self, data: dict[str, object], exclude_types: list[str]
    ) -> list[str]:
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
            # Get excluded classes using the registry
            excluded_classes = self._graph_registry.get_classes_for_types(exclude_types)

            # Filter graphs list
            original_count = len(graphs)
            graphs = [
                graph
                for graph in graphs
                if not any(isinstance(graph, cls) for cls in excluded_classes)
            ]
            filtered_count = len(graphs)

            if original_count > filtered_count:
                logger.info(
                    f"Excluded {original_count - filtered_count} graph(s) from generation: {exclude_types}"
                )

        generated_paths: list[str] = []

        logger.info(f"Starting generation of {len(graphs)} enabled graphs")

        # Pass the full data structure to all graphs - let each graph extract what it needs
        # GraphManager provides: {"play_history": {...}, "monthly_plays": {...}, "time_range_days": int, "time_range_months": int}
        # Different graphs can extract different parts of this data structure

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
