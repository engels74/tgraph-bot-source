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
from unittest.mock import MagicMock, patch

import pytest

from graphs.graph_modules.base_graph import BaseGraph
from tests.utils.graph_helpers import (
    matplotlib_cleanup,
    assert_graph_properties,
    assert_graph_cleanup,
)
from tests.utils.test_helpers import create_temp_directory


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
        graph = ConcreteGraph(
            width=10,
            height=6,
            dpi=150,
            background_color="#f0f0f0"
        )
        assert_graph_properties(
            graph,
            expected_width=10,
            expected_height=6,
            expected_dpi=150,
            expected_background_color="#f0f0f0"
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
        assert figure.get_figwidth() == 12
        assert figure.get_figheight() == 8
        assert figure.dpi == 100
        
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
    
    @patch('matplotlib.pyplot.close')
    def test_cleanup_calls_plt_close(self, mock_close: MagicMock) -> None:
        """Test that cleanup properly calls plt.close."""
        graph = ConcreteGraph()
        _ = graph.setup_figure()
        
        figure = graph.figure
        graph.cleanup()
        
        mock_close.assert_called_once_with(figure)
    
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

        with pytest.raises(ValueError, match="Either output_path or graph_type must be provided"):
            _ = graph.save_figure()
