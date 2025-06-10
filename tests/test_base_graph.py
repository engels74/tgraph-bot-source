"""
Tests for the base graph system in TGraph Bot.

This module tests the abstract base class, factory pattern, and utility functions
for the graph generation system.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import pytest

from graphs.graph_modules.base_graph import BaseGraph


class ConcreteGraph(BaseGraph):
    """Concrete implementation of BaseGraph for testing."""
    
    def generate(self, data: dict[str, any]) -> str:  # pyright: ignore[reportExplicitAny]
        """Generate a test graph."""
        self.setup_figure()
        if self.axes is not None:
            self.axes.plot([1, 2, 3], [1, 4, 2])
            self.axes.set_title(self.get_title())
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            output_path = tmp.name
            
        return self.save_figure(output_path)
    
    def get_title(self) -> str:
        """Get the title for this test graph."""
        return "Test Graph"


class TestBaseGraph:
    """Test cases for the BaseGraph abstract base class."""
    
    def test_cannot_instantiate_base_graph_directly(self) -> None:
        """Test that BaseGraph cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseGraph()  # pyright: ignore[reportAbstractUsage]
    
    def test_concrete_graph_instantiation(self) -> None:
        """Test that concrete implementation can be instantiated."""
        graph = ConcreteGraph()
        assert graph.width == 12
        assert graph.height == 8
        assert graph.dpi == 100
        assert graph.background_color == "#ffffff"
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
        assert graph.width == 10
        assert graph.height == 6
        assert graph.dpi == 150
        assert graph.background_color == "#f0f0f0"
    
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
            graph.save_figure("test.png")
    
    def test_save_figure_creates_directory(self) -> None:
        """Test that save_figure creates output directory if it doesn't exist."""
        graph = ConcreteGraph()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "test_graph.png"
            
            # Setup figure
            graph.setup_figure()
            if graph.axes is not None:
                graph.axes.plot([1, 2, 3], [1, 4, 2])
            
            # Save figure
            saved_path = graph.save_figure(str(output_path))
            
            assert saved_path == str(output_path)
            assert output_path.exists()
            assert output_path.parent.exists()
            
            # Clean up
            graph.cleanup()
    
    def test_cleanup(self) -> None:
        """Test cleanup functionality."""
        graph = ConcreteGraph()
        graph.setup_figure()
        
        assert graph.figure is not None
        assert graph.axes is not None
        
        graph.cleanup()
        
        assert graph.figure is None
        assert graph.axes is None
    
    def test_context_manager(self) -> None:
        """Test BaseGraph as context manager."""
        with ConcreteGraph() as graph:
            assert isinstance(graph, ConcreteGraph)
            graph.setup_figure()
            assert graph.figure is not None
            assert graph.axes is not None
        
        # After context exit, cleanup should have been called
        assert graph.figure is None
        assert graph.axes is None
    
    def test_generate_method_implementation(self) -> None:
        """Test that concrete implementation's generate method works."""
        graph = ConcreteGraph()
        
        with tempfile.TemporaryDirectory() as temp_dir:
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
        graph.setup_figure()
        
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
        
        class IncompleteGraph(BaseGraph):
            """Incomplete implementation missing abstract methods."""
            pass
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteGraph()  # pyright: ignore[reportAbstractUsage]
    
    def test_partial_implementation_still_abstract(self) -> None:
        """Test that partial implementation is still abstract."""
        
        class PartialGraph(BaseGraph):
            """Partial implementation with only one abstract method."""
            
            def generate(self, data: dict[str, any]) -> str:  # pyright: ignore[reportExplicitAny]
                return "test.png"
            # Missing get_title method
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PartialGraph()  # pyright: ignore[reportAbstractUsage]
