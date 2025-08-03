"""
Resolution grouping utilities for analytics graphs.

This module provides resolution grouping functionality based on Tautulli's approach
to reduce visual clutter in resolution analytics by categorizing resolutions into
meaningful groups.

Based on research of Tautulli's resolution handling:
- Simple categorical grouping (SD, HD, FHD, UHD)
- Standard resolution names (4K, 1440p, 1080p, etc.)
- Detailed formatting with friendly names
- Quality-based sorting logic
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .utils import ProcessedRecords, ResolutionAggregates, ResolutionStreamTypeAggregates
    from .utils import ResolutionAggregateRecord, ResolutionStreamTypeAggregateRecord

logger = logging.getLogger(__name__)


def group_resolution_by_strategy(resolution: str, strategy: str) -> str:
    """
    Group resolution according to specified strategy.
    
    Args:
        resolution: Raw resolution string (e.g., "1920x1080")
        strategy: Grouping strategy ("simplified", "standard", "detailed")
        
    Returns:
        Grouped resolution string based on strategy
    """
    if strategy == "simplified":
        return _group_simplified(resolution)
    elif strategy == "standard":
        return _group_standard(resolution)
    elif strategy == "detailed":
        return _format_detailed(resolution)
    else:
        # Fallback to detailed for invalid strategies
        logger.warning(f"Invalid grouping strategy '{strategy}', falling back to 'detailed'")
        return _format_detailed(resolution)


def _group_simplified(resolution: str) -> str:
    """
    Group into SD, HD, FHD, UHD categories.
    
    This follows a simplified approach similar to Tautulli's minimal categorization.
    
    Args:
        resolution: Raw resolution string
        
    Returns:
        Simplified category (SD, HD, FHD, UHD, Other)
    """
    if not resolution or resolution == "unknown":
        return "Other"
    
    # SD (Standard Definition) - up to 480p
    if resolution in ["720x480", "720x576", "854x480"]:
        return "SD"
    
    # HD (High Definition) - 720p and similar
    elif resolution in ["1280x720", "1366x768"]:
        return "HD"
    
    # FHD (Full HD) - 1080p and similar
    elif resolution in ["1920x1080", "1680x1050"]:
        return "FHD"
    
    # UHD (Ultra HD) - 1440p, 4K and above
    elif resolution in ["3840x2160", "4096x2160", "2560x1440"]:
        return "UHD"
    
    else:
        return "Other"


def _group_standard(resolution: str) -> str:
    """
    Group into standard resolution names (4K, 1440p, 1080p, etc.).
    
    This follows Tautulli's approach of using common resolution names
    while falling back to original resolution for unmapped values.
    
    Args:
        resolution: Raw resolution string
        
    Returns:
        Standard resolution name or original resolution
    """
    if not resolution:
        return resolution
    
    # Standard resolution mappings based on Tautulli research
    standard_mapping = {
        "3840x2160": "4K",
        "4096x2160": "4K", 
        "2560x1440": "1440p",
        "1920x1080": "1080p",
        "1280x720": "720p",
        "854x480": "480p",
        "720x480": "NTSC",
        "720x576": "PAL",
    }
    
    return standard_mapping.get(resolution, resolution)


def _format_detailed(resolution: str) -> str:
    """
    Format resolution with detailed friendly names.
    
    This provides the most detailed view, similar to our current implementation
    but with consistent formatting.
    
    Args:
        resolution: Raw resolution string
        
    Returns:
        Detailed resolution string with friendly names
    """
    if resolution == "unknown" or not resolution:
        return "Unknown (No resolution data from Tautulli)" if resolution == "unknown" else resolution
    
    # Detailed resolution mappings with friendly names
    detailed_mapping = {
        "3840x2160": "4K UHD (3840×2160)",
        "4096x2160": "4K DCI (4096×2160)", 
        "2560x1440": "1440p (2560×1440)",
        "1920x1080": "1080p (1920×1080)",
        "1680x1050": "WSXGA+ (1680×1050)",
        "1600x900": "HD+ (1600×900)",
        "1366x768": "WXGA (1366×768)",
        "1280x720": "720p (1280×720)",
        "1024x768": "XGA (1024×768)",
        "854x480": "FWVGA (854×480)",
        "720x480": "NTSC (720×480)",
        "720x576": "PAL (720×576)",
    }
    
    return detailed_mapping.get(resolution, resolution)


def sort_resolutions_by_quality(resolutions: list[str]) -> list[str]:
    """
    Sort resolutions by quality (highest to lowest).
    
    This implements quality-based sorting similar to Tautulli's approach.
    
    Args:
        resolutions: List of resolution strings to sort
        
    Returns:
        Sorted list of resolutions (highest quality first)
    """
    # Quality order mapping (lower number = higher quality)
    quality_order = {
        "4K": 1,
        "UHD": 1,  # Same as 4K for simplified grouping
        "1440p": 2,
        "1080p": 3,
        "FHD": 3,  # Same as 1080p for simplified grouping
        "720p": 4,
        "HD": 4,   # Same as 720p for simplified grouping
        "480p": 5,
        "NTSC": 6,
        "PAL": 7,
        "SD": 8,   # Standard definition for simplified grouping
        "Other": 9,
        "unknown": 10,
    }
    
    def get_quality_score(resolution: str) -> int:
        """Get quality score for sorting, with fallback for unmapped resolutions."""
        # Check direct mapping first
        if resolution in quality_order:
            return quality_order[resolution]
        
        # For detailed format, extract the base resolution
        if "(" in resolution and "×" in resolution:
            # Extract resolution from detailed format like "1080p (1920×1080)"
            base_resolution = resolution.split("(")[0].strip()
            if base_resolution in quality_order:
                return quality_order[base_resolution]
        
        # For unmapped resolutions, assign a middle score
        return 999
    
    return sorted(resolutions, key=get_quality_score)


def aggregate_by_resolution_grouped(
    records: "ProcessedRecords", 
    resolution_field: str = "video_resolution",
    grouping_strategy: str = "standard"
) -> "ResolutionAggregates":
    """
    Aggregate play records by resolution with grouping applied.
    
    This extends the basic resolution aggregation to apply grouping strategies
    that reduce visual clutter in analytics graphs.
    
    Args:
        records: List of processed play history records
        resolution_field: Field to use for resolution
        grouping_strategy: Grouping strategy to apply
        
    Returns:
        Aggregated resolution data with grouping applied, sorted by quality and count
    """
    from .utils import ResolutionAggregateRecord
    
    # Group resolutions before aggregating
    grouped_counts: defaultdict[str, int] = defaultdict(int)
    unknown_count = 0
    total_records = len(records)

    for record in records:
        resolution = record[resolution_field]  # type: ignore[misc]
        if resolution and resolution != "unknown":
            grouped_resolution = group_resolution_by_strategy(str(resolution), grouping_strategy)
            grouped_counts[grouped_resolution] += 1
        else:
            unknown_count += 1
    
    # Log statistics
    logger.info(f"Grouped resolution aggregation for field '{resolution_field}' with strategy '{grouping_strategy}': " +
               f"{len(grouped_counts)} unique grouped resolutions, " +
               f"{unknown_count} unknown values out of {total_records} total records")
    
    # Handle unknown values based on strategy
    if unknown_count > 0:
        unknown_group = group_resolution_by_strategy("unknown", grouping_strategy)
        grouped_counts[unknown_group] += unknown_count
    
    # Convert to aggregates
    aggregates: "ResolutionAggregates" = []
    for resolution, count in grouped_counts.items():
        aggregates.append(ResolutionAggregateRecord(
            resolution=resolution,
            play_count=count
        ))
    
    # Sort by quality first, then by play count
    return _sort_aggregates_by_quality_and_count(aggregates)


def aggregate_by_resolution_and_stream_type_grouped(
    records: "ProcessedRecords", 
    resolution_field: str = "video_resolution",
    grouping_strategy: str = "standard"
) -> "ResolutionStreamTypeAggregates":
    """
    Aggregate play records by resolution and stream type with grouping applied.
    
    Args:
        records: List of processed play history records
        resolution_field: Field to use for resolution
        grouping_strategy: Grouping strategy to apply
        
    Returns:
        Dictionary mapping grouped resolution to list of stream type aggregates
    """
    from .utils import ResolutionStreamTypeAggregateRecord, _get_stream_type_display_name, _get_stream_type_color
    
    # Count by grouped resolution and stream type
    resolution_stream_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    unknown_count = 0
    total_records = len(records)

    for record in records:
        resolution = record[resolution_field]  # type: ignore[misc]
        stream_type: str = record["transcode_decision"]  # type: ignore[misc]

        if resolution and resolution != "unknown":
            grouped_resolution = group_resolution_by_strategy(str(resolution), grouping_strategy)
            resolution_stream_counts[grouped_resolution][stream_type] += 1
        else:
            unknown_count += 1

    # Handle unknown values
    if unknown_count > 0:
        unknown_group = group_resolution_by_strategy("unknown", grouping_strategy)
        # Assign unknown stream type for unknown resolutions
        resolution_stream_counts[unknown_group]["unknown"] += unknown_count

    # Log statistics
    logger.info(f"Grouped resolution and stream type aggregation for field '{resolution_field}' with strategy '{grouping_strategy}': " +
               f"{len(resolution_stream_counts)} unique grouped resolutions, " +
               f"{unknown_count} unknown values out of {total_records} total records")

    # Convert to aggregate format
    result: "ResolutionStreamTypeAggregates" = {}
    for resolution, stream_counts in resolution_stream_counts.items():
        aggregates: list["ResolutionStreamTypeAggregateRecord"] = []
        for stream_type, count in stream_counts.items():
            display_name = _get_stream_type_display_name(stream_type)
            color = _get_stream_type_color(stream_type)

            aggregates.append(ResolutionStreamTypeAggregateRecord(
                resolution=resolution,
                stream_type=stream_type,
                display_name=display_name,
                play_count=count,
                color=color
            ))

        # Sort by play count (descending)
        aggregates.sort(key=lambda x: x["play_count"], reverse=True)
        result[resolution] = aggregates

    # Sort resolutions by quality, then by total play count
    return _sort_resolution_stream_aggregates_by_quality(result)


def _sort_aggregates_by_quality_and_count(aggregates: "ResolutionAggregates") -> "ResolutionAggregates":
    """Sort resolution aggregates by quality first, then by play count."""
    # Get unique resolutions and sort by quality
    resolutions = [agg["resolution"] for agg in aggregates]
    quality_sorted_resolutions = sort_resolutions_by_quality(resolutions)
    
    # Create quality order mapping
    quality_order = {res: i for i, res in enumerate(quality_sorted_resolutions)}
    
    # Sort by quality first, then by play count (descending)
    return sorted(aggregates, key=lambda x: (quality_order.get(x["resolution"], 999), -x["play_count"]))


def _sort_resolution_stream_aggregates_by_quality(
    result: "ResolutionStreamTypeAggregates"
) -> "ResolutionStreamTypeAggregates":
    """Sort resolution stream type aggregates by quality."""
    # Sort resolutions by quality first, then by total play count
    resolution_totals = {
        resolution: sum(agg["play_count"] for agg in aggregates)
        for resolution, aggregates in result.items()
    }
    
    # Get quality-sorted resolutions
    quality_sorted_resolutions = sort_resolutions_by_quality(list(result.keys()))
    
    # Create quality order mapping
    quality_order = {res: i for i, res in enumerate(quality_sorted_resolutions)}
    
    # Sort by quality first, then by total play count (descending)
    sorted_resolutions = sorted(
        result.keys(), 
        key=lambda x: (quality_order.get(x, 999), -resolution_totals[x])
    )
    
    # Return sorted result
    return {resolution: result[resolution] for resolution in sorted_resolutions}
