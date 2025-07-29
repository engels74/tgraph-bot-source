"""
Graph generation modules for TGraph Bot.

This package contains all graph generation implementations including
base classes, data fetching, graph factory, and specific graph types
for Tautulli statistics visualization using Matplotlib and Seaborn.
"""

# Configure logging early to suppress matplotlib categorical units warnings
# These warnings occur when matplotlib detects numeric-looking string data
import logging

from .config import ConfigAccessor
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
from .data import (
    DataFetcher,
    DataProcessor,
    data_processor,
    EmptyDataHandler,
    MediaTypeProcessor,
)
from .implementations import (
    DailyPlayCountGraph,
    PlayCountByDayOfWeekGraph,
    PlayCountByHourOfDayGraph,
    PlayCountByMonthGraph,
    Top10PlatformsGraph,
    Top10UsersGraph,
    SampleGraph,
)
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
from .utils import (
    AnnotationHelper,
    BaseProgressTracker,
    ProgressTracker,
    ProgressTrackerConfig,
    SimpleProgressTracker,
    ProcessedPlayRecord,
    ProcessedRecords,
    SeparatedPlatformAggregates,
    SeparatedUserAggregates,
    aggregate_by_day_of_week,
    aggregate_by_day_of_week_separated,
    aggregate_by_hour_of_day,
    aggregate_by_month,
    aggregate_by_month_separated,
    aggregate_top_platforms_separated,
    aggregate_top_users_separated,
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
from .visualization import VisualizationMixin, VisualizationProtocol

_matplotlib_category_logger = logging.getLogger("matplotlib.category")
_matplotlib_category_logger.setLevel(logging.WARNING)

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
    "SeparatedPlatformAggregates",
    "SeparatedUserAggregates",
    "aggregate_by_day_of_week",
    "aggregate_by_day_of_week_separated",
    "aggregate_by_hour_of_day",
    "aggregate_by_month",
    "aggregate_by_month_separated",
    "aggregate_top_platforms_separated",
    "aggregate_top_users_separated",
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
