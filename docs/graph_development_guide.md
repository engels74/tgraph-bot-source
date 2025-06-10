# Graph Development Guide

This guide explains how to extend the TGraph Bot graph system by creating new graph types. The system is built on a solid foundation using modern Python patterns including abstract base classes, factory patterns, and comprehensive utility functions.

## Architecture Overview

The graph system consists of several key components:

- **BaseGraph**: Abstract base class defining the interface for all graph types
- **GraphFactory**: Factory class for creating graph instances based on configuration
- **Utility Functions**: Reusable functions for common operations (file management, data formatting, etc.)
- **Concrete Graph Classes**: Specific implementations for different graph types

## Creating a New Graph Type

### Step 1: Implement the BaseGraph Interface

Create a new Python file in `graphs/graph_modules/` that extends the `BaseGraph` class:

```python
from .base_graph import BaseGraph

class MyCustomGraph(BaseGraph):
    """Custom graph implementation."""
    
    def get_title(self) -> str:
        """Return the title for this graph type."""
        return "My Custom Graph"
        
    def generate(self, data: dict[str, object]) -> str:
        """Generate the graph and return the output path."""
        # Implementation here
        pass
```

### Step 2: Required Methods

Every graph class must implement these abstract methods:

#### `get_title() -> str`
Returns a human-readable title for the graph type.

#### `generate(data: dict[str, object]) -> str`
The main method that:
1. Validates input data
2. Sets up the matplotlib figure
3. Creates the visualization
4. Saves the figure
5. Returns the output file path

### Step 3: Recommended Implementation Pattern

Follow this pattern for consistent and maintainable code:

```python
def generate(self, data: dict[str, object]) -> str:
    # 1. Validate input data
    if not self.validate_data(data):
        raise ValueError("Invalid input data")
    
    # 2. Setup figure using base class
    figure, axes = self.setup_figure()
    
    # 3. Configure styling
    sns.set_style("whitegrid")
    
    # 4. Create visualization
    try:
        # Your plotting code here
        axes.plot(x_data, y_data)
        axes.set_title(self.get_title())
        
    except Exception as e:
        logger.error(f"Error creating visualization: {e}")
        raise
    
    # 5. Save and return path
    try:
        output_path = self.save_figure(
            graph_type="my_custom_graph",
            user_id=data.get('user_id')
        )
        return output_path
    finally:
        self.cleanup()
```

## Utility Functions Available

The base class provides several utility methods:

### File Management
- `save_figure()`: Save with automatic filename generation
- `format_username()`: Censor usernames for privacy

### From Utils Module
- `ensure_graph_directory()`: Create output directories
- `generate_graph_filename()`: Standardized filename generation
- `validate_color()`: Color format validation
- `censor_username()`: Username privacy protection
- `cleanup_old_files()`: File cleanup utilities

## Adding to the Factory

### Step 1: Import Your Graph Class

Add the import to `graph_factory.py`:

```python
from .my_custom_graph import MyCustomGraph
```

### Step 2: Add to Factory Methods

Update three locations in the `GraphFactory` class:

1. **create_enabled_graphs()** method:
```python
if self.config.get("ENABLE_MY_CUSTOM_GRAPH", True):
    logger.debug("Creating my custom graph")
    graphs.append(MyCustomGraph())
```

2. **create_graph_by_type()** method:
```python
graph_type_map = {
    # ... existing mappings ...
    "my_custom_graph": MyCustomGraph,
}
```

3. **get_enabled_graph_types()** method:
```python
type_config_map: dict[str, str] = {
    # ... existing mappings ...
    "my_custom_graph": "ENABLE_MY_CUSTOM_GRAPH",
}
```

## Configuration

Add configuration options to support your new graph:

```yaml
# In config.yml
graphs:
  enable_my_custom_graph: true
```

The configuration key should match the pattern used in the factory.

## Testing

### Required Tests

Create comprehensive tests in `tests/test_my_custom_graph.py`:

1. **Instantiation tests**: Verify the class can be created
2. **Method tests**: Test all public methods
3. **Data validation tests**: Test with valid and invalid data
4. **End-to-end tests**: Full workflow from data to saved file
5. **Error handling tests**: Verify proper error handling

### Test Template

```python
import pytest
from graphs.graph_modules.my_custom_graph import MyCustomGraph

class TestMyCustomGraph:
    def test_instantiation(self) -> None:
        graph = MyCustomGraph()
        assert graph is not None
        
    def test_get_title(self) -> None:
        graph = MyCustomGraph()
        assert graph.get_title() == "My Custom Graph"
        
    def test_generate_with_valid_data(self) -> None:
        graph = MyCustomGraph()
        data = {"key": "value"}  # Your test data
        output_path = graph.generate(data)
        assert Path(output_path).exists()
        # Cleanup
        Path(output_path).unlink(missing_ok=True)
```

## Best Practices

### Code Quality
- Use type hints for all parameters and return values
- Add comprehensive docstrings
- Follow PEP 8 style guidelines
- Use meaningful variable names

### Error Handling
- Validate input data thoroughly
- Use try/except blocks around matplotlib operations
- Always call `self.cleanup()` in finally blocks
- Log errors with appropriate detail

### Performance
- Use context managers when possible
- Clean up matplotlib resources promptly
- Consider memory usage for large datasets

### Maintainability
- Keep methods focused and single-purpose
- Use utility functions to avoid code duplication
- Add helper methods for complex operations
- Document any special requirements or limitations

## Example: Complete Implementation

See `graphs/graph_modules/sample_graph.py` for a complete example that demonstrates:
- Proper inheritance from BaseGraph
- Data validation
- Error handling
- Utility function usage
- Comprehensive documentation
- Modern Python patterns

## Integration Checklist

Before submitting a new graph type:

- [ ] Extends BaseGraph correctly
- [ ] Implements all required abstract methods
- [ ] Added to GraphFactory in all three locations
- [ ] Comprehensive test coverage
- [ ] Proper error handling and logging
- [ ] Documentation and docstrings
- [ ] Follows established patterns
- [ ] Type safety verified with basedpyright
- [ ] Configuration options added

## Support

For questions or issues with graph development:
1. Review existing graph implementations for patterns
2. Check the sample_graph.py for a complete example
3. Ensure all tests pass before integration
4. Follow the established code review process
