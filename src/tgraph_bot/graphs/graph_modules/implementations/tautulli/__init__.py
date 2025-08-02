"""
Tautulli-specific graph modules for TGraph Bot.

This package contains graph implementations that specifically work with
Tautulli API data to generate various statistics visualizations.
"""

from .daily_play_count_graph import DailyPlayCountGraph
from .daily_play_count_by_stream_type_graph import DailyPlayCountByStreamTypeGraph
from .daily_concurrent_stream_count_by_stream_type_graph import DailyConcurrentStreamCountByStreamTypeGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .play_count_by_month_graph import PlayCountByMonthGraph
from .play_count_by_platform_and_stream_type_graph import PlayCountByPlatformAndStreamTypeGraph
from .play_count_by_source_resolution_graph import PlayCountBySourceResolutionGraph
from .play_count_by_stream_resolution_graph import PlayCountByStreamResolutionGraph
from .play_count_by_user_and_stream_type_graph import PlayCountByUserAndStreamTypeGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph

__all__ = [
    "DailyPlayCountGraph",
    "DailyPlayCountByStreamTypeGraph", 
    "DailyConcurrentStreamCountByStreamTypeGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "PlayCountByPlatformAndStreamTypeGraph",
    "PlayCountBySourceResolutionGraph",
    "PlayCountByStreamResolutionGraph",
    "PlayCountByUserAndStreamTypeGraph",
    "Top10PlatformsGraph",
    "Top10UsersGraph",
]
