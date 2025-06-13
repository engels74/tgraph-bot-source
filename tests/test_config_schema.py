"""Tests for configuration schema validation."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from config.schema import TGraphBotConfig


class TestTGraphBotConfig:
    """Test cases for TGraphBotConfig Pydantic model."""

    def test_valid_minimal_config(self) -> None:
        """Test that minimal required configuration is valid."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
        }
        config = TGraphBotConfig(**config_data)
        
        assert config.TAUTULLI_API_KEY == "test_api_key"
        assert config.TAUTULLI_URL == "http://localhost:8181/api/v2"
        assert config.DISCORD_TOKEN == "test_discord_token"
        assert config.CHANNEL_ID == 123456789012345678

    def test_valid_full_config(self) -> None:
        """Test that full configuration with all options is valid."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "UPDATE_DAYS": 14,
            "FIXED_UPDATE_TIME": "12:30",
            "KEEP_DAYS": 14,
            "TIME_RANGE_DAYS": 60,
            "LANGUAGE": "en",
            "CENSOR_USERNAMES": False,
            "ENABLE_GRAPH_GRID": True,
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": True,
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ENABLE_TOP_10_PLATFORMS": True,
            "ENABLE_TOP_10_USERS": True,
            "ENABLE_PLAY_COUNT_BY_MONTH": True,
            "TV_COLOR": "#1f77b4",
            "MOVIE_COLOR": "#ff7f0e",
            "GRAPH_BACKGROUND_COLOR": "#ffffff",
            "ANNOTATION_COLOR": "#ff0000",
            "ANNOTATION_OUTLINE_COLOR": "#000000",
            "ENABLE_ANNOTATION_OUTLINE": True,
            "ANNOTATE_DAILY_PLAY_COUNT": True,
            "ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK": True,
            "ANNOTATE_PLAY_COUNT_BY_HOUROFDAY": True,
            "ANNOTATE_TOP_10_PLATFORMS": True,
            "ANNOTATE_TOP_10_USERS": True,
            "ANNOTATE_PLAY_COUNT_BY_MONTH": True,
            "CONFIG_COOLDOWN_MINUTES": 5,
            "CONFIG_GLOBAL_COOLDOWN_SECONDS": 30,
            "UPDATE_GRAPHS_COOLDOWN_MINUTES": 10,
            "UPDATE_GRAPHS_GLOBAL_COOLDOWN_SECONDS": 60,
            "MY_STATS_COOLDOWN_MINUTES": 5,
            "MY_STATS_GLOBAL_COOLDOWN_SECONDS": 60,
        }
        config = TGraphBotConfig(**config_data)
        
        assert config.UPDATE_DAYS == 14
        assert config.FIXED_UPDATE_TIME == "12:30"
        assert config.CENSOR_USERNAMES is False
        assert config.TV_COLOR == "#1f77b4"

    def test_default_values(self) -> None:
        """Test that default values are applied correctly."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
        }
        config = TGraphBotConfig(**config_data)
        
        # Test some default values from PRD
        assert config.UPDATE_DAYS == 7
        assert config.FIXED_UPDATE_TIME == "XX:XX"
        assert config.KEEP_DAYS == 7
        assert config.TIME_RANGE_DAYS == 30
        assert config.LANGUAGE == "en"
        assert config.CENSOR_USERNAMES is True
        assert config.ENABLE_GRAPH_GRID is False
        assert config.ENABLE_DAILY_PLAY_COUNT is True

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig()  # pyright: ignore[reportCallIssue]
        
        errors = exc_info.value.errors()
        required_fields = {"TAUTULLI_API_KEY", "TAUTULLI_URL", "DISCORD_TOKEN", "CHANNEL_ID"}
        error_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        
        assert required_fields.issubset(error_fields)

    def test_invalid_color_format(self) -> None:
        """Test that invalid color formats raise ValidationError."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "TV_COLOR": "invalid_color",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TGraphBotConfig(**config_data)
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("TV_COLOR",) for error in errors)

    def test_invalid_time_format(self) -> None:
        """Test that invalid time formats raise ValidationError."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "FIXED_UPDATE_TIME": "25:99",  # Invalid time
        }
        
        with pytest.raises(ValidationError):
            TGraphBotConfig(**config_data)

    def test_negative_values_validation(self) -> None:
        """Test that negative values for certain fields raise ValidationError."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "UPDATE_DAYS": -1,  # Should be positive
        }
        
        with pytest.raises(ValidationError):
            TGraphBotConfig(**config_data)

    def test_channel_id_validation(self) -> None:
        """Test that channel ID validation works correctly."""
        config_data: dict[str, Any] = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": "not_an_integer",
        }
        
        with pytest.raises(ValidationError):
            TGraphBotConfig(**config_data)
