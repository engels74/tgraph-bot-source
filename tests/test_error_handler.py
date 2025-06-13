"""
Tests for the error handling utilities.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

import discord

from utils.error_handler import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    TGraphBotError,
    NetworkError,
    APIError,
    ValidationError,
    ConfigurationError,
    ErrorTracker,
    classify_exception,
    create_user_friendly_message,
    handle_command_error,
    log_error_with_context,
    error_handler,
    command_error_handler,
    error_tracker
)


class TestErrorContext:
    """Test ErrorContext class."""
    
    def test_error_context_creation(self) -> None:
        """Test ErrorContext creation with all parameters."""
        context = ErrorContext(
            user_id=123,
            guild_id=456,
            channel_id=789,
            command_name="test_command",
            additional_context={"key": "value"}
        )
        
        assert context.user_id == 123
        assert context.guild_id == 456
        assert context.channel_id == 789
        assert context.command_name == "test_command"
        assert context.additional_context == {"key": "value"}
        assert isinstance(context.timestamp, datetime)
    
    def test_error_context_to_dict(self) -> None:
        """Test ErrorContext to_dict conversion."""
        context = ErrorContext(
            user_id=123,
            command_name="test",
            additional_context={"test": True}
        )
        
        result = context.to_dict()
        
        assert result["user_id"] == 123
        assert result["command_name"] == "test"
        assert result["additional_context"] == {"test": True}
        assert "timestamp" in result


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_tgraph_bot_error(self) -> None:
        """Test TGraphBotError base exception."""
        error = TGraphBotError(
            "Test error",
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            user_message="User friendly message",
            recoverable=False
        )
        
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.API
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "User friendly message"
        assert error.recoverable is False
    
    def test_network_error(self) -> None:
        """Test NetworkError exception."""
        error = NetworkError("Connection timeout")
        
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
    
    def test_api_error(self) -> None:
        """Test APIError exception."""
        error = APIError("API rate limit exceeded")
        
        assert error.category == ErrorCategory.API
        assert error.severity == ErrorSeverity.MEDIUM
    
    def test_validation_error(self) -> None:
        """Test ValidationError exception."""
        error = ValidationError("Invalid input")
        
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.recoverable is False
    
    def test_configuration_error(self) -> None:
        """Test ConfigurationError exception."""
        error = ConfigurationError("Missing config file")
        
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable is False


class TestErrorTracker:
    """Test ErrorTracker class."""
    
    def test_error_tracker_record_error(self) -> None:
        """Test error recording."""
        tracker = ErrorTracker()
        
        tracker.record_error("test_error", ErrorSeverity.HIGH)
        tracker.record_error("test_error", ErrorSeverity.LOW)
        tracker.record_error("other_error", ErrorSeverity.MEDIUM)
        
        assert tracker._error_counts["test_error"] == 2
        assert tracker._error_counts["other_error"] == 1
        assert len(tracker._error_history) == 3
    
    def test_error_tracker_get_error_rate(self) -> None:
        """Test error rate calculation."""
        tracker = ErrorTracker()
        
        # Record some errors
        for _ in range(5):
            tracker.record_error("test_error")
        
        rate = tracker.get_error_rate("test_error", window_minutes=60)
        assert rate == 5 / 60  # 5 errors in 60 minutes
    
    def test_error_tracker_get_summary(self) -> None:
        """Test error summary generation."""
        tracker = ErrorTracker()
        
        tracker.record_error("error1", ErrorSeverity.CRITICAL)
        tracker.record_error("error2", ErrorSeverity.LOW)
        
        summary = tracker.get_summary()
        
        assert summary["total_errors"] == 2
        assert summary["critical_errors_1h"] == 1
        error_types = summary["error_types"]
        assert isinstance(error_types, (list, set, dict))
        assert "error1" in error_types
        assert "error2" in error_types


class TestErrorClassification:
    """Test error classification functions."""
    
    def test_classify_network_errors(self) -> None:
        """Test classification of network errors."""
        timeout_error = TimeoutError("Connection timeout")
        category, severity = classify_exception(timeout_error)
        
        assert category == ErrorCategory.NETWORK
        assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_api_errors(self) -> None:
        """Test classification of API errors."""
        api_error = Exception("API rate limit exceeded")
        category, severity = classify_exception(api_error)
        
        assert category == ErrorCategory.API
        assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_validation_errors(self) -> None:
        """Test classification of validation errors."""
        value_error = ValueError("Invalid value provided")
        category, severity = classify_exception(value_error)
        
        assert category == ErrorCategory.VALIDATION
        assert severity == ErrorSeverity.LOW
    
    def test_classify_unknown_errors(self) -> None:
        """Test classification of unknown errors."""
        unknown_error = Exception("Some random error")
        category, severity = classify_exception(unknown_error)
        
        assert category == ErrorCategory.UNKNOWN
        assert severity == ErrorSeverity.MEDIUM


class TestUserFriendlyMessages:
    """Test user-friendly message generation."""
    
    def test_create_user_friendly_message_network(self) -> None:
        """Test user-friendly message for network errors."""
        error = Exception("Connection failed")
        message = create_user_friendly_message(error, ErrorCategory.NETWORK)
        
        assert "network connectivity issue" in message.lower()
        assert "try again" in message.lower()
    
    def test_create_user_friendly_message_with_context(self) -> None:
        """Test user-friendly message with command context."""
        error = Exception("Test error")
        context = ErrorContext(command_name="test_command")
        message = create_user_friendly_message(error, ErrorCategory.API, context)
        
        assert "test_command" in message
        assert "Error in `test_command` command:" in message
    
    def test_create_user_friendly_message_permission(self) -> None:
        """Test user-friendly message for permission errors."""
        error = Exception("Access denied")
        message = create_user_friendly_message(error, ErrorCategory.PERMISSION)
        
        assert "permission" in message.lower()


class TestErrorHandling:
    """Test error handling functions."""
    
    @pytest.mark.asyncio
    async def test_handle_command_error(self) -> None:
        """Test command error handling."""
        # Mock interaction
        interaction = Mock(spec=discord.Interaction)
        interaction.user = Mock()
        interaction.user.id = 123
        interaction.guild = Mock()
        interaction.guild.id = 456
        interaction.channel = Mock()
        interaction.channel.id = 789
        interaction.command = Mock()
        interaction.command.name = "test_command"
        
        error = ValueError("Test validation error")
        
        with patch('utils.error_handler.send_error_response') as mock_send:
            mock_send.return_value = True
            await handle_command_error(interaction, error)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[1]['title'] == "Command Error"
            assert "invalid" in call_args[1]['description'].lower()
    
    def test_log_error_with_context(self) -> None:
        """Test error logging with context."""
        error = ValueError("Test error")
        context = ErrorContext(user_id=123, command_name="test")
        
        with patch('utils.error_handler.logger') as mock_logger:
            log_error_with_context(error, context)
            
            # Should log at info level for low severity validation error
            mock_logger.info.assert_called_once()


class TestErrorDecorators:
    """Test error handling decorators."""
    
    @pytest.mark.asyncio
    async def test_error_handler_decorator_success(self) -> None:
        """Test error_handler decorator with successful function."""
        @error_handler()
        async def test_function() -> str:
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_error_handler_decorator_with_retry(self) -> None:
        """Test error_handler decorator with retry logic."""
        call_count = 0
        
        @error_handler(retry_attempts=2, retry_delay=0.01)
        async def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Temporary network error")
            return "success"
        
        result = await test_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_error_handler_decorator_permanent_error(self) -> None:
        """Test error_handler decorator with permanent error."""
        @error_handler(retry_attempts=2)
        async def test_function() -> str:
            raise ConfigurationError("Permanent config error")
        
        with pytest.raises(ConfigurationError):
            await test_function()
    
    @pytest.mark.asyncio
    async def test_command_error_handler_decorator(self) -> None:
        """Test command_error_handler decorator."""
        interaction = Mock(spec=discord.Interaction)
        interaction.user = Mock()
        interaction.user.id = 123
        interaction.guild = None
        interaction.channel = Mock()
        interaction.channel.id = 789
        
        @command_error_handler()
        async def test_command(self: Mock, interaction: discord.Interaction) -> None:
            raise ValueError("Test error")
        
        mock_self = Mock()
        
        with patch('utils.error_handler.handle_command_error') as mock_handle:
            await test_command(mock_self, interaction)
            mock_handle.assert_called_once()


class TestGlobalErrorTracker:
    """Test global error tracker instance."""
    
    def test_global_error_tracker_exists(self) -> None:
        """Test that global error tracker exists and works."""
        initial_count = len(error_tracker._error_history)
        
        error_tracker.record_error("test_global_error")
        
        assert len(error_tracker._error_history) == initial_count + 1
        assert "test_global_error" in error_tracker._error_counts
