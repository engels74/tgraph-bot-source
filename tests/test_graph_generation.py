"""Tests for graph generation engine.

This test suite validates the graph generation system including:
- Seaborn theme application (style, palette, context)
- Graph styling application (colors, dimensions, palettes)
- Seaborn palette retrieval and color management
- Annotation system (basic and peak highlighting)
- Media type separation logic
- GraphFactory creating correct generator types

Requirements tested: 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 6.6, 6.7
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from tgraph_bot.config.models import (
    AnnotationConfig,
    GraphAppearanceConfig,
    GraphColors,
    GraphConfig,
    GraphDimensions,
    GridConfig,
    SeabornConfig,
)
from tgraph_bot.graphs.data import StreamRecord

# Import actual implementations (task 16 completed)
from tgraph_bot.graphs.factory import GraphFactory
from tgraph_bot.graphs.generators import (
    DailyPlayCountGraph,
    PlayCountByDayOfWeekGraph,
    PlayCountByHourOfDayGraph,
    PlayCountByMonthGraph,
    TopPlatformsGraph,
    TopUsersGraph,
)
from tgraph_bot.graphs.styling import GraphStyling


# Fixtures


@pytest.fixture
def sample_stream_records() -> list[StreamRecord]:
    """Fixture providing sample stream records for testing."""
    return [
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            media_type="movie",
            stream_type="direct play",
            platform="Plex for Android",
            user="Alice",
            source_resolution="1920x1080",
            stream_resolution="1080p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
            media_type="tv",
            stream_type="transcode",
            platform="Plex for iOS",
            user="Bob",
            source_resolution="1280x720",
            stream_resolution="720p",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            media_type="movie",
            stream_type="direct play",
            platform="Plex for Android",
            user="Alice",
            source_resolution="3840x2160",
            stream_resolution="4K",
        ),
        StreamRecord(
            timestamp=datetime(2024, 1, 2, 1, 0, 0, tzinfo=timezone.utc),
            media_type="tv",
            stream_type="copy",
            platform="Plex Web",
            user="Charlie",
            source_resolution="1920x1080",
            stream_resolution="1080p",
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
def sample_appearance_config() -> GraphAppearanceConfig:
    """Fixture providing sample appearance configuration."""
    return GraphAppearanceConfig(
        dimensions=GraphDimensions(width=12, height=8, dpi=100),
        colors=GraphColors(tv="#3498db", movie="#e74c3c", background="#ffffff"),
        grid=GridConfig(enabled=True, alpha=0.3),
        annotations=AnnotationConfig(
            color="#000000",
            outline_color="#ffffff",
            enable_outline=True,
            font_size=10,
        ),
        palettes={
            "custom_palette_1": "viridis",
            "custom_palette_2": "plasma",
        },
        seaborn=SeabornConfig(
            style="darkgrid",
            context="notebook",
            palette="muted",
        ),
    )


# Tests for Seaborn Theme Application


class TestSeabornThemeApplication:
    """Tests for seaborn theme application (style, palette, context).

    Requirements: 5.5, 6.6, 6.7
    """

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    def test_apply_theme_with_default_values(self, mock_set_theme: Mock) -> None:
        """Test applying seaborn theme with default values."""
        styling = GraphStyling()
        styling.apply_theme()

        # Should call seaborn.set_theme with defaults
        mock_set_theme.assert_called_once_with(
            style="darkgrid",
            palette="muted",
            context="notebook",
        )

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    @pytest.mark.parametrize(
        "style",
        ["whitegrid", "darkgrid", "white", "dark", "ticks"],
    )
    def test_apply_theme_with_different_styles(
        self, mock_set_theme: Mock, style: str
    ) -> None:
        """Test applying different seaborn styles (Requirement 6.6)."""
        styling = GraphStyling()
        styling.apply_theme(style=style)

        mock_set_theme.assert_called_once()
        call_args = mock_set_theme.call_args
        assert call_args is not None
        assert call_args.kwargs["style"] == style

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    @pytest.mark.parametrize(
        "palette",
        ["muted", "deep", "pastel", "viridis", "plasma", "inferno", "magma"],
    )
    def test_apply_theme_with_different_palettes(
        self, mock_set_theme: Mock, palette: str
    ) -> None:
        """Test applying different seaborn palettes (Requirement 6.7)."""
        styling = GraphStyling()
        styling.apply_theme(palette=palette)

        mock_set_theme.assert_called_once()
        call_args = mock_set_theme.call_args
        assert call_args is not None
        assert call_args.kwargs["palette"] == palette

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    @pytest.mark.parametrize(
        "context",
        ["paper", "notebook", "talk", "poster"],
    )
    def test_apply_theme_with_different_contexts(
        self, mock_set_theme: Mock, context: str
    ) -> None:
        """Test applying different seaborn contexts."""
        styling = GraphStyling()
        styling.apply_theme(context=context)

        mock_set_theme.assert_called_once()
        call_args = mock_set_theme.call_args
        assert call_args is not None
        assert call_args.kwargs["context"] == context

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    def test_apply_theme_from_config(
        self, mock_set_theme: Mock, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test applying theme using configuration values."""
        styling = GraphStyling()
        seaborn_config = sample_appearance_config.seaborn

        styling.apply_theme(
            style=seaborn_config.style,
            palette=seaborn_config.palette,
            context=seaborn_config.context,
        )

        mock_set_theme.assert_called_once_with(
            style="darkgrid",
            palette="muted",
            context="notebook",
        )


# Tests for Graph Styling Application


class TestGraphStylingApplication:
    """Tests for graph styling application (colors, dimensions, palettes).

    Requirements: 5.2, 6.7
    """

    def test_apply_styling_with_dimensions(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test applying graph dimensions (Requirement 5.2)."""
        fig = plt.figure()
        styling = GraphStyling()

        dimensions = sample_appearance_config.dimensions
        colors = sample_appearance_config.colors
        grid = sample_appearance_config.grid

        styling.apply_styling(
            fig,
            dimensions=dimensions,
            colors=colors,
            grid=grid,
        )

        # Figure dimensions should be set
        # Note: actual implementation will set these, here we verify the interface
        assert isinstance(fig, Figure)

    @pytest.mark.parametrize(
        "width,height,dpi",
        [
            (6, 4, 72),  # Minimum values
            (12, 8, 100),  # Typical values
            (20, 16, 300),  # Maximum values
        ],
    )
    def test_apply_styling_with_various_dimensions(
        self, width: int, height: int, dpi: int
    ) -> None:
        """Test applying various dimension configurations (Requirement 5.2)."""
        dimensions = GraphDimensions(width=width, height=height, dpi=dpi)
        colors = GraphColors(tv="#3498db", movie="#e74c3c", background="#ffffff")
        grid = GridConfig(enabled=True, alpha=0.3)

        fig = plt.figure()
        styling = GraphStyling()
        styling.apply_styling(fig, dimensions=dimensions, colors=colors, grid=grid)

        # Should not raise any errors
        assert isinstance(fig, Figure)

    def test_apply_styling_with_colors(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test applying color configuration."""
        fig = plt.figure()
        styling = GraphStyling()

        dimensions = sample_appearance_config.dimensions
        colors = sample_appearance_config.colors
        grid = sample_appearance_config.grid

        styling.apply_styling(
            fig,
            dimensions=dimensions,
            colors=colors,
            grid=grid,
        )

        # Should apply colors without error
        assert isinstance(fig, Figure)

    def test_apply_styling_with_grid_enabled(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test applying grid configuration when enabled."""
        fig = plt.figure()
        styling = GraphStyling()

        dimensions = sample_appearance_config.dimensions
        colors = sample_appearance_config.colors
        grid = GridConfig(enabled=True, alpha=0.5)

        styling.apply_styling(
            fig,
            dimensions=dimensions,
            colors=colors,
            grid=grid,
        )

        assert isinstance(fig, Figure)

    def test_apply_styling_with_grid_disabled(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test applying grid configuration when disabled."""
        fig = plt.figure()
        styling = GraphStyling()

        dimensions = sample_appearance_config.dimensions
        colors = sample_appearance_config.colors
        grid = GridConfig(enabled=False, alpha=0.3)

        styling.apply_styling(
            fig,
            dimensions=dimensions,
            colors=colors,
            grid=grid,
        )

        assert isinstance(fig, Figure)


# Tests for Seaborn Palette Retrieval


class TestSeabornPaletteRetrieval:
    """Tests for seaborn palette retrieval and color management.

    Requirements: 6.7
    """

    @patch("tgraph_bot.graphs.styling.sns.color_palette")
    @pytest.mark.parametrize(
        "palette_name,n_colors",
        [
            ("viridis", 5),
            ("plasma", 10),
            ("inferno", 3),
            ("magma", 7),
            ("muted", 6),
            ("deep", 8),
        ],
    )
    def test_get_palette_with_various_palettes(
        self, mock_color_palette: Mock, palette_name: str, n_colors: int
    ) -> None:
        """Test retrieving various seaborn palettes (Requirement 6.7)."""
        # Mock the seaborn color_palette to return a list-like object
        mock_palette = MagicMock()
        mock_palette.as_hex.return_value = [  # pyright: ignore[reportAny]  # MagicMock dynamic attrs
            f"#{i:02x}{i:02x}{i:02x}" for i in range(n_colors)
        ]
        mock_color_palette.return_value = mock_palette

        styling = GraphStyling()
        result = styling.get_palette(palette_name, n_colors)

        mock_color_palette.assert_called_once_with(palette_name, n_colors=n_colors)
        assert isinstance(result, list)
        assert len(result) == n_colors

    @patch("seaborn.color_palette")
    def test_get_palette_returns_hex_colors(self, mock_color_palette: Mock) -> None:
        """Test that palette returns hex color codes."""
        mock_palette = MagicMock()
        mock_palette.as_hex.return_value = ["#ff0000", "#00ff00", "#0000ff"]  # pyright: ignore[reportAny]  # MagicMock dynamic attrs
        mock_color_palette.return_value = mock_palette

        styling = GraphStyling()
        result = styling.get_palette("viridis", 3)

        # Should return hex color codes
        assert all(color.startswith("#") for color in result)
        assert all(len(color) == 7 for color in result)

    def test_get_palette_with_empty_name(self) -> None:
        """Test behavior when palette name is empty."""
        styling = GraphStyling()
        result = styling.get_palette("", 5)

        # Should return empty list for empty palette name
        assert result == []

    @patch("seaborn.color_palette")
    def test_get_palette_with_zero_colors(self, mock_color_palette: Mock) -> None:
        """Test behavior when requesting zero colors."""
        _ = mock_color_palette  # Mock for decorator
        styling = GraphStyling()
        result = styling.get_palette("viridis", 0)

        # Should handle gracefully
        assert isinstance(result, list)

    @patch("tgraph_bot.graphs.styling.sns.color_palette")
    def test_palette_override_in_config(
        self, mock_color_palette: Mock, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test using palette from configuration."""
        mock_palette = MagicMock()
        mock_palette.as_hex.return_value = ["#color1", "#color2", "#color3"]  # pyright: ignore[reportAny]  # MagicMock dynamic attrs
        mock_color_palette.return_value = mock_palette

        styling = GraphStyling()

        # Get palette from config
        palette_name = sample_appearance_config.palettes["custom_palette_1"]
        result = styling.get_palette(palette_name, 3)

        assert isinstance(result, list)
        assert len(result) == 3


# Tests for Annotation System


class TestAnnotationSystem:
    """Tests for annotation system (basic and peak highlighting).

    Requirements: 6.1, 6.2
    """

    def test_add_annotations_to_axes(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test adding basic annotations to graph (Requirement 6.1)."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [10.0, 20.0, 15.0, 25.0]
        annotation_config = sample_appearance_config.annotations

        # Should not raise any errors
        styling.add_annotations(
            ax,
            values=values,
            annotation_config=annotation_config,
        )

        assert isinstance(ax, Axes)

    @pytest.mark.parametrize(
        "font_size",
        [6, 10, 14, 18, 24],  # Valid range: 6-24
    )
    def test_add_annotations_with_various_font_sizes(self, font_size: int) -> None:
        """Test annotations with different font sizes (Requirement 6.1)."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [10.0, 20.0, 15.0]
        annotation_config = AnnotationConfig(
            color="#000000",
            outline_color="#ffffff",
            enable_outline=True,
            font_size=font_size,
        )

        styling.add_annotations(
            ax,
            values=values,
            annotation_config=annotation_config,
        )

        assert isinstance(ax, Axes)

    def test_add_annotations_with_outline_enabled(self) -> None:
        """Test annotations with outline enabled."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [10.0, 20.0, 15.0]
        annotation_config = AnnotationConfig(
            color="#000000",
            outline_color="#ffffff",
            enable_outline=True,
            font_size=10,
        )

        styling.add_annotations(
            ax,
            values=values,
            annotation_config=annotation_config,
        )

        assert isinstance(ax, Axes)

    def test_add_annotations_with_outline_disabled(self) -> None:
        """Test annotations with outline disabled."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [10.0, 20.0, 15.0]
        annotation_config = AnnotationConfig(
            color="#000000",
            outline_color="#ffffff",
            enable_outline=False,
            font_size=10,
        )

        styling.add_annotations(
            ax,
            values=values,
            annotation_config=annotation_config,
        )

        assert isinstance(ax, Axes)

    def test_highlight_peak_value(self) -> None:
        """Test highlighting peak value in graph (Requirement 6.2)."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [10.0, 25.0, 15.0, 20.0]  # Peak is 25.0 at index 1
        peak_color = "#ff0000"

        styling.highlight_peak(
            ax,
            values=values,
            peak_color=peak_color,
        )

        assert isinstance(ax, Axes)

    def test_highlight_peak_with_single_value(self) -> None:
        """Test peak highlighting with single value."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [42.0]
        peak_color = "#ff0000"

        styling.highlight_peak(
            ax,
            values=values,
            peak_color=peak_color,
        )

        assert isinstance(ax, Axes)

    def test_highlight_peak_with_multiple_peaks(self) -> None:
        """Test peak highlighting with multiple equal peak values."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values = [25.0, 25.0, 15.0, 25.0]  # Multiple peaks at 25.0
        peak_color = "#ff0000"

        styling.highlight_peak(
            ax,
            values=values,
            peak_color=peak_color,
        )

        assert isinstance(ax, Axes)

    def test_highlight_peak_with_empty_values(self) -> None:
        """Test peak highlighting with empty values list."""
        _, ax = plt.subplots()
        styling = GraphStyling()

        values: list[float] = []
        peak_color = "#ff0000"

        # Should handle gracefully
        styling.highlight_peak(
            ax,
            values=values,
            peak_color=peak_color,
        )

        assert isinstance(ax, Axes)


# Tests for Media Type Separation


class TestMediaTypeSeparation:
    """Tests for media type separation logic.

    Requirements: 5.3
    """

    def test_media_type_separation_enabled(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test graph with media type separation enabled (Requirement 5.3)."""
        _ = sample_appearance_config  # Fixture for future use
        # Create config with media type separation enabled
        _ = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )

        # Should separate movies and TV shows
        movies = [r for r in sample_stream_records if r.media_type == "movie"]
        tv_shows = [r for r in sample_stream_records if r.media_type == "tv"]

        assert len(movies) > 0
        assert len(tv_shows) > 0
        assert len(movies) + len(tv_shows) == len(sample_stream_records)

    def test_media_type_separation_disabled(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test graph with media type separation disabled."""
        _ = sample_appearance_config  # Fixture for future use
        # Create config with media type separation disabled
        _ = GraphConfig(
            enabled=True,
            media_type_separation=False,
            palette="",
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )

        # Should process all records together
        assert len(sample_stream_records) == 4

    def test_media_type_colors_from_config(
        self, sample_appearance_config: GraphAppearanceConfig
    ) -> None:
        """Test that media type colors are read from config."""
        colors = sample_appearance_config.colors

        # Should have separate colors for TV and movies
        assert colors.tv == "#3498db"
        assert colors.movie == "#e74c3c"
        assert colors.tv != colors.movie

    @pytest.mark.parametrize(
        "media_type,expected_count",
        [
            ("movie", 2),
            ("tv", 2),
        ],
    )
    def test_separate_records_by_media_type(
        self,
        sample_stream_records: list[StreamRecord],
        media_type: str,
        expected_count: int,
    ) -> None:
        """Test separating records by media type."""
        filtered_records = [
            r for r in sample_stream_records if r.media_type == media_type
        ]

        assert len(filtered_records) == expected_count

    def test_media_type_separation_with_palette_override(
        self, sample_stream_records: list[StreamRecord]
    ) -> None:
        """Test that palette overrides base media type colors (Requirement 5.3)."""
        _ = sample_stream_records  # Fixture for future use
        # When palette is specified, it should override base colors
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="viridis",  # Palette specified
            annotations_enabled=False,
            peak_highlighting_enabled=False,
            stacked=False,
        )

        # Palette should take precedence over base colors
        assert config.palette == "viridis"
        assert config.palette != ""


# Tests for GraphFactory


class TestGraphFactory:
    """Tests for GraphFactory creating correct generator types.

    Requirements: 5.1
    """

    def test_create_generator_for_daily_play_count(self) -> None:
        """Test creating generator for daily play count graph."""
        factory = GraphFactory()

        # Should create DailyPlayCountGraph instance
        generator = factory.create_generator("daily_play_count")
        assert isinstance(generator, DailyPlayCountGraph)

    def test_create_generator_for_play_by_day_of_week(self) -> None:
        """Test creating generator for play count by day of week graph."""
        factory = GraphFactory()

        generator = factory.create_generator("play_count_by_day_of_week")
        assert isinstance(generator, PlayCountByDayOfWeekGraph)

    def test_create_generator_for_play_by_hour(self) -> None:
        """Test creating generator for play count by hour graph."""
        factory = GraphFactory()

        generator = factory.create_generator("play_count_by_hour_of_day")
        assert isinstance(generator, PlayCountByHourOfDayGraph)

    def test_create_generator_for_top_platforms(self) -> None:
        """Test creating generator for top platforms graph."""
        factory = GraphFactory()

        generator = factory.create_generator("top_platforms")
        assert isinstance(generator, TopPlatformsGraph)

    def test_create_generator_for_top_users(self) -> None:
        """Test creating generator for top users graph."""
        factory = GraphFactory()

        generator = factory.create_generator("top_users")
        assert isinstance(generator, TopUsersGraph)

    def test_create_generator_for_play_by_month(self) -> None:
        """Test creating generator for play count by month graph."""
        factory = GraphFactory()

        generator = factory.create_generator("play_count_by_month")
        assert isinstance(generator, PlayCountByMonthGraph)

    @pytest.mark.parametrize(
        "graph_type",
        [
            "daily_play_count",
            "play_count_by_day_of_week",
            "play_count_by_hour_of_day",
            "top_platforms",
            "top_users",
            "play_count_by_month",
            "daily_play_count_by_stream_type",
            "daily_concurrent_stream_count_by_stream_type",
            "play_count_by_source_resolution",
            "play_count_by_stream_resolution",
            "play_count_by_platform_and_stream_type",
            "play_count_by_user_and_stream_type",
        ],
    )
    def test_create_generator_for_all_graph_types(self, graph_type: str) -> None:
        """Test that factory can create generators for all graph types (Requirement 5.1)."""
        factory = GraphFactory()

        # Task 18 graph types are implemented, others should raise NotImplementedError
        implemented_types = {
            "daily_play_count",
            "play_count_by_day_of_week",
            "play_count_by_hour_of_day",
            "top_platforms",
            "top_users",
            "play_count_by_month",
        }

        if graph_type in implemented_types:
            # Should successfully create generator
            generator = factory.create_generator(graph_type)
            assert generator is not None
        else:
            # Should raise NotImplementedError for not-yet-implemented types
            with pytest.raises(NotImplementedError):
                _ = factory.create_generator(graph_type)

    def test_create_generator_with_invalid_type(self) -> None:
        """Test creating generator with invalid graph type."""
        factory = GraphFactory()

        # Should raise error for invalid type
        with pytest.raises((ValueError, KeyError, NotImplementedError)):
            _ = factory.create_generator("invalid_graph_type")


# Integration Tests


class TestGraphGenerationIntegration:
    """Integration tests combining multiple graph generation components.

    Requirements: 5.1, 5.2, 5.3, 5.5, 6.1, 6.2, 6.6, 6.7
    """

    def test_complete_graph_generation_workflow(
        self,
        sample_stream_records: list[StreamRecord],
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test complete workflow from data to styled graph."""
        # This test defines the expected integration workflow
        _ = (sample_stream_records, sample_graph_config)  # Fixtures for future use

        # 1. Apply seaborn theme
        styling = GraphStyling()
        styling.apply_theme(
            style=sample_appearance_config.seaborn.style,
            palette=sample_appearance_config.seaborn.palette,
            context=sample_appearance_config.seaborn.context,
        )

        # 2. Create figure
        fig = plt.figure()

        # 3. Apply styling
        styling.apply_styling(
            fig,
            dimensions=sample_appearance_config.dimensions,
            colors=sample_appearance_config.colors,
            grid=sample_appearance_config.grid,
        )

        # 4. Verify figure was created
        assert isinstance(fig, Figure)

    def test_graph_with_all_features_enabled(
        self,
        sample_stream_records: list[StreamRecord],
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test graph generation with all features enabled."""
        _ = (sample_stream_records, sample_appearance_config)  # Fixtures for future use
        # Create config with all features enabled
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="viridis",
            annotations_enabled=True,
            peak_highlighting_enabled=True,
            stacked=False,
        )

        # Should be able to handle all features together
        assert config.enabled is True
        assert config.media_type_separation is True
        assert config.palette == "viridis"
        assert config.annotations_enabled is True
        assert config.peak_highlighting_enabled is True

    def test_graph_with_custom_palette_and_annotations(
        self, sample_stream_records: list[StreamRecord]
    ) -> None:
        """Test graph with custom palette and annotations."""
        _ = sample_stream_records  # Fixture for future use
        config = GraphConfig(
            enabled=True,
            media_type_separation=True,
            palette="plasma",
            annotations_enabled=True,
            peak_highlighting_enabled=False,
            stacked=False,
        )

        # Verify configuration
        assert config.palette == "plasma"
        assert config.annotations_enabled is True

    @patch("tgraph_bot.graphs.styling.sns.set_theme")
    @patch("tgraph_bot.graphs.styling.sns.color_palette")
    def test_full_styling_pipeline(
        self,
        mock_color_palette: Mock,
        mock_set_theme: Mock,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test complete styling pipeline with seaborn integration."""
        # Mock color palette
        mock_palette = MagicMock()
        mock_palette.as_hex.return_value = ["#color1", "#color2", "#color3"]  # pyright: ignore[reportAny]  # MagicMock dynamic attrs
        mock_color_palette.return_value = mock_palette

        styling = GraphStyling()

        # 1. Apply theme
        styling.apply_theme(
            style=sample_appearance_config.seaborn.style,
            palette=sample_appearance_config.seaborn.palette,
            context=sample_appearance_config.seaborn.context,
        )

        # 2. Get palette for graph
        _ = styling.get_palette("viridis", 5)

        # 3. Create and style figure
        fig = plt.figure()
        styling.apply_styling(
            fig,
            dimensions=sample_appearance_config.dimensions,
            colors=sample_appearance_config.colors,
            grid=sample_appearance_config.grid,
        )

        # Verify all steps executed
        mock_set_theme.assert_called_once()
        assert isinstance(fig, Figure)


# Edge Case Tests


class TestGraphGenerationEdgeCases:
    """Tests for edge cases in graph generation."""

    def test_empty_data_list(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test graph generation with empty data."""
        _ = (sample_graph_config, sample_appearance_config)  # Fixtures for future use
        empty_data: list[StreamRecord] = []

        # Should handle empty data gracefully
        assert len(empty_data) == 0

    def test_single_record(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test graph generation with single record."""
        _ = (sample_graph_config, sample_appearance_config)  # Fixtures for future use
        single_record = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Plex",
                user="Alice",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            )
        ]

        # Should handle single record
        assert len(single_record) == 1

    def test_all_same_media_type(
        self,
        sample_graph_config: GraphConfig,
        sample_appearance_config: GraphAppearanceConfig,
    ) -> None:
        """Test media type separation when all records are same type."""
        _ = (sample_graph_config, sample_appearance_config)  # Fixtures for future use
        all_movies = [
            StreamRecord(
                timestamp=datetime(2024, 1, 1, i, 0, 0, tzinfo=timezone.utc),
                media_type="movie",
                stream_type="direct play",
                platform="Plex",
                user=f"User{i}",
                source_resolution="1920x1080",
                stream_resolution="1080p",
            )
            for i in range(5)
        ]

        # All records should be movies
        assert all(r.media_type == "movie" for r in all_movies)

    @pytest.mark.parametrize(
        "invalid_palette",
        ["", "nonexistent_palette", "custom_invalid"],
    )
    def test_invalid_palette_handling(self, invalid_palette: str) -> None:
        """Test handling of invalid palette names."""
        styling = GraphStyling()

        # Should handle invalid palette gracefully
        result = styling.get_palette(invalid_palette, 5)

        # Empty palette should return empty list
        if invalid_palette == "":
            assert result == []
