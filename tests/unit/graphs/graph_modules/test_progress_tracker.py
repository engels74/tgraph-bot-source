"""
Tests for the unified progress tracking utilities.

This module provides comprehensive test coverage for the consolidated progress
tracking system, ensuring all functionality from the original ProgressTracker
and SimpleProgressTracker implementations is preserved and working correctly.
"""

import time
from unittest.mock import MagicMock


from src.tgraph_bot.graphs.graph_modules import (
    BaseProgressTracker,
    ProgressTracker,
    ProgressTrackerConfig,
    SimpleProgressTracker,
)
from src.tgraph_bot.graphs.graph_modules.utils.progress_tracker import (
    DEFAULT_CONFIG,
    DETAILED_CONFIG,
    SILENT_CONFIG,
)


class TestProgressTrackerConfig:
    """Test ProgressTrackerConfig functionality."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ProgressTrackerConfig()

        assert config.enable_debug_logging is True
        assert config.log_level == "DEBUG"
        assert config.track_elapsed_time is True
        assert config.include_timing_in_metadata is True
        assert config.max_errors == 100
        assert config.max_warnings == 100
        assert config.enable_callbacks is True
        assert config.callback_timeout_seconds == 5.0
        assert config.include_messages_in_summary is False
        assert config.include_detailed_timing is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = ProgressTrackerConfig(
            enable_debug_logging=False,
            max_errors=50,
            max_warnings=25,
            enable_callbacks=False,
        )

        assert config.enable_debug_logging is False
        assert config.max_errors == 50
        assert config.max_warnings == 25
        assert config.enable_callbacks is False

    def test_predefined_configs(self) -> None:
        """Test predefined configuration instances."""
        # Test DEFAULT_CONFIG
        assert DEFAULT_CONFIG.enable_debug_logging is True
        assert DEFAULT_CONFIG.enable_callbacks is True

        # Test SILENT_CONFIG
        assert SILENT_CONFIG.enable_debug_logging is False
        assert SILENT_CONFIG.enable_callbacks is False

        # Test DETAILED_CONFIG
        assert DETAILED_CONFIG.include_messages_in_summary is True
        assert DETAILED_CONFIG.include_detailed_timing is True


class TestBaseProgressTracker:
    """Test BaseProgressTracker abstract base class."""

    def test_base_initialization(self) -> None:
        """Test base progress tracker initialization."""

        # Create a concrete implementation for testing
        class ConcreteTracker(BaseProgressTracker):
            def update(
                self, message: str, current: int, total: int, **kwargs: object
            ) -> None:
                self.current_step = current
                self.total_steps = total

            def get_summary(self) -> dict[str, object]:
                return self._get_base_summary()

        tracker = ConcreteTracker()

        assert isinstance(tracker.config, ProgressTrackerConfig)
        assert tracker.current_step == 0
        assert tracker.total_steps == 0
        assert tracker.errors == []
        assert tracker.warnings == []
        assert isinstance(tracker.start_time, float)

    def test_error_handling(self) -> None:
        """Test error tracking functionality."""

        class ConcreteTracker(BaseProgressTracker):
            def update(
                self, message: str, current: int, total: int, **kwargs: object
            ) -> None:
                pass

            def get_summary(self) -> dict[str, object]:
                return self._get_base_summary()

        tracker = ConcreteTracker()

        tracker.add_error("Test error 1")
        tracker.add_error("Test error 2")

        assert len(tracker.errors) == 2
        assert tracker.errors[0] == "Test error 1"
        assert tracker.errors[1] == "Test error 2"

    def test_warning_handling(self) -> None:
        """Test warning tracking functionality."""

        class ConcreteTracker(BaseProgressTracker):
            def update(
                self, message: str, current: int, total: int, **kwargs: object
            ) -> None:
                pass

            def get_summary(self) -> dict[str, object]:
                return self._get_base_summary()

        tracker = ConcreteTracker()

        tracker.add_warning("Test warning 1")
        tracker.add_warning("Test warning 2")

        assert len(tracker.warnings) == 2
        assert tracker.warnings[0] == "Test warning 1"
        assert tracker.warnings[1] == "Test warning 2"

    def test_max_errors_limit(self) -> None:
        """Test that error count is limited by configuration."""
        config = ProgressTrackerConfig(max_errors=2)

        class ConcreteTracker(BaseProgressTracker):
            def update(
                self, message: str, current: int, total: int, **kwargs: object
            ) -> None:
                pass

            def get_summary(self) -> dict[str, object]:
                return self._get_base_summary()

        tracker = ConcreteTracker(config)

        tracker.add_error("Error 1")
        tracker.add_error("Error 2")
        tracker.add_error("Error 3")  # Should be ignored due to limit

        assert len(tracker.errors) == 2
        assert "Error 3" not in tracker.errors

    def test_base_summary(self) -> None:
        """Test base summary generation."""

        class ConcreteTracker(BaseProgressTracker):
            def update(
                self, message: str, current: int, total: int, **kwargs: object
            ) -> None:
                self.current_step = current
                self.total_steps = total

            def get_summary(self) -> dict[str, object]:
                return self._get_base_summary()

        tracker = ConcreteTracker()
        tracker.update("Test", 3, 5)
        tracker.add_error("Test error")
        tracker.add_warning("Test warning")

        summary = tracker.get_summary()

        assert summary["completed_steps"] == 3
        assert summary["total_steps"] == 5
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert summary["errors"] == ["Test error"]
        assert summary["warnings"] == ["Test warning"]
        assert "total_time" in summary


class TestProgressTracker:
    """Test ProgressTracker enhanced implementation."""

    def test_initialization(self) -> None:
        """Test ProgressTracker initialization."""
        callback = MagicMock()
        tracker = ProgressTracker(callback)

        assert tracker.callback == callback
        assert tracker.current_step == 0
        assert tracker.total_steps == 0
        assert tracker.errors == []
        assert tracker.warnings == []
        assert isinstance(tracker.start_time, float)

    def test_initialization_without_callback(self) -> None:
        """Test ProgressTracker initialization without callback."""
        tracker = ProgressTracker()

        assert tracker.callback is None
        assert isinstance(tracker.config, ProgressTrackerConfig)

    def test_update_with_callback(self) -> None:
        """Test progress update with callback execution."""
        callback = MagicMock()
        tracker = ProgressTracker(callback)

        tracker.update("Test message", 1, 3, test_data="value")

        assert tracker.current_step == 1
        assert tracker.total_steps == 3
        callback.assert_called_once()

        # Verify callback arguments
        args, kwargs = callback.call_args
        assert args[0] == "Test message"
        assert args[1] == 1
        assert args[2] == 3
        assert isinstance(args[3], dict)  # metadata
        assert "test_data" in args[3]
        assert args[3]["test_data"] == "value"

    def test_update_without_callback(self) -> None:
        """Test progress update without callback."""
        tracker = ProgressTracker()

        tracker.update("Test message", 2, 4)

        assert tracker.current_step == 2
        assert tracker.total_steps == 4

    def test_callback_error_handling(self) -> None:
        """Test that callback errors are handled gracefully."""

        def failing_callback(
            message: str, current: int, total: int, metadata: dict[str, object]
        ) -> None:
            raise ValueError("Callback failed")

        tracker = ProgressTracker(failing_callback)

        tracker.update("Test", 1, 2)

        # Should have recorded the callback error
        assert len(tracker.errors) == 1
        assert "Progress callback failed" in tracker.errors[0]

    def test_metadata_inclusion(self) -> None:
        """Test that metadata includes timing and error information."""
        callback = MagicMock()
        tracker = ProgressTracker(callback)
        tracker.add_error("Test error")
        tracker.add_warning("Test warning")

        tracker.update("Test", 1, 2, custom_data="test")

        # Verify metadata content
        args, kwargs = callback.call_args
        metadata = args[3]

        assert "elapsed_time" in metadata
        assert "errors" in metadata
        assert "warnings" in metadata
        assert "custom_data" in metadata
        assert metadata["custom_data"] == "test"
        assert metadata["errors"] == ["Test error"]
        assert metadata["warnings"] == ["Test warning"]

    def test_silent_config(self) -> None:
        """Test progress tracker with silent configuration."""
        callback = MagicMock()
        tracker = ProgressTracker(callback, SILENT_CONFIG)

        tracker.update("Test", 1, 2)

        # Callback should not be called due to silent config
        callback.assert_not_called()

    def test_summary_generation(self) -> None:
        """Test comprehensive summary generation."""
        tracker = ProgressTracker()
        tracker.update("Test", 2, 5)
        tracker.add_error("Error 1")
        tracker.add_warning("Warning 1")

        summary = tracker.get_summary()

        assert summary["completed_steps"] == 2
        assert summary["total_steps"] == 5
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert "total_time" in summary
        assert summary["errors"] == ["Error 1"]
        assert summary["warnings"] == ["Warning 1"]


class TestSimpleProgressTracker:
    """Test SimpleProgressTracker basic implementation."""

    def test_initialization(self) -> None:
        """Test SimpleProgressTracker initialization."""
        tracker = SimpleProgressTracker("Test Operation", 10)

        assert tracker.operation_name == "Test Operation"
        assert tracker.total_steps == 10
        assert tracker.current_step == 0
        assert tracker.messages == []
        assert tracker.errors == []
        assert tracker.warnings == []

    def test_update_with_explicit_step(self) -> None:
        """Test progress update with explicit step number."""
        tracker = SimpleProgressTracker("Test Op")

        tracker.update("Step 1", current=1, total=3)

        assert tracker.current_step == 1
        assert tracker.total_steps == 3

    def test_update_with_auto_increment(self) -> None:
        """Test progress update with automatic step increment."""
        tracker = SimpleProgressTracker("Test Op", 5)

        tracker.update("Step 1")
        tracker.update("Step 2")

        assert tracker.current_step == 2
        assert tracker.total_steps == 5

    def test_message_tracking(self) -> None:
        """Test message tracking with detailed configuration."""
        tracker = SimpleProgressTracker("Test Op", config=DETAILED_CONFIG)

        tracker.update("Message 1")
        tracker.update("Message 2")

        assert len(tracker.messages) == 2
        assert tracker.messages[0] == "Message 1"
        assert tracker.messages[1] == "Message 2"

    def test_summary_generation(self) -> None:
        """Test simple tracker summary generation."""
        tracker = SimpleProgressTracker("Test Operation", 5)
        tracker.update("Step 1", 2)
        tracker.add_error("Test error")
        tracker.add_warning("Test warning")

        summary = tracker.get_summary()

        assert summary["operation_name"] == "Test Operation"
        assert summary["completed_steps"] == 2
        assert summary["total_steps"] == 5
        assert summary["completed"] is False
        assert summary["has_errors"] is True
        assert summary["has_warnings"] is True
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1

    def test_completion_detection(self) -> None:
        """Test completion detection in summary."""
        tracker = SimpleProgressTracker("Test Op", 3)
        tracker.update("Final step", 3)

        summary = tracker.get_summary()

        assert summary["completed"] is True

    def test_messages_in_summary(self) -> None:
        """Test that messages are included in summary when configured."""
        config = ProgressTrackerConfig(include_messages_in_summary=True)
        tracker = SimpleProgressTracker("Test Op", config=config)

        tracker.update("Message 1")
        tracker.update("Message 2")

        summary = tracker.get_summary()

        assert "messages" in summary
        assert summary["messages"] == ["Message 1", "Message 2"]


class TestProgressTrackerIntegration:
    """Test integration scenarios and backward compatibility."""

    def test_backward_compatibility_with_original_interface(self) -> None:
        """Test that the new ProgressTracker maintains the original interface."""
        # This test ensures the new implementation can be used as a drop-in replacement
        callback = MagicMock()
        tracker = ProgressTracker(callback)

        # Original interface methods
        tracker.update("Test", 1, 3, extra_data="test")
        tracker.add_error("Error")
        tracker.add_warning("Warning")
        summary = tracker.get_summary()

        # Verify all original functionality works
        assert tracker.current_step == 1
        assert tracker.total_steps == 3
        assert len(tracker.errors) == 1
        assert len(tracker.warnings) == 1
        assert isinstance(summary, dict)
        callback.assert_called_once()

    def test_simple_tracker_backward_compatibility(self) -> None:
        """Test that SimpleProgressTracker maintains original interface."""
        tracker = SimpleProgressTracker("Test Op", 5)

        # Original interface methods
        tracker.update("Message")
        tracker.add_error("Error")
        tracker.add_warning("Warning")
        summary = tracker.get_summary()

        # Verify all original functionality works
        assert tracker.current_step == 1
        assert tracker.operation_name == "Test Op"
        assert len(tracker.errors) == 1
        assert len(tracker.warnings) == 1
        assert isinstance(summary, dict)
        assert "operation_name" in summary

    def test_timing_accuracy(self) -> None:
        """Test that timing measurements are reasonably accurate."""
        tracker = ProgressTracker()

        _ = time.time()
        time.sleep(0.01)  # Small delay
        tracker.update("Test", 1, 1)

        summary = tracker.get_summary()
        elapsed = summary["total_time"]

        assert isinstance(elapsed, float)
        assert elapsed >= 0.01  # Should be at least the sleep time
        assert elapsed < 1.0  # Should be reasonable
