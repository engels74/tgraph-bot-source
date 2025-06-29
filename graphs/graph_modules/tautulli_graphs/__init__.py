"""
Tautulli-specific graph modules for TGraph Bot.

This package contains graph implementations that specifically work with
Tautulli API data to generate various statistics visualizations.
"""

from .daily_play_count_graph import DailyPlayCountGraph
from .play_count_by_dayofweek_graph import PlayCountByDayOfWeekGraph
from .play_count_by_hourofday_graph import PlayCountByHourOfDayGraph
from .play_count_by_month_graph import PlayCountByMonthGraph
from .top_10_platforms_graph import Top10PlatformsGraph
from .top_10_users_graph import Top10UsersGraph

__all__ = [
    "DailyPlayCountGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "Top10PlatformsGraph",
    "Top10UsersGraph",
]
