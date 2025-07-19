"""
Unified progress tracking utilities for TGraph Bot.

This module consolidates progress tracking patterns from graph_manager.py and
progress_utils.py into a unified system that eliminates DRY violations while
maintaining all existing functionality and backward compatibility.

The module provides:
- BaseProgressTracker: Abstract base class defining the progress tracking interface
- ProgressTracker: Enhanced progress tracking with callbacks, timing, and metadata
- SimpleProgressTracker: Basic progress tracking for internal operations
- ProgressTrackerConfig: Configuration options for progress tracking behavior
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Final, final, override

logger = logging.getLogger(__name__)

# Type aliases for better readability
ProgressCallback = Callable[[str, int, int, dict[str, object]], None]
ProgressMetadata = dict[str, object]


@dataclass(frozen=True)
class ProgressTrackerConfig:
    """Configuration options for progress tracking behavior."""

    # Logging configuration
    enable_debug_logging: bool = True
    log_level: str = "DEBUG"

    # Timing configuration
    track_elapsed_time: bool = True
    include_timing_in_metadata: bool = True

    # Error handling configuration
    max_errors: int = 100
    max_warnings: int = 100

    # Callback configuration
    enable_callbacks: bool = True
    callback_timeout_seconds: float = 5.0

    # Summary configuration
    include_messages_in_summary: bool = False
    include_detailed_timing: bool = True


class BaseProgressTracker(ABC):
    """
    Abstract base class for progress tracking implementations.

    Defines the common interface that all progress trackers must implement,
    ensuring consistency across different tracking implementations.
    """

    def __init__(self, config: ProgressTrackerConfig | None = None) -> None:
        """
        Initialize the base progress tracker.

        Args:
            config: Optional configuration for progress tracking behavior
        """
        self.config: ProgressTrackerConfig = config or ProgressTrackerConfig()
        self.start_time: float = time.time()
        self.current_step: int = 0
        self.total_steps: int = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @abstractmethod
    def update(self, message: str, current: int, total: int, **kwargs: object) -> None:
        """
        Update progress with a new message and step information.

        Args:
            message: Progress message to display
            current: Current step number
            total: Total number of steps
            **kwargs: Additional metadata for the progress update
        """
        pass

    def add_error(self, error: str) -> None:
        """
        Add an error to the tracker.

        Args:
            error: Error message to add
        """
        if len(self.errors) < self.config.max_errors:
            self.errors.append(error)

        if self.config.enable_debug_logging:
            logger.error(f"Progress tracker error: {error}")

    def add_warning(self, warning: str) -> None:
        """
        Add a warning to the tracker.

        Args:
            warning: Warning message to add
        """
        if len(self.warnings) < self.config.max_warnings:
            self.warnings.append(warning)

        if self.config.enable_debug_logging:
            logger.warning(f"Progress tracker warning: {warning}")

    @abstractmethod
    def get_summary(self) -> dict[str, object]:
        """
        Get a summary of the progress tracking session.

        Returns:
            Dictionary containing progress summary information
        """
        pass

    def _get_base_summary(self) -> dict[str, object]:
        """
        Get base summary information common to all progress trackers.

        Returns:
            Dictionary containing base summary information
        """
        summary: dict[str, object] = {
            "completed_steps": self.current_step,
            "total_steps": self.total_steps,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
        }

        if self.config.track_elapsed_time:
            summary["total_time"] = time.time() - self.start_time

        return summary


@final
class ProgressTracker(BaseProgressTracker):
    """
    Enhanced progress tracking with callbacks, timing, and detailed metadata.

    This class consolidates the functionality from the original ProgressTracker
    in graph_manager.py, providing enhanced progress tracking with error states,
    detailed reporting, and callback support.
    """

    def __init__(
        self,
        callback: ProgressCallback | None = None,
        config: ProgressTrackerConfig | None = None,
    ) -> None:
        """
        Initialize the enhanced progress tracker.

        Args:
            callback: Optional callback function for progress updates
            config: Optional configuration for progress tracking behavior
        """
        super().__init__(config)
        self.callback: ProgressCallback | None = callback

    @override
    def update(self, message: str, current: int, total: int, **kwargs: object) -> None:
        """
        Update progress with additional metadata and callback support.

        Args:
            message: Progress message to display
            current: Current step number
            total: Total number of steps
            **kwargs: Additional metadata for the progress update
        """
        self.current_step = current
        self.total_steps = total

        # Build metadata dictionary
        metadata: ProgressMetadata = dict(kwargs)

        if self.config.include_timing_in_metadata and self.config.track_elapsed_time:
            metadata["elapsed_time"] = time.time() - self.start_time

        # Always include error/warning information in metadata
        metadata["errors"] = self.errors.copy()
        metadata["warnings"] = self.warnings.copy()

        # Execute callback if configured and available
        if self.config.enable_callbacks and self.callback:
            try:
                self.callback(message, current, total, metadata)
            except Exception as e:
                self.add_error(f"Progress callback failed: {e}")

        # Log progress if debug logging is enabled
        if self.config.enable_debug_logging:
            elapsed_time = time.time() - self.start_time
            logger.debug(
                f"Progress: {message} ({current}/{total}) - Elapsed: {elapsed_time:.2f}s"
            )

    @override
    def get_summary(self) -> dict[str, object]:
        """
        Get a comprehensive summary of the progress tracking session.

        Returns:
            Dictionary containing detailed progress summary
        """
        return self._get_base_summary()


@final
class SimpleProgressTracker(BaseProgressTracker):
    """
    Simple progress tracker for operations that don't need callbacks or Discord updates.

    This class consolidates the functionality from the original SimpleProgressTracker
    in progress_utils.py, providing basic progress tracking functionality for internal
    operations and logging purposes.
    """

    def __init__(
        self,
        operation_name: str,
        total_steps: int = 0,
        config: ProgressTrackerConfig | None = None,
    ) -> None:
        """
        Initialize the simple progress tracker.

        Args:
            operation_name: Name of the operation being tracked
            total_steps: Total number of steps in the operation
            config: Optional configuration for progress tracking behavior
        """
        super().__init__(config)
        self.operation_name: str = operation_name
        self.total_steps: int = total_steps
        self.messages: list[str] = []

    @override
    def update(
        self,
        message: str,
        current: int | None = None,
        total: int | None = None,
        **kwargs: object,
    ) -> None:
        """
        Update progress with a new message and optional step information.

        Args:
            message: Progress message
            current: Optional current step number (auto-increments if not provided)
            total: Optional total steps (uses initialized value if not provided)
            **kwargs: Additional metadata (ignored in simple tracker)
        """
        if current is not None:
            self.current_step = current
        else:
            self.current_step += 1

        if total is not None:
            self.total_steps = total

        if self.config.include_messages_in_summary:
            self.messages.append(message)

        if self.config.enable_debug_logging:
            logger.debug(
                f"{self.operation_name} progress ({self.current_step}/{self.total_steps}): {message}"
            )

    @override
    def get_summary(self) -> dict[str, object]:
        """
        Get a summary of the progress tracking with operation-specific information.

        Returns:
            Dictionary containing progress summary with operation details
        """
        summary = self._get_base_summary()
        summary.update(
            {
                "operation_name": self.operation_name,
                "completed": self.current_step >= self.total_steps,
                "has_errors": len(self.errors) > 0,
                "has_warnings": len(self.warnings) > 0,
            }
        )

        if self.config.include_messages_in_summary:
            summary["messages"] = self.messages.copy()

        return summary


# Default configuration instances for common use cases
DEFAULT_CONFIG: Final[ProgressTrackerConfig] = ProgressTrackerConfig()
SILENT_CONFIG: Final[ProgressTrackerConfig] = ProgressTrackerConfig(
    enable_debug_logging=False,
    enable_callbacks=False,
)
DETAILED_CONFIG: Final[ProgressTrackerConfig] = ProgressTrackerConfig(
    include_messages_in_summary=True,
    include_detailed_timing=True,
)
