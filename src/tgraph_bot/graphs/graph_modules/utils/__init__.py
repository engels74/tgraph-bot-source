"""
Utility functions and helpers for TGraph Bot graph modules.

This package contains utility functions, helper classes, and common
functionality used across the graph generation system.
"""

from .annotation_helper import AnnotationHelper
from .progress_tracker import (
    BaseProgressTracker,
    ProgressTracker,
    ProgressTrackerConfig,
    SimpleProgressTracker,
)
from .utils import (
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
    validate_color,
    validate_graph_data,
)

__all__ = [
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
    "validate_color",
    "validate_graph_data",
]
