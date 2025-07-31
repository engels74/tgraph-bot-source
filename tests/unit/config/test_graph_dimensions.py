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

        # Test default values match BaseGraph defaults
        assert config.graphs.appearance.dimensions.width == 14
        assert config.graphs.appearance.dimensions.height == 8
        assert config.graphs.appearance.dimensions.dpi == 100

    def test_graph_dimensions_custom_values(self) -> None:
        """Test that custom graph dimension values are accepted."""
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
                    "dimensions": {
                        "width": 16,
                        "height": 10,
                        "dpi": 150,
                    },
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        assert config.graphs.appearance.dimensions.width == 16
        assert config.graphs.appearance.dimensions.height == 10
        assert config.graphs.appearance.dimensions.dpi == 150

    def test_graph_width_validation_minimum(self) -> None:
        """Test that GRAPH_WIDTH validates minimum value."""
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
                    "dimensions": {
                        "width": 5,  # Below minimum of 6
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "width") for error in errors)

    def test_graph_width_validation_maximum(self) -> None:
        """Test that GRAPH_WIDTH validates maximum value."""
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
                    "dimensions": {
                        "width": 25,  # Above maximum of 20
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "width") for error in errors)

    def test_graph_height_validation_minimum(self) -> None:
        """Test that GRAPH_HEIGHT validates minimum value."""
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
                    "dimensions": {
                        "height": 3,  # Below minimum of 4
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "height") for error in errors)

    def test_graph_height_validation_maximum(self) -> None:
        """Test that GRAPH_HEIGHT validates maximum value."""
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
                    "dimensions": {
                        "height": 18,  # Above maximum of 16
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "height") for error in errors)

    def test_graph_dpi_validation_minimum(self) -> None:
        """Test that GRAPH_DPI validates minimum value."""
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
                    "dimensions": {
                        "dpi": 60,  # Below minimum of 72
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "dpi") for error in errors)

    def test_graph_dpi_validation_maximum(self) -> None:
        """Test that GRAPH_DPI validates maximum value."""
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
                    "dimensions": {
                        "dpi": 350,  # Above maximum of 300
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "dpi") for error in errors)

    def test_graph_dimensions_boundary_values(self) -> None:
        """Test that boundary values are accepted for graph dimensions."""
        # Test minimum boundary values
        config_data_min = {
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
                    "dimensions": {
                        "width": 6,  # Minimum allowed
                        "height": 4,  # Minimum allowed
                        "dpi": 72,  # Minimum allowed
                    },
                },
            },
        }
        config_min = TGraphBotConfig(**config_data_min)  # pyright: ignore[reportArgumentType]
        assert config_min.graphs.appearance.dimensions.width == 6
        assert config_min.graphs.appearance.dimensions.height == 4
        assert config_min.graphs.appearance.dimensions.dpi == 72

        # Test maximum boundary values
        config_data_max = {
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
                    "dimensions": {
                        "width": 20,  # Maximum allowed
                        "height": 16,  # Maximum allowed
                        "dpi": 300,  # Maximum allowed
                    },
                },
            },
        }
        config_max = TGraphBotConfig(**config_data_max)  # pyright: ignore[reportArgumentType]
        assert config_max.graphs.appearance.dimensions.width == 20
        assert config_max.graphs.appearance.dimensions.height == 16
        assert config_max.graphs.appearance.dimensions.dpi == 300

    def test_graph_dimensions_integer_type_validation(self) -> None:
        """Test that graph dimensions only accept integer values."""
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
                    "dimensions": {
                        "width": "12",  # String instead of int
                    },
                },
            },
        }

        # Pydantic should coerce string to int if possible
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.graphs.appearance.dimensions.width == 12
        assert isinstance(config.graphs.appearance.dimensions.width, int)

    def test_graph_dimensions_float_coercion(self) -> None:
        """Test that whole float values are coerced to integers."""
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
                    "dimensions": {
                        "width": 12.0,  # Whole float value
                        "height": 8.0,  # Whole float value
                        "dpi": 100.0,  # Whole float value
                    },
                },
            },
        }

        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
        assert config.graphs.appearance.dimensions.width == 12
        assert config.graphs.appearance.dimensions.height == 8
        assert config.graphs.appearance.dimensions.dpi == 100
        assert isinstance(config.graphs.appearance.dimensions.width, int)
        assert isinstance(config.graphs.appearance.dimensions.height, int)
        assert isinstance(config.graphs.appearance.dimensions.dpi, int)

    def test_graph_dimensions_fractional_float_rejected(self) -> None:
        """Test that fractional float values are rejected."""
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
                    "dimensions": {
                        "width": 12.7,  # Fractional float value
                    },
                },
            },
        }

        with pytest.raises(ValidationError) as exc_info:
            _ = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("graphs", "appearance", "dimensions", "width") for error in errors)

    def test_graph_dimensions_common_use_cases(self) -> None:
        """Test common use cases for graph dimensions."""
        # Test typical Discord-friendly dimensions
        config_data_discord = {
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
                    "dimensions": {
                        "width": 10,
                        "height": 6,
                        "dpi": 120,
                    },
                },
            },
        }
        config_discord = TGraphBotConfig(**config_data_discord)  # pyright: ignore[reportArgumentType]
        assert config_discord.graphs.appearance.dimensions.width == 10
        assert config_discord.graphs.appearance.dimensions.height == 6
        assert config_discord.graphs.appearance.dimensions.dpi == 120

        # Test high-quality dimensions
        config_data_hq = {
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
                    "dimensions": {
                        "width": 16,
                        "height": 12,
                        "dpi": 200,
                    },
                },
            },
        }
        config_hq = TGraphBotConfig(**config_data_hq)  # pyright: ignore[reportArgumentType]
        assert config_hq.graphs.appearance.dimensions.width == 16
        assert config_hq.graphs.appearance.dimensions.height == 12
        assert config_hq.graphs.appearance.dimensions.dpi == 200

    def test_graph_dimensions_in_full_config(self) -> None:
        """Test that graph dimensions work properly in a full configuration."""
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
                "appearance": {
                    "dimensions": {
                        "width": 14,
                        "height": 10,
                        "dpi": 150,
                    },
                    "colors": {
                        "tv": "#1f77b4",
                        "movie": "#ff7f0e",
                        "background": "#ffffff",
                    },
                    "grid": {
                        "enabled": True,
                    },
                },
            },
        }
        config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]

        # Verify all values are set correctly
        assert config.graphs.appearance.dimensions.width == 14
        assert config.graphs.appearance.dimensions.height == 10
        assert config.graphs.appearance.dimensions.dpi == 150
        assert config.automation.scheduling.update_days == 14
        assert config.graphs.appearance.colors.tv == "#1f77b4"
