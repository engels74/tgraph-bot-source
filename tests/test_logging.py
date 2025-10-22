"""Tests for structured logging and sensitive value masking."""

import logging

import pytest

from tgraph_bot.utils.logging import (
    ContextFilter,
    command_name,
    get_logger,
    is_sensitive_field,
    log_api_request,
    log_operation_complete,
    log_operation_start,
    mask_sensitive_dict,
    mask_sensitive_value,
    operation_id,
    setup_logging,
    user_id,
)


class TestMaskSensitiveValue:
    """Tests for mask_sensitive_value function."""

    def test_mask_with_default_show_last(self) -> None:
        """Test masking with default show_last=4."""
        input_value = "my_secret_api_key_12345"
        result = mask_sensitive_value(input_value)
        # Should be (len - 4) asterisks + last 4 chars
        assert result == "*" * (len(input_value) - 4) + "2345"
        assert len(result) == len(input_value)

    def test_mask_with_custom_show_last(self) -> None:
        """Test masking with custom show_last parameter."""
        result = mask_sensitive_value("secret123456", show_last=6)
        assert result == "******123456"

    def test_mask_short_value(self) -> None:
        """Test masking value shorter than show_last."""
        result = mask_sensitive_value("abc", show_last=4)
        assert result == "***"

    def test_mask_empty_string(self) -> None:
        """Test masking empty string."""
        result = mask_sensitive_value("")
        assert result == "****"

    def test_mask_exact_length(self) -> None:
        """Test masking value with length equal to show_last."""
        result = mask_sensitive_value("test", show_last=4)
        assert result == "****"


class TestIsSensitiveField:
    """Tests for is_sensitive_field function."""

    def test_sensitive_field_token(self) -> None:
        """Test that 'token' is identified as sensitive."""
        assert is_sensitive_field("token") is True
        assert is_sensitive_field("discord_token") is True
        assert is_sensitive_field("access_token") is True

    def test_sensitive_field_key(self) -> None:
        """Test that 'key' fields are identified as sensitive."""
        assert is_sensitive_field("api_key") is True
        assert is_sensitive_field("secret_key") is True
        assert is_sensitive_field("tautulli_key") is True

    def test_sensitive_field_password(self) -> None:
        """Test that 'password' is identified as sensitive."""
        assert is_sensitive_field("password") is True
        assert is_sensitive_field("db_password") is True
        assert is_sensitive_field("user_password") is True

    def test_sensitive_field_secret(self) -> None:
        """Test that 'secret' is identified as sensitive."""
        assert is_sensitive_field("secret") is True
        assert is_sensitive_field("client_secret") is True

    def test_sensitive_field_auth(self) -> None:
        """Test that 'auth' fields are identified as sensitive."""
        assert is_sensitive_field("authorization") is True
        assert is_sensitive_field("auth_header") is True

    def test_sensitive_field_case_insensitive(self) -> None:
        """Test that field detection is case-insensitive."""
        assert is_sensitive_field("API_KEY") is True
        assert is_sensitive_field("Token") is True
        assert is_sensitive_field("PASSWORD") is True

    def test_non_sensitive_field(self) -> None:
        """Test that non-sensitive fields are not flagged."""
        assert is_sensitive_field("username") is False
        assert is_sensitive_field("email") is False
        assert is_sensitive_field("port") is False
        assert is_sensitive_field("host") is False


class TestMaskSensitiveDict:
    """Tests for mask_sensitive_dict function."""

    def test_mask_simple_dict(self) -> None:
        """Test masking sensitive values in simple dictionary."""
        data = {"api_key": "secret123", "username": "john"}
        result = mask_sensitive_dict(data)

        assert result["api_key"] == "*****t123"  # 9 chars, last 4: "t123"
        assert result["username"] == "john"

    def test_mask_nested_dict(self) -> None:
        """Test masking sensitive values in nested dictionary."""
        data = {
            "services": {
                "discord": {"token": "discord_token_12345", "channel_id": 123},
                "tautulli": {"api_key": "tautulli_key_67890", "url": "http://example.com"},
            }
        }
        result = mask_sensitive_dict(data)

        services = result["services"]
        assert isinstance(services, dict)
        discord = services["discord"]
        assert isinstance(discord, dict)
        # "discord_token_12345" is 19 chars, last 4: "2345"
        assert discord["token"] == "*" * 15 + "2345"
        assert discord["channel_id"] == 123
        tautulli = services["tautulli"]
        assert isinstance(tautulli, dict)
        # "tautulli_key_67890" is 18 chars, last 4: "7890"
        assert tautulli["api_key"] == "*" * 14 + "7890"
        assert tautulli["url"] == "http://example.com"

    def test_mask_dict_with_list(self) -> None:
        """Test masking sensitive values in dict containing lists."""
        data = {
            "credentials": [
                {"api_key": "key1", "name": "service1"},
                {"api_key": "key2", "name": "service2"},
            ]
        }
        result = mask_sensitive_dict(data)

        credentials_list = result["credentials"]
        assert isinstance(credentials_list, list)
        cred0 = credentials_list[0]
        assert isinstance(cred0, dict)
        assert cred0["api_key"] == "****"
        assert cred0["name"] == "service1"
        cred1 = credentials_list[1]
        assert isinstance(cred1, dict)
        assert cred1["api_key"] == "****"

    def test_mask_dict_non_recursive(self) -> None:
        """Test masking with recursive=False."""
        data = {"api_key": "secret123", "nested": {"token": "token456"}}
        result = mask_sensitive_dict(data, recursive=False)

        assert result["api_key"] == "*****t123"
        assert result["nested"] == {"token": "token456"}

    def test_mask_dict_custom_show_last(self) -> None:
        """Test masking with custom show_last parameter."""
        data = {"api_key": "secret123456"}
        result = mask_sensitive_dict(data, show_last=6)

        # "secret123456" is 12 chars, last 6: "123456"
        assert result["api_key"] == "******123456"

    def test_mask_dict_preserves_non_string_values(self) -> None:
        """Test that non-string values are preserved."""
        data = {
            "api_key": "secret123",
            "port": 8080,
            "enabled": True,
            "ratio": 1.5,
        }
        result = mask_sensitive_dict(data)

        assert result["api_key"] == "*****t123"
        assert result["port"] == 8080
        assert result["enabled"] is True
        assert result["ratio"] == 1.5


class TestContextVariables:
    """Tests for context variables."""

    def test_operation_id_default(self) -> None:
        """Test that operation_id has default None value."""
        assert operation_id.get() is None

    def test_operation_id_set_and_get(self) -> None:
        """Test setting and getting operation_id."""
        token = operation_id.set("test_operation_123")
        try:
            assert operation_id.get() == "test_operation_123"
        finally:
            operation_id.reset(token)

    def test_user_id_default(self) -> None:
        """Test that user_id has default None value."""
        assert user_id.get() is None

    def test_user_id_set_and_get(self) -> None:
        """Test setting and getting user_id."""
        token = user_id.set(12345)
        try:
            assert user_id.get() == 12345
        finally:
            user_id.reset(token)

    def test_command_name_default(self) -> None:
        """Test that command_name has default None value."""
        assert command_name.get() is None

    def test_command_name_set_and_get(self) -> None:
        """Test setting and getting command_name."""
        token = command_name.set("update_graphs")
        try:
            assert command_name.get() == "update_graphs"
        finally:
            command_name.reset(token)


class TestContextFilter:
    """Tests for ContextFilter logging filter."""

    def test_context_filter_adds_attributes(self) -> None:
        """Test that ContextFilter adds context variables to log records."""
        context_filter = ContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Set context variables
        op_token = operation_id.set("op_123")
        user_token = user_id.set(456)
        cmd_token = command_name.set("test_command")

        try:
            result = context_filter.filter(record)
            assert result is True

            assert hasattr(record, "operation_id")
            assert hasattr(record, "user_id")
            assert hasattr(record, "command_name")

            assert getattr(record, "operation_id") == "op_123"
            assert getattr(record, "user_id") == 456
            assert getattr(record, "command_name") == "test_command"
        finally:
            operation_id.reset(op_token)
            user_id.reset(user_token)
            command_name.reset(cmd_token)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default parameters."""
        # Note: setup_logging affects the root logger, which may already be configured
        # Just verify it doesn't raise an exception
        setup_logging()
        # Verify setup_logging executed without error

    def test_setup_logging_debug_level(self) -> None:
        """Test setup_logging with DEBUG level."""
        # Note: setup_logging affects the root logger, which may already be configured
        # Just verify it doesn't raise an exception
        setup_logging(level="DEBUG")
        # Verify setup_logging executed without error

    def test_setup_logging_simple_format(self) -> None:
        """Test setup_logging with simple format style."""
        setup_logging(format_style="simple")
        # Just verify it doesn't raise an exception

    def test_setup_logging_detailed_format(self) -> None:
        """Test setup_logging with detailed format style."""
        setup_logging(format_style="detailed")
        # Just verify it doesn't raise an exception


class TestLogApiRequest:
    """Tests for log_api_request function."""

    def test_log_api_request_success(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging successful API request."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            log_api_request(
                logger, "GET", "https://api.example.com/data", status_code=200
            )

        assert "API request: GET https://api.example.com/data" in caplog.text

    def test_log_api_request_with_duration(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging API request with duration."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            log_api_request(
                logger,
                "POST",
                "https://api.example.com/create",
                status_code=201,
                duration_ms=123.45,
            )

        assert "API request: POST https://api.example.com/create" in caplog.text

    def test_log_api_request_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging failed API request."""
        logger = get_logger("test")

        with caplog.at_level(logging.ERROR):
            log_api_request(
                logger,
                "GET",
                "https://api.example.com/data",
                status_code=500,
                error="Internal server error",
            )

        assert "API request failed: GET https://api.example.com/data" in caplog.text


class TestLogOperationStartComplete:
    """Tests for log_operation_start and log_operation_complete functions."""

    def test_log_operation_start(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging operation start."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            op_id = log_operation_start(logger, "generate_graphs")

        assert op_id.startswith("generate_graphs_")
        assert operation_id.get() == op_id
        assert "Starting operation: generate_graphs" in caplog.text

    def test_log_operation_start_with_details(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging operation start with details."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            op_id = log_operation_start(
                logger, "fetch_data", details={"days": 30, "user": "john"}
            )

        assert op_id.startswith("fetch_data_")
        assert "Starting operation: fetch_data" in caplog.text

    def test_log_operation_start_masks_sensitive_details(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that sensitive details are masked in operation start."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            _ = log_operation_start(
                logger, "api_call", details={"api_key": "secret123", "endpoint": "/data"}
            )

        # Verify the secret is not in the log
        assert "secret123" not in caplog.text
        # Verify the operation was logged
        assert "Starting operation: api_call" in caplog.text

    def test_log_operation_complete_success(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging successful operation completion."""
        logger = get_logger("test")

        with caplog.at_level(logging.INFO):
            log_operation_complete(logger, "generate_graphs", duration_ms=1234.56)

        assert "Completed operation: generate_graphs" in caplog.text
        assert operation_id.get() is None

    def test_log_operation_complete_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging failed operation completion."""
        logger = get_logger("test")

        with caplog.at_level(logging.ERROR):
            log_operation_complete(
                logger,
                "generate_graphs",
                success=False,
                error="Graph generation failed",
            )

        assert "Failed operation: generate_graphs" in caplog.text
        assert operation_id.get() is None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_module_name(self) -> None:
        """Test get_logger with module name."""
        logger = get_logger("tgraph_bot.test")
        assert logger.name == "tgraph_bot.test"
