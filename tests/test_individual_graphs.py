"""Tests for individual graph type implementations.

This test suite validates individual graph generators including:
- DailyPlayCountGraph data preparation and rendering
- PlayCountByDayOfWeekGraph aggregation and stacking
- PlayCountByHourOfDayGraph aggregation and stacking
- TopPlatformsGraph limiting and grouping
- TopUsersGraph limiting and privacy
- PlayCountByMonthGraph data preparation and media type separation

Requirements tested: 5.5, 5.6, 18.1, 18.2, 18.3, 18.4, 18.5

NOTE: All tests in this file are placeholder tests (skipped) pending task 18 implementation.
Unused parameters and variables are expected and will be used when implementations are added.
"""

# pyright: reportUnusedParameter=false, reportUnusedVariable=false

from datetime import datetime, timezone

import pytest

from tgraph_bot.config.models import (
    AnnotationConfig,
    GraphAppearanceConfig,
    GraphColors,
    GraphConfig,
    GraphDimensions,
    GridConfig,
    SeabornConfig,
    TopGraphConfig,
)
from tgraph_bot.graphs.data import StreamRecord


# Fixtures


@pytest.fixture
def sample_stream_records() -> list[StreamRecord]:
    """Fixture providing sample stream records for testing."""
    return [
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            media_type="movie",
            stream_type="direct play",
            platform="Plex for Android",
            user="Alice",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            media_type="tv",
            stream_type="transcode",
            platform="Plex for iOS",
            user="Bob",
            source_resolution="1280x720",
            stream_resolution="720p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
            media_type="movie",
            stream_type="direct play",
            platform="Plex for Android",
            user="Alice",
            source_resolution="3840x2160",
            stream_resolution="4K",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 2, 15, 0, 0, tzinfo=timezone.utc),
            media_type="tv",
            stream_type="copy",
            platform="Plex Web",
            user="Charlie",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 3, 9, 0, 0, tzinfo=timezone.utc),
            media_type="movie",
            stream_type="transcode",
            platform="Plex for Android TV",
            user="Bob",
            source_resolution="1920x1080",
            stream_resolution="720p",
        ),
    ]


@pytest.fixture
def sample_graph_config() -> GraphConfig:
    """Fixture providing sample graph configuration."""
    return GraphConfig(
        enabled=True,
        media_type_separation=False,
        palette="",
        annotations_enabled=False,
        peak_highlighting_enabled=False,
        stacked=False,
    )


@pytest.fixture
def sample_top_graph_config() -> TopGraphConfig:
    """Fixture providing sample top graph configuration."""
    return TopGraphConfig(
        enabled=True,
        media_type_separation=False,
        palette="",
        annotations_enabled=False,
        peak_highlighting_enabled=False,
        stacked=False,
        limit=10,
    )


@pytest.fixture
def sample_appearance_config() -> GraphAppearanceConfig:
    """Fixture providing sample appearance configuration."""
    return GraphAppearanceConfig(
        dimensions=GraphDimensions(width=10, height=6, dpi=100),
        colors=GraphColors(tv="#FF6B6B", movie="#4ECDC4", background="#FFFFFF"),
        grid=GridConfig(enabled=True, alpha=0.3),
        annotations=AnnotationConfig(
            color="#000000",
            outline_color="#FFFFFF",
            enable_outline=True,
            font_size=10,
        ),
        palettes={},
        seaborn=SeabornConfig(
            style="darkgrid",
            context="notebook",
            palette="muted",
        ),
    )


# Test Classes


class TestDailyPlayCountGraph:
    """Tests for DailyPlayCountGraph data preparation.

    Requirements: 5.5, 5.6, 18.1
    """

    def test_aggregates_data_by_date(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph aggregates data by date correctly."""
        # This test will verify that the graph generator uses aggregate_by_date
        # and produces correct date-based grouping
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_supports_media_type_separation(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph separates movies and TV when enabled."""
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )
        # This test will verify media type separation creates separate lines
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_returns_matplotlib_figure(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph returns a matplotlib Figure."""
        # This test will verify the return type is Figure
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        # This test will verify empty data doesn't crash
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_applies_palette_when_specified(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph applies palette colors when specified."""
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="viridis",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )
        # This test will verify palette override works
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")


class TestPlayCountByDayOfWeekGraph:
    """Tests for PlayCountByDayOfWeekGraph aggregation.

    Requirements: 5.5, 5.6, 18.2
    """

    def test_aggregates_data_by_day_of_week(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByDayOfWeekGraph aggregates by day of week."""
        # This test will verify aggregate_by_day_of_week is used
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_includes_all_seven_days(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that all 7 days are present even with sparse data."""
        # This test will verify all days Monday-Sunday are shown
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_supports_stacked_bars(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByDayOfWeekGraph supports stacked bar option."""
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=True,
        )
        # This test will verify stacked bars when media_type_separation + stacked
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")


class TestPlayCountByHourOfDayGraph:
    """Tests for PlayCountByHourOfDayGraph aggregation.

    Requirements: 5.5, 5.6, 18.3
    """

    def test_aggregates_data_by_hour(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByHourOfDayGraph aggregates by hour of day."""
        # This test will verify aggregate_by_hour is used
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_includes_all_24_hours(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that all 24 hours are present even with sparse data."""
        # This test will verify all hours 0-23 are shown
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_supports_stacked_bars(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByHourOfDayGraph supports stacked bar option."""
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=True,
        )
        # This test will verify stacked bars when media_type_separation + stacked
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByHourOfDayGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        # This test will verify empty data shows all hours with 0 counts
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")


class TestTopPlatformsGraph:
    """Tests for TopPlatformsGraph limiting and grouping.

    Requirements: 5.5, 5.6, 18.4
    """

    def test_limits_to_top_n_platforms(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph limits results to top N platforms."""
        # Create data with more platforms than limit
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform=f"Platform {i}",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            )
            for i in range(15)  # 15 different platforms
        ]
        # This test will verify only top 10 are shown (based on limit)
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_groups_similar_platforms(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph groups similar platform names."""
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Plex for Android",
                user="User1",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Plex for Android TV",
                user="User2",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
        ]
        # This test will verify "Plex for Android" and "Plex for Android TV"
        # are grouped as "Android"
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_sorts_by_play_count_descending(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph sorts platforms by play count."""
        # This test will verify platforms are sorted by count (highest first)
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_creates_horizontal_bar_chart(
        self,
        sample_stream_records: list[StreamRecord],
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph creates horizontal bar chart."""
        # This test will verify the chart uses horizontal bars
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")


class TestTopUsersGraph:
    """Tests for TopUsersGraph limiting and privacy.

    Requirements: 5.5, 5.6, 18.5
    """

    def test_limits_to_top_n_users(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph limits results to top N users."""
        # Create data with more users than limit
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user=f"User{i}",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            )
            for i in range(15)  # 15 different users
        ]
        # This test will verify only top 10 are shown (based on limit)
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_sorts_by_play_count_descending(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph sorts users by play count."""
        # This test will verify users are sorted by count (highest first)
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_creates_horizontal_bar_chart(
        self,
        sample_stream_records: list[StreamRecord],
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph creates horizontal bar chart."""
        # This test will verify the chart uses horizontal bars
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_handles_empty_data(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        # This test will verify empty data doesn't crash
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")


class TestPlayCountByMonthGraph:
    """Tests for PlayCountByMonthGraph data preparation.

    Requirements: 5.5, 5.6
    """

    def test_aggregates_data_by_month(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph aggregates data by month."""
        # Create data spanning multiple months
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
                media_type="tv",
                stream_type="transcode",
                platform="Platform",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="720p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 3, 5, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
        ]
        # This test will verify aggregate_by_month is used
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_supports_media_type_separation(
        self,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph separates movies and TV when enabled."""
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 1, 20, 10, 0, 0, tzinfo=timezone.utc),
                media_type="tv",
                stream_type="transcode",
                platform="Platform",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="720p",
            ),
        ]
        # This test will verify media type separation creates separate lines
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_returns_matplotlib_figure(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph returns a matplotlib Figure."""
        # This test will verify the return type is Figure
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        # This test will verify empty data doesn't crash
        # Implementation will be in task 18
        pytest.skip("Graph implementation not yet available (task 18)")

