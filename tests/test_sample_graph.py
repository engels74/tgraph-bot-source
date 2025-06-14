"""
Tests for the sample graph implementation.

This module tests the SampleGraph class to validate the foundation
for specific graph implementations and demonstrate the complete
end-to-end workflow.
# pyright: reportPrivateUsage=false, reportAny=false
"""

from pathlib import Path

import pytest

from graphs.graph_modules.sample_graph import SampleGraph


class TestSampleGraph:
    """Test cases for the SampleGraph implementation."""
    
    def test_sample_graph_instantiation(self) -> None:
        """Test that SampleGraph can be instantiated properly."""
        graph = SampleGraph()
        assert graph.width == 10
        assert graph.height == 6
        assert graph.dpi == 100
        assert graph.background_color == "#ffffff"
        
    def test_sample_graph_custom_parameters(self) -> None:
        """Test SampleGraph with custom initialization parameters."""
        graph = SampleGraph(
            width=12,
            height=8,
            dpi=150,
            background_color="#f0f0f0"
        )
        assert graph.width == 12
        assert graph.height == 8
        assert graph.dpi == 150
        assert graph.background_color == "#f0f0f0"
        
    def test_get_title(self) -> None:
        """Test that get_title returns the expected title."""
        graph = SampleGraph()
        title = graph.get_title()
        assert title == "Sample Data Visualization"
        
    def test_validate_data_valid_input(self) -> None:
        """Test data validation with valid input."""
        graph = SampleGraph()
        
        valid_data = {
            'x_values': [1, 2, 3, 4, 5],
            'y_values': [10, 20, 30, 40, 50]
        }
        
        assert graph.validate_data(valid_data) is True
        
    def test_validate_data_missing_keys(self) -> None:
        """Test data validation with missing required keys."""
        graph = SampleGraph()
        
        # Missing y_values
        invalid_data = {
            'x_values': [1, 2, 3, 4, 5]
        }
        
        assert graph.validate_data(invalid_data) is False
        
        # Missing x_values
        invalid_data = {
            'y_values': [10, 20, 30, 40, 50]
        }
        
        assert graph.validate_data(invalid_data) is False
        
    def test_validate_data_wrong_types(self) -> None:
        """Test data validation with wrong data types."""
        graph = SampleGraph()
        
        invalid_data = {
            'x_values': "not a list",
            'y_values': [10, 20, 30, 40, 50]
        }
        
        assert graph.validate_data(invalid_data) is False
        
    def test_validate_data_empty_values(self) -> None:
        """Test data validation with empty values."""
        graph = SampleGraph()
        
        invalid_data: dict[str, list[int]] = {
            'x_values': [],
            'y_values': []
        }
        
        assert graph.validate_data(invalid_data) is False
        
    def test_validate_data_mismatched_lengths(self) -> None:
        """Test data validation with mismatched array lengths."""
        graph = SampleGraph()
        
        invalid_data = {
            'x_values': [1, 2, 3],
            'y_values': [10, 20, 30, 40, 50]
        }
        
        assert graph.validate_data(invalid_data) is False
        
    def test_get_sample_data(self) -> None:
        """Test that get_sample_data returns valid sample data."""
        graph = SampleGraph()
        sample_data = graph.get_sample_data()
        
        # Verify structure
        assert 'x_values' in sample_data
        assert 'y_values' in sample_data
        assert 'title' in sample_data
        assert 'user_id' in sample_data
        
        # Verify data validity
        assert graph.validate_data(sample_data) is True
        
        # Verify content
        x_values = sample_data['x_values']
        y_values = sample_data['y_values']
        assert isinstance(x_values, list) and isinstance(y_values, list)
        assert len(x_values) == len(y_values)  # pyright: ignore[reportUnknownArgumentType]
        assert len(x_values) == 10  # Should be 1 to 10  # pyright: ignore[reportUnknownArgumentType]
        assert sample_data['title'] == 'Sample Data Points'
        assert sample_data['user_id'] == 'demo_user'
        
    def test_generate_with_valid_data(self) -> None:
        """Test end-to-end graph generation with valid data."""
        graph = SampleGraph()
        
        test_data = {
            'x_values': [1, 2, 3, 4, 5],
            'y_values': [10, 25, 30, 45, 50],
            'title': 'Test Graph',
            'user_id': 'test_user'
        }
        
        # Generate the graph
        output_path = graph.generate(test_data)
        
        # Verify file was created
        assert Path(output_path).exists()
        assert output_path.endswith('.png')
        assert 'sample_graph' in output_path
        assert 'test_user' in output_path
        
        # Clean up
        Path(output_path).unlink(missing_ok=True)
        
    def test_generate_with_sample_data(self) -> None:
        """Test graph generation using the built-in sample data."""
        graph = SampleGraph()
        
        # Get sample data and generate graph
        sample_data = graph.get_sample_data()
        output_path = graph.generate(sample_data)
        
        # Verify file was created
        assert Path(output_path).exists()
        assert output_path.endswith('.png')
        assert 'sample_graph' in output_path
        assert 'demo_user' in output_path
        
        # Clean up
        Path(output_path).unlink(missing_ok=True)
        
    def test_generate_without_optional_parameters(self) -> None:
        """Test graph generation without optional parameters."""
        graph = SampleGraph()
        
        minimal_data = {
            'x_values': [1, 2, 3],
            'y_values': [5, 10, 15]
        }
        
        # Generate the graph
        output_path = graph.generate(minimal_data)
        
        # Verify file was created
        assert Path(output_path).exists()
        assert output_path.endswith('.png')
        assert 'sample_graph' in output_path
        
        # Clean up
        Path(output_path).unlink(missing_ok=True)
        
    def test_generate_with_missing_data_raises_error(self) -> None:
        """Test that generate raises ValueError with missing required data."""
        graph = SampleGraph()
        
        invalid_data = {
            'x_values': [1, 2, 3]
            # Missing y_values
        }
        
        with pytest.raises(ValueError, match="Both 'x_values' and 'y_values' are required"):
            _ = graph.generate(invalid_data)
            
    def test_generate_with_mismatched_data_raises_error(self) -> None:
        """Test that generate raises ValueError with mismatched data lengths."""
        graph = SampleGraph()
        
        invalid_data = {
            'x_values': [1, 2, 3],
            'y_values': [10, 20]  # Different length
        }
        
        with pytest.raises(ValueError, match="x_values and y_values must have the same length"):
            _ = graph.generate(invalid_data)
            
    def test_context_manager_usage(self) -> None:
        """Test using SampleGraph as a context manager."""
        test_data = {
            'x_values': [1, 2, 3],
            'y_values': [10, 20, 30]
        }
        
        with SampleGraph() as graph:
            output_path = graph.generate(test_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
            
        # After context exit, cleanup should have been called
        assert graph.figure is None
        assert graph.axes is None
