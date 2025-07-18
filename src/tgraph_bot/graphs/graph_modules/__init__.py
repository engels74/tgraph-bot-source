"""
Graph generation modules for TGraph Bot.

This package contains all graph generation implementations including
base classes, data fetching, graph factory, and specific graph types
for Tautulli statistics visualization using Matplotlib and Seaborn.
"""

# Import core components
from .core import (
    BaseGraph,
    GraphError,
    GraphDataError,
    GraphConfigurationError,
    GraphGenerationError,
    GraphValidationError,
    GraphFactory,
    GraphTypeRegistry,
    get_graph_type_registry,
)

# Import configuration utilities
from .config import ConfigAccessor

# Import data processing components
from .data import (
    DataFetcher,
    DataProcessor,
    data_processor,
    EmptyDataHandler,
    MediaTypeProcessor,
)

# Import type definitions and constants
from .types import (
    DAYS_OF_WEEK,
    DATETIME_FORMATS,
    MEDIA_TYPES,
    MEDIA_TYPE_DISPLAY_NAMES,
    MEDIA_TYPE_ALIASES,
    GRAPH_TYPES,
    GRAPH_TITLES,
    DEFAULT_COLORS,
    COLOR_PALETTES,
    CONFIG_KEYS,
    FILE_EXTENSIONS,
    FILE_FORMATS,
    PATH_PATTERNS,
    validate_color,
    validate_graph_type,
    validate_media_type,
    validate_day_of_week,
    get_localized_day_names,
    get_localized_media_type_names,
    get_localized_graph_titles,
)

# Import utility functions and helpers
from .utils import (
    AnnotationHelper,
    BaseProgressTracker,
    ProgressTracker,
    ProgressTrackerConfig,
    SimpleProgressTracker,
    ProcessedPlayRecord,
    ProcessedRecords,
    aggregate_by_day_of_week,
    aggregate_by_day_of_week_separated,
    aggregate_by_hour_of_day,
    aggregate_by_month,
    aggregate_by_month_separated,
    apply_modern_seaborn_styling,
    censor_username,
    cleanup_old_files,
    ensure_graph_directory,
    generate_graph_filename,
    get_current_graph_storage_path,
    get_media_type_display_info,
    process_play_history_data,
    validate_graph_data,
)

# Import visualization utilities
from .visualization import VisualizationMixin, VisualizationProtocol

# Import graph implementations
from .implementations import (
    DailyPlayCountGraph,
    PlayCountByDayOfWeekGraph,
    PlayCountByHourOfDayGraph,
    PlayCountByMonthGraph,
    Top10PlatformsGraph,
    Top10UsersGraph,
    SampleGraph,
)

__all__ = [
    # Core components
    "BaseGraph",
    "GraphError",
    "GraphDataError",
    "GraphConfigurationError",
    "GraphGenerationError",
    "GraphValidationError",
    "GraphFactory",
    "GraphTypeRegistry",
    "get_graph_type_registry",
    # Configuration
    "ConfigAccessor",
    # Data processing
    "DataFetcher",
    "DataProcessor",
    "data_processor",
    "EmptyDataHandler",
    "MediaTypeProcessor",
    # Types and constants
    "DAYS_OF_WEEK",
    "DATETIME_FORMATS",
    "MEDIA_TYPES",
    "MEDIA_TYPE_DISPLAY_NAMES",
    "MEDIA_TYPE_ALIASES",
    "GRAPH_TYPES",
    "GRAPH_TITLES",
    "DEFAULT_COLORS",
    "COLOR_PALETTES",
    "CONFIG_KEYS",
    "FILE_EXTENSIONS",
    "FILE_FORMATS",
    "PATH_PATTERNS",
    "validate_color",
    "validate_graph_type",
    "validate_media_type",
    "validate_day_of_week",
    "get_localized_day_names",
    "get_localized_media_type_names",
    "get_localized_graph_titles",
    # Utilities
    "AnnotationHelper",
    "BaseProgressTracker",
    "ProgressTracker",
    "ProgressTrackerConfig",
    "SimpleProgressTracker",
    "ProcessedPlayRecord",
    "ProcessedRecords",
    "aggregate_by_day_of_week",
    "aggregate_by_day_of_week_separated",
    "aggregate_by_hour_of_day",
    "aggregate_by_month",
    "aggregate_by_month_separated",
    "apply_modern_seaborn_styling",
    "censor_username",
    "cleanup_old_files",
    "ensure_graph_directory",
    "generate_graph_filename",
    "get_current_graph_storage_path",
    "get_media_type_display_info",
    "process_play_history_data",
    "validate_graph_data",
    # Visualization
    "VisualizationMixin",
    "VisualizationProtocol",
    # Graph implementations
    "DailyPlayCountGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "Top10PlatformsGraph",
    "Top10UsersGraph",
    "SampleGraph",
]
