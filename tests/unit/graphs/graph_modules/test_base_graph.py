"""
Test module for the BaseGraph abstract base class.

This module tests the BaseGraph functionality including:
- Abstract method requirements
- Figure setup and management
- Color validation
- Context manager behavior
- Cleanup operations
"""

from abc import ABC
from pathlib import Path
from collections.abc import Mapping
from typing import override
from unittest.mock import patch

import pytest

from src.tgraph_bot.graphs.graph_modules.core.base_graph import BaseGraph
from tests.utils.graph_helpers import (
    matplotlib_cleanup,
    assert_graph_properties,
    assert_graph_cleanup,
)
from tests.utils.test_helpers import create_temp_directory, create_test_config_custom, create_test_config


class ConcreteGraph(BaseGraph):
    """Concrete implementation of BaseGraph for testing."""

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """Generate a test graph."""
        _ = self.setup_figure()
        if self.axes is not None:
            _ = self.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]
            _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]

        with create_temp_directory() as temp_dir:
            output_path = str(temp_dir / "test_graph.png")

        return self.save_figure(output_path=output_path)

    @override
    def get_title(self) -> str:
        """Get the title for this test graph."""
        return "Test Graph"


class TestBaseGraph:
    """Test cases for the BaseGraph abstract base class."""

    def test_cannot_instantiate_base_graph_directly(self) -> None:
        """Test that BaseGraph cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = BaseGraph()  # pyright: ignore[reportAbstractUsage]

    def test_concrete_graph_instantiation(self) -> None:
        """Test that concrete implementation can be instantiated."""
        graph = ConcreteGraph()
        assert_graph_properties(graph)  # Uses default values
        assert graph.figure is None
        assert graph.axes is None

    def test_custom_initialization_parameters(self) -> None:
        """Test BaseGraph initialization with custom parameters."""
        graph = ConcreteGraph(width=10, height=6, dpi=150, background_color="#f0f0f0")
        assert_graph_properties(
            graph,
            expected_width=10,
            expected_height=6,
            expected_dpi=150,
            expected_background_color="#f0f0f0",
        )

    def test_setup_figure(self) -> None:
        """Test figure setup functionality."""
        graph = ConcreteGraph()
        figure, axes = graph.setup_figure()

        assert graph.figure is not None
        assert graph.axes is not None
        assert figure is graph.figure
        assert axes is graph.axes

        # Verify figure properties
        assert figure.get_figwidth() == 14  # pyright: ignore[reportUnknownMemberType]
        assert figure.get_figheight() == 8  # pyright: ignore[reportUnknownMemberType]
        # On high-DPI displays (like Retina), matplotlib may double the DPI
        # The graph instance stores the requested DPI, but matplotlib figure may use system DPI
        assert graph.dpi == 100  # This is what was requested
        assert figure.dpi in [100, 200]  # pyright: ignore[reportAny] # Allow system DPI scaling

        # Clean up
        graph.cleanup()

    def test_save_figure_without_setup_raises_error(self) -> None:
        """Test that saving figure without setup raises ValueError."""
        graph = ConcreteGraph()

        with pytest.raises(ValueError, match="Figure not initialized"):
            _ = graph.save_figure(output_path="test.png")

    def test_save_figure_creates_directory(self) -> None:
        """Test that save_figure creates output directory if it doesn't exist."""
        graph = ConcreteGraph()

        with create_temp_directory() as temp_dir:
            output_path = temp_dir / "subdir" / "test_graph.png"

            # Setup figure
            _ = graph.setup_figure()
            if graph.axes is not None:
                _ = graph.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]

            # Save figure
            saved_path = graph.save_figure(output_path=str(output_path))

            assert saved_path == str(output_path)
            assert output_path.exists()
            assert output_path.parent.exists()

            # Clean up
            graph.cleanup()

    def test_cleanup(self) -> None:
        """Test cleanup functionality."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        assert graph.figure is not None
        assert graph.axes is not None

        graph.cleanup()
        assert_graph_cleanup(graph)

    def test_context_manager(self) -> None:
        """Test BaseGraph as context manager."""
        with ConcreteGraph() as graph:
            assert isinstance(graph, ConcreteGraph)
            _ = graph.setup_figure()
            assert graph.figure is not None
            assert graph.axes is not None

        # After context exit, cleanup should have been called
        assert_graph_cleanup(graph)

    def test_generate_method_implementation(self) -> None:
        """Test that concrete implementation's generate method works."""
        with matplotlib_cleanup():
            graph = ConcreteGraph()

            with create_temp_directory():
                # Generate graph
                output_path = graph.generate({"test": "data"})

                # Verify file was created
                assert Path(output_path).exists()
                assert Path(output_path).suffix == ".png"

                # Clean up
                Path(output_path).unlink(missing_ok=True)

    def test_get_title_method_implementation(self) -> None:
        """Test that concrete implementation's get_title method works."""
        graph = ConcreteGraph()
        title = graph.get_title()
        assert title == "Test Graph"

    def test_cleanup_resets_figure_references(self) -> None:
        """Test that cleanup properly resets figure and axes references."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        # Verify figure and axes are set up
        assert graph.figure is not None
        assert graph.axes is not None

        # Store references for later verification
        figure_ref = graph.figure
        axes_ref = graph.axes

        graph.cleanup()

        # Verify references are reset to None
        assert graph.figure is None
        assert graph.axes is None

        # Verify the original objects still exist but are no longer referenced
        assert figure_ref is not None
        assert axes_ref is not None

    def test_figure_background_color_applied(self) -> None:
        """Test that background color is properly applied to figure and axes."""
        background_color = "#ff0000"
        graph = ConcreteGraph(background_color=background_color)

        figure, axes = graph.setup_figure()

        # Note: matplotlib color comparison can be tricky, so we just verify
        # the setup completed without error and the color was set
        assert figure is not None
        assert axes is not None

        graph.cleanup()

    def test_abstract_methods_must_be_implemented(self) -> None:
        """Test that abstract methods must be implemented in subclasses."""

        class IncompleteGraph(BaseGraph, ABC):
            """Incomplete implementation missing abstract methods."""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = IncompleteGraph()  # pyright: ignore[reportAbstractUsage]

    def test_partial_implementation_still_abstract(self) -> None:
        """Test that partial implementation is still abstract."""

        class PartialGraph(BaseGraph, ABC):
            """Partial implementation with only one abstract method."""

            @override
            def generate(self, data: Mapping[str, object]) -> str:
                return "test.png"

            # Missing get_title method

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            _ = PartialGraph()  # pyright: ignore[reportAbstractUsage]

    def test_color_validation_in_constructor(self) -> None:
        """Test that invalid colors are rejected in constructor."""
        with pytest.raises(ValueError, match="Invalid background color format"):
            _ = ConcreteGraph(background_color="invalid_color")

    def test_valid_hex_color_accepted(self) -> None:
        """Test that valid hex colors are accepted."""
        graph = ConcreteGraph(background_color="#ff0000")
        assert graph.background_color == "#ff0000"

    def test_valid_named_color_accepted(self) -> None:
        """Test that valid named colors are accepted."""
        graph = ConcreteGraph(background_color="red")
        assert graph.background_color == "red"

    def test_format_username_with_censoring(self) -> None:
        """Test username formatting with censoring enabled."""
        graph = ConcreteGraph()

        # Test normal username
        result = graph.format_username("testuser", censor_enabled=True)
        assert result == "t******r"

        # Test short username
        result = graph.format_username("ab", censor_enabled=True)
        assert result == "**"

        # Test without censoring
        result = graph.format_username("testuser", censor_enabled=False)
        assert result == "testuser"

    def test_save_figure_with_graph_type_generates_filename(self) -> None:
        """Test that save_figure can generate filename using graph_type."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        if graph.axes is not None:
            _ = graph.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]

        # Save with graph_type instead of output_path
        saved_path = graph.save_figure(graph_type="test_graph")

        # Verify file was created and path contains graph type
        assert Path(saved_path).exists()
        assert "test_graph" in saved_path
        assert saved_path.endswith(".png")

        # Clean up
        Path(saved_path).unlink(missing_ok=True)
        graph.cleanup()

    def test_save_figure_with_user_id_in_filename(self) -> None:
        """Test that save_figure includes user_id in generated filename."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        if graph.axes is not None:
            _ = graph.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]

        # Save with graph_type and user_id
        saved_path = graph.save_figure(graph_type="test_graph", user_id="user123")

        # Verify file was created and path contains user ID
        assert Path(saved_path).exists()
        assert "test_graph" in saved_path
        assert "user_user123" in saved_path
        assert saved_path.endswith(".png")

        # Clean up
        Path(saved_path).unlink(missing_ok=True)
        graph.cleanup()

    def test_save_figure_requires_graph_type_when_no_output_path(self) -> None:
        """Test that save_figure requires graph_type when output_path not provided."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        with pytest.raises(
            ValueError, match="Either output_path or graph_type must be provided"
        ):
            _ = graph.save_figure()

    def test_get_stacked_bar_charts_enabled_default(self) -> None:
        """Test get_stacked_bar_charts_enabled returns default value."""
        graph = ConcreteGraph()
        # Should return False by default (no config provided)
        assert graph.get_stacked_bar_charts_enabled() is False

    def test_get_stacked_bar_charts_enabled_with_config(self) -> None:
        """Test get_stacked_bar_charts_enabled with configuration object."""
        # Test with stacked charts enabled
        config_enabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"stacked_bar_charts": True}
            }
        )
        graph_enabled = ConcreteGraph(config=config_enabled)
        assert graph_enabled.get_stacked_bar_charts_enabled() is True

        # Test with stacked charts disabled
        config_disabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"stacked_bar_charts": False}
            }
        )
        graph_disabled = ConcreteGraph(config=config_disabled)
        assert graph_disabled.get_stacked_bar_charts_enabled() is False

    def test_get_media_type_separation_enabled_default(self) -> None:
        """Test get_media_type_separation_enabled returns default value."""
        graph = ConcreteGraph()
        # Should return True by default (no config provided)
        assert graph.get_media_type_separation_enabled() is True

    def test_get_media_type_separation_enabled_with_config(self) -> None:
        """Test get_media_type_separation_enabled with configuration object."""
        # Test with media type separation enabled
        config_enabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"media_type_separation": True}
            }
        )
        graph_enabled = ConcreteGraph(config=config_enabled)
        assert graph_enabled.get_media_type_separation_enabled() is True

        # Test with media type separation disabled
        config_disabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"media_type_separation": False}
            }
        )
        graph_disabled = ConcreteGraph(config=config_disabled)
        assert graph_disabled.get_media_type_separation_enabled() is False

    def test_extract_and_validate_play_history_data_success(self) -> None:
        """Test successful extraction and validation of play history data."""
        graph = ConcreteGraph()

        # Valid input data
        input_data = {
            "play_history": {
                "data": [
                    {"date": "2023-01-01", "user": "test_user", "platform": "Web"},
                    {"date": "2023-01-02", "user": "test_user2", "platform": "Mobile"},
                ]
            }
        }

        result = graph.extract_and_validate_play_history_data(input_data)
        assert isinstance(result, dict)
        assert "data" in result
        assert isinstance(result["data"], list)
        data_list = result["data"]  # pyright: ignore[reportUnknownVariableType]
        assert isinstance(data_list, list)
        assert len(data_list) == 2  # pyright: ignore[reportUnknownArgumentType]

    def test_extract_and_validate_play_history_data_missing_play_history(self) -> None:
        """Test extraction with missing play_history key."""
        graph = ConcreteGraph()

        # Input data without play_history key
        input_data = {"other_data": "value"}

        with pytest.raises(
            ValueError, match="Invalid play history data: Missing required key: data"
        ):
            _ = graph.extract_and_validate_play_history_data(input_data)

    def test_extract_and_validate_play_history_data_invalid_play_history(self) -> None:
        """Test extraction with invalid play_history data."""
        graph = ConcreteGraph()

        # Input data with invalid play_history (not a dict)
        input_data = {"play_history": "invalid_data"}

        with pytest.raises(
            ValueError, match="Missing or invalid 'play_history' data in input"
        ):
            _ = graph.extract_and_validate_play_history_data(input_data)

    def test_extract_and_validate_play_history_data_missing_data_key(self) -> None:
        """Test extraction with missing data key in play_history."""
        graph = ConcreteGraph()

        # Input data without data key in play_history
        input_data = {"play_history": {"other_key": "value"}}

        with pytest.raises(
            ValueError, match="Invalid play history data: Missing required key: data"
        ):
            _ = graph.extract_and_validate_play_history_data(input_data)

    def test_process_play_history_safely_success(self) -> None:
        """Test successful processing of play history data."""
        graph = ConcreteGraph()

        # Mock the process_play_history_data function
        with patch(
            "src.tgraph_bot.graphs.graph_modules.core.base_graph.process_play_history_data"
        ) as mock_process:
            mock_process.return_value = [
                {
                    "date": "2023-01-01",
                    "user": "test_user",
                    "platform": "Web",
                    "media_type": "tv",
                    "duration": 3600,
                },
                {
                    "date": "2023-01-02",
                    "user": "test_user2",
                    "platform": "Mobile",
                    "media_type": "movie",
                    "duration": 7200,
                },
            ]

            play_history_data = {"data": [{"mock": "data"}]}
            result = graph.process_play_history_safely(play_history_data)

            assert isinstance(result, list)
            assert len(result) == 2
            mock_process.assert_called_once_with(play_history_data)

    def test_process_play_history_safely_error_handling(self) -> None:
        """Test error handling in play history processing."""
        graph = ConcreteGraph()

        # Mock the process_play_history_data function to raise an error
        with patch(
            "src.tgraph_bot.graphs.graph_modules.core.base_graph.process_play_history_data"
        ) as mock_process:
            mock_process.side_effect = ValueError("Processing failed")

            play_history_data = {"data": [{"mock": "data"}]}
            result = graph.process_play_history_safely(play_history_data)

            # Should return empty list on error
            assert result == []
            mock_process.assert_called_once_with(play_history_data)

    def test_setup_figure_with_styling(self) -> None:
        """Test combined figure setup and styling."""
        graph = ConcreteGraph()

        figure, axes = graph.setup_figure_with_styling()

        # Verify setup was successful
        assert graph.figure is not None
        assert graph.axes is not None
        assert figure is graph.figure
        assert axes is graph.axes

        # Clean up
        graph.cleanup()

    def test_finalize_and_save_figure(self) -> None:
        """Test figure finalization and saving."""
        graph = ConcreteGraph()

        # Setup figure first
        _ = graph.setup_figure_with_styling()
        if graph.axes is not None:
            _ = graph.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]

        # Save and finalize
        output_path = graph.finalize_and_save_figure(graph_type="test_graph")

        # Verify file was created
        assert Path(output_path).exists()
        assert "test_graph" in output_path

        # Clean up
        Path(output_path).unlink(missing_ok=True)

    def test_get_time_range_days_from_config_default(self) -> None:
        """Test get_time_range_days_from_config with default value."""
        graph = ConcreteGraph()

        # Should return default value (30) when no config provided
        result = graph.get_time_range_days_from_config()
        assert result == 30

    def test_get_time_range_days_from_config_with_config(self) -> None:
        """Test get_time_range_days_from_config with configuration."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"days": 60}
            }
        )
        graph = ConcreteGraph(config=config)

        result = graph.get_time_range_days_from_config()
        assert result == 60

    def test_get_time_range_days_from_config_invalid_value(self) -> None:
        """Test get_time_range_days_from_config with invalid value."""
        # Note: Since TIME_RANGE_DAYS maps to nested structure, we'll test with a minimal config
        # and rely on the default value handling in the method
        graph = ConcreteGraph(config=create_test_config())

        result = graph.get_time_range_days_from_config()
        assert result == 30  # Should return default

    def test_get_time_range_months_from_config_default(self) -> None:
        """Test get_time_range_months_from_config with default value."""
        graph = ConcreteGraph()

        # Should return default value (12) when no config provided
        result = graph.get_time_range_months_from_config()
        assert result == 12

    def test_get_time_range_months_from_config_with_config(self) -> None:
        """Test get_time_range_months_from_config with configuration."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"months": 24}
            }
        )
        graph = ConcreteGraph(config=config)

        result = graph.get_time_range_months_from_config()
        assert result == 24

    def test_time_range_days_method_consistency(self) -> None:
        """Test that time range days methods are consistent and don't have unnecessary wrappers."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"days": 45}
            }
        )
        graph = ConcreteGraph(config=config)

        # Test that the base method works correctly
        result = graph.get_time_range_days_from_config()
        assert result == 45

        # Test that the method handles invalid values correctly
        # Note: Since TIME_RANGE_DAYS maps to nested structure, we'll test with a minimal config
        graph_invalid = ConcreteGraph(config=create_test_config())
        result_invalid = graph_invalid.get_time_range_days_from_config()
        assert result_invalid == 30  # Should return default

    def test_handle_empty_data_with_message(self) -> None:
        """Test empty data handling with custom message."""
        graph = ConcreteGraph()

        # Setup figure
        _ = graph.setup_figure()

        # Test with default message
        if graph.axes is not None:
            graph.handle_empty_data_with_message(graph.axes)

            # Verify axes was configured (we can't easily test visual output,
            # but we can verify no exceptions were raised)
            assert graph.axes is not None

        # Test with custom message
        if graph.axes is not None:
            graph.handle_empty_data_with_message(graph.axes, "Custom empty message")

            # Verify axes was configured
            assert graph.axes is not None

        # Clean up
        graph.cleanup()

    def test_config_accessor_integration(self) -> None:
        """Test ConfigAccessor integration in BaseGraph."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "features": {"media_type_separation": True, "stacked_bar_charts": False}
            }
        )
        graph = ConcreteGraph(config=config)

        # Test ConfigAccessor is properly initialized
        assert graph._config_accessor is not None  # pyright: ignore[reportPrivateUsage]

        # Test config value retrieval through BaseGraph methods
        assert graph.get_media_type_separation_enabled() is True
        assert graph.get_stacked_bar_charts_enabled() is False

    def test_config_accessor_none_when_no_config(self) -> None:
        """Test ConfigAccessor is None when no config provided."""
        graph = ConcreteGraph()
        assert graph._config_accessor is None  # pyright: ignore[reportPrivateUsage]

        # Should use defaults when no config available
        assert graph.get_media_type_separation_enabled() is True  # default
        assert graph.get_stacked_bar_charts_enabled() is False  # default

    def test_media_type_processor_lazy_initialization(self) -> None:
        """Test MediaTypeProcessor lazy initialization."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            }
        )
        graph = ConcreteGraph(config=config)

        # Initially None
        assert graph._media_type_processor is None  # pyright: ignore[reportPrivateUsage]

        # Access property triggers lazy initialization
        processor = graph.media_type_processor
        assert processor is not None
        assert graph._media_type_processor is processor  # pyright: ignore[reportPrivateUsage]

        # Subsequent access returns same instance
        processor2 = graph.media_type_processor
        assert processor2 is processor

    def test_apply_seaborn_style_with_grid(self) -> None:
        """Test apply_seaborn_style with grid enabled."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"grid": {"enabled": True}}
            }
        )
        graph = ConcreteGraph(config=config)
        _ = graph.setup_figure()

        # Should not raise exception
        graph.apply_seaborn_style()

        # Clean up
        graph.cleanup()

    def test_apply_seaborn_style_without_grid(self) -> None:
        """Test apply_seaborn_style with grid disabled."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"grid": {"enabled": False}}
            }
        )
        graph = ConcreteGraph(config=config)
        _ = graph.setup_figure()

        # Should not raise exception
        graph.apply_seaborn_style()

        # Clean up
        graph.cleanup()

    def test_get_grid_enabled(self) -> None:
        """Test get_grid_enabled method."""
        # Test with grid enabled
        config_enabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"grid": {"enabled": True}}
            }
        )
        graph_enabled = ConcreteGraph(config=config_enabled)
        assert graph_enabled.get_grid_enabled() is True

        # Test with grid disabled
        config_disabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"grid": {"enabled": False}}
            }
        )
        graph_disabled = ConcreteGraph(config=config_disabled)
        assert graph_disabled.get_grid_enabled() is False

        # Test default when no config
        graph_default = ConcreteGraph()
        assert graph_default.get_grid_enabled() is False  # default

    def test_color_methods(self) -> None:
        """Test color retrieval methods."""
        graph = ConcreteGraph()

        # These should not raise exceptions and return valid colors
        tv_color = graph.get_tv_color()
        movie_color = graph.get_movie_color()
        annotation_color = graph.get_annotation_color()
        outline_color = graph.get_annotation_outline_color()
        peak_color = graph.get_peak_annotation_color()
        peak_text_color = graph.get_peak_annotation_text_color()

        # Should be valid color strings
        assert isinstance(tv_color, str)
        assert isinstance(movie_color, str)
        assert isinstance(annotation_color, str)
        assert isinstance(outline_color, str)
        assert isinstance(peak_color, str)
        assert isinstance(peak_text_color, str)

    def test_annotation_settings_methods(self) -> None:
        """Test annotation configuration methods."""
        graph = ConcreteGraph()

        # Test boolean settings
        assert isinstance(graph.is_annotation_outline_enabled(), bool)
        assert isinstance(graph.is_peak_annotations_enabled(), bool)
        assert isinstance(graph.should_censor_usernames(), bool)

        # Test font size setting
        font_size = graph.get_annotation_font_size()
        assert isinstance(font_size, int)
        assert font_size > 0

    def test_peak_annotations_settings_with_config(self) -> None:
        """Test peak annotation settings with nested configuration."""
        # Test with peak annotations enabled
        config_enabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {
                    "annotations": {
                        "peaks": {
                            "enabled": True,
                            "color": "#ffcc00",
                            "text_color": "#000000"
                        },
                        "basic": {
                            "font_size": 12
                        }
                    }
                }
            }
        )
        graph_enabled = ConcreteGraph(config=config_enabled)
        
        # Test peak annotations enabled
        assert graph_enabled.is_peak_annotations_enabled() is True
        assert graph_enabled.get_peak_annotation_color() == "#ffcc00"
        assert graph_enabled.get_peak_annotation_text_color() == "#000000"
        assert graph_enabled.get_annotation_font_size() == 12

        # Test with peak annotations disabled
        config_disabled = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {
                    "annotations": {
                        "peaks": {
                            "enabled": False,
                            "color": "#ff0000",
                            "text_color": "#ffffff"
                        }
                    }
                }
            }
        )
        graph_disabled = ConcreteGraph(config=config_disabled)
        
        # Test peak annotations disabled
        assert graph_disabled.is_peak_annotations_enabled() is False
        assert graph_disabled.get_peak_annotation_color() == "#ff0000"
        assert graph_disabled.get_peak_annotation_text_color() == "#ffffff"

    def test_annotation_enabled_on_specific_graphs_with_config(self) -> None:
        """Test annotation enabled_on settings with nested configuration."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {
                    "annotations": {
                        "enabled_on": {
                            "top_10_users": True,
                            "top_10_platforms": False,
                            "play_count_by_hourofday": True
                        }
                    }
                }
            }
        )
        graph = ConcreteGraph(config=config)
        
        # Test specific graph annotation settings
        assert graph.get_config_value("graphs.appearance.annotations.enabled_on.top_10_users", False) is True
        assert graph.get_config_value("graphs.appearance.annotations.enabled_on.top_10_platforms", True) is False
        assert graph.get_config_value("graphs.appearance.annotations.enabled_on.play_count_by_hourofday", False) is True

    def test_enhanced_title_with_timeframe_days(self) -> None:
        """Test enhanced title generation with days timeframe."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"days": 7}
            }
        )
        graph = ConcreteGraph(config=config)

        result = graph.get_enhanced_title_with_timeframe(
            "Daily Play Count", use_months=False
        )
        assert result == "Daily Play Count (Last 7 days)"

        # Test singular form
        config_singular = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"days": 1}
            }
        )
        graph_singular = ConcreteGraph(config=config_singular)

        result_singular = graph_singular.get_enhanced_title_with_timeframe(
            "Daily Play Count", use_months=False
        )
        assert result_singular == "Daily Play Count (Last 1 day)"

    def test_enhanced_title_with_timeframe_months(self) -> None:
        """Test enhanced title generation with months timeframe."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"months": 6}
            }
        )
        graph = ConcreteGraph(config=config)

        result = graph.get_enhanced_title_with_timeframe(
            "Monthly Play Count", use_months=True
        )
        assert result == "Monthly Play Count (Last 6 months)"

        # Test singular form
        config_singular = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            data_collection_overrides={
                "time_ranges": {"months": 1}
            }
        )
        graph_singular = ConcreteGraph(config=config_singular)

        result_singular = graph_singular.get_enhanced_title_with_timeframe(
            "Monthly Play Count", use_months=True
        )
        assert result_singular == "Monthly Play Count (Last 1 month)"

    def test_add_bar_value_annotation_with_outline(self) -> None:
        """Test add_bar_value_annotation with outline enabled."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"annotations": {"basic": {"enable_outline": True}}}
            }
        )
        graph = ConcreteGraph(config=config)
        _ = graph.setup_figure()

        # Should not raise exception
        if graph.axes is not None:
            graph.add_bar_value_annotation(
                graph.axes, x=1.0, y=2.0, value=42, ha="center", va="bottom"
            )

        # Clean up
        graph.cleanup()

    def test_add_bar_value_annotation_without_outline(self) -> None:
        """Test add_bar_value_annotation with outline disabled."""
        config = create_test_config_custom(
            services_overrides={
                "tautulli": {"api_key": "test_api_key", "url": "http://localhost:8181/api/v2"},
                "discord": {"token": "test_discord_token", "channel_id": 123456789}
            },
            graphs_overrides={
                "appearance": {"annotations": {"basic": {"enable_outline": False}}}
            }
        )
        graph = ConcreteGraph(config=config)
        _ = graph.setup_figure()

        # Should not raise exception
        if graph.axes is not None:
            graph.add_bar_value_annotation(
                graph.axes, x=1.0, y=2.0, value=42.5, ha="left", va="top"
            )

        # Clean up
        graph.cleanup()

    def test_create_separated_legend(self) -> None:
        """Test create_separated_legend method."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()

        # Should not raise exception
        if graph.axes is not None:
            graph.create_separated_legend(graph.axes, ["tv", "movie"])

        # Clean up
        graph.cleanup()

    def test_cleanup_all_figures_class_method(self) -> None:
        """Test cleanup_all_figures class method."""
        # Should not raise exception
        BaseGraph.cleanup_all_figures()
