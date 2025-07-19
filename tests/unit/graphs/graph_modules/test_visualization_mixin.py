"""
Test module for the VisualizationMixin class.

This module tests the VisualizationMixin functionality including:
- Seaborn style configuration with grid awareness
- Standard title and axis setup
- Empty data message display
- Bar chart annotations
- Layout finalization
- Legend configuration
- Time series axis setup
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig
from unittest.mock import MagicMock, patch

import matplotlib.axes
import matplotlib.pyplot as plt

from src.tgraph_bot.graphs.graph_modules import VisualizationMixin
from tests.utils.graph_helpers import matplotlib_cleanup


class MockGraphWithVisualization(VisualizationMixin):
    """Mock graph class that implements VisualizationMixin for testing."""

    def __init__(self, config: "TGraphBotConfig | dict[str, Any] | None" = None, grid_enabled: bool = True):
        """Initialize mock graph with optional configuration."""
        self.config: "TGraphBotConfig | dict[str, Any] | None" = config
        self.figure: Any | None = None
        self.axes: matplotlib.axes.Axes | None = None
        self._grid_enabled: bool = grid_enabled
        self._title: str = "Test Graph"

    def get_grid_enabled(self) -> bool:
        """Return grid enabled status."""
        return self._grid_enabled

    def get_title(self) -> str:
        """Return graph title."""
        return self._title

    def setup_figure(self) -> tuple[Any, Any]:
        """Set up matplotlib figure and axes."""
        self.figure, self.axes = plt.subplots(figsize=(10, 6))
        return self.figure, self.axes

    def cleanup(self) -> None:
        """Clean up matplotlib resources."""
        if self.figure is not None:
            plt.close(self.figure)
            self.figure = None
            self.axes = None


class TestVisualizationMixin:
    """Test cases for the VisualizationMixin class."""

    def test_configure_seaborn_style_with_grid_enabled(self) -> None:
        """Test seaborn style configuration with grid enabled."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization(grid_enabled=True)
            
            with patch('seaborn.set_style') as mock_set_style:
                graph.configure_seaborn_style_with_grid()
                mock_set_style.assert_called_once_with("whitegrid")

    def test_configure_seaborn_style_with_grid_disabled(self) -> None:
        """Test seaborn style configuration with grid disabled."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization(grid_enabled=False)
            
            with patch('seaborn.set_style') as mock_set_style:
                graph.configure_seaborn_style_with_grid()
                mock_set_style.assert_called_once_with("white")

    def test_setup_standard_title_and_axes_with_defaults(self) -> None:
        """Test standard title and axes setup with default parameters."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Test with default title
            graph.setup_standard_title_and_axes()
            
            # Verify title was set
            assert graph.axes is not None
            title = graph.axes.get_title()
            assert title == "Test Graph"
            
            graph.cleanup()

    def test_setup_standard_title_and_axes_with_custom_values(self) -> None:
        """Test standard title and axes setup with custom parameters."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Test with custom values
            graph.setup_standard_title_and_axes(
                title="Custom Title",
                xlabel="X Label",
                ylabel="Y Label",
                title_fontsize=20,
                label_fontsize=14
            )
            
            # Verify title and labels were set
            assert graph.axes is not None
            title = graph.axes.get_title()
            xlabel = graph.axes.get_xlabel()
            ylabel = graph.axes.get_ylabel()
            
            assert title == "Custom Title"
            assert xlabel == "X Label"
            assert ylabel == "Y Label"
            
            graph.cleanup()

    def test_setup_standard_title_and_axes_with_no_axes(self) -> None:
        """Test standard title and axes setup when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.setup_standard_title_and_axes()
                mock_logger.warning.assert_called_once_with("Cannot setup title and axes: axes is None")

    def test_display_no_data_message_with_defaults(self) -> None:
        """Test empty data message display with default parameters."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the text method to verify it was called
            with patch.object(graph.axes, 'text') as mock_text:
                graph.display_no_data_message()
                
                # Verify text was called with correct parameters
                mock_text.assert_called_once_with(
                    0.5, 0.5,
                    "No data available\nfor the selected time period",
                    ha="center", va="center",
                    transform=graph.axes.transAxes,
                    fontsize=16,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7)
                )
            
            graph.cleanup()

    def test_display_no_data_message_with_custom_parameters(self) -> None:
        """Test empty data message display with custom parameters."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the text method to verify it was called
            with patch.object(graph.axes, 'text') as mock_text:
                graph.display_no_data_message(
                    message="Custom message",
                    fontsize=20,
                    alpha=0.5
                )
                
                # Verify text was called with custom parameters
                mock_text.assert_called_once_with(
                    0.5, 0.5,
                    "Custom message",
                    ha="center", va="center",
                    transform=graph.axes.transAxes,
                    fontsize=20,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.5)
                )
            
            graph.cleanup()

    def test_display_no_data_message_with_no_axes(self) -> None:
        """Test empty data message display when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.display_no_data_message()
                mock_logger.warning.assert_called_once_with("Cannot display no data message: axes is None")

    def test_setup_figure_with_seaborn_grid(self) -> None:
        """Test combined figure setup with seaborn grid styling."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization(grid_enabled=True)
            
            with patch('seaborn.set_style') as mock_set_style:
                figure, axes = graph.setup_figure_with_seaborn_grid()
                
                # Verify figure and axes were created
                assert figure is not None
                assert axes is not None
                assert graph.figure is figure
                assert graph.axes is axes
                
                # Verify seaborn style was applied
                mock_set_style.assert_called_once_with("whitegrid")
            
            graph.cleanup()

    def test_finalize_plot_layout_with_figure(self) -> None:
        """Test plot layout finalization with valid figure."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock tight_layout to verify it was called
            with patch.object(graph.figure, 'tight_layout') as mock_tight_layout:
                graph.finalize_plot_layout()
                mock_tight_layout.assert_called_once()
            
            graph.cleanup()

    def test_finalize_plot_layout_with_no_figure(self) -> None:
        """Test plot layout finalization when figure is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so figure remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.finalize_plot_layout()
                mock_logger.warning.assert_called_once_with("Cannot finalize layout: figure is None or not available")

    def test_configure_standard_grid(self) -> None:
        """Test standard grid configuration."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the grid method to verify it was called
            with patch.object(graph.axes, 'grid') as mock_grid:
                graph.configure_standard_grid(alpha=0.5)
                mock_grid.assert_called_once_with(True, alpha=0.5)
            
            graph.cleanup()

    def test_configure_standard_grid_with_no_axes(self) -> None:
        """Test standard grid configuration when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.configure_standard_grid()
                mock_logger.warning.assert_called_once_with("Cannot configure grid: axes is None")

    def test_setup_bar_chart_annotations(self) -> None:
        """Test bar chart annotation setup."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Create mock bars
            mock_bars = [MagicMock(), MagicMock()]
            mock_bars[0].get_height.return_value = 10
            mock_bars[0].get_x.return_value = 0
            mock_bars[0].get_width.return_value = 1
            mock_bars[1].get_height.return_value = 20
            mock_bars[1].get_x.return_value = 1
            mock_bars[1].get_width.return_value = 1
            
            values = [10.0, 20.0]
            
            # Mock the annotate method
            with patch.object(graph.axes, 'annotate') as mock_annotate:
                graph.setup_bar_chart_annotations(mock_bars, values)
                
                # Verify annotate was called for each bar
                assert mock_annotate.call_count == 2
                
                # Check first annotation call
                first_call = mock_annotate.call_args_list[0]
                assert first_call[0][0] == "10"  # formatted value
                assert first_call[1]['xy'] == (0.5, 10)  # x center, height
                
                # Check second annotation call
                second_call = mock_annotate.call_args_list[1]
                assert second_call[0][0] == "20"  # formatted value
                assert second_call[1]['xy'] == (1.5, 20)  # x center, height
            
            graph.cleanup()

    def test_setup_bar_chart_annotations_with_no_axes(self) -> None:
        """Test bar chart annotation setup when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.setup_bar_chart_annotations([], [])
                mock_logger.warning.assert_called_once_with("Cannot setup bar annotations: axes is None")

    def test_apply_seaborn_palette(self) -> None:
        """Test seaborn palette application."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            
            with patch('seaborn.set_palette') as mock_set_palette:
                graph.apply_seaborn_palette("viridis")
                mock_set_palette.assert_called_once_with("viridis")

    def test_apply_seaborn_palette_with_default(self) -> None:
        """Test seaborn palette application with default palette."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            
            with patch('seaborn.set_palette') as mock_set_palette:
                graph.apply_seaborn_palette()
                mock_set_palette.assert_called_once_with("husl")

    def test_configure_tick_parameters(self) -> None:
        """Test tick parameter configuration."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the tick_params method
            with patch.object(graph.axes, 'tick_params') as mock_tick_params:
                graph.configure_tick_parameters(axis="x", labelsize=12, rotation=45)
                mock_tick_params.assert_called_once_with(axis="x", labelsize=12, rotation=45)
            
            graph.cleanup()

    def test_configure_tick_parameters_with_no_axes(self) -> None:
        """Test tick parameter configuration when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.configure_tick_parameters()
                mock_logger.warning.assert_called_once_with("Cannot configure tick parameters: axes is None")

    def test_setup_legend_with_standard_config(self) -> None:
        """Test legend setup with standard configuration."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the legend method
            with patch.object(graph.axes, 'legend') as mock_legend:
                graph.setup_legend_with_standard_config(location="upper right", fontsize=12)
                mock_legend.assert_called_once_with(
                    loc="upper right",
                    fontsize=12,
                    frameon=True,
                    fancybox=True,
                    shadow=True,
                    framealpha=0.9
                )
            
            graph.cleanup()

    def test_setup_legend_with_standard_config_no_axes(self) -> None:
        """Test legend setup when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.setup_legend_with_standard_config()
                mock_logger.warning.assert_called_once_with("Cannot setup legend: axes is None")

    def test_clear_axes_for_empty_data(self) -> None:
        """Test axes clearing for empty data display."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the axes methods
            with patch.object(graph.axes, 'clear') as mock_clear, \
                 patch.object(graph.axes, 'set_xlim') as mock_set_xlim, \
                 patch.object(graph.axes, 'set_ylim') as mock_set_ylim, \
                 patch.object(graph.axes, 'set_xticks') as mock_set_xticks, \
                 patch.object(graph.axes, 'set_yticks') as mock_set_yticks:
                
                graph.clear_axes_for_empty_data()
                
                # Verify all methods were called
                mock_clear.assert_called_once()
                mock_set_xlim.assert_called_once_with(0, 1)
                mock_set_ylim.assert_called_once_with(0, 1)
                mock_set_xticks.assert_called_once_with([])
                mock_set_yticks.assert_called_once_with([])
            
            graph.cleanup()

    def test_clear_axes_for_empty_data_with_no_axes(self) -> None:
        """Test axes clearing when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.clear_axes_for_empty_data()
                mock_logger.warning.assert_called_once_with("Cannot clear axes: axes is None")

    def test_setup_time_series_axes(self) -> None:
        """Test time series axes setup."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the required matplotlib methods
            with patch.object(graph.axes, 'set_title') as mock_set_title, \
                 patch.object(graph.axes, 'set_xlabel') as mock_set_xlabel, \
                 patch.object(graph.axes, 'set_ylabel') as mock_set_ylabel, \
                 patch.object(graph.axes, 'tick_params') as mock_tick_params, \
                 patch('matplotlib.dates.DateFormatter') as mock_date_formatter:
                
                mock_formatter_instance = MagicMock()
                mock_date_formatter.return_value = mock_formatter_instance
                
                graph.setup_time_series_axes(
                    xlabel="Time",
                    ylabel="Value",
                    date_format="%Y-%m",
                    rotation=30
                )
                
                # Verify methods were called
                mock_set_title.assert_called_once()
                mock_set_xlabel.assert_called_once_with("Time", fontsize=12)
                mock_set_ylabel.assert_called_once_with("Value", fontsize=12)
                mock_tick_params.assert_called_once_with(axis="x", rotation=30)
                mock_date_formatter.assert_called_once_with("%Y-%m")
            
            graph.cleanup()

    def test_setup_time_series_axes_with_no_axes(self) -> None:
        """Test time series axes setup when axes is None."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            # Don't setup figure, so axes remains None
            
            with patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                graph.setup_time_series_axes()
                mock_logger.warning.assert_called_once_with("Cannot setup time series axes: axes is None")

    def test_setup_time_series_axes_without_matplotlib_dates(self) -> None:
        """Test time series axes setup when matplotlib.dates is not available."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization()
            graph.setup_figure()
            
            # Mock the required matplotlib methods and import error
            with patch.object(graph.axes, 'set_title') as mock_set_title, \
                 patch.object(graph.axes, 'set_xlabel') as mock_set_xlabel, \
                 patch.object(graph.axes, 'set_ylabel') as mock_set_ylabel, \
                 patch.object(graph.axes, 'tick_params') as mock_tick_params, \
                 patch('matplotlib.dates.DateFormatter', side_effect=ImportError("No module")) as mock_date_formatter, \
                 patch('src.tgraph_bot.graphs.graph_modules.visualization.visualization_mixin.logger') as mock_logger:
                
                graph.setup_time_series_axes()
                
                # Verify methods were called
                mock_set_title.assert_called_once()
                mock_set_xlabel.assert_called_once_with("Date", fontsize=12)
                mock_set_ylabel.assert_called_once_with("Count", fontsize=12)
                mock_tick_params.assert_called_once_with(axis="x", rotation=45)
                mock_date_formatter.assert_called_once_with("%Y-%m-%d")
                mock_logger.warning.assert_called_once_with("matplotlib.dates not available for date formatting")
            
            graph.cleanup()

    def test_mixin_integration_with_multiple_methods(self) -> None:
        """Test integration of multiple mixin methods together."""
        with matplotlib_cleanup():
            graph = MockGraphWithVisualization(grid_enabled=True)
            
            with patch('seaborn.set_style') as mock_set_style, \
                 patch('seaborn.set_palette') as mock_set_palette:
                
                # Setup figure and configure multiple aspects
                figure, axes = graph.setup_figure_with_seaborn_grid()
                graph.apply_seaborn_palette("viridis")
                graph.setup_standard_title_and_axes(
                    title="Integration Test",
                    xlabel="X Axis",
                    ylabel="Y Axis"
                )
                graph.configure_standard_grid(alpha=0.4)
                graph.finalize_plot_layout()
                
                # Verify all methods were called
                mock_set_style.assert_called_once_with("whitegrid")
                mock_set_palette.assert_called_once_with("viridis")
                
                # Verify title and labels were set
                assert graph.axes is not None
                assert graph.axes.get_title() == "Integration Test"
                assert graph.axes.get_xlabel() == "X Axis"
                assert graph.axes.get_ylabel() == "Y Axis"
            
            graph.cleanup()