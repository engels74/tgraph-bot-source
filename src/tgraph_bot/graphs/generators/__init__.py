"""Graph generator implementations.

This package contains individual graph generator implementations for all
supported graph types.

Requirements: 5.5, 5.6, 16.1, 16.2, 16.3, 16.4, 16.5, 17.1, 17.2, 17.3, 17.4, 17.5, 18.1, 18.2, 18.3, 18.4, 18.5
"""

from tgraph_bot.graphs.generators.daily_concurrent_stream_count_by_stream_type import (
    DailyConcurrentStreamCountByStreamTypeGraph,
)
from tgraph_bot.graphs.generators.daily_play_count import DailyPlayCountGraph
from tgraph_bot.graphs.generators.daily_play_count_by_stream_type import (
    DailyPlayCountByStreamTypeGraph,
)
from tgraph_bot.graphs.generators.play_count_by_day_of_week import (
    PlayCountByDayOfWeekGraph,
)
from tgraph_bot.graphs.generators.play_count_by_hour_of_day import (
    PlayCountByHourOfDayGraph,
)
from tgraph_bot.graphs.generators.play_count_by_month import PlayCountByMonthGraph
from tgraph_bot.graphs.generators.play_count_by_platform_and_stream_type import (
    PlayCountByPlatformAndStreamTypeGraph,
)
from tgraph_bot.graphs.generators.play_count_by_source_resolution import (
    PlayCountBySourceResolutionGraph,
)
from tgraph_bot.graphs.generators.play_count_by_stream_resolution import (
    PlayCountByStreamResolutionGraph,
)
from tgraph_bot.graphs.generators.play_count_by_user_and_stream_type import (
    PlayCountByUserAndStreamTypeGraph,
)
from tgraph_bot.graphs.generators.top_platforms import TopPlatformsGraph
from tgraph_bot.graphs.generators.top_users import TopUsersGraph

__all__ = [
    "DailyConcurrentStreamCountByStreamTypeGraph",
    "DailyPlayCountByStreamTypeGraph",
    "DailyPlayCountGraph",
    "PlayCountByDayOfWeekGraph",
    "PlayCountByHourOfDayGraph",
    "PlayCountByMonthGraph",
    "PlayCountByPlatformAndStreamTypeGraph",
    "PlayCountBySourceResolutionGraph",
    "PlayCountByStreamResolutionGraph",
    "PlayCountByUserAndStreamTypeGraph",
    "TopPlatformsGraph",
    "TopUsersGraph",
]
