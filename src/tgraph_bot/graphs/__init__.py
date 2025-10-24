"""Graph generation and data transformation modules."""

from tgraph_bot.graphs.data import (
    AggregatedData,
    GraphMetadata,
    StreamRecord,
    TautulliStreamRecord,
    aggregate_by_date,
    aggregate_by_day_of_week,
    aggregate_by_hour,
    aggregate_by_month,
    aggregate_by_platform,
    aggregate_by_user,
    anonymize_usernames,
    create_stream_record,
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
    "aggregate_by_day_of_week",
    "aggregate_by_hour",
    "aggregate_by_month",
    "aggregate_by_platform",
    "aggregate_by_user",
    "anonymize_usernames",
    "create_stream_record",
    # Graph generation core
    "GraphFactory",
    "GraphGenerator",
    "GraphRenderer",
    "GraphStyling",
]
