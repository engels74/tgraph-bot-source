"""
Graph type registry for TGraph Bot.

This module provides a centralized registry for all graph types, eliminating
code duplication in GraphFactory and providing a single source of truth for
graph type mappings, enable keys, and class relationships.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, NamedTuple, final

if TYPE_CHECKING:
    from .base_graph import BaseGraph

logger = logging.getLogger(__name__)


class GraphTypeInfo(NamedTuple):
    """Information about a graph type."""

    type_name: str
    graph_class: type[BaseGraph]
    default_enabled: bool
    description: str


@final
class GraphTypeRegistry:
    """
    Centralized registry for all graph types.

    This class provides a single source of truth for graph type mappings,
    eliminating the need for duplicated mapping logic throughout the codebase.
    """

    def __init__(self) -> None:
        """Initialize the graph type registry."""
        self._registry: dict[str, GraphTypeInfo] = {}
        self._class_to_type: dict[type[BaseGraph], str] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized with all graph types."""
        if self._initialized:
            return

        # Import graph classes here to avoid circular imports
        from ..implementations.sample_graph import SampleGraph
        from ..implementations.tautulli.daily_play_count_graph import (
            DailyPlayCountGraph,
        )
        from ..implementations.tautulli.play_count_by_dayofweek_graph import (
            PlayCountByDayOfWeekGraph,
        )
        from ..implementations.tautulli.play_count_by_hourofday_graph import (
            PlayCountByHourOfDayGraph,
        )
        from ..implementations.tautulli.play_count_by_month_graph import (
            PlayCountByMonthGraph,
        )
        from ..implementations.tautulli.top_10_platforms_graph import (
            Top10PlatformsGraph,
        )
        from ..implementations.tautulli.top_10_users_graph import Top10UsersGraph

        # Register all graph types
        self._register_graph_type(
            type_name="daily_play_count",
            graph_class=DailyPlayCountGraph,
            default_enabled=True,
            description="Daily play count graph showing plays over time",
        )

        self._register_graph_type(
            type_name="play_count_by_dayofweek",
            graph_class=PlayCountByDayOfWeekGraph,
            default_enabled=True,
            description="Play count by day of week graph",
        )

        self._register_graph_type(
            type_name="play_count_by_hourofday",
            graph_class=PlayCountByHourOfDayGraph,
            default_enabled=True,
            description="Play count by hour of day graph",
        )

        self._register_graph_type(
            type_name="play_count_by_month",
            graph_class=PlayCountByMonthGraph,
            default_enabled=True,
            description="Play count by month graph",
        )

        self._register_graph_type(
            type_name="top_10_platforms",
            graph_class=Top10PlatformsGraph,
            default_enabled=True,
            description="Top 10 platforms graph",
        )

        self._register_graph_type(
            type_name="top_10_users",
            graph_class=Top10UsersGraph,
            default_enabled=True,
            description="Top 10 users graph",
        )

        self._register_graph_type(
            type_name="sample_graph",
            graph_class=SampleGraph,
            default_enabled=False,
            description="Sample graph for demonstration purposes",
        )

        self._initialized = True
        logger.debug(
            f"Graph type registry initialized with {len(self._registry)} graph types"
        )

    def _register_graph_type(
        self,
        type_name: str,
        graph_class: type[BaseGraph],
        default_enabled: bool,
        description: str,
    ) -> None:
        """
        Register a graph type in the registry.

        Args:
            type_name: The graph type name (e.g., "daily_play_count")
            graph_class: The graph class
            default_enabled: Whether this graph type is enabled by default
            description: Human-readable description of the graph type
        """
        info = GraphTypeInfo(
            type_name=type_name,
            graph_class=graph_class,
            default_enabled=default_enabled,
            description=description,
        )

        self._registry[type_name] = info
        self._class_to_type[graph_class] = type_name

    def get_graph_class(self, type_name: str) -> type[BaseGraph]:
        """
        Get the graph class for a given type name.

        Args:
            type_name: The graph type name

        Returns:
            The graph class

        Raises:
            ValueError: If graph type is not registered
        """
        self._ensure_initialized()

        if type_name not in self._registry:
            raise ValueError(f"Unknown graph type: {type_name}")

        return self._registry[type_name].graph_class


    def get_type_name_from_class(self, graph_class: type[BaseGraph]) -> str:
        """
        Get the type name for a given graph class.

        Args:
            graph_class: The graph class

        Returns:
            The graph type name

        Raises:
            ValueError: If graph class is not registered
        """
        self._ensure_initialized()

        if graph_class not in self._class_to_type:
            raise ValueError(f"Unknown graph class: {graph_class}")

        return self._class_to_type[graph_class]

    def get_default_enabled(self, type_name: str) -> bool:
        """
        Get the default enabled status for a given type name.

        Args:
            type_name: The graph type name

        Returns:
            True if enabled by default, False otherwise

        Raises:
            ValueError: If graph type is not registered
        """
        self._ensure_initialized()

        if type_name not in self._registry:
            raise ValueError(f"Unknown graph type: {type_name}")

        return self._registry[type_name].default_enabled

    def get_all_type_names(self) -> list[str]:
        """
        Get all registered graph type names.

        Returns:
            List of all graph type names
        """
        self._ensure_initialized()
        return list(self._registry.keys())


    def get_type_info(self, type_name: str) -> GraphTypeInfo:
        """
        Get complete information about a graph type.

        Args:
            type_name: The graph type name

        Returns:
            GraphTypeInfo containing all information about the type

        Raises:
            ValueError: If graph type is not registered
        """
        self._ensure_initialized()

        if type_name not in self._registry:
            raise ValueError(f"Unknown graph type: {type_name}")

        return self._registry[type_name]

    def get_all_type_info(self) -> Mapping[str, GraphTypeInfo]:
        """
        Get information about all registered graph types.

        Returns:
            Mapping of type names to GraphTypeInfo
        """
        self._ensure_initialized()
        return dict(self._registry)

    def is_valid_type(self, type_name: str) -> bool:
        """
        Check if a graph type name is valid/registered.

        Args:
            type_name: The graph type name to check

        Returns:
            True if the type is registered, False otherwise
        """
        self._ensure_initialized()
        return type_name in self._registry

    def get_classes_for_types(self, type_names: list[str]) -> list[type[BaseGraph]]:
        """
        Get graph classes for a list of type names.

        Args:
            type_names: List of graph type names

        Returns:
            List of corresponding graph classes

        Raises:
            ValueError: If any graph type is not registered
        """
        self._ensure_initialized()

        classes: list[type[BaseGraph]] = []
        for type_name in type_names:
            if type_name not in self._registry:
                raise ValueError(f"Unknown graph type: {type_name}")
            classes.append(self._registry[type_name].graph_class)

        return classes


# Global registry instance
_graph_type_registry: GraphTypeRegistry | None = None


def get_graph_type_registry() -> GraphTypeRegistry:
    """
    Get the global graph type registry instance.

    Returns:
        The global GraphTypeRegistry instance
    """
    global _graph_type_registry
    if _graph_type_registry is None:
        _graph_type_registry = GraphTypeRegistry()
    return _graph_type_registry
