"""Graph generator protocol definition.

This module defines the GraphGenerator protocol that all graph implementations
must follow. This provides structural subtyping for graph generation.

Requirements: 19.5 - Small composable Protocols
"""

from typing import Protocol

from matplotlib.figure import Figure

from tgraph_bot.config.models import GraphAppearanceConfig, GraphConfig
from tgraph_bot.graphs.data import StreamRecord


class GraphGenerator(Protocol):
    """Protocol for graph generation implementations.

    All graph generators must implement this protocol. The protocol uses
    structural subtyping (duck typing) - any class that implements these
    methods satisfies the protocol without explicit inheritance.

    Requirements:
        - 19.5: Define small composable Protocols with 1-3 methods
    """

    def generate(
        self,
        data: list[StreamRecord],
        *,
        config: GraphConfig,
        appearance: GraphAppearanceConfig,
    ) -> Figure:
        """Generate matplotlib figure from stream data.

        Args:
            data: List of stream records to visualize
            config: Graph-specific configuration (enabled, media type separation, etc.)
            appearance: Visual styling configuration (colors, dimensions, seaborn, etc.)

        Returns:
            Matplotlib Figure object with the generated graph

        Requirements:
            - 5.1: Generate graph from data with configuration
            - 5.2: Apply configured dimensions and DPI
            - 5.3: Support media type separation
            - 5.4: Apply palette colors when specified
        """
        ...
