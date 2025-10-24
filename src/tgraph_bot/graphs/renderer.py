"""Graph renderer orchestrator for generating all enabled graphs.

This module provides the GraphRenderer class that orchestrates the generation
of all enabled graphs with proper seaborn theme application.

Requirements: 5.1, 5.2, 5.5, 6.6, 6.7
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tgraph_bot.config.models import GraphConfig, GraphsConfig
from tgraph_bot.graphs.data import GraphMetadata, StreamRecord
from tgraph_bot.graphs.factory import GraphFactory
from tgraph_bot.graphs.styling import GraphStyling


@dataclass(slots=True)
class GraphRenderer:
    """Orchestrates graph generation with seaborn theme application.

    This class manages the complete graph rendering pipeline:
    1. Apply seaborn theme globally
    2. For each enabled graph type:
        a. Create generator via factory
        b. Generate figure
        c. Save to disk
    3. Return metadata for all generated graphs

    Uses dataclass with slots for memory efficiency.

    Attributes:
        styling: GraphStyling instance for theme and visual management
        factory: GraphFactory instance for creating generators

    Requirements:
        - 5.1: Generate all enabled graph types
        - 5.2: Apply configured dimensions and DPI
        - 5.5: Use seaborn for enhanced aesthetics
        - 6.6: Apply seaborn style
        - 6.7: Use seaborn palette system
    """

    styling: GraphStyling
    factory: GraphFactory

    async def render_all_graphs(
        self,
        data: Sequence[StreamRecord],
        *,
        config: GraphsConfig,
        output_dir: str | Path,
    ) -> list[GraphMetadata]:
        """Generate all enabled graphs and save to disk.

        This method:
        1. Applies seaborn theme from config
        2. Identifies all enabled graph types
        3. Generates each graph concurrently (future enhancement)
        4. Saves figures to output directory
        5. Returns metadata for all generated graphs

        Args:
            data: Sequence of stream records to visualize
            config: Complete graphs configuration including appearance
            output_dir: Directory path for saving graph images

        Returns:
            List of GraphMetadata for all successfully generated graphs

        Requirements:
            - 5.1: Generate all enabled graph types as specified in configuration
            - 5.5: Apply seaborn theme before generating graphs
            - 6.6: Apply configured seaborn style
            - 6.7: Apply configured seaborn palette
        """
        # Apply seaborn theme before generating any graphs (Requirements 5.5, 6.6, 6.7)
        self.styling.apply_theme(
            style=config.appearance.seaborn.style,
            palette=config.appearance.seaborn.palette,
            context=config.appearance.seaborn.context,
        )

        # Convert data to list for generators
        data_list = list(data)

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get all enabled graph types (Requirement 5.1)
        enabled_graphs = self._get_enabled_graphs(config)

        # Generate graphs (future: use TaskGroup for concurrent generation)
        # For now, generate sequentially to keep it simple
        metadata_list: list[GraphMetadata] = []

        for graph_type, graph_config in enabled_graphs:
            try:
                # Create generator for this graph type
                generator = self.factory.create_generator(graph_type)

                # Generate the figure
                fig = generator.generate(
                    data_list,
                    config=graph_config,
                    appearance=config.appearance,
                )

                # Save figure to disk
                file_path = output_path / f"{graph_type}.png"
                fig.savefig(  # pyright: ignore[reportUnknownMemberType]  # matplotlib incomplete stubs
                    file_path,
                    dpi=config.appearance.dimensions.dpi,
                    bbox_inches="tight",
                    facecolor=fig.get_facecolor(),
                )

                # Create metadata
                from datetime import datetime, timezone

                metadata = GraphMetadata(
                    graph_type=graph_type,
                    file_path=str(file_path),
                    generated_at=datetime.now(tz=timezone.utc),
                    data_range_days=self._calculate_data_range_days(data_list),
                )
                metadata_list.append(metadata)

            except NotImplementedError:
                # Graph generators not yet implemented (tasks 17-20)
                # Skip for now
                continue
            except Exception:
                # Log error and continue with other graphs
                # Future: proper error handling and logging
                continue

        return metadata_list

    def _get_enabled_graphs(
        self, config: GraphsConfig
    ) -> list[tuple[str, GraphConfig]]:
        """Get list of enabled graph configurations.

        Extracts all graph configurations that have enabled=True.

        Args:
            config: Complete graphs configuration

        Returns:
            List of tuples (graph_type, graph_config) for enabled graphs

        Requirements:
            - 5.1: Identify enabled graph types from configuration
        """
        enabled: list[tuple[str, GraphConfig]] = []

        # Map graph type names to their config objects
        graph_configs = {
            "daily_play_count": config.daily_play_count,
            "play_count_by_day_of_week": config.play_count_by_day_of_week,
            "play_count_by_hour_of_day": config.play_count_by_hour_of_day,
            "play_count_by_month": config.play_count_by_month,
            "daily_play_count_by_stream_type": config.daily_play_count_by_stream_type,
            "daily_concurrent_stream_count_by_stream_type": config.daily_concurrent_stream_count_by_stream_type,
            "play_count_by_source_resolution": config.play_count_by_source_resolution,
            "play_count_by_stream_resolution": config.play_count_by_stream_resolution,
            "play_count_by_platform_and_stream_type": config.play_count_by_platform_and_stream_type,
            "play_count_by_user_and_stream_type": config.play_count_by_user_and_stream_type,
        }

        # Add enabled graphs
        for graph_type, graph_config in graph_configs.items():
            if graph_config.enabled:  # pyright: ignore[reportUnknownMemberType]  # always GraphConfig
                enabled.append((graph_type, graph_config))

        # Handle top graphs separately (they use TopGraphConfig)
        # For now, check if they're dict or TopGraphConfig and have enabled=True
        if hasattr(config.top_platforms, "enabled"):
            if config.top_platforms.enabled:  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]  # union type
                enabled.append(("top_platforms", config.top_platforms))  # pyright: ignore[reportArgumentType]  # union type
        elif isinstance(config.top_platforms, dict):
            if config.top_platforms.get("enabled"):
                # Create a basic GraphConfig-like object
                from tgraph_bot.config.models import GraphConfig as GC

                gc = GC(
                    enabled=True,
                    media_type_separation=config.top_platforms.get(
                        "media_type_separation", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    palette=config.top_platforms.get("palette", ""),  # pyright: ignore[reportArgumentType]  # dict access
                    annotations_enabled=config.top_platforms.get(
                        "annotations_enabled", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    peak_highlighting_enabled=config.top_platforms.get(
                        "peak_highlighting_enabled", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    stacked=config.top_platforms.get("stacked", False),  # pyright: ignore[reportArgumentType]  # dict access
                )
                enabled.append(("top_platforms", gc))

        if hasattr(config.top_users, "enabled"):
            if config.top_users.enabled:  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]  # union type
                enabled.append(("top_users", config.top_users))  # pyright: ignore[reportArgumentType]  # union type
        elif isinstance(config.top_users, dict):
            if config.top_users.get("enabled"):
                from tgraph_bot.config.models import GraphConfig as GC

                gc = GC(
                    enabled=True,
                    media_type_separation=config.top_users.get(
                        "media_type_separation", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    palette=config.top_users.get("palette", ""),  # pyright: ignore[reportArgumentType]  # dict access
                    annotations_enabled=config.top_users.get(
                        "annotations_enabled", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    peak_highlighting_enabled=config.top_users.get(
                        "peak_highlighting_enabled", False
                    ),  # pyright: ignore[reportArgumentType]  # dict access
                    stacked=config.top_users.get("stacked", False),  # pyright: ignore[reportArgumentType]  # dict access
                )
                enabled.append(("top_users", gc))

        return enabled

    def _calculate_data_range_days(self, data: Sequence[StreamRecord]) -> int:
        """Calculate the number of days covered by the data.

        Args:
            data: Sequence of stream records

        Returns:
            Number of days from earliest to latest record, or 0 if no data
        """
        if not data:
            return 0

        timestamps = [record.timestamp for record in data]
        earliest = min(timestamps)
        latest = max(timestamps)

        return (latest - earliest).days + 1
