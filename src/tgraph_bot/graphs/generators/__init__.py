"""Graph generator implementations.

This package contains individual graph generator implementations for all
supported graph types.

Requirements: 5.5, 5.6, 18.1, 18.2, 18.3, 18.4, 18.5
"""

from tgraph_bot.graphs.generators.daily_play_count import DailyPlayCountGraph
from tgraph_bot.graphs.generators.play_count_by_day_of_week import (
    PlayCountByDayOfWeekGraph,
)
from tgraph_bot.graphs.generators.play_count_by_hour_of_day import (
    PlayCountByHourOfDayGraph,
)
from tgraph_bot.graphs.generators.play_count_by_month import PlayCountByMonthGraph
from tgraph_bot.graphs.generators.top_platforms import TopPlatformsGraph
from tgraph_bot.graphs.generators.top_users import TopUsersGraph

__all__ = [
    "DailyPlayCountGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "TopPlatformsGraph",
    "TopUsersGraph",
]
