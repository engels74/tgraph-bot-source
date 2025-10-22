"""Custom exception hierarchy for TGraph Bot.

This module defines the exception hierarchy for all TGraph Bot errors,
providing specific exception types for different error scenarios.
"""


class TGraphBotError(Exception):
    """Base exception for all TGraph Bot errors.

    All custom exceptions in the TGraph Bot application should inherit from this
    base exception to enable consistent error handling and logging.
    """


class ConfigurationError(TGraphBotError):
    """Configuration validation or loading errors.

    Raised when configuration files cannot be loaded, parsed, or validated.
    This includes YAML syntax errors, missing required fields, and invalid
    configuration values.

    Attributes:
        field_name: Optional name of the configuration field that failed validation
        expected_value: Optional description of the expected value or format
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str | None = None,
        expected_value: str | None = None,
    ) -> None:
        """Initialize ConfigurationError with optional field details.

        Args:
            message: Error message describing the configuration issue
            field_name: Name of the configuration field that caused the error
            expected_value: Description of expected value or format
        """
        super().__init__(message)
        self.field_name: str | None = field_name
        self.expected_value: str | None = expected_value


class TautulliAPIError(TGraphBotError):
    """Tautulli API communication errors.

    Raised when communication with the Tautulli API fails, including network
    errors, authentication failures, and invalid API responses.

    Attributes:
        status_code: HTTP status code if available
        url: API endpoint URL that was accessed
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        url: str | None = None,
    ) -> None:
        """Initialize TautulliAPIError with optional HTTP details.

        Args:
            message: Error message describing the API failure
            status_code: HTTP status code returned by the API
            url: URL of the API endpoint that failed
        """
        super().__init__(message)
        self.status_code: int | None = status_code
        self.url: str | None = url


class GraphGenerationError(TGraphBotError):
    """Graph generation and rendering errors.

    Raised when graph generation or rendering fails, including data processing
    errors, matplotlib rendering issues, and file I/O failures.

    Attributes:
        graph_type: Type of graph that failed to generate
        data_range_days: Number of days of data being processed
    """

    def __init__(
        self,
        message: str,
        *,
        graph_type: str | None = None,
        data_range_days: int | None = None,
    ) -> None:
        """Initialize GraphGenerationError with optional graph details.

        Args:
            message: Error message describing the generation failure
            graph_type: Type of graph that failed (e.g., 'daily_play_count')
            data_range_days: Number of days of data being processed
        """
        super().__init__(message)
        self.graph_type: str | None = graph_type
        self.data_range_days: int | None = data_range_days


class RateLimitError(TGraphBotError):
    """Command rate limit exceeded.

    Raised when a user attempts to execute a command while still on cooldown,
    either due to per-user or global rate limits.

    Attributes:
        retry_after: Seconds until the command can be used again
        is_user_cooldown: True if user cooldown, False if global cooldown
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float,
        is_user_cooldown: bool = True,
    ) -> None:
        """Initialize RateLimitError with cooldown details.

        Args:
            message: Error message describing the rate limit
            retry_after: Seconds until the command can be used again
            is_user_cooldown: Whether this is a per-user or global cooldown
        """
        super().__init__(message)
        self.retry_after: float = retry_after
        self.is_user_cooldown: bool = is_user_cooldown
