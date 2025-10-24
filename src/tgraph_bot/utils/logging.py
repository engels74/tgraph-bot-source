"""Structured logging with sensitive value masking for TGraph Bot.

This module provides structured logging functionality with support for:
- Sensitive value masking (API keys, tokens)
- Context variable tracking for operations
- Consistent log formatting across the application
- Different log levels for different use cases
"""

import contextvars
import logging
import re
from collections.abc import Mapping
from datetime import datetime
from typing import override

# Context variables for operation tracking
operation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "operation_id", default=None
)
user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "user_id", default=None
)
command_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "command_name", default=None
)

# Sensitive field patterns to mask
SENSITIVE_PATTERNS = [
    re.compile(r"(token|key|password|secret|credential)", re.IGNORECASE),
    re.compile(r"(authorization|auth)", re.IGNORECASE),
]


def mask_sensitive_value(value: str, *, show_last: int = 4) -> str:
    """Mask a sensitive value, showing only the last N characters.

    Args:
        value: The sensitive value to mask
        show_last: Number of characters to show at the end

    Returns:
        Masked string with only last N characters visible

    Examples:
        >>> mask_sensitive_value("my_secret_api_key_12345", show_last=4)
        '**********************2345'
        >>> mask_sensitive_value("abc", show_last=4)
        '****'
    """
    if not value:
        return "****"

    if len(value) <= show_last:
        return "*" * len(value)

    return "*" * (len(value) - show_last) + value[-show_last:]


def is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data.

    Args:
        field_name: Name of the field to check

    Returns:
        True if the field name matches sensitive patterns

    Examples:
        >>> is_sensitive_field("api_key")
        True
        >>> is_sensitive_field("username")
        False
        >>> is_sensitive_field("discord_token")
        True
    """
    return any(pattern.search(field_name) for pattern in SENSITIVE_PATTERNS)


def mask_sensitive_dict(
    data: Mapping[str, object], *, show_last: int = 4, recursive: bool = True
) -> dict[str, object]:
    """Mask sensitive values in a dictionary.

    Args:
        data: Dictionary containing potentially sensitive data
        show_last: Number of characters to show at the end of masked values
        recursive: Whether to recursively mask nested dictionaries

    Returns:
        New dictionary with sensitive values masked

    Examples:
        >>> mask_sensitive_dict({"api_key": "secret123", "username": "john"})
        {'api_key': '******123', 'username': 'john'}
    """
    masked: dict[str, object] = {}

    for key, value in data.items():
        if is_sensitive_field(key) and isinstance(value, str):
            masked[key] = mask_sensitive_value(value, show_last=show_last)
        elif recursive and isinstance(value, dict):
            # Type narrowing: value is confirmed to be dict here
            dict_value: dict[str, object] = value  # pyright: ignore[reportUnknownVariableType]
            masked[key] = mask_sensitive_dict(
                dict_value, show_last=show_last, recursive=recursive
            )
        elif recursive and isinstance(value, list):
            masked[key] = [
                mask_sensitive_dict(item, show_last=show_last, recursive=recursive)  # pyright: ignore[reportUnknownArgumentType]
                if isinstance(item, dict)
                else item
                for item in value  # pyright: ignore[reportUnknownVariableType]
            ]
        else:
            masked[key] = value

    return masked


class ContextFilter(logging.Filter):
    """Logging filter that adds context variables to log records.

    This filter adds operation tracking context variables to each log record,
    enabling correlation of log messages across operations.
    """

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to the log record.

        Args:
            record: Log record to modify

        Returns:
            True to allow the record to be logged
        """
        # Add context variables as dynamic attributes to log record
        # Use "-" as default value when context variables are not set
        record.operation_id = operation_id.get() or "-"
        record.user_id = user_id.get() or "-"
        record.command_name = command_name.get() or "-"
        return True


def setup_logging(*, level: str = "INFO", format_style: str = "detailed") -> None:
    """Set up structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_style: Format style ('detailed' or 'simple')

    Examples:
        >>> setup_logging(level="DEBUG", format_style="detailed")
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Choose format based on style
    if format_style == "simple":
        log_format = "[%(levelname)s] %(message)s"
    else:
        # Detailed format with timestamp, level, location, and context
        log_format = "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d]"
        # Add context variables if available
        log_format += (
            " [op=%(operation_id)s user=%(user_id)s cmd=%(command_name)s] %(message)s"
        )

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration to ensure our settings are applied
    )

    # Add context filter to root logger and all handlers
    context_filter = ContextFilter()
    logging.root.addFilter(context_filter)

    # Also add the filter to all existing handlers to ensure it's applied
    for handler in logging.root.handlers:
        handler.addFilter(context_filter)


def log_api_request(
    logger: logging.Logger,
    method: str,
    url: str,
    *,
    status_code: int | None = None,
    error: str | None = None,
    duration_ms: float | None = None,
) -> None:
    """Log an API request with structured data.

    Args:
        logger: Logger instance to use
        method: HTTP method (GET, POST, etc.)
        url: API endpoint URL (will be logged as-is, ensure no sensitive data)
        status_code: HTTP status code if available
        error: Error message if request failed
        duration_ms: Request duration in milliseconds
    """
    extra: dict[str, object] = {
        "method": method,
        "url": url,
    }

    if status_code is not None:
        extra["status_code"] = status_code

    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)

    if error:
        logger.error(f"API request failed: {method} {url}", extra=extra, exc_info=True)
    else:
        logger.info(f"API request: {method} {url}", extra=extra)


def log_operation_start(
    logger: logging.Logger,
    operation: str,
    *,
    details: dict[str, object] | None = None,
) -> str:
    """Log the start of an operation and set operation context.

    Args:
        logger: Logger instance to use
        operation: Name of the operation starting
        details: Optional additional details to log

    Returns:
        Operation ID that was set in context

    Examples:
        >>> logger = logging.getLogger(__name__)
        >>> op_id = log_operation_start(logger, "generate_graphs", details={"days": 30})
    """
    # Generate operation ID with timestamp
    op_id = f"{operation}_{datetime.now().timestamp()}"
    _ = operation_id.set(op_id)

    extra: dict[str, object] = {"operation": operation}
    if details:
        # Mask sensitive values in details
        masked_details = mask_sensitive_dict(details)
        extra.update(masked_details)

    logger.info(f"Starting operation: {operation}", extra=extra)
    return op_id


def log_operation_complete(
    logger: logging.Logger,
    operation: str,
    *,
    success: bool = True,
    duration_ms: float | None = None,
    error: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    """Log the completion of an operation.

    Args:
        logger: Logger instance to use
        operation: Name of the operation that completed
        success: Whether the operation succeeded
        duration_ms: Operation duration in milliseconds
        error: Error message if operation failed
        details: Optional additional details to log

    Examples:
        >>> logger = logging.getLogger(__name__)
        >>> log_operation_complete(logger, "generate_graphs", duration_ms=5420.5)
    """
    extra: dict[str, object] = {
        "operation": operation,
        "success": success,
    }

    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)

    if details:
        # Mask sensitive values in details
        masked_details = mask_sensitive_dict(details)
        extra.update(masked_details)

    if success:
        logger.info(f"Completed operation: {operation}", extra=extra)
    else:
        if error:
            extra["error"] = error
        logger.error(f"Failed operation: {operation}", extra=extra, exc_info=True)

    # Clear operation context
    _ = operation_id.set(None)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance

    Examples:
        >>> logger = get_logger(__name__)
    """
    return logging.getLogger(name)
