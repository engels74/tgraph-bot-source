"""
Test module for generic graph patterns and behaviors.

This module tests common patterns and behaviors that should be consistent
across all graph implementations, focusing on generic functionality rather
than specific graph implementations.

The tests validate:
- Common initialization patterns
- Shared configuration handling
- Standard graph lifecycle behavior
- Common error handling patterns
- Resource management patterns
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, override
from unittest.mock import MagicMock, patch

import pytest

from src.tgraph_bot.graphs.graph_modules.base_graph import BaseGraph
from src.tgraph_bot.graphs.graph_modules.graph_errors import (
    GraphGenerationError,
)
from tests.utils.graph_helpers import (
    assert_graph_cleanup,
    assert_graph_properties,
    create_test_config_comprehensive,
    create_test_config_minimal,
    create_test_config_privacy_focused,
    create_test_config_selective,
    matplotlib_cleanup,
)

if TYPE_CHECKING:
    from src.tgraph_bot.config.schema import TGraphBotConfig


class GenericTestGraph(BaseGraph):
    """Generic test graph implementation for pattern testing."""
    
    def __init__(
        self,
        *,
        config: TGraphBotConfig | None = None,
        width: int = 12,
        height: int = 8,
        dpi: int = 100,
        background_color: str = "#ffffff",
        should_fail: bool = False,
        fail_on_generate: bool = False,
        fail_on_setup: bool = False,
    ) -> None:
        """Initialize generic test graph with optional failure modes."""
        super().__init__(
            config=config,
            width=width,
            height=height,
            dpi=dpi,
            background_color=background_color,
        )
        self._should_fail: bool = should_fail
        self._fail_on_generate: bool = fail_on_generate
        self._fail_on_setup: bool = fail_on_setup
    
    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """Generate a test graph with optional failure modes."""
        if self._fail_on_generate:
            msg = "Simulated generation failure"
            raise GraphGenerationError(msg)
        
        try:
            if self._fail_on_setup:
                msg = "Simulated setup failure"
                raise GraphGenerationError(msg)
            
            _ = self.setup_figure()
            
            if self.axes is not None:
                # Create simple test plot
                _ = self.axes.plot([1, 2, 3], [1, 4, 2])  # pyright: ignore[reportUnknownMemberType]
                _ = self.axes.set_title(self.get_title())  # pyright: ignore[reportUnknownMemberType]
            
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                output_path = tmp.name
            
            return self.save_figure(output_path=output_path)
        finally:
            self.cleanup()
    
    @override
    def get_title(self) -> str:
        """Get the title for this test graph."""
        return "Generic Test Graph"


class TestGenericGraphPatterns:
    """Test cases for generic graph patterns and behaviors."""
    
    def test_standard_initialization_patterns(self) -> None:
        """Test that all graphs follow standard initialization patterns."""
        # Test default initialization
        graph = GenericTestGraph()
        assert_graph_properties(graph)
        assert graph.config is None
        
        # Test with configuration
        config = create_test_config_minimal()
        graph_with_config = GenericTestGraph(config=config)
        assert graph_with_config.config is config
        
        # Test custom dimensions
        graph_custom = GenericTestGraph(width=14, height=10, dpi=120)
        assert_graph_properties(
            graph_custom,
            expected_width=14,
            expected_height=10,
            expected_dpi=120,
        )
        
        # Test custom background color
        graph_colored = GenericTestGraph(background_color="#f0f0f0")
        assert_graph_properties(
            graph_colored,
            expected_background_color="#f0f0f0",
        )
    
    def test_configuration_access_patterns(self) -> None:
        """Test that graphs consistently access configuration values."""
        # Test with minimal configuration
        minimal_config = create_test_config_minimal()
        graph_minimal = GenericTestGraph(config=minimal_config)
        
        # Test that configuration is accessible
        assert graph_minimal.config is minimal_config
        assert graph_minimal.get_config_value("TAUTULLI_API_KEY") == "test_api_key_minimal"
        
        # Test with comprehensive configuration
        comprehensive_config = create_test_config_comprehensive()
        graph_comprehensive = GenericTestGraph(config=comprehensive_config)
        
        assert graph_comprehensive.config is comprehensive_config
        assert graph_comprehensive.get_config_value("TV_COLOR") == "#2e86ab"
        assert graph_comprehensive.get_config_value("MOVIE_COLOR") == "#a23b72"
        
        # Test with privacy-focused configuration
        privacy_config = create_test_config_privacy_focused()
        graph_privacy = GenericTestGraph(config=privacy_config)
        
        assert graph_privacy.config is privacy_config
        assert graph_privacy.get_config_value("CENSOR_USERNAMES") is True
    
    def test_selective_configuration_patterns(self) -> None:
        """Test graphs with selective configuration options."""
        selective_config = create_test_config_selective(
            enable_daily_play_count=True,
            enable_play_count_by_dayofweek=False,
            enable_top_10_users=True,
        )
        
        graph = GenericTestGraph(config=selective_config)
        
        assert graph.get_config_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert graph.get_config_value("ENABLE_PLAY_COUNT_BY_DAYOFWEEK") is False
        assert graph.get_config_value("ENABLE_TOP_10_USERS") is True
    
    def test_graph_lifecycle_patterns(self) -> None:
        """Test standard graph lifecycle patterns."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Test initial state
            assert graph.figure is None
            assert graph.axes is None
            
            # Test figure setup
            _ = graph.setup_figure()
            assert graph.figure is not None
            assert graph.axes is not None
            
            # Test cleanup
            graph.cleanup()
            assert_graph_cleanup(graph)
    
    def test_context_manager_patterns(self) -> None:
        """Test that graphs work properly as context managers."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Manual setup and cleanup testing (BaseGraph doesn't implement context manager)
            _ = graph.setup_figure()
            assert graph.figure is not None
            assert graph.axes is not None
            
            graph.cleanup()
            assert_graph_cleanup(graph)
    
    def test_graph_generation_patterns(self) -> None:
        """Test standard graph generation patterns."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Test successful generation
            test_data: dict[str, object] = {"test_key": "test_value"}
            output_path = graph.generate(test_data)
            
            # Verify file was created
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
    
    def test_error_handling_patterns(self) -> None:
        """Test consistent error handling patterns across graphs."""
        # Test generation failure
        with matplotlib_cleanup():
            graph_fail_generate = GenericTestGraph(fail_on_generate=True)
            
            with pytest.raises(GraphGenerationError, match="Simulated generation failure"):
                _ = graph_fail_generate.generate({})
        
        # Test setup failure
        with matplotlib_cleanup():
            graph_fail_setup = GenericTestGraph(fail_on_setup=True)
            
            with pytest.raises(GraphGenerationError, match="Simulated setup failure"):
                _ = graph_fail_setup.generate({})
    
    def test_resource_cleanup_patterns(self) -> None:
        """Test that graphs properly clean up resources."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Set up figure
            _ = graph.setup_figure()
            figure = graph.figure
            axes = graph.axes
            
            # Verify resources exist
            assert figure is not None
            assert axes is not None
            
            # Clean up
            graph.cleanup()
            
            # Verify cleanup
            assert_graph_cleanup(graph)
    
    def test_color_handling_patterns(self) -> None:
        """Test consistent color handling patterns."""
        config = create_test_config_comprehensive()
        graph = GenericTestGraph(config=config)
        
        # Test color access methods
        tv_color = graph.get_tv_color()
        movie_color = graph.get_movie_color()
        background_color = graph.background_color
        
        assert tv_color == "#2e86ab"
        assert movie_color == "#a23b72"
        assert background_color == "#f8f9fa"
        
        # Test fallback to defaults when config is None
        graph_no_config = GenericTestGraph()
        default_tv_color = graph_no_config.get_tv_color()
        default_movie_color = graph_no_config.get_movie_color()
        
        assert default_tv_color == "#1f77b4"  # Default matplotlib blue
        assert default_movie_color == "#ff7f0e"  # Default matplotlib orange
    
    def test_annotation_settings_patterns(self) -> None:
        """Test consistent annotation settings patterns."""
        config = create_test_config_comprehensive()
        graph = GenericTestGraph(config=config)
        
        # Test annotation color access
        annotation_color = graph.get_annotation_color()
        annotation_outline_color = graph.get_annotation_outline_color()
        
        assert annotation_color == "#c73e1d"
        assert annotation_outline_color == "#ffffff"
        
        # Test annotation outline setting
        outline_enabled = graph.is_annotation_outline_enabled()
        assert outline_enabled is True
        
        # Test with privacy config (which might disable some annotations)
        privacy_config = create_test_config_privacy_focused()
        privacy_graph = GenericTestGraph(config=privacy_config)
        
        # Should still have basic annotation settings
        privacy_annotation_color = privacy_graph.get_annotation_color()
        assert privacy_annotation_color is not None
    
    def test_title_generation_patterns(self) -> None:
        """Test consistent title generation patterns."""
        graph = GenericTestGraph()
        
        # Test basic title
        title = graph.get_title()
        assert title == "Generic Test Graph"
        assert isinstance(title, str)
        assert len(title) > 0
    
    @patch('src.tgraph_bot.graphs.graph_modules.utils.apply_modern_seaborn_styling')
    def test_styling_application_patterns(self, mock_styling: MagicMock) -> None:
        """Test that graphs consistently apply styling."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Test that styling is applied during setup
            _ = graph.setup_figure()
            
            # Verify styling function was called
            mock_styling.assert_called_once()
    
    def test_save_figure_patterns(self) -> None:
        """Test consistent figure saving patterns."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Set up figure
            _ = graph.setup_figure()
            
            # Test saving to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                output_path = tmp.name
            
            saved_path = graph.save_figure(output_path=output_path)
            
            # Verify file was saved
            assert saved_path == output_path
            assert Path(output_path).exists()
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
            graph.cleanup()
    
    def test_configuration_validation_patterns(self) -> None:
        """Test that graphs handle configuration validation consistently."""
        # Test with valid configurations
        valid_configs = [
            create_test_config_minimal(),
            create_test_config_comprehensive(),
            create_test_config_privacy_focused(),
        ]
        
        for config in valid_configs:
            graph = GenericTestGraph(config=config)
            assert graph.config is config
            
            # Test that configuration is accessible
            api_key = graph.get_config_value("TAUTULLI_API_KEY")
            assert api_key is not None
            assert isinstance(api_key, str)
    
    def test_media_type_processor_patterns(self) -> None:
        """Test consistent media type processor patterns."""
        config = create_test_config_comprehensive()
        graph = GenericTestGraph(config=config)
        
        # Test that media type processor is available
        processor = graph.media_type_processor
        assert processor is not None
        
        # Test processor configuration
        assert processor.get_color_for_type("tv") == "#2e86ab"
        assert processor.get_color_for_type("movie") == "#a23b72"
    
    def test_empty_data_handling_patterns(self) -> None:
        """Test consistent empty data handling patterns."""
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Test with empty data
            empty_data: dict[str, object] = {}
            
            # Should not raise an error
            output_path = graph.generate(empty_data)
            
            # Should still create a file
            assert Path(output_path).exists()
            assert output_path.endswith('.png')
            
            # Clean up
            Path(output_path).unlink(missing_ok=True)
    
    def test_performance_characteristics_patterns(self) -> None:
        """Test that graphs maintain consistent performance characteristics."""
        import time
        
        with matplotlib_cleanup():
            graph = GenericTestGraph()
            
            # Measure setup time
            start_time = time.time()
            _ = graph.setup_figure()
            setup_time = time.time() - start_time
            
            # Setup should be reasonably fast (under 1 second)
            assert setup_time < 1.0
            
            # Measure cleanup time
            start_time = time.time()
            graph.cleanup()
            cleanup_time = time.time() - start_time
            
            # Cleanup should be very fast (under 0.1 seconds)
            assert cleanup_time < 0.1
    
    def test_memory_management_patterns(self) -> None:
        """Test consistent memory management patterns."""
        import gc
        
        with matplotlib_cleanup():
            # Create and use graph
            graph = GenericTestGraph()
            _ = graph.setup_figure()
            
            # Get initial figure reference
            figure = graph.figure
            assert figure is not None
            
            # Clean up graph
            graph.cleanup()
            
            # Force garbage collection
            _ = gc.collect()
            
            # Verify cleanup
            assert_graph_cleanup(graph)