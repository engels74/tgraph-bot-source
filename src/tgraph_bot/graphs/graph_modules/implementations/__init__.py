"""
Graph implementation packages for TGraph Bot.

This package contains concrete graph implementations organized by data source
or functionality. Each subpackage contains graph classes that implement
specific visualization types.
"""

# Import from subpackages
from .tautulli import *  # noqa: F403, F401
from .sample_graph import SampleGraph

__all__ = [
    # Re-export all Tautulli graph implementations
    "DailyPlayCountGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "Top10PlatformsGraph",
    "Top10UsersGraph",
    # Sample graph for reference
    "SampleGraph",
]
