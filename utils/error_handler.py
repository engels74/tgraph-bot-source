"""
Centralized error handling utilities for TGraph Bot.

This module provides comprehensive error handling capabilities including:
- Error classification and categorization
- Retry mechanisms with exponential backoff
- Error context tracking and logging
- User-friendly error message generation
- Error recovery strategies
"""

import asyncio
import functools
import logging
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, TypeVar, ParamSpec
from collections import defaultdict
from collections.abc import Awaitable, Callable

import discord

from utils.command_utils import send_error_response

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type variables for decorators
P = ParamSpec('P')
T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for appropriate handling strategies."""
    NETWORK = "network"
    API = "api"
    PERMISSION = "permission"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    DISCORD = "discord"
    UNKNOWN = "unknown"


class ErrorContext:
    """Context information for error tracking and debugging."""

    def __init__(
        self,
        user_id: int | None = None,
        guild_id: int | None = None,
        channel_id: int | None = None,
        command_name: str | None = None,
        additional_context: dict[str, object] | None = None
    ) -> None:
        self.user_id: int | None = user_id
        self.guild_id: int | None = guild_id
        self.channel_id: int | None = channel_id
        self.command_name: str | None = command_name
        self.additional_context: dict[str, object] = additional_context or {}
        self.timestamp: datetime = datetime.now()

    def to_dict(self) -> dict[str, object]:
        """Convert context to dictionary for logging."""
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "command_name": self.command_name,
            "timestamp": self.timestamp.isoformat(),
            "additional_context": self.additional_context
        }


class TGraphBotError(Exception):
    """Base exception class for TGraph Bot specific errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        recoverable: bool = True
    ) -> None:
        super().__init__(message)
        self.category: ErrorCategory = category
        self.severity: ErrorSeverity = severity
        self.user_message: str = user_message or message
        self.context: ErrorContext | None = context
        self.recoverable: bool = recoverable


class NetworkError(TGraphBotError):
    """Network-related errors (timeouts, connection issues)."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        recoverable: bool = True
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable
        )


class APIError(TGraphBotError):
    """API-related errors (Tautulli, Discord API)."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None,
        recoverable: bool = True
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable
        )


class ValidationError(TGraphBotError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            user_message=user_message,
            context=context
        )


class ConfigurationError(TGraphBotError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: ErrorContext | None = None
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            user_message=user_message,
            context=context
        )


class ErrorTracker:
    """Track error patterns and frequencies for monitoring."""

    def __init__(self) -> None:
        self._error_counts: dict[str, int] = defaultdict(int)
        self._last_errors: dict[str, datetime] = {}
        self._error_history: list[tuple[datetime, str, ErrorSeverity]] = []
    
    def record_error(
        self,
        error_type: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ) -> None:
        """Record an error occurrence."""
        now = datetime.now()
        self._error_counts[error_type] += 1
        self._last_errors[error_type] = now
        self._error_history.append((now, error_type, severity))
        
        # Keep only last 1000 errors
        if len(self._error_history) > 1000:
            self._error_history = self._error_history[-1000:]
    
    def get_error_rate(self, error_type: str, window_minutes: int = 60) -> float:
        """Get error rate for a specific error type within time window."""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_errors = [
            e for e in self._error_history
            if e[0] > cutoff and e[1] == error_type
        ]
        return len(recent_errors) / window_minutes  # errors per minute
    
    def get_summary(self) -> dict[str, object]:
        """Get error tracking summary."""
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=1)

        recent_errors = [e for e in self._error_history if e[0] > recent_cutoff]
        critical_errors = [e for e in recent_errors if e[2] == ErrorSeverity.CRITICAL]

        return {
            "total_errors": len(self._error_history),
            "recent_errors_1h": len(recent_errors),
            "critical_errors_1h": len(critical_errors),
            "error_types": dict(self._error_counts),
            "last_error_times": {k: v.isoformat() for k, v in self._last_errors.items()}
        }


# Global error tracker instance
error_tracker = ErrorTracker()


def classify_exception(exception: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
    """Classify an exception to determine handling strategy."""
    error_str = str(exception).lower()
    exception_type = type(exception).__name__.lower()
    
    # Network-related errors
    if any(keyword in error_str for keyword in [
        "timeout", "connection", "network", "unreachable", "dns"
    ]) or any(exc_type in exception_type for exc_type in [
        "timeout", "connection", "network"
    ]):
        return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
    
    # API errors
    if any(keyword in error_str for keyword in [
        "api", "rate limit", "quota", "unauthorized", "forbidden"
    ]) or any(exc_type in exception_type for exc_type in [
        "http", "api"
    ]):
        return ErrorCategory.API, ErrorSeverity.MEDIUM
    
    # Discord-specific errors
    if any(exc_type in exception_type for exc_type in [
        "discord", "interaction", "webhook"
    ]):
        return ErrorCategory.DISCORD, ErrorSeverity.MEDIUM
    
    # Permission errors
    if any(keyword in error_str for keyword in [
        "permission", "access denied", "forbidden"
    ]):
        return ErrorCategory.PERMISSION, ErrorSeverity.LOW
    
    # Validation errors
    if any(exc_type in exception_type for exc_type in [
        "value", "type", "validation"
    ]):
        return ErrorCategory.VALIDATION, ErrorSeverity.LOW
    
    # Configuration errors
    if any(keyword in error_str for keyword in [
        "config", "setting", "missing", "not found"
    ]):
        return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH
    
    # Resource errors
    if any(keyword in error_str for keyword in [
        "memory", "disk", "space", "resource"
    ]):
        return ErrorCategory.RESOURCE, ErrorSeverity.HIGH
    
    return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


def create_user_friendly_message(
    exception: Exception,  # pyright: ignore[reportUnusedParameter]
    category: ErrorCategory,
    context: ErrorContext | None = None
) -> str:
    """Create a user-friendly error message based on error category."""
    base_messages = {
        ErrorCategory.NETWORK: "There was a network connectivity issue. Please try again in a moment.",
        ErrorCategory.API: "The external service is temporarily unavailable. Please try again later.",
        ErrorCategory.PERMISSION: "You don't have permission to perform this action.",
        ErrorCategory.VALIDATION: "The provided input is invalid. Please check your parameters and try again.",
        ErrorCategory.CONFIGURATION: "There's a configuration issue. Please contact the server administrators.",
        ErrorCategory.RESOURCE: "The server is experiencing resource constraints. Please try again later.",
        ErrorCategory.DISCORD: "There was an issue communicating with Discord. Please try again.",
        ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or contact support if the issue persists."
    }
    
    message = base_messages.get(category, base_messages[ErrorCategory.UNKNOWN])
    
    # Add context-specific information if available
    if context and context.command_name:
        message = f"Error in `{context.command_name}` command: {message}"
    
    return message


async def handle_command_error(
    interaction: discord.Interaction,
    error: Exception,
    context: ErrorContext | None = None
) -> None:
    """Handle command errors with comprehensive logging and user feedback."""
    # Create context if not provided
    if context is None:
        context = ErrorContext(
            user_id=interaction.user.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            channel_id=interaction.channel.id if interaction.channel else None,
            command_name=getattr(interaction.command, 'name', None)
        )
    
    # Classify the error
    category, severity = classify_exception(error)
    
    # Track the error
    error_type = f"{category.value}_{type(error).__name__}"
    error_tracker.record_error(error_type, severity)
    
    # Log the error with context
    log_error_with_context(error, context, category, severity)
    
    # Create user-friendly message
    user_message = create_user_friendly_message(error, category, context)
    
    # Send error response to user
    _ = await send_error_response(
        interaction=interaction,
        title="Command Error",
        description=user_message,
        ephemeral=True
    )


def log_error_with_context(
    error: Exception,
    context: ErrorContext | None = None,
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None
) -> None:
    """Log error with comprehensive context information."""
    if category is None or severity is None:
        category, severity = classify_exception(error)
    
    # Prepare log message
    error_info: dict[str, object] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "category": category.value,
        "severity": severity.value,
        "traceback": traceback.format_exc()
    }

    if context:
        context_dict = context.to_dict()
        for key, value in context_dict.items():
            error_info[key] = value
    
    # Log at appropriate level based on severity
    if severity == ErrorSeverity.CRITICAL:
        logger.critical(f"Critical error occurred: {error_info}")
    elif severity == ErrorSeverity.HIGH:
        logger.error(f"High severity error: {error_info}")
    elif severity == ErrorSeverity.MEDIUM:
        logger.warning(f"Medium severity error: {error_info}")
    else:
        logger.info(f"Low severity error: {error_info}")


def error_handler(
    *,
    category: ErrorCategory | None = None,
    severity: ErrorSeverity | None = None,
    user_message: str | None = None,  # pyright: ignore[reportUnusedParameter]
    retry_attempts: int = 0,
    retry_delay: float = 1.0
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator for comprehensive error handling in async functions.
    
    Args:
        category: Error category override
        severity: Error severity override
        user_message: Custom user message
        retry_attempts: Number of retry attempts for recoverable errors
        retry_delay: Delay between retry attempts
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(retry_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    error_category, error_severity = classify_exception(e)
                    
                    # Use override values if provided
                    if category is not None:
                        error_category = category
                    if severity is not None:
                        error_severity = severity
                    
                    # Track error
                    error_type = f"{error_category.value}_{type(e).__name__}"
                    error_tracker.record_error(error_type, error_severity)
                    
                    # Log error
                    context = ErrorContext(
                        command_name=func.__name__,
                        additional_context={"attempt": attempt + 1, "max_attempts": retry_attempts + 1}
                    )
                    log_error_with_context(e, context, error_category, error_severity)
                    
                    # Don't retry on last attempt or non-recoverable errors
                    if attempt == retry_attempts or error_severity == ErrorSeverity.CRITICAL:
                        break
                    
                    # Wait before retry
                    if retry_delay > 0:
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # pyright: ignore[reportAny]
            
            # All attempts failed, re-raise the last exception
            if last_exception:
                raise last_exception
            
            # This should never happen, but satisfy type checker
            raise RuntimeError("Unexpected error in error_handler decorator")
        
        return wrapper
    return decorator


def command_error_handler(
    user_message: str | None = None,  # pyright: ignore[reportUnusedParameter]
    retry_attempts: int = 0  # pyright: ignore[reportUnusedParameter]
) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
    """
    Decorator specifically for Discord command error handling.

    Args:
        user_message: Custom user message for errors
        retry_attempts: Number of retry attempts
    """
    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        @functools.wraps(func)
        async def wrapper(self: object, interaction: discord.Interaction, *args: object, **kwargs: object) -> None:
            try:
                await func(self, interaction, *args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    user_id=interaction.user.id,
                    guild_id=interaction.guild.id if interaction.guild else None,
                    channel_id=interaction.channel.id if interaction.channel else None,
                    command_name=func.__name__
                )

                await handle_command_error(interaction, e, context)

        return wrapper
    return decorator


def get_error_summary() -> dict[str, object]:
    """Get a summary of recent errors for monitoring."""
    return error_tracker.get_summary()


def reset_error_tracking() -> None:
    """Reset error tracking (useful for testing)."""
    global error_tracker
    error_tracker = ErrorTracker()


async def log_performance_metrics(
    operation_name: str,
    duration: float,
    success: bool,
    additional_metrics: dict[str, object] | None = None
) -> None:
    """
    Log performance metrics for monitoring and optimization.

    Args:
        operation_name: Name of the operation
        duration: Duration in seconds
        success: Whether the operation succeeded
        additional_metrics: Additional metrics to log
    """
    metrics: dict[str, object] = {
        "operation": operation_name,
        "duration_seconds": duration,
        "success": success,
        "timestamp": datetime.now().isoformat()
    }

    if additional_metrics:
        for key, value in additional_metrics.items():
            metrics[key] = value

    # Log at appropriate level
    if success:
        if duration > 30:  # Slow operations
            logger.warning(f"Slow operation completed: {metrics}")
        else:
            logger.info(f"Operation completed: {metrics}")
    else:
        logger.error(f"Operation failed: {metrics}")


class PerformanceMonitor:
    """Context manager for monitoring operation performance."""

    def __init__(self, operation_name: str, additional_metrics: dict[str, object] | None = None) -> None:
        self.operation_name: str = operation_name
        self.additional_metrics: dict[str, object] = additional_metrics or {}
        self.start_time: float = 0.0
        self.success: bool = False

    async def __aenter__(self) -> "PerformanceMonitor":
        self.start_time = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        duration = asyncio.get_event_loop().time() - self.start_time
        self.success = exc_type is None

        await log_performance_metrics(
            self.operation_name,
            duration,
            self.success,
            self.additional_metrics
        )
