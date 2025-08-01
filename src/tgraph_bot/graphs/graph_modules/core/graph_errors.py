"""
Graph-specific error handling for TGraph Bot graph modules.

This module provides a standardized error hierarchy for graph operations,
building on the existing TGraphBotError system to provide graph-specific
error handling with localization support and recovery patterns.

The GraphError hierarchy eliminates inconsistent error handling by providing:
- Standardized graph-specific exception classes
- Consistent error message templates with context
- Localization support through the i18n system
- Error recovery patterns and graceful degradation
- Integration with the existing error handling infrastructure

Usage Examples:
    Data validation error:
        >>> raise GraphDataError(
        ...     "Invalid play history data structure",
        ...     data_context="play_history",
        ...     expected_keys=["data", "records"]
        ... )

    Configuration error:
        >>> raise GraphConfigurationError(
        ...     "Missing required graph dimension configuration",
        ...     config_key="graphs.appearance.dimensions.width",
        ...     graph_type="daily_play_count"
        ... )

    Generation error with recovery:
        >>> try:
        ...     generate_graph()
        ... except GraphGenerationError as e:
        ...     if e.recoverable:
        ...         return fallback_graph()
        ...     raise
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, final

from ....i18n import translate
from ....utils.core.exceptions import (
    ErrorCategory,
    ErrorSeverity,
    TGraphBotError,
)
from ....utils.core.error_handler import ErrorContext

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class GraphError(TGraphBotError):
    """
    Base exception class for graph-related errors.

    This class extends TGraphBotError to provide graph-specific error handling
    with additional context information relevant to graph operations.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        recoverable: bool = True,
        graph_type: str | None = None,
        operation: str | None = None,
    ) -> None:
        """
        Initialize a graph error.

        Args:
            message: Technical error message for logging
            category: Error category for handling strategy
            severity: Error severity level
            user_message: User-friendly error message
            context: Error context information
            recoverable: Whether the error allows for recovery
            graph_type: Type of graph where error occurred
            operation: Graph operation that failed
        """
        super().__init__(
            message=message,
            category=category,
            severity=severity,
            user_message=user_message,
            context=context,
            recoverable=recoverable,
        )
        self.graph_type: str | None = graph_type
        self.operation: str | None = operation


@final
class GraphDataError(GraphError):
    """
    Data-related errors in graph processing.

    This exception is raised when there are issues with the data provided
    to graph generation, including missing data, invalid formats, or
    data validation failures.
    """

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        graph_type: str | None = None,
        data_context: str | None = None,
        expected_keys: Sequence[str] | None = None,
        received_keys: Sequence[str] | None = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize a graph data error.

        Args:
            message: Technical error message
            user_message: User-friendly message
            context: Error context
            graph_type: Type of graph
            data_context: Context of the data (e.g., "play_history", "user_data")
            expected_keys: Keys that were expected in the data
            received_keys: Keys that were actually received
            recoverable: Whether error allows recovery
        """
        # Generate user-friendly message if not provided
        if user_message is None:
            if data_context:
                user_message = translate(
                    "The {data_context} data provided is invalid or incomplete. Please check your data source and try again.",
                    data_context=data_context,
                )
            else:
                user_message = translate(
                    "The data provided for graph generation is invalid. Please check your data source and try again."
                )

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable,
            graph_type=graph_type,
            operation="data_processing",
        )
        self.data_context: str | None = data_context
        self.expected_keys: Sequence[str] | None = expected_keys
        self.received_keys: Sequence[str] | None = received_keys


@final
class GraphConfigurationError(GraphError):
    """
    Configuration-related errors in graph processing.

    This exception is raised when there are issues with graph configuration,
    including missing configuration values, invalid settings, or
    configuration validation failures.
    """

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        graph_type: str | None = None,
        config_key: str | None = None,
        config_value: object = None,
        expected_type: str | None = None,
    ) -> None:
        """
        Initialize a graph configuration error.

        Args:
            message: Technical error message
            user_message: User-friendly message
            context: Error context
            graph_type: Type of graph
            config_key: Configuration key that caused the error
            config_value: The problematic configuration value
            expected_type: Expected type/format for the configuration
        """
        # Generate user-friendly message if not provided
        if user_message is None:
            if config_key:
                user_message = translate(
                    "The configuration setting '{config_key}' is invalid or missing. Please check your configuration and try again.",
                    config_key=config_key,
                )
            else:
                user_message = translate(
                    "There is an issue with the graph configuration. Please check your settings and try again."
                )

        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            user_message=user_message,
            context=context,
            recoverable=False,
            graph_type=graph_type,
            operation="configuration",
        )
        self.config_key: str | None = config_key
        self.config_value: object = config_value
        self.expected_type: str | None = expected_type


@final
class GraphGenerationError(GraphError):
    """
    Graph generation and rendering errors.

    This exception is raised when there are issues during the actual
    graph generation process, including matplotlib errors, file I/O
    issues, or rendering failures.
    """

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        graph_type: str | None = None,
        generation_stage: str | None = None,
        output_path: str | None = None,
        recoverable: bool = True,
    ) -> None:
        """
        Initialize a graph generation error.

        Args:
            message: Technical error message
            user_message: User-friendly message
            context: Error context
            graph_type: Type of graph
            generation_stage: Stage of generation where error occurred
            output_path: Intended output path for the graph
            recoverable: Whether error allows recovery
        """
        # Generate user-friendly message if not provided
        if user_message is None:
            if graph_type:
                user_message = translate(
                    "Failed to generate the {graph_type} graph. This may be a temporary issue - please try again.",
                    graph_type=graph_type.replace("_", " ").title(),
                )
            else:
                user_message = translate(
                    "Failed to generate the requested graph. This may be a temporary issue - please try again."
                )

        super().__init__(
            message=message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable,
            graph_type=graph_type,
            operation="generation",
        )
        self.generation_stage: str | None = generation_stage
        self.output_path: str | None = output_path


@final
class GraphValidationError(GraphError):
    """
    Graph validation and verification errors.

    This exception is raised when generated graphs fail validation checks,
    including file integrity issues, dimension validation failures, or
    content verification problems.
    """

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        graph_type: str | None = None,
        validation_type: str | None = None,
        expected_value: object = None,
        actual_value: object = None,
    ) -> None:
        """
        Initialize a graph validation error.

        Args:
            message: Technical error message
            user_message: User-friendly message
            context: Error context
            graph_type: Type of graph
            validation_type: Type of validation that failed
            expected_value: Expected value for validation
            actual_value: Actual value that failed validation
        """
        # Generate user-friendly message if not provided
        if user_message is None:
            user_message = translate(
                "The generated graph failed validation checks. Please try generating the graph again."
            )

        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            user_message=user_message,
            context=context,
            recoverable=True,
            graph_type=graph_type,
            operation="validation",
        )
        self.validation_type: str | None = validation_type
        self.expected_value: object = expected_value
        self.actual_value: object = actual_value


# Error message templates for common scenarios
ERROR_MESSAGES = {
    "missing_data": "Required data '{data_key}' is missing from the input",
    "invalid_data_format": "Data format is invalid for '{data_context}': expected {expected}, got {actual}",
    "empty_dataset": "No data available for the specified time period",
    "config_missing": "Configuration key '{config_key}' is required but not found",
    "config_invalid": "Configuration value for '{config_key}' is invalid: {reason}",
    "generation_failed": "Graph generation failed at stage '{stage}': {reason}",
    "file_write_error": "Failed to write graph file to '{path}': {reason}",
    "validation_failed": "Graph validation failed for '{validation_type}': {reason}",
}


def create_standardized_error_message(template_key: str, **kwargs: object) -> str:
    """
    Create a standardized error message using templates.

    Args:
        template_key: Key for the error message template
        **kwargs: Template variables

    Returns:
        Formatted error message
    """
    template = ERROR_MESSAGES.get(template_key, "Unknown error occurred")
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        logger.warning(f"Failed to format error message template '{template_key}': {e}")
        return f"Error in {template_key}: {kwargs}"
