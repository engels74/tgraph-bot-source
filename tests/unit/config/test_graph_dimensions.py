"""Tests for graph dimension configuration fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.tgraph_bot.config.schema import TGraphBotConfig


class TestGraphDimensionConfiguration:
    """Test cases for GRAPH_WIDTH, GRAPH_HEIGHT, and GRAPH_DPI configuration fields."""

    def test_graph_dimensions_default_values(self) -> None:
        """Test that graph dimension fields have correct default values."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        # Test default values match BaseGraph defaults
        assert config.GRAPH_WIDTH == 12
        assert config.GRAPH_HEIGHT == 8
        assert config.GRAPH_DPI == 100

    def test_graph_dimensions_custom_values(self) -> None:
        """Test that custom graph dimension values are accepted."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 16,
            "GRAPH_HEIGHT": 10,
            "GRAPH_DPI": 150,
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.GRAPH_WIDTH == 16
        assert config.GRAPH_HEIGHT == 10
        assert config.GRAPH_DPI == 150

    def test_graph_width_validation_minimum(self) -> None:
        """Test that GRAPH_WIDTH validates minimum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 5,  # Below minimum of 6
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_WIDTH",) for error in errors)

    def test_graph_width_validation_maximum(self) -> None:
        """Test that GRAPH_WIDTH validates maximum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 25,  # Above maximum of 20
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_WIDTH",) for error in errors)

    def test_graph_height_validation_minimum(self) -> None:
        """Test that GRAPH_HEIGHT validates minimum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_HEIGHT": 3,  # Below minimum of 4
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_HEIGHT",) for error in errors)

    def test_graph_height_validation_maximum(self) -> None:
        """Test that GRAPH_HEIGHT validates maximum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_HEIGHT": 18,  # Above maximum of 16
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_HEIGHT",) for error in errors)

    def test_graph_dpi_validation_minimum(self) -> None:
        """Test that GRAPH_DPI validates minimum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_DPI": 60,  # Below minimum of 72
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_DPI",) for error in errors)

    def test_graph_dpi_validation_maximum(self) -> None:
        """Test that GRAPH_DPI validates maximum value."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_DPI": 350,  # Above maximum of 300
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_DPI",) for error in errors)

    def test_graph_dimensions_boundary_values(self) -> None:
        """Test that boundary values are accepted for graph dimensions."""
        # Test minimum boundary values
        config_data_min = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 6,  # Minimum allowed
            "GRAPH_HEIGHT": 4,  # Minimum allowed
            "GRAPH_DPI": 72,  # Minimum allowed
        }
        config_min = TGraphBotConfig(**config_data_min)  # pyright: ignore[reportArgumentType]
        assert config_min.GRAPH_WIDTH == 6
        assert config_min.GRAPH_HEIGHT == 4
        assert config_min.GRAPH_DPI == 72

        # Test maximum boundary values
        config_data_max = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 20,  # Maximum allowed
            "GRAPH_HEIGHT": 16,  # Maximum allowed
            "GRAPH_DPI": 300,  # Maximum allowed
        }
        config_max = TGraphBotConfig(**config_data_max)  # pyright: ignore[reportArgumentType]
        assert config_max.GRAPH_WIDTH == 20
        assert config_max.GRAPH_HEIGHT == 16
        assert config_max.GRAPH_DPI == 300

    def test_graph_dimensions_integer_type_validation(self) -> None:
        """Test that graph dimensions only accept integer values."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": "12",  # String instead of int
        }

        # Pydantic should coerce string to int if possible
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.GRAPH_WIDTH == 12
        assert isinstance(config.GRAPH_WIDTH, int)

    def test_graph_dimensions_float_coercion(self) -> None:
        """Test that whole float values are coerced to integers."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 12.0,  # Whole float value
            "GRAPH_HEIGHT": 8.0,  # Whole float value
            "GRAPH_DPI": 100.0,  # Whole float value
        }

        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.GRAPH_WIDTH == 12
        assert config.GRAPH_HEIGHT == 8
        assert config.GRAPH_DPI == 100
        assert isinstance(config.GRAPH_WIDTH, int)
        assert isinstance(config.GRAPH_HEIGHT, int)
        assert isinstance(config.GRAPH_DPI, int)

    def test_graph_dimensions_fractional_float_rejected(self) -> None:
        """Test that fractional float values are rejected."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 12.7,  # Fractional float value
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("GRAPH_WIDTH",) for error in errors)

    def test_graph_dimensions_common_use_cases(self) -> None:
        """Test common use cases for graph dimensions."""
        # Test typical Discord-friendly dimensions
        config_data_discord = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 10,
            "GRAPH_HEIGHT": 6,
            "GRAPH_DPI": 120,
        }
        config_discord = TGraphBotConfig(**config_data_discord)  # pyright: ignore[reportArgumentType]
        assert config_discord.GRAPH_WIDTH == 10
        assert config_discord.GRAPH_HEIGHT == 6
        assert config_discord.GRAPH_DPI == 120

        # Test high-quality dimensions
        config_data_hq = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "GRAPH_WIDTH": 16,
            "GRAPH_HEIGHT": 12,
            "GRAPH_DPI": 200,
        }
        config_hq = TGraphBotConfig(**config_data_hq)  # pyright: ignore[reportArgumentType]
        assert config_hq.GRAPH_WIDTH == 16
        assert config_hq.GRAPH_HEIGHT == 12
        assert config_hq.GRAPH_DPI == 200

    def test_graph_dimensions_in_full_config(self) -> None:
        """Test that graph dimensions work properly in a full configuration."""
        config_data = {
            "TAUTULLI_API_KEY": "test_api_key",
            "TAUTULLI_URL": "http://localhost:8181/api/v2",
            "DISCORD_TOKEN": "test_discord_token",
            "CHANNEL_ID": 123456789012345678,
            "UPDATE_DAYS": 14,
            "FIXED_UPDATE_TIME": "12:30",
            "KEEP_DAYS": 14,
            "TIME_RANGE_DAYS": 60,
            "GRAPH_WIDTH": 14,
            "GRAPH_HEIGHT": 10,
            "GRAPH_DPI": 150,
            "LANGUAGE": "en",
            "CENSOR_USERNAMES": False,
            "ENABLE_GRAPH_GRID": True,
            "TV_COLOR": "#1f77b4",
            "MOVIE_COLOR": "#ff7f0e",
            "GRAPH_BACKGROUND_COLOR": "#ffffff",
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        # Verify all values are set correctly
        assert config.GRAPH_WIDTH == 14
        assert config.GRAPH_HEIGHT == 10
        assert config.GRAPH_DPI == 150
        assert config.UPDATE_DAYS == 14
        assert config.TV_COLOR == "#1f77b4"
