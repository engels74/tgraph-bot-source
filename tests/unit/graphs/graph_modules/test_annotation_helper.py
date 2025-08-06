"""
Unit tests for AnnotationHelper utility.

This module tests the AnnotationHelper class that consolidates annotation
patterns from graph implementations, ensuring proper functionality and
type safety.
"""
# pyright: reportAny=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUninitializedInstanceVariable=false

from typing import final
from unittest.mock import Mock, patch

from src.tgraph_bot.graphs.graph_modules import AnnotationHelper
from src.tgraph_bot.graphs.graph_modules.utils.annotation_helper import (
    AnnotationProtocol,
)


@final
class MockGraph:
    """Mock graph class implementing AnnotationProtocol for testing."""

    annotation_font_size: int
    annotation_color: str
    annotation_outline_color: str
    annotation_outline_enabled: bool
    peak_annotation_color: str
    peak_annotation_text_color: str
    peak_annotations_enabled: bool

    def __init__(self) -> None:
        self.config_values: dict[str, object] = {}
        self.annotation_font_size = 10
        self.annotation_color = "black"
        self.annotation_outline_color = "white"
        self.annotation_outline_enabled = False
        self.peak_annotation_color = "yellow"
        self.peak_annotation_text_color = "black"
        self.peak_annotations_enabled = False

    def get_config_value(self, key: str, default: object = None) -> object:
        return self.config_values.get(key, default)

    def get_annotation_font_size(self) -> int:
        return self.annotation_font_size

    def get_annotation_color(self) -> str:
        return self.annotation_color

    def get_annotation_outline_color(self) -> str:
        return self.annotation_outline_color

    def is_annotation_outline_enabled(self) -> bool:
        return self.annotation_outline_enabled

    def get_peak_annotation_color(self) -> str:
        return self.peak_annotation_color

    def get_peak_annotation_text_color(self) -> str:
        return self.peak_annotation_text_color

    def is_peak_annotations_enabled(self) -> bool:
        return self.peak_annotations_enabled


class TestAnnotationHelper:
    """Test cases for AnnotationHelper utility."""

    mock_graph: MockGraph
    helper: AnnotationHelper
    mock_ax: Mock

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_graph = MockGraph()
        self.helper = AnnotationHelper(self.mock_graph)
        self.mock_ax = Mock()

    def test_init(self) -> None:
        """Test AnnotationHelper initialization."""
        assert self.helper.graph is self.mock_graph

    def test_annotation_protocol_compliance(self) -> None:
        """Test that MockGraph implements AnnotationProtocol."""
        assert isinstance(self.mock_graph, AnnotationProtocol)

    def test_annotate_bar_patches_disabled(self) -> None:
        """Test bar patch annotation when disabled in config."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = False

        self.helper.annotate_bar_patches(self.mock_ax, "TEST_ANNOTATION")

        # Should not access patches when disabled
        assert not self.mock_ax.patches.called

    def test_annotate_bar_patches_enabled_no_patches(self) -> None:
        """Test bar patch annotation with no patches."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True
        self.mock_ax.patches = []

        self.helper.annotate_bar_patches(self.mock_ax, "TEST_ANNOTATION")

        # Should handle empty patches gracefully
        assert len(self.mock_ax.patches) == 0

    @patch("src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger")
    def test_annotate_bar_patches_with_valid_patches(self, _mock_logger: Mock) -> None:
        """Test bar patch annotation with valid patches."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        # Create mock patches
        mock_patch1 = Mock()
        mock_patch1.get_height.return_value = 10.0
        mock_patch1.get_x.return_value = 0.0
        mock_patch1.get_width.return_value = 1.0

        mock_patch2 = Mock()
        mock_patch2.get_height.return_value = 0.0  # Should be skipped
        mock_patch2.get_x.return_value = 1.0
        mock_patch2.get_width.return_value = 1.0

        self.mock_ax.patches = [mock_patch1, mock_patch2]

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_bar_patches(
                self.mock_ax, "TEST_ANNOTATION", offset_y=2.0
            )

            # Should only annotate non-zero patches
            mock_add_text.assert_called_once_with(
                self.mock_ax,
                x=0.5,  # x + width/2
                y=10.0,
                value=10,
                ha="center",
                va="bottom",
                offset_y=2.0,
                fontweight="bold",
            )

    def test_annotate_horizontal_bar_patches_disabled(self) -> None:
        """Test horizontal bar annotation when disabled."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = False

        self.helper.annotate_horizontal_bar_patches(self.mock_ax, "TEST_ANNOTATION")

        assert not self.mock_ax.patches.called

    @patch("src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger")
    def test_annotate_horizontal_bar_patches_enabled(self, _mock_logger: Mock) -> None:
        """Test horizontal bar annotation with valid patches."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        # Create mock patches
        mock_patch = Mock()
        mock_patch.get_width.return_value = 20.0
        mock_patch.get_y.return_value = 0.0
        mock_patch.get_height.return_value = 1.0

        self.mock_ax.patches = [mock_patch]

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_horizontal_bar_patches(
                self.mock_ax, "TEST_ANNOTATION", offset_x_ratio=0.05
            )

            mock_add_text.assert_called_once_with(
                self.mock_ax,
                x=20.0,
                y=0.5,  # y + height/2
                value=20,
                ha="left",
                va="center",
                offset_x=1.0,  # 20.0 * 0.05
                fontweight="normal",
            )

    def test_annotate_stacked_bar_segments_disabled(self) -> None:
        """Test stacked bar annotation when disabled."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = False

        self.helper.annotate_stacked_bar_segments(
            self.mock_ax, "TEST_ANNOTATION", [], []
        )

        # Should return early without processing
        assert True  # Test passes if no exception

    @patch("src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger")
    def test_annotate_stacked_bar_segments_enabled(self, _mock_logger: Mock) -> None:
        """Test stacked bar annotation with valid data."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        # Mock bar containers data
        bar_containers = [
            (Mock(), "movies", [10.0, 5.0]),
            (Mock(), "tv", [15.0, 8.0]),
        ]
        categories = ["Jan", "Feb"]

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_stacked_bar_segments(
                self.mock_ax,
                "TEST_ANNOTATION",
                bar_containers,
                categories,
                include_totals=True,
            )

            # Should call _add_text_annotation for segments and totals
            assert mock_add_text.call_count == 6  # 4 segments + 2 totals

    def test_annotate_peak_value_disabled(self) -> None:
        """Test peak annotation when disabled."""
        self.mock_graph.peak_annotations_enabled = False

        self.helper.annotate_peak_value(self.mock_ax, x=5.0, y=10.0, value=100)

        # Should not call annotate when disabled
        assert not self.mock_ax.annotate.called

    def test_annotate_peak_value_enabled(self) -> None:
        """Test peak annotation when enabled."""
        self.mock_graph.peak_annotations_enabled = True

        self.helper.annotate_peak_value(
            self.mock_ax, x=5.0, y=10.0, value=100, label_prefix="Max"
        )

        self.mock_ax.annotate.assert_called_once()
        call_args = self.mock_ax.annotate.call_args
        assert call_args[0][0] == "Max: 100"
        assert call_args[1]["xy"] == (5.0, 10.0)

    def test_add_text_annotation_with_outline(self) -> None:
        """Test text annotation with outline enabled."""
        self.mock_graph.annotation_outline_enabled = True

        # Create a mock axes that will pass isinstance check
        from matplotlib.axes import Axes

        mock_ax_instance = Mock(spec=Axes)

        with patch("matplotlib.patheffects.Stroke"):
            with patch("matplotlib.patheffects.Normal"):
                self.helper._add_text_annotation(  # pyright: ignore[reportPrivateUsage]
                    mock_ax_instance,
                    x=1.0,
                    y=2.0,
                    value=42,
                    fontsize=12,
                )

                mock_ax_instance.text.assert_called_once()
                call_kwargs = mock_ax_instance.text.call_args[1]
                assert call_kwargs["color"] == "white"
                assert "path_effects" in call_kwargs

    def test_add_text_annotation_without_outline(self) -> None:
        """Test text annotation without outline."""
        self.mock_graph.annotation_outline_enabled = False

        # Create a mock axes that will pass isinstance check
        from matplotlib.axes import Axes

        mock_ax_instance = Mock(spec=Axes)

        self.helper._add_text_annotation(  # pyright: ignore[reportPrivateUsage]
            mock_ax_instance,
            x=1.0,
            y=2.0,
            value=42.0,
            fontsize=12,
        )

        mock_ax_instance.text.assert_called_once()
        call_kwargs = mock_ax_instance.text.call_args[1]
        assert call_kwargs["color"] == "black"
        assert "path_effects" not in call_kwargs

    def test_add_text_annotation_invalid_axes(self) -> None:
        """Test text annotation with invalid axes."""
        invalid_ax = "not_an_axes"

        # Should handle gracefully without error
        self.helper._add_text_annotation(  # pyright: ignore[reportPrivateUsage]
            invalid_ax,  # pyright: ignore[reportArgumentType] # testing invalid input
            x=1.0,
            y=2.0,
            value=42,
        )

        # Test passes if no exception is raised
        assert True

    def test_add_text_annotation_float_value_formatting(self) -> None:
        """Test text annotation value formatting for floats."""
        # Create a mock axes that will pass isinstance check
        from matplotlib.axes import Axes

        mock_ax_instance = Mock(spec=Axes)

        # Test integer float
        self.helper._add_text_annotation(mock_ax_instance, x=1.0, y=2.0, value=42.0)  # pyright: ignore[reportPrivateUsage]

        call_args = mock_ax_instance.text.call_args[0]
        assert call_args[2] == "42"  # Should format as integer

        mock_ax_instance.reset_mock()

        # Test non-integer float
        self.helper._add_text_annotation(mock_ax_instance, x=1.0, y=2.0, value=42.5)  # pyright: ignore[reportPrivateUsage]

        call_args = mock_ax_instance.text.call_args[0]
        assert call_args[2] == "42.5"  # Should keep decimal

    @patch("src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger")
    def test_error_handling_in_methods(self, mock_logger: Mock) -> None:
        """Test error handling in annotation methods."""
        # Test with patches that raise exceptions
        mock_patch = Mock()
        mock_patch.get_height.side_effect = Exception("Test error")
        self.mock_ax.patches = [mock_patch]

        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        # Should handle exceptions gracefully
        self.helper.annotate_bar_patches(self.mock_ax, "TEST_ANNOTATION")

        # Should log warning
        mock_logger.warning.assert_called_once()
        assert "Failed to annotate bar patches" in str(mock_logger.warning.call_args)

    def test_annotate_line_points_disabled(self) -> None:
        """Test line points annotation when disabled in config."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = False

        x_data = [0, 1, 2, 3]
        y_data = [10, 20, 15, 25]

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax, "TEST_ANNOTATION", x_data, y_data
            )

            # Should not call _add_text_annotation when disabled
            mock_add_text.assert_not_called()

    def test_annotate_line_points_enabled_valid_data(self) -> None:
        """Test line points annotation with valid data."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2, 3]
        y_data = [10, 20, 15, 25]

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax, "TEST_ANNOTATION", x_data, y_data, offset_y=3.0
            )

            # Should call _add_text_annotation for each data point
            assert mock_add_text.call_count == 4

            # Check the first call
            first_call = mock_add_text.call_args_list[0]
            args, kwargs = first_call
            assert len(args) == 1  # Only ax as positional arg
            assert kwargs["x"] == 0.0  # x position
            assert kwargs["y"] == 10.0  # y position
            assert kwargs["value"] == 10  # value
            assert kwargs["offset_y"] == 3.0

    def test_annotate_line_points_with_threshold(self) -> None:
        """Test line points annotation with minimum value threshold."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2, 3]
        y_data = [1, 20, 5, 25]  # First and third values below threshold

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax,
                "TEST_ANNOTATION",
                x_data,
                y_data,
                min_value_threshold=10.0,
            )

            # Should only annotate values above threshold (20 and 25)
            assert mock_add_text.call_count == 2

            # Check that only values > 10 were annotated
            call_values = [call[1]["value"] for call in mock_add_text.call_args_list]
            assert call_values == [20, 25]

    def test_annotate_line_points_mismatched_data_length(self) -> None:
        """Test line points annotation with mismatched x and y data lengths."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2]
        y_data = [10, 20]  # Different length

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            with patch(
                "src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger"
            ) as mock_logger:
                self.helper.annotate_line_points(
                    self.mock_ax, "TEST_ANNOTATION", x_data, y_data
                )

                # Should not call _add_text_annotation and log warning
                mock_add_text.assert_not_called()
                mock_logger.warning.assert_called_once()

    def test_annotate_line_points_with_zero_values(self) -> None:
        """Test line points annotation with zero values."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2, 3]
        y_data = [0, 20, 0, 25]  # Include zero values

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax, "TEST_ANNOTATION", x_data, y_data
            )

            # Should only annotate non-zero values (20 and 25)
            assert mock_add_text.call_count == 2

            # Check that only non-zero values were annotated
            call_values = [call[1]["value"] for call in mock_add_text.call_args_list]
            assert call_values == [20, 25]

    def test_annotate_line_points_float_conversion(self) -> None:
        """Test line points annotation with float values that should be converted to integers."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2]
        y_data = [10.0, 20.5, 15.0]  # Mix of integer floats and decimal floats

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax, "TEST_ANNOTATION", x_data, y_data
            )

            # Should convert integer floats to int, keep decimal floats as-is
            assert mock_add_text.call_count == 3

            call_values = [call[1]["value"] for call in mock_add_text.call_args_list]
            assert call_values == [10, 20.5, 15]  # 10.0 -> 10, 15.0 -> 15

    @patch("src.tgraph_bot.graphs.graph_modules.utils.annotation_helper.logger")
    def test_annotate_line_points_error_handling(self, mock_logger: Mock) -> None:
        """Test error handling in annotate_line_points method."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [0, 1, 2]
        y_data = [10, 20, 15]

        # Mock _add_text_annotation to raise an exception
        with patch.object(
            self.helper, "_add_text_annotation", side_effect=Exception("Test error")
        ):
            self.helper.annotate_line_points(
                self.mock_ax, "TEST_ANNOTATION", x_data, y_data
            )

            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "Failed to annotate line points" in str(
                mock_logger.warning.call_args
            )

    def test_annotate_line_points_with_offset_x(self) -> None:
        """Test line points annotation with x-offset for horizontal annotations."""
        self.mock_graph.config_values["TEST_ANNOTATION"] = True

        x_data = [10, 20, 30]
        y_data = [1, 2, 3]  # Horizontal bar chart style coordinates (non-zero)

        with patch.object(self.helper, "_add_text_annotation") as mock_add_text:
            self.helper.annotate_line_points(
                self.mock_ax,
                "TEST_ANNOTATION",
                x_data,
                y_data,
                offset_x=5.0,
                ha="left",
                va="center",
            )

            # Should call _add_text_annotation with correct offset_x
            assert mock_add_text.call_count == 3

            # Check the first call has offset_x
            first_call = mock_add_text.call_args_list[0]
            _, kwargs = first_call
            assert kwargs["offset_x"] == 5.0
            assert kwargs["ha"] == "left"
            assert kwargs["va"] == "center"
