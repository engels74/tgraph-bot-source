"""Tests for Discord timestamp format configuration."""

import pytest

from src.tgraph_bot.config.schema import TGraphBotConfig


class TestTimestampFormatConfig:
    """Test cases for the Discord timestamp format configuration option."""

    def test_default_timestamp_format(self) -> None:
        """Test that the default timestamp format is 'F'."""
        config_data: dict[str, str | int] = {
            "TAUTULLI_API_KEY": "test_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_token_12345",
            "CHANNEL_ID": 123456789,
        }
        
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.DISCORD_TIMESTAMP_FORMAT == "F"

    def test_valid_timestamp_formats(self) -> None:
        """Test that all valid Discord timestamp formats are accepted."""
        valid_formats = ["t", "T", "d", "D", "f", "F", "R"]
        
        base_config = {
            "TAUTULLI_API_KEY": "test_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_token_12345",
            "CHANNEL_ID": 123456789,
        }
        
        for format_option in valid_formats:
            config_data = {**base_config, "DISCORD_TIMESTAMP_FORMAT": format_option}
            config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
            assert config.DISCORD_TIMESTAMP_FORMAT == format_option

    def test_invalid_timestamp_format_raises_error(self) -> None:
        """Test that invalid timestamp formats raise validation errors."""
        invalid_formats = ["X", "FF", "123", "", "G", "timestamp"]
        
        base_config = {
            "TAUTULLI_API_KEY": "test_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_token_12345",
            "CHANNEL_ID": 123456789,
        }
        
        for invalid_format in invalid_formats:
            config_data = {**base_config, "DISCORD_TIMESTAMP_FORMAT": invalid_format}
            with pytest.raises(ValueError, match="Input should be"):
                _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

    def test_timestamp_format_case_sensitivity(self) -> None:
        """Test that timestamp format validation is case-sensitive."""
        base_config = {
            "TAUTULLI_API_KEY": "test_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_token_12345",
            "CHANNEL_ID": 123456789,
        }
        
        # Lowercase should work
        config_data = {**base_config, "DISCORD_TIMESTAMP_FORMAT": "f"}
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.DISCORD_TIMESTAMP_FORMAT == "f"
        
        # Uppercase should work
        config_data = {**base_config, "DISCORD_TIMESTAMP_FORMAT": "F"}
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.DISCORD_TIMESTAMP_FORMAT == "F"

    def test_timestamp_format_description(self) -> None:
        """Test that the field has an appropriate description."""
        # Access field info through Pydantic's model fields
        field_info = TGraphBotConfig.model_fields["DISCORD_TIMESTAMP_FORMAT"]
        assert field_info.description is not None
        assert "Discord timestamp format" in field_info.description
        assert "F" in field_info.description  # Should mention default