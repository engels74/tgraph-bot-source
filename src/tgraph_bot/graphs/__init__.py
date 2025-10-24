"""Graph generation and data transformation modules."""

from tgraph_bot.graphs.data import (
    AggregatedData,
    GraphMetadata,
    StreamRecord,
    TautulliStreamRecord,
    aggregate_by_date,
    aggregate_by_date_and_stream_type,
    aggregate_by_day_of_week,
    aggregate_by_hour,
    aggregate_by_month,
    aggregate_by_platform,
    aggregate_by_platform_and_stream_type,
    aggregate_by_resolution,
    aggregate_by_stream_type,
    aggregate_by_user,
    aggregate_by_user_and_stream_type,
    anonymize_usernames,
    create_stream_record,
    group_resolution,
)
from tgraph_bot.graphs.factory import GraphFactory
from tgraph_bot.graphs.protocol import GraphGenerator
from tgraph_bot.graphs.renderer import GraphRenderer
from tgraph_bot.graphs.styling import GraphStyling

__all__ = [
    # Data models and transformation
    "AggregatedData",
    "GraphMetadata",
    "StreamRecord",
    "TautulliStreamRecord",
    "aggregate_by_date",
    "aggregate_by_date_and_stream_type",
    "aggregate_by_day_of_week",
    "aggregate_by_hour",
    "aggregate_by_month",
    "aggregate_by_platform",
    "aggregate_by_platform_and_stream_type",
    "aggregate_by_resolution",
    "aggregate_by_stream_type",
    "aggregate_by_user",
    "aggregate_by_user_and_stream_type",
    "anonymize_usernames",
    "create_stream_record",
    "group_resolution",
    # Graph generation core
    "GraphFactory",
    "GraphGenerator",
    "GraphRenderer",
    "GraphStyling",
]
