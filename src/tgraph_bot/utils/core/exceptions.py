"""
Basic exception classes for TGraph Bot.

This module contains fundamental exception classes that are used throughout
the codebase without creating import cycles.
"""

from __future__ import annotations

from enum import Enum


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


class TGraphBotError(Exception):
    """Base exception class for TGraph Bot specific errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: str | None = None,
        context: object | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(message)
        self.category: ErrorCategory = category
        self.severity: ErrorSeverity = severity
        self.user_message: str = user_message or message
        self.context: object | None = context
        self.recoverable: bool = recoverable


class NetworkError(TGraphBotError):
    """Network-related errors (timeouts, connection issues)."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: object | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable,
        )


class APIError(TGraphBotError):
    """API-related errors (Tautulli, Discord API)."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: object | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            user_message=user_message,
            context=context,
            recoverable=recoverable,
        )


class ValidationError(TGraphBotError):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: object | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            user_message=user_message,
            context=context,
        )


class ConfigurationError(TGraphBotError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        context: object | None = None,
    ) -> None:
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            user_message=user_message,
            context=context,
        )
