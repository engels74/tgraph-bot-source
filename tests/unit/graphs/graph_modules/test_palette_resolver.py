"""
Tests for the PaletteResolver utility in TGraph Bot.

This module tests the priority-based color and palette resolution system that
handles conflicts between custom palette configurations and media type separation.
"""

from unittest.mock import Mock, patch

from src.tgraph_bot.graphs.graph_modules.core.palette_resolver import (
    PaletteResolver,
    ColorStrategy,
    ColorResolution,
)
from src.tgraph_bot.graphs.graph_modules.types.constants import DEFAULT_COLORS
from tests.utils.graph_helpers import (
    create_test_config_minimal,
    create_test_config_comprehensive,
)
from tests.utils.test_helpers import create_test_config_with_nested_overrides


class TestColorStrategy:
    """Test cases for the ColorStrategy enum."""

    def test_color_strategy_values(self) -> None:
        """Test that ColorStrategy enum has the expected values."""
        assert ColorStrategy.PALETTE
        assert ColorStrategy.SEPARATION
        assert ColorStrategy.DEFAULT


class TestColorResolution:
    """Test cases for the ColorResolution NamedTuple."""

    def test_color_resolution_creation(self) -> None:
        """Test that ColorResolution can be created with required fields."""
        resolution = ColorResolution(
            strategy=ColorStrategy.PALETTE,
            use_palette=True,
            palette_name="viridis",
            palette_colors=["#ff0000", "#00ff00"],
            fallback_colors=["#0000ff"],
        )

        assert resolution.strategy == ColorStrategy.PALETTE
        assert resolution.use_palette is True
        assert resolution.palette_name == "viridis"
        assert resolution.palette_colors == ["#ff0000", "#00ff00"]
        assert resolution.fallback_colors == ["#0000ff"]
        assert resolution.media_type_colors is None

    def test_color_resolution_defaults(self) -> None:
        """Test ColorResolution with default values."""
        resolution = ColorResolution(
            strategy=ColorStrategy.DEFAULT,
            use_palette=False,
        )

        assert resolution.strategy == ColorStrategy.DEFAULT
        assert resolution.use_palette is False
        assert resolution.palette_name is None
        assert resolution.palette_colors is None
        assert resolution.fallback_colors is None
        assert resolution.media_type_colors is None


class TestPaletteResolver:
    """Test cases for the PaletteResolver class."""

    def test_initialization_with_no_config(self) -> None:
        """Test PaletteResolver initialization with no configuration."""
        resolver = PaletteResolver()
        assert resolver.config is None

    def test_initialization_with_config(self) -> None:
        """Test PaletteResolver initialization with TGraphBotConfig."""
        config = create_test_config_minimal()
        resolver = PaletteResolver(config=config)
        assert resolver.config == config

    def test_initialization_with_dict_config(self) -> None:
        """Test PaletteResolver initialization with TGraphBotConfig."""
        config = create_test_config_with_nested_overrides(ENABLE_MEDIA_TYPE_SEPARATION=True)
        resolver = PaletteResolver(config=config)
        assert resolver.config == config

    def test_graph_type_to_palette_key_mapping(self) -> None:
        """Test that all expected graph types are mapped to palette keys."""
        expected_mappings = {
            "PlayCountByHourOfDayGraph": "graphs.appearance.palettes.play_count_by_hourofday",
            "Top10UsersGraph": "graphs.appearance.palettes.top_10_users",
            "DailyPlayCountGraph": "graphs.appearance.palettes.daily_play_count",
            "PlayCountByDayOfWeekGraph": "graphs.appearance.palettes.play_count_by_dayofweek",
            "Top10PlatformsGraph": "graphs.appearance.palettes.top_10_platforms",
            "PlayCountByMonthGraph": "graphs.appearance.palettes.play_count_by_month",
        }

        assert PaletteResolver.GRAPH_TYPE_TO_PALETTE_KEY == expected_mappings

    def test_resolve_color_strategy_no_config(self) -> None:
        """Test resolve_color_strategy with no configuration."""
        resolver = PaletteResolver()
        resolution = resolver.resolve_color_strategy("PlayCountByHourOfDayGraph")

        assert resolution.strategy == ColorStrategy.DEFAULT
        assert resolution.use_palette is False
        assert resolution.palette_name is None
        assert resolution.fallback_colors == [DEFAULT_COLORS.TV_COLOR]

    def test_resolve_color_strategy_palette_priority(self) -> None:
        """Test that custom palette has highest priority."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_hourofday = "viridis"
        config.graphs.features.media_type_separation = True

        resolver = PaletteResolver(config=config)

        with patch.object(resolver, "_is_valid_seaborn_palette", return_value=True):
            with patch.object(
                resolver, "_get_palette_colors", return_value=["#ff0000", "#00ff00"]
            ):
                resolution = resolver.resolve_color_strategy(
                    "PlayCountByHourOfDayGraph"
                )

        assert resolution.strategy == ColorStrategy.PALETTE
        assert resolution.use_palette is True
        assert resolution.palette_name == "viridis"
        assert resolution.palette_colors == ["#ff0000", "#00ff00"]

    def test_resolve_color_strategy_separation_priority(self) -> None:
        """Test that media type separation has medium priority."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_hourofday = ""  # Empty palette
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#0000ff"
        config.graphs.appearance.colors.movie = "#ff0000"

        resolver = PaletteResolver(config=config)
        resolution = resolver.resolve_color_strategy("PlayCountByHourOfDayGraph")

        assert resolution.strategy == ColorStrategy.SEPARATION
        assert resolution.use_palette is False
        assert resolution.media_type_colors == {"tv": "#0000ff", "movie": "#ff0000"}
        assert resolution.fallback_colors == ["#0000ff", "#ff0000"]

    def test_resolve_color_strategy_default_priority(self) -> None:
        """Test that default colors have lowest priority."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_hourofday = ""  # Empty palette
        config.graphs.features.media_type_separation = False

        resolver = PaletteResolver(config=config)
        resolution = resolver.resolve_color_strategy("PlayCountByHourOfDayGraph")

        assert resolution.strategy == ColorStrategy.DEFAULT
        assert resolution.use_palette is False
        assert resolution.fallback_colors == [DEFAULT_COLORS.TV_COLOR]

    def test_should_palette_override_separation_true(self) -> None:
        """Test that palette should override separation when valid palette is configured."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.top_10_users = "plasma"

        resolver = PaletteResolver(config=config)

        with patch.object(resolver, "_is_valid_seaborn_palette", return_value=True):
            result = resolver.should_palette_override_separation("Top10UsersGraph")

        assert result is True

    def test_should_palette_override_separation_false_empty_palette(self) -> None:
        """Test that empty palette should not override separation."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.top_10_users = ""

        resolver = PaletteResolver(config=config)
        result = resolver.should_palette_override_separation("Top10UsersGraph")

        assert result is False

    def test_should_palette_override_separation_false_invalid_palette(self) -> None:
        """Test that invalid palette should not override separation."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.top_10_users = "invalid_palette"

        resolver = PaletteResolver(config=config)

        with patch.object(resolver, "_is_valid_seaborn_palette", return_value=False):
            result = resolver.should_palette_override_separation("Top10UsersGraph")

        assert result is False

    def test_should_palette_override_separation_unknown_graph_type(self) -> None:
        """Test that unknown graph types return False."""
        config = create_test_config_comprehensive()
        resolver = PaletteResolver(config=config)

        result = resolver.should_palette_override_separation("UnknownGraphType")
        assert result is False

    def test_get_effective_colors_palette_priority(self) -> None:
        """Test get_effective_colors returns palette colors when palette is configured."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.daily_play_count = "inferno"

        resolver = PaletteResolver(config=config)

        with patch.object(resolver, "_is_valid_seaborn_palette", return_value=True):
            with patch.object(
                resolver,
                "_get_palette_colors",
                return_value=["#ff0000", "#00ff00", "#0000ff"],
            ):
                colors = resolver.get_effective_colors("DailyPlayCountGraph")

        assert colors == ["#ff0000", "#00ff00", "#0000ff"]

    def test_get_effective_colors_separation_priority(self) -> None:
        """Test get_effective_colors returns separation colors when no palette."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.daily_play_count = ""
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#1111ff"
        config.graphs.appearance.colors.movie = "#ff1111"

        resolver = PaletteResolver(config=config)
        colors = resolver.get_effective_colors("DailyPlayCountGraph")

        assert colors == ["#1111ff", "#ff1111"]

    def test_get_effective_colors_default_fallback(self) -> None:
        """Test get_effective_colors returns default when no other options."""
        resolver = PaletteResolver()
        colors = resolver.get_effective_colors("DailyPlayCountGraph")

        assert colors == [DEFAULT_COLORS.TV_COLOR]

    def test_get_palette_for_graph_type_with_tgraph_config(self) -> None:
        """Test _get_palette_for_graph_type with TGraphBotConfig object."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_month = "turbo"

        resolver = PaletteResolver(config=config)
        palette = resolver._get_palette_for_graph_type("PlayCountByMonthGraph")  # pyright: ignore[reportPrivateUsage]

        assert palette == "turbo"

    def test_get_palette_for_graph_type_with_dict_config(self) -> None:
        """Test _get_palette_for_graph_type with TGraphBotConfig."""
        config = create_test_config_with_nested_overrides(
            TOP_10_PLATFORMS_PALETTE="cividis"
        )

        resolver = PaletteResolver(config=config)
        palette = resolver._get_palette_for_graph_type("Top10PlatformsGraph")  # pyright: ignore[reportPrivateUsage]

        assert palette == "cividis"

    def test_get_palette_for_graph_type_empty_string(self) -> None:
        """Test _get_palette_for_graph_type with empty string returns None."""
        config = create_test_config_with_nested_overrides(
            TOP_10_PLATFORMS_PALETTE=""
        )

        resolver = PaletteResolver(config=config)
        palette = resolver._get_palette_for_graph_type("Top10PlatformsGraph")  # pyright: ignore[reportPrivateUsage]

        assert palette is None

    def test_get_palette_for_graph_type_whitespace_string(self) -> None:
        """Test _get_palette_for_graph_type with whitespace string returns None."""
        config = create_test_config_with_nested_overrides(
            TOP_10_PLATFORMS_PALETTE="   "
        )

        resolver = PaletteResolver(config=config)
        palette = resolver._get_palette_for_graph_type("Top10PlatformsGraph")  # pyright: ignore[reportPrivateUsage]

        assert palette is None

    def test_get_palette_for_graph_type_unknown_graph(self) -> None:
        """Test _get_palette_for_graph_type with unknown graph type returns None."""
        config = create_test_config_comprehensive()
        resolver = PaletteResolver(config=config)

        palette = resolver._get_palette_for_graph_type("UnknownGraphType")  # pyright: ignore[reportPrivateUsage]
        assert palette is None

    def test_is_media_type_separation_enabled_true(self) -> None:
        """Test _is_media_type_separation_enabled returns True when enabled."""
        config = create_test_config_comprehensive()
        config.graphs.features.media_type_separation = True

        resolver = PaletteResolver(config=config)
        result = resolver._is_media_type_separation_enabled()  # pyright: ignore[reportPrivateUsage]

        assert result is True

    def test_is_media_type_separation_enabled_false(self) -> None:
        """Test _is_media_type_separation_enabled returns False when disabled."""
        config = create_test_config_comprehensive()
        config.graphs.features.media_type_separation = False

        resolver = PaletteResolver(config=config)
        result = resolver._is_media_type_separation_enabled()  # pyright: ignore[reportPrivateUsage]

        assert result is False

    def test_is_media_type_separation_enabled_no_config(self) -> None:
        """Test _is_media_type_separation_enabled returns False with no config."""
        resolver = PaletteResolver()
        result = resolver._is_media_type_separation_enabled()  # pyright: ignore[reportPrivateUsage]

        assert result is False

    def test_is_media_type_separation_enabled_dict_config(self) -> None:
        """Test _is_media_type_separation_enabled with TGraphBotConfig."""
        config = create_test_config_with_nested_overrides(ENABLE_MEDIA_TYPE_SEPARATION=True)

        resolver = PaletteResolver(config=config)
        result = resolver._is_media_type_separation_enabled()  # pyright: ignore[reportPrivateUsage]

        assert result is True

    def test_get_media_type_colors_with_custom_colors(self) -> None:
        """Test _get_media_type_colors returns custom configured colors."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.colors.tv = "#ff1111"
        config.graphs.appearance.colors.movie = "#22ff22"

        resolver = PaletteResolver(config=config)
        colors = resolver._get_media_type_colors()  # pyright: ignore[reportPrivateUsage]

        assert colors == {
            "tv": "#ff1111",
            "movie": "#22ff22",
        }

    def test_get_media_type_colors_with_defaults(self) -> None:
        """Test _get_media_type_colors returns defaults when no config."""
        resolver = PaletteResolver()
        colors = resolver._get_media_type_colors()  # pyright: ignore[reportPrivateUsage]

        assert colors == {
            "tv": DEFAULT_COLORS.TV_COLOR,
            "movie": DEFAULT_COLORS.MOVIE_COLOR,
        }

    def test_get_media_type_colors_dict_config(self) -> None:
        """Test _get_media_type_colors with TGraphBotConfig."""
        config = create_test_config_with_nested_overrides(
            TV_COLOR="#33dd33",
            MOVIE_COLOR="#dd3333"
        )

        resolver = PaletteResolver(config=config)
        colors = resolver._get_media_type_colors()  # pyright: ignore[reportPrivateUsage]

        assert colors == {
            "tv": "#33dd33",
            "movie": "#dd3333",
        }

    def test_get_fallback_colors_with_separation_enabled(self) -> None:
        """Test _get_fallback_colors returns media type colors when separation is enabled."""
        config = create_test_config_comprehensive()
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#44bb44"
        config.graphs.appearance.colors.movie = "#bb4444"

        resolver = PaletteResolver(config=config)
        colors = resolver._get_fallback_colors()  # pyright: ignore[reportPrivateUsage]

        assert colors == ["#44bb44", "#bb4444"]

    def test_get_fallback_colors_with_separation_disabled(self) -> None:
        """Test _get_fallback_colors returns default TV color when separation is disabled."""
        config = create_test_config_comprehensive()
        config.graphs.features.media_type_separation = False

        resolver = PaletteResolver(config=config)
        colors = resolver._get_fallback_colors()  # pyright: ignore[reportPrivateUsage]

        assert colors == [DEFAULT_COLORS.TV_COLOR]

    @patch("seaborn.color_palette")
    @patch("matplotlib.colors.to_hex")
    def test_get_palette_colors_success(
        self, mock_to_hex: Mock, mock_color_palette: Mock
    ) -> None:
        """Test _get_palette_colors successfully generates colors."""
        # Mock seaborn palette colors (RGB tuples)
        mock_color_palette.return_value = [
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ]
        # Mock hex conversion
        mock_to_hex.side_effect = ["#ff0000", "#00ff00", "#0000ff"]

        resolver = PaletteResolver()
        colors = resolver._get_palette_colors("viridis", n_colors=3)  # pyright: ignore[reportPrivateUsage]

        assert colors == ["#ff0000", "#00ff00", "#0000ff"]
        mock_color_palette.assert_called_once_with("viridis", n_colors=3)
        assert mock_to_hex.call_count == 3

    @patch("seaborn.color_palette")
    def test_get_palette_colors_failure(self, mock_color_palette: Mock) -> None:
        """Test _get_palette_colors handles errors gracefully."""
        mock_color_palette.side_effect = Exception("Palette not found")

        config = create_test_config_comprehensive()
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#ee4444"
        config.graphs.appearance.colors.movie = "#44ee44"

        resolver = PaletteResolver(config=config)
        colors = resolver._get_palette_colors("invalid_palette")  # pyright: ignore[reportPrivateUsage]

        # Should return fallback colors
        assert colors == ["#ee4444", "#44ee44"]

    def test_is_valid_seaborn_palette_known_palette(self) -> None:
        """Test _is_valid_seaborn_palette returns True for known palettes."""
        resolver = PaletteResolver()

        known_palettes = ["viridis", "plasma", "inferno", "magma", "Set1", "tab10"]
        for palette in known_palettes:
            assert resolver._is_valid_seaborn_palette(palette) is True  # pyright: ignore[reportPrivateUsage]

    @patch("seaborn.color_palette")
    def test_is_valid_seaborn_palette_loadable_palette(
        self, mock_color_palette: Mock
    ) -> None:
        """Test _is_valid_seaborn_palette returns True for loadable unknown palettes."""
        mock_color_palette.return_value = [(1.0, 0.0, 0.0)]

        resolver = PaletteResolver()
        result = resolver._is_valid_seaborn_palette("custom_palette")  # pyright: ignore[reportPrivateUsage]

        assert result is True
        mock_color_palette.assert_called_once_with("custom_palette", n_colors=1)

    @patch("seaborn.color_palette")
    def test_is_valid_seaborn_palette_invalid_palette(
        self, mock_color_palette: Mock
    ) -> None:
        """Test _is_valid_seaborn_palette returns False for invalid palettes."""
        mock_color_palette.side_effect = Exception("Invalid palette")

        resolver = PaletteResolver()
        result = resolver._is_valid_seaborn_palette("definitely_invalid_palette")  # pyright: ignore[reportPrivateUsage]

        assert result is False


class TestPaletteResolverIntegration:
    """Integration tests for PaletteResolver with real configuration scenarios."""

    def test_full_priority_system_palette_wins(self) -> None:
        """Test complete priority system where palette overrides separation."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_dayofweek = "magma"
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#5555aa"
        config.graphs.appearance.colors.movie = "#aa5555"

        resolver = PaletteResolver(config=config)

        # Mock palette validation and color generation
        with patch.object(resolver, "_is_valid_seaborn_palette", return_value=True):
            with patch.object(
                resolver, "_get_palette_colors", return_value=["#palette1", "#palette2"]
            ):
                # Test priority check
                assert (
                    resolver.should_palette_override_separation(
                        "PlayCountByDayOfWeekGraph"
                    )
                    is True
                )

                # Test strategy resolution
                resolution = resolver.resolve_color_strategy(
                    "PlayCountByDayOfWeekGraph"
                )
                assert resolution.strategy == ColorStrategy.PALETTE
                assert resolution.use_palette is True
                assert resolution.palette_name == "magma"

                # Test effective colors
                colors = resolver.get_effective_colors("PlayCountByDayOfWeekGraph")
                assert colors == ["#palette1", "#palette2"]

    def test_full_priority_system_separation_wins(self) -> None:
        """Test complete priority system where separation is used (no palette)."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_dayofweek = ""  # No palette
        config.graphs.features.media_type_separation = True
        config.graphs.appearance.colors.tv = "#6666bb"
        config.graphs.appearance.colors.movie = "#bb6666"

        resolver = PaletteResolver(config=config)

        # Test priority check
        assert (
            resolver.should_palette_override_separation("PlayCountByDayOfWeekGraph")
            is False
        )

        # Test strategy resolution
        resolution = resolver.resolve_color_strategy("PlayCountByDayOfWeekGraph")
        assert resolution.strategy == ColorStrategy.SEPARATION
        assert resolution.use_palette is False
        assert resolution.media_type_colors == {"tv": "#6666bb", "movie": "#bb6666"}

        # Test effective colors
        colors = resolver.get_effective_colors("PlayCountByDayOfWeekGraph")
        assert colors == ["#6666bb", "#bb6666"]

    def test_full_priority_system_default_wins(self) -> None:
        """Test complete priority system where defaults are used."""
        config = create_test_config_comprehensive()
        config.graphs.appearance.palettes.play_count_by_dayofweek = ""  # No palette
        config.graphs.features.media_type_separation = False  # No separation

        resolver = PaletteResolver(config=config)

        # Test priority check
        assert (
            resolver.should_palette_override_separation("PlayCountByDayOfWeekGraph")
            is False
        )

        # Test strategy resolution
        resolution = resolver.resolve_color_strategy("PlayCountByDayOfWeekGraph")
        assert resolution.strategy == ColorStrategy.DEFAULT
        assert resolution.use_palette is False

        # Test effective colors
        colors = resolver.get_effective_colors("PlayCountByDayOfWeekGraph")
        assert colors == [DEFAULT_COLORS.TV_COLOR]
