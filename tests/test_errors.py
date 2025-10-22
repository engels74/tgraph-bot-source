"""Tests for custom exception hierarchy."""

import pytest

from tgraph_bot.utils.errors import (
    ConfigurationError,
    GraphGenerationError,
    RateLimitError,
    TautulliAPIError,
    TGraphBotError,
)


class TestTGraphBotError:
    """Tests for base TGraphBotError exception."""

    def test_base_exception_creation(self) -> None:
        """Test creating base exception with message."""
        error = TGraphBotError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_base_exception_inheritance(self) -> None:
        """Test that all custom exceptions inherit from TGraphBotError."""
        assert issubclass(ConfigurationError, TGraphBotError)
        assert issubclass(TautulliAPIError, TGraphBotError)
        assert issubclass(GraphGenerationError, TGraphBotError)
        assert issubclass(RateLimitError, TGraphBotError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_basic(self) -> None:
        """Test creating ConfigurationError with just a message."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert error.field_name is None
        assert error.expected_value is None

    def test_configuration_error_with_field_name(self) -> None:
        """Test ConfigurationError with field name."""
        error = ConfigurationError(
            "Invalid port number", field_name="services.discord.port"
        )
        assert str(error) == "Invalid port number"
        assert error.field_name == "services.discord.port"
        assert error.expected_value is None

    def test_configuration_error_with_expected_value(self) -> None:
        """Test ConfigurationError with expected value."""
        error = ConfigurationError(
            "Invalid color format",
            field_name="graphs.colors.background",
            expected_value="#RRGGBB hex format",
        )
        assert str(error) == "Invalid color format"
        assert error.field_name == "graphs.colors.background"
        assert error.expected_value == "#RRGGBB hex format"

    def test_configuration_error_can_be_caught_as_base(self) -> None:
        """Test that ConfigurationError can be caught as TGraphBotError."""
        with pytest.raises(TGraphBotError):
            raise ConfigurationError("Test error")


class TestTautulliAPIError:
    """Tests for TautulliAPIError exception."""

    def test_tautulli_api_error_basic(self) -> None:
        """Test creating TautulliAPIError with just a message."""
        error = TautulliAPIError("API connection failed")
        assert str(error) == "API connection failed"
        assert error.status_code is None
        assert error.url is None

    def test_tautulli_api_error_with_status_code(self) -> None:
        """Test TautulliAPIError with HTTP status code."""
        error = TautulliAPIError("Authentication failed", status_code=401)
        assert str(error) == "Authentication failed"
        assert error.status_code == 401
        assert error.url is None

    def test_tautulli_api_error_with_url(self) -> None:
        """Test TautulliAPIError with URL."""
        error = TautulliAPIError(
            "Request failed", status_code=500, url="https://tautulli.example.com/api"
        )
        assert str(error) == "Request failed"
        assert error.status_code == 500
        assert error.url == "https://tautulli.example.com/api"

    def test_tautulli_api_error_can_be_caught_as_base(self) -> None:
        """Test that TautulliAPIError can be caught as TGraphBotError."""
        with pytest.raises(TGraphBotError):
            raise TautulliAPIError("Test error")


class TestGraphGenerationError:
    """Tests for GraphGenerationError exception."""

    def test_graph_generation_error_basic(self) -> None:
        """Test creating GraphGenerationError with just a message."""
        error = GraphGenerationError("Failed to generate graph")
        assert str(error) == "Failed to generate graph"
        assert error.graph_type is None
        assert error.data_range_days is None

    def test_graph_generation_error_with_graph_type(self) -> None:
        """Test GraphGenerationError with graph type."""
        error = GraphGenerationError(
            "Insufficient data", graph_type="daily_play_count"
        )
        assert str(error) == "Insufficient data"
        assert error.graph_type == "daily_play_count"
        assert error.data_range_days is None

    def test_graph_generation_error_with_all_details(self) -> None:
        """Test GraphGenerationError with all optional parameters."""
        error = GraphGenerationError(
            "Data aggregation failed",
            graph_type="top_platforms",
            data_range_days=30,
        )
        assert str(error) == "Data aggregation failed"
        assert error.graph_type == "top_platforms"
        assert error.data_range_days == 30

    def test_graph_generation_error_can_be_caught_as_base(self) -> None:
        """Test that GraphGenerationError can be caught as TGraphBotError."""
        with pytest.raises(TGraphBotError):
            raise GraphGenerationError("Test error")


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_rate_limit_error_basic(self) -> None:
        """Test creating RateLimitError with message and retry_after."""
        error = RateLimitError("Command on cooldown", retry_after=60.0)
        assert str(error) == "Command on cooldown"
        assert error.retry_after == 60.0
        assert error.is_user_cooldown is True

    def test_rate_limit_error_user_cooldown(self) -> None:
        """Test RateLimitError with user cooldown."""
        error = RateLimitError(
            "User cooldown active", retry_after=300.0, is_user_cooldown=True
        )
        assert str(error) == "User cooldown active"
        assert error.retry_after == 300.0
        assert error.is_user_cooldown is True

    def test_rate_limit_error_global_cooldown(self) -> None:
        """Test RateLimitError with global cooldown."""
        error = RateLimitError(
            "Global cooldown active", retry_after=30.0, is_user_cooldown=False
        )
        assert str(error) == "Global cooldown active"
        assert error.retry_after == 30.0
        assert error.is_user_cooldown is False

    def test_rate_limit_error_retry_after_type(self) -> None:
        """Test that retry_after accepts float values."""
        error = RateLimitError("Cooldown", retry_after=45.5)
        assert error.retry_after == 45.5
        assert isinstance(error.retry_after, float)

    def test_rate_limit_error_can_be_caught_as_base(self) -> None:
        """Test that RateLimitError can be caught as TGraphBotError."""
        with pytest.raises(TGraphBotError):
            raise RateLimitError("Test error", retry_after=10.0)


class TestExceptionGroupHandling:
    """Tests for exception group handling with custom exceptions."""

    def test_multiple_configuration_errors_in_group(self) -> None:
        """Test handling multiple ConfigurationError in ExceptionGroup."""
        errors = [
            ConfigurationError("Error 1", field_name="field1"),
            ConfigurationError("Error 2", field_name="field2"),
        ]
        group = ExceptionGroup("Configuration errors", errors)

        assert len(group.exceptions) == 2
        assert all(isinstance(e, ConfigurationError) for e in group.exceptions)

    def test_mixed_errors_in_group(self) -> None:
        """Test handling mixed TGraphBotError subclasses in ExceptionGroup."""
        errors: list[Exception] = [
            ConfigurationError("Config error"),
            TautulliAPIError("API error", status_code=500),
            GraphGenerationError("Graph error", graph_type="daily"),
        ]
        group = ExceptionGroup("Multiple errors", errors)

        assert len(group.exceptions) == 3
        assert all(isinstance(e, TGraphBotError) for e in group.exceptions)

    def test_catch_specific_error_from_group(self) -> None:
        """Test catching specific error type from ExceptionGroup."""
        errors: list[Exception] = [
            ConfigurationError("Config error"),
            TautulliAPIError("API error"),
        ]
        group = ExceptionGroup("Mixed errors", errors)

        config_errors_caught = False
        try:
            raise group
        except* ConfigurationError as eg:
            config_errors_caught = True
            assert len(eg.exceptions) == 1
            assert isinstance(eg.exceptions[0], ConfigurationError)
        except* TautulliAPIError:
            pass  # Other errors are expected

        assert config_errors_caught
