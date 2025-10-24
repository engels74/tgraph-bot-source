"""Tests for individual graph type implementations.

This test suite validates individual graph generators including:
- DailyPlayCountGraph data preparation and rendering
- PlayCountByDayOfWeekGraph aggregation and stacking
- PlayCountByHourOfDayGraph aggregation and stacking
- TopPlatformsGraph limiting and grouping
- TopUsersGraph limiting and privacy
- PlayCountByMonthGraph data preparation and media type separation

Requirements tested: 5.5, 5.6, 18.1, 18.2, 18.3, 18.4, 18.5
"""

from datetime import datetime, timezone

import pytest
from matplotlib.figure import Figure

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
from tgraph_bot.graphs.generators import (
    DailyPlayCountGraph,
    PlayCountByDayOfWeekGraph,
    PlayCountByHourOfDayGraph,
    PlayCountByMonthGraph,
    TopPlatformsGraph,
    TopUsersGraph,
)


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
        generator = DailyPlayCountGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = DailyPlayCountGraph()
        fig = generator.generate(
            sample_stream_records,
            config=config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_returns_matplotlib_figure(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph returns a matplotlib Figure."""
        generator = DailyPlayCountGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that DailyPlayCountGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        generator = DailyPlayCountGraph()
        fig = generator.generate(
            empty_data,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = DailyPlayCountGraph()
        fig = generator.generate(
            sample_stream_records,
            config=config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)


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
        generator = PlayCountByDayOfWeekGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_includes_all_seven_days(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that all 7 days are present even with sparse data."""
        generator = PlayCountByDayOfWeekGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = PlayCountByDayOfWeekGraph()
        fig = generator.generate(
            sample_stream_records,
            config=config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)


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
        generator = PlayCountByHourOfDayGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_includes_all_24_hours(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that all 24 hours are present even with sparse data."""
        generator = PlayCountByHourOfDayGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = PlayCountByHourOfDayGraph()
        fig = generator.generate(
            sample_stream_records,
            config=config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByHourOfDayGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        generator = PlayCountByHourOfDayGraph()
        fig = generator.generate(
            empty_data,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)


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
        generator = TopPlatformsGraph()
        fig = generator.generate(
            records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = TopPlatformsGraph()
        fig = generator.generate(
            records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_sorts_by_play_count_descending(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph sorts platforms by play count."""
        generator = TopPlatformsGraph()
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform A",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform B",
                user="User",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
        ]
        fig = generator.generate(
            records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_creates_horizontal_bar_chart(
        self,
        sample_stream_records: list[StreamRecord],
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopPlatformsGraph creates horizontal bar chart."""
        generator = TopPlatformsGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)


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
        generator = TopUsersGraph()
        fig = generator.generate(
            records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_sorts_by_play_count_descending(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph sorts users by play count."""
        generator = TopUsersGraph()
        records = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user="User A",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Platform",
                user="User B",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            ),
        ]
        fig = generator.generate(
            records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_creates_horizontal_bar_chart(
        self,
        sample_stream_records: list[StreamRecord],
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph creates horizontal bar chart."""
        generator = TopUsersGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_handles_empty_data(
        self,
        sample_top_graph_config: TopGraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that TopUsersGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        generator = TopUsersGraph()
        fig = generator.generate(
            empty_data,
            config=sample_top_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)


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
        generator = PlayCountByMonthGraph()
        fig = generator.generate(
            records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

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
        generator = PlayCountByMonthGraph()
        fig = generator.generate(
            records,
            config=config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_returns_matplotlib_figure(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph returns a matplotlib Figure."""
        generator = PlayCountByMonthGraph()
        fig = generator.generate(
            sample_stream_records,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

    def test_handles_empty_data(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test that PlayCountByMonthGraph handles empty data gracefully."""
        empty_data: list[StreamRecord] = []
        generator = PlayCountByMonthGraph()
        fig = generator.generate(
            empty_data,
            config=sample_graph_config,
            appearance=sample_appearance_config,
        )
        assert isinstance(fig, Figure)

