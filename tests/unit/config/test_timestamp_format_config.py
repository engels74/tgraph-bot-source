"""Tests for Discord timestamp format configuration."""

import pytest

from src.tgraph_bot.config.schema import (
    TGraphBotConfig,
    ServicesConfig,
    TautulliConfig,
    DiscordConfig,
)


class TestTimestampFormatConfig:
    """Test cases for the Discord timestamp format configuration option."""

    def test_default_timestamp_format(self) -> None:
        """Test that the default timestamp format is 'R'."""
        config = TGraphBotConfig(
            services=ServicesConfig(
                tautulli=TautulliConfig(
                    api_key="test_key", url="http://localhost:8181/api/v2"
                ),
                discord=DiscordConfig(token="test_token_12345", channel_id=123456789),
            )
        )
        assert config.services.discord.timestamp_format == "R"

    def test_valid_timestamp_formats(self) -> None:
        """Test that all valid Discord timestamp formats are accepted."""
        valid_formats = ["t", "T", "d", "D", "f", "F", "R"]

        for format_option in valid_formats:
            config = TGraphBotConfig(
                services=ServicesConfig(
                    tautulli=TautulliConfig(
                        api_key="test_key", url="http://localhost:8181/api/v2"
                    ),
                    discord=DiscordConfig(
                        token="test_token_12345",
                        channel_id=123456789,
                        timestamp_format=format_option,  # pyright: ignore[reportArgumentType]
                    ),
                )
            )
            assert config.services.discord.timestamp_format == format_option

    def test_invalid_timestamp_format_raises_error(self) -> None:
        """Test that invalid timestamp formats raise validation errors."""
        invalid_formats = ["X", "FF", "123", "", "G", "timestamp"]

        for invalid_format in invalid_formats:
            with pytest.raises(ValueError, match="Input should be"):
                _ = TGraphBotConfig(
                    services=ServicesConfig(
                        tautulli=TautulliConfig(
                            api_key="test_key", url="http://localhost:8181/api/v2"
                        ),
                        discord=DiscordConfig(
                            token="test_token_12345",
                            channel_id=123456789,
                            timestamp_format=invalid_format,  # pyright: ignore[reportArgumentType]
                        ),
                    )
                )

    def test_timestamp_format_case_sensitivity(self) -> None:
        """Test that timestamp format validation is case-sensitive."""
        # Lowercase should work
        config = TGraphBotConfig(
            services=ServicesConfig(
                tautulli=TautulliConfig(
                    api_key="test_key", url="http://localhost:8181/api/v2"
                ),
                discord=DiscordConfig(
                    token="test_token_12345", channel_id=123456789, timestamp_format="f"
                ),
            )
        )
        assert config.services.discord.timestamp_format == "f"

        # Uppercase should work
        config = TGraphBotConfig(
            services=ServicesConfig(
                tautulli=TautulliConfig(
                    api_key="test_key", url="http://localhost:8181/api/v2"
                ),
                discord=DiscordConfig(
                    token="test_token_12345", channel_id=123456789, timestamp_format="F"
                ),
            )
        )
        assert config.services.discord.timestamp_format == "F"

    def test_timestamp_format_description(self) -> None:
        """Test that the field has an appropriate description."""
        # Access field info through Pydantic's model fields for the nested structure
        from src.tgraph_bot.config.schema import DiscordConfig

        field_info = DiscordConfig.model_fields["timestamp_format"]
        assert field_info.description is not None
        assert "Discord timestamp format" in field_info.description
        assert "R" in field_info.description  # Should mention default
