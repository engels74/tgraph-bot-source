"""
Unit tests for graph error handling.

This module tests the graph-specific error hierarchy and error handling
utilities to ensure proper error classification, message generation,
and recovery patterns.
"""

from __future__ import annotations

from unittest.mock import patch, Mock

from src.tgraph_bot.graphs.graph_modules import (
    GraphError,
    GraphDataError,
    GraphConfigurationError,
    GraphGenerationError,
    GraphValidationError,
)
from src.tgraph_bot.graphs.graph_modules.core.graph_errors import (
    ERROR_MESSAGES,
    create_standardized_error_message,
)
from src.tgraph_bot.utils.core.error_handler import (
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
)


class TestGraphError:
    """Test the base GraphError class."""

    def test_basic_initialization(self) -> None:
        """Test basic GraphError initialization."""
        error = GraphError("Test error message")

        assert str(error) == "Test error message"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.user_message == "Test error message"
        assert error.recoverable is True
        assert error.graph_type is None
        assert error.operation is None

    def test_full_initialization(self) -> None:
        """Test GraphError with all parameters."""
        context = ErrorContext(user_id=123, command_name="test_command")

        error = GraphError(
            message="Technical error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            user_message="User friendly message",
            context=context,
            recoverable=False,
            graph_type="daily_play_count",
            operation="data_processing",
        )

        assert str(error) == "Technical error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "User friendly message"
        assert error.recoverable is False
        assert error.graph_type == "daily_play_count"
        assert error.operation == "data_processing"
        assert error.context == context


class TestGraphDataError:
    """Test the GraphDataError class."""

    def test_basic_initialization(self) -> None:
        """Test basic GraphDataError initialization."""
        error = GraphDataError("Invalid data structure")

        assert str(error) == "Invalid data structure"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert error.operation == "data_processing"
        assert error.data_context is None
        assert error.expected_keys is None
        assert error.received_keys is None

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_with_context(
        self, mock_translate: Mock
    ) -> None:
        """Test auto-generated user message with data context."""
        mock_translate.return_value = "Translated message"

        error = GraphDataError(
            "Technical error",
            data_context="play_history",
            graph_type="daily_play_count",
        )

        mock_translate.assert_called_once()
        assert error.user_message == "Translated message"
        assert error.data_context == "play_history"
        assert error.graph_type == "daily_play_count"

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_without_context(
        self, mock_translate: Mock
    ) -> None:
        """Test auto-generated user message without data context."""
        mock_translate.return_value = "Generic translated message"

        error = GraphDataError("Technical error")

        mock_translate.assert_called_once()
        assert error.user_message == "Generic translated message"

    def test_with_key_information(self) -> None:
        """Test GraphDataError with expected and received keys."""
        expected_keys = ["data", "records", "total"]
        received_keys = ["data", "records"]

        error = GraphDataError(
            "Missing required keys",
            expected_keys=expected_keys,
            received_keys=received_keys,
            data_context="api_response",
        )

        assert error.expected_keys == expected_keys
        assert error.received_keys == received_keys
        assert error.data_context == "api_response"


class TestGraphConfigurationError:
    """Test the GraphConfigurationError class."""

    def test_basic_initialization(self) -> None:
        """Test basic GraphConfigurationError initialization."""
        error = GraphConfigurationError("Missing config value")

        assert str(error) == "Missing config value"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False
        assert error.operation == "configuration"
        assert error.config_key is None
        assert error.config_value is None
        assert error.expected_type is None

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_with_key(self, mock_translate: Mock) -> None:
        """Test auto-generated user message with config key."""
        mock_translate.return_value = "Config key error message"

        error = GraphConfigurationError(
            "Technical config error",
            config_key="GRAPH_WIDTH",
            config_value="invalid",
            expected_type="int",
        )

        mock_translate.assert_called_once()
        assert error.user_message == "Config key error message"
        assert error.config_key == "GRAPH_WIDTH"
        assert error.config_value == "invalid"
        assert error.expected_type == "int"

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_without_key(
        self, mock_translate: Mock
    ) -> None:
        """Test auto-generated user message without config key."""
        mock_translate.return_value = "Generic config error message"

        error = GraphConfigurationError("Technical config error")

        mock_translate.assert_called_once()
        assert error.user_message == "Generic config error message"


class TestGraphGenerationError:
    """Test the GraphGenerationError class."""

    def test_basic_initialization(self) -> None:
        """Test basic GraphGenerationError initialization."""
        error = GraphGenerationError("Generation failed")

        assert str(error) == "Generation failed"
        assert error.category == ErrorCategory.RESOURCE
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert error.operation == "generation"
        assert error.generation_stage is None
        assert error.output_path is None

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_with_graph_type(
        self, mock_translate: Mock
    ) -> None:
        """Test auto-generated user message with graph type."""
        mock_translate.return_value = "Graph generation error message"

        error = GraphGenerationError(
            "Technical generation error",
            graph_type="daily_play_count",
            generation_stage="rendering",
            output_path="/tmp/graph.png",
        )

        mock_translate.assert_called_once()
        assert error.user_message == "Graph generation error message"
        assert error.graph_type == "daily_play_count"
        assert error.generation_stage == "rendering"
        assert error.output_path == "/tmp/graph.png"

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message_without_graph_type(
        self, mock_translate: Mock
    ) -> None:
        """Test auto-generated user message without graph type."""
        mock_translate.return_value = "Generic generation error message"

        error = GraphGenerationError("Technical generation error")

        mock_translate.assert_called_once()
        assert error.user_message == "Generic generation error message"


class TestGraphValidationError:
    """Test the GraphValidationError class."""

    def test_basic_initialization(self) -> None:
        """Test basic GraphValidationError initialization."""
        error = GraphValidationError("Validation failed")

        assert str(error) == "Validation failed"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is True
        assert error.operation == "validation"
        assert error.validation_type is None
        assert error.expected_value is None
        assert error.actual_value is None

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.translate")
    def test_auto_generated_user_message(self, mock_translate: Mock) -> None:
        """Test auto-generated user message."""
        mock_translate.return_value = "Validation error message"

        error = GraphValidationError(
            "Technical validation error",
            validation_type="dimensions",
            expected_value=(800, 600),
            actual_value=(400, 300),
        )

        mock_translate.assert_called_once()
        assert error.user_message == "Validation error message"
        assert error.validation_type == "dimensions"
        assert error.expected_value == (800, 600)
        assert error.actual_value == (400, 300)


class TestErrorMessageTemplates:
    """Test error message templates and utilities."""

    def test_error_messages_constant(self) -> None:
        """Test that ERROR_MESSAGES contains expected templates."""
        expected_keys = {
            "missing_data",
            "invalid_data_format",
            "empty_dataset",
            "config_missing",
            "config_invalid",
            "generation_failed",
            "file_write_error",
            "validation_failed",
        }

        assert set(ERROR_MESSAGES.keys()) == expected_keys

        # Test that all templates are strings
        for template in ERROR_MESSAGES.values():
            assert isinstance(template, str)
            assert len(template) > 0

    def test_create_standardized_error_message_success(self) -> None:
        """Test successful error message creation."""
        message = create_standardized_error_message(
            "missing_data", data_key="play_history"
        )

        expected = "Required data 'play_history' is missing from the input"
        assert message == expected

    def test_create_standardized_error_message_with_multiple_params(self) -> None:
        """Test error message creation with multiple parameters."""
        message = create_standardized_error_message(
            "invalid_data_format",
            data_context="user_data",
            expected="dict",
            actual="list",
        )

        expected = "Data format is invalid for 'user_data': expected dict, got list"
        assert message == expected

    def test_create_standardized_error_message_unknown_template(self) -> None:
        """Test error message creation with unknown template."""
        message = create_standardized_error_message("unknown_template", param1="value1")

        assert message == "Unknown error occurred"

    @patch("src.tgraph_bot.graphs.graph_modules.core.graph_errors.logger")
    def test_create_standardized_error_message_format_error(
        self, mock_logger: Mock
    ) -> None:
        """Test error message creation with format error."""
        message = create_standardized_error_message(
            "missing_data"  # Missing required 'data_key' parameter
        )

        # Should log warning and return fallback message
        mock_logger.warning.assert_called_once()
        assert "Error in missing_data" in message

    def test_all_templates_format_correctly(self) -> None:
        """Test that all templates can be formatted with appropriate parameters."""
        test_params = {
            "missing_data": {"data_key": "test_key"},
            "invalid_data_format": {
                "data_context": "test",
                "expected": "dict",
                "actual": "list",
            },
            "empty_dataset": {},
            "config_missing": {"config_key": "TEST_KEY"},
            "config_invalid": {"config_key": "TEST_KEY", "reason": "invalid format"},
            "generation_failed": {"stage": "rendering", "reason": "memory error"},
            "file_write_error": {
                "path": "/tmp/test.png",
                "reason": "permission denied",
            },
            "validation_failed": {
                "validation_type": "dimensions",
                "reason": "size mismatch",
            },
        }

        for template_key, params in test_params.items():
            message = create_standardized_error_message(template_key, **params)
            assert isinstance(message, str)
            assert len(message) > 0
            # Ensure no template placeholders remain
            assert "{" not in message
            assert "}" not in message
