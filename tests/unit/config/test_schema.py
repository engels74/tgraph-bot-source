"""Tests for configuration schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.tgraph_bot.config.schema import TGraphBotConfig


class TestTGraphBotConfig:
    """Test cases for TGraphBotConfig Pydantic model."""

    def test_valid_minimal_config(self) -> None:
        """Test that minimal required configuration is valid."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.services.tautulli.api_key == "test_api_key"
        assert config.services.tautulli.url == "http://localhost:8181/api/v2"
        assert config.services.discord.token == "test_discord_token"
        assert config.services.discord.channel_id == 123456789012345678

    def test_valid_full_config(self) -> None:
        """Test that full configuration with all options is valid."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "timestamp_format": "f",
                    "ephemeral_message_delete_after": 45.0,
                },
            },
            "automation": {
                "scheduling": {
                    "update_days": 14,
                    "fixed_update_time": "12:30",
                },
                "data_retention": {
                    "keep_days": 14,
                },
            },
            "data_collection": {
                "time_ranges": {
                    "days": 60,
                    "months": 12,
                },
                "privacy": {
                    "censor_usernames": False,
                },
            },
            "system": {
                "localization": {
                    "language": "en",
                },
            },
            "graphs": {
                "features": {
                    "enabled_types": {
                        "daily_play_count": True,
                        "play_count_by_dayofweek": True,
                        "play_count_by_hourofday": True,
                        "top_10_platforms": True,
                        "top_10_users": True,
                        "play_count_by_month": True,
                    },
                    "media_type_separation": True,
                    "stacked_bar_charts": True,
                },
                "appearance": {
                    "colors": {
                        "tv": "#1f77b4",
                        "movie": "#ff7f0e",
                        "background": "#ffffff",
                    },
                    "grid": {
                        "enabled": True,
                    },
                    "annotations": {
                        "basic": {
                            "color": "#ff0000",
                            "outline_color": "#000000",
                            "enable_outline": True,
                        },
                        "enabled_on": {
                            "daily_play_count": True,
                            "play_count_by_dayofweek": True,
                            "play_count_by_hourofday": True,
                            "top_10_platforms": True,
                            "top_10_users": True,
                            "play_count_by_month": True,
                        },
                    },
                },
            },
            "rate_limiting": {
                "commands": {
                    "config": {
                        "user_cooldown_minutes": 5,
                        "global_cooldown_seconds": 30,
                    },
                    "update_graphs": {
                        "user_cooldown_minutes": 10,
                        "global_cooldown_seconds": 60,
                    },
                    "my_stats": {
                        "user_cooldown_minutes": 5,
                        "global_cooldown_seconds": 60,
                    },
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.automation.scheduling.update_days == 14
        assert config.automation.scheduling.fixed_update_time == "12:30"
        assert config.data_collection.privacy.censor_usernames is False
        assert config.graphs.appearance.colors.tv == "#1f77b4"
        assert config.graphs.features.stacked_bar_charts is True

    def test_default_values(self) -> None:
        """Test that default values are applied correctly."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        # Test some default values from PRD
        assert config.automation.scheduling.update_days == 7
        assert config.automation.scheduling.fixed_update_time == "XX:XX"
        assert config.automation.data_retention.keep_days == 7
        assert config.data_collection.time_ranges.days == 30
        assert config.system.localization.language == "en"
        assert config.data_collection.privacy.censor_usernames is True
        assert config.graphs.appearance.grid.enabled is False
        assert config.graphs.features.media_type_separation is True
        assert config.graphs.features.stacked_bar_charts is True
        assert config.graphs.features.enabled_types.daily_play_count is True

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig()  # pyright: ignore[reportCallIssue]

        errors = exc_info.value.errors()
        # Check that the services section is missing
        assert any(
            error["loc"] == ("services",) and error["type"] == "missing"
            for error in errors
        )

    def test_invalid_color_format(self) -> None:
        """Test that invalid color formats raise ValidationError."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
            "graphs": {
                "appearance": {
                    "colors": {
                        "tv": "invalid_color",
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("graphs", "appearance", "colors", "tv")
            for error in errors
        )

    def test_invalid_time_format(self) -> None:
        """Test that invalid time formats raise ValidationError."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
            "automation": {
                "scheduling": {
                    "fixed_update_time": "25:99",  # Invalid time
                },
            },
        }

        with pytest.raises(ValidationError):
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

    def test_negative_values_validation(self) -> None:
        """Test that negative values for certain fields raise ValidationError."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
            "automation": {
                "scheduling": {
                    "update_days": -1,  # Should be positive
                },
            },
        }

        with pytest.raises(ValidationError):
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

    def test_channel_id_validation(self) -> None:
        """Test that channel ID validation works correctly."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": "not_an_integer",
                },
            },
        }

        with pytest.raises(ValidationError):
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

    def test_stacked_bar_charts_configuration(self) -> None:
        """Test stacked_bar_charts boolean configuration field."""
        # Test with stacked bar charts enabled
        config_data_enabled = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
            "graphs": {
                "features": {
                    "stacked_bar_charts": True,
                },
            },
        }
        config_enabled = TGraphBotConfig(**config_data_enabled)  # pyright: ignore[reportArgumentType]
        assert config_enabled.graphs.features.stacked_bar_charts is True

        # Test with stacked bar charts disabled
        config_data_disabled = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
            "graphs": {
                "features": {
                    "stacked_bar_charts": False,
                },
            },
        }
        config_disabled = TGraphBotConfig(**config_data_disabled)  # pyright: ignore[reportArgumentType]
        assert config_disabled.graphs.features.stacked_bar_charts is False

        # Test default value (should be True)
        config_data_default = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
        }
        config_default = TGraphBotConfig(**config_data_default)  # pyright: ignore[reportArgumentType]
        assert config_default.graphs.features.stacked_bar_charts is True

    def test_ephemeral_message_delete_after_default_value(self) -> None:
        """Test that ephemeral_message_delete_after has correct default value."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.services.discord.ephemeral_message_delete_after == 30.0
        assert isinstance(config.services.discord.ephemeral_message_delete_after, float)

    def test_ephemeral_message_delete_after_custom_value(self) -> None:
        """Test that ephemeral_message_delete_after accepts custom values."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": 120.5,
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.services.discord.ephemeral_message_delete_after == 120.5

    def test_ephemeral_message_delete_after_validation_positive(self) -> None:
        """Test that ephemeral_message_delete_after must be positive."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": -1.0,
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("services", "discord", "ephemeral_message_delete_after")
            for error in errors
        )

    def test_ephemeral_message_delete_after_validation_zero(self) -> None:
        """Test that ephemeral_message_delete_after cannot be zero."""
        config_data = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": 0.0,
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("services", "discord", "ephemeral_message_delete_after")
            for error in errors
        )

    def test_ephemeral_message_delete_after_validation_range(self) -> None:
        """Test that ephemeral_message_delete_after has reasonable range limits."""
        # Test minimum valid value
        config_data_min = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": 1.0,
                },
            },
        }
        config_min = TGraphBotConfig(**config_data_min)  # pyright: ignore[reportArgumentType]
        assert config_min.services.discord.ephemeral_message_delete_after == 1.0

        # Test maximum valid value
        config_data_max = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": 3600.0,
                },
            },
        }
        config_max = TGraphBotConfig(**config_data_max)  # pyright: ignore[reportArgumentType]
        assert config_max.services.discord.ephemeral_message_delete_after == 3600.0

        # Test value above maximum
        config_data_too_large = {
            "services": {
                "tautulli": {
                    "api_key": "test_api_key",
                    "url": "http://localhost:8181/api/v2",
                },
                "discord": {
                    "token": "test_discord_token",
                    "channel_id": 123456789012345678,
                    "ephemeral_message_delete_after": 3601.0,
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data_too_large)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("services", "discord", "ephemeral_message_delete_after")
            for error in errors
        )
