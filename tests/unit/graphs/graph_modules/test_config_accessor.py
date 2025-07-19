"""
Tests for the ConfigAccessor utility in TGraph Bot.

This module tests the centralized configuration access utility that handles
both dict and TGraphBotConfig objects for graph modules.
"""

import pytest

from src.tgraph_bot.graphs.graph_modules import ConfigAccessor
from src.tgraph_bot.utils.core.error_handler import ConfigurationError
from tests.utils.graph_helpers import create_test_config_minimal, create_test_config_comprehensive


class TestConfigAccessor:
    """Test cases for the ConfigAccessor class."""

    def test_initialization_with_dict_config(self) -> None:
        """Test ConfigAccessor initialization with dictionary configuration."""
        config_dict: dict[str, object] = {"ENABLE_DAILY_PLAY_COUNT": True}
        accessor = ConfigAccessor(config_dict)
        assert accessor.config == config_dict
        assert accessor.is_dict_config()
        assert not accessor.is_tgraph_config()

    def test_initialization_with_tgraph_config(self) -> None:
        """Test ConfigAccessor initialization with TGraphBotConfig."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)
        assert accessor.config == config
        assert not accessor.is_dict_config()
        assert accessor.is_tgraph_config()

    def test_get_value_from_dict_config(self) -> None:
        """Test getting values from dictionary configuration."""
        config_dict: dict[str, object] = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "GRAPH_WIDTH": 15,
            "TEST_STRING": "hello",
        }
        accessor = ConfigAccessor(config_dict)

        assert accessor.get_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert accessor.get_value("GRAPH_WIDTH") == 15
        assert accessor.get_value("TEST_STRING") == "hello"

    def test_get_value_from_tgraph_config(self) -> None:
        """Test getting values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        assert accessor.get_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert accessor.get_value("GRAPH_WIDTH") == 12  # Default value from schema
        assert accessor.get_value("TAUTULLI_API_KEY") == "test_api_key_comprehensive"

    def test_get_value_with_default_dict(self) -> None:
        """Test getting values with defaults from dictionary configuration."""
        config_dict: dict[str, object] = {"EXISTING_KEY": "value"}
        accessor = ConfigAccessor(config_dict)

        assert accessor.get_value("EXISTING_KEY", "default") == "value"
        assert accessor.get_value("MISSING_KEY", "default") == "default"
        assert accessor.get_value("MISSING_KEY", 42) == 42

    def test_get_value_with_default_tgraph(self) -> None:
        """Test getting values with defaults from TGraphBotConfig."""
        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        assert accessor.get_value("TAUTULLI_API_KEY", "default") == "test_api_key_minimal"
        assert accessor.get_value("NONEXISTENT_KEY", "default") == "default"
        assert accessor.get_value("NONEXISTENT_KEY", 123) == 123

    def test_get_value_missing_key_raises_error(self) -> None:
        """Test that missing keys without defaults raise ConfigurationError."""
        config_dict: dict[str, object] = {}
        accessor = ConfigAccessor(config_dict)

        with pytest.raises(ConfigurationError, match="Configuration key 'MISSING_KEY' not found"):
            accessor.get_value("MISSING_KEY")

        config = create_test_config_minimal()
        accessor = ConfigAccessor(config)

        with pytest.raises(ConfigurationError, match="Configuration key 'MISSING_KEY' not found"):
            accessor.get_value("MISSING_KEY")

    def test_get_bool_value_dict(self) -> None:
        """Test getting boolean values from dictionary configuration."""
        config_dict: dict[str, object] = {
            "TRUE_BOOL": True,
            "FALSE_BOOL": False,
            "TRUTHY_INT": 1,
            "FALSY_INT": 0,
            "TRUTHY_STRING": "yes",
            "FALSY_STRING": "",
            "NONE_VALUE": None,
        }
        accessor = ConfigAccessor(config_dict)

        assert accessor.get_bool_value("TRUE_BOOL") is True
        assert accessor.get_bool_value("FALSE_BOOL") is False
        assert accessor.get_bool_value("TRUTHY_INT") is True
        assert accessor.get_bool_value("FALSY_INT") is False
        assert accessor.get_bool_value("TRUTHY_STRING") is True
        assert accessor.get_bool_value("FALSY_STRING") is False
        assert accessor.get_bool_value("NONE_VALUE") is False
        assert accessor.get_bool_value("MISSING_KEY", False) is False
        assert accessor.get_bool_value("MISSING_KEY", True) is True

    def test_get_bool_value_tgraph(self) -> None:
        """Test getting boolean values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        assert accessor.get_bool_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert accessor.get_bool_value("CENSOR_USERNAMES") is True
        assert accessor.get_bool_value("MISSING_KEY", False) is False

    def test_get_int_value_dict(self) -> None:
        """Test getting integer values from dictionary configuration."""
        config_dict: dict[str, object] = {
            "INT_VALUE": 42,
            "STRING_INT": "123",
            "INVALID_STRING": "not_a_number",
            "NONE_VALUE": None,
            "FLOAT_VALUE": 3.14,
        }
        accessor = ConfigAccessor(config_dict)

        assert accessor.get_int_value("INT_VALUE", 0) == 42
        assert accessor.get_int_value("STRING_INT", 0) == 123
        assert accessor.get_int_value("INVALID_STRING", 999) == 999  # Falls back to default
        assert accessor.get_int_value("NONE_VALUE", 888) == 888
        assert accessor.get_int_value("FLOAT_VALUE", 0) == 3  # Converts float to int
        assert accessor.get_int_value("MISSING_KEY", 777) == 777

    def test_get_int_value_tgraph(self) -> None:
        """Test getting integer values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        assert accessor.get_int_value("GRAPH_WIDTH", 0) == 12  # Default value from schema
        assert accessor.get_int_value("GRAPH_HEIGHT", 0) == 8  # Default value from schema
        assert accessor.get_int_value("GRAPH_DPI", 0) == 100  # Default value from schema
        assert accessor.get_int_value("MISSING_KEY", 555) == 555

    def test_get_graph_enable_value_dict(self) -> None:
        """Test getting graph enable values from dictionary configuration."""
        config_dict: dict[str, object] = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_TOP_10_USERS": 1,  # Truthy
            "ENABLE_TOP_10_PLATFORMS": 0,  # Falsy
        }
        accessor = ConfigAccessor(config_dict)

        assert accessor.get_graph_enable_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert accessor.get_graph_enable_value("ENABLE_PLAY_COUNT_BY_DAYOFWEEK") is False
        assert accessor.get_graph_enable_value("ENABLE_TOP_10_USERS") is True
        assert accessor.get_graph_enable_value("ENABLE_TOP_10_PLATFORMS") is False
        assert accessor.get_graph_enable_value("ENABLE_SAMPLE_GRAPH", False) is False
        assert accessor.get_graph_enable_value("MISSING_KEY", True) is True

    def test_get_graph_enable_value_tgraph(self) -> None:
        """Test getting graph enable values from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        assert accessor.get_graph_enable_value("ENABLE_DAILY_PLAY_COUNT") is True
        assert accessor.get_graph_enable_value("ENABLE_PLAY_COUNT_BY_DAYOFWEEK") is True
        assert accessor.get_graph_enable_value("ENABLE_PLAY_COUNT_BY_HOUROFDAY") is True
        assert accessor.get_graph_enable_value("ENABLE_PLAY_COUNT_BY_MONTH") is True
        assert accessor.get_graph_enable_value("ENABLE_TOP_10_PLATFORMS") is True
        assert accessor.get_graph_enable_value("ENABLE_TOP_10_USERS") is True
        assert accessor.get_graph_enable_value("ENABLE_SAMPLE_GRAPH") is False  # Not in schema

    def test_get_graph_dimensions_dict(self) -> None:
        """Test getting graph dimensions from dictionary configuration."""
        config_dict: dict[str, object] = {
            "GRAPH_WIDTH": 16,
            "GRAPH_HEIGHT": 9,
            "GRAPH_DPI": 200,
        }
        accessor = ConfigAccessor(config_dict)

        dimensions = accessor.get_graph_dimensions()
        assert dimensions == {"width": 16, "height": 9, "dpi": 200}

    def test_get_graph_dimensions_tgraph(self) -> None:
        """Test getting graph dimensions from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        dimensions = accessor.get_graph_dimensions()
        assert dimensions == {"width": 12, "height": 8, "dpi": 100}  # Default values from schema

    def test_get_graph_dimensions_with_defaults(self) -> None:
        """Test getting graph dimensions with default values."""
        config_dict: dict[str, object] = {}  # Empty config
        accessor = ConfigAccessor(config_dict)

        dimensions = accessor.get_graph_dimensions()
        assert dimensions == {"width": 12, "height": 8, "dpi": 100}  # Defaults

    def test_validate_required_keys_success(self) -> None:
        """Test successful validation of required keys."""
        config_dict: dict[str, object] = {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
        }
        accessor = ConfigAccessor(config_dict)

        # Should not raise any exception
        accessor.validate_required_keys(["KEY1", "KEY2", "KEY3"])

    def test_validate_required_keys_failure(self) -> None:
        """Test validation failure for missing required keys."""
        config_dict: dict[str, object] = {"KEY1": "value1"}
        accessor = ConfigAccessor(config_dict)

        with pytest.raises(ConfigurationError, match="Missing required configuration keys"):
            accessor.validate_required_keys(["KEY1", "KEY2", "KEY3"])

    def test_get_all_graph_enable_keys_dict(self) -> None:
        """Test getting all graph enable keys from dictionary configuration."""
        config_dict: dict[str, object] = {
            "ENABLE_DAILY_PLAY_COUNT": True,
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK": False,
            "ENABLE_TOP_10_USERS": True,
        }
        accessor = ConfigAccessor(config_dict)

        enable_keys = accessor.get_all_graph_enable_keys()
        
        # Check that all expected keys are present
        expected_keys = [
            "ENABLE_DAILY_PLAY_COUNT",
            "ENABLE_PLAY_COUNT_BY_DAYOFWEEK",
            "ENABLE_PLAY_COUNT_BY_HOUROFDAY",
            "ENABLE_PLAY_COUNT_BY_MONTH",
            "ENABLE_TOP_10_PLATFORMS",
            "ENABLE_TOP_10_USERS",
            "ENABLE_SAMPLE_GRAPH",
        ]
        
        assert set(enable_keys.keys()) == set(expected_keys)
        assert enable_keys["ENABLE_DAILY_PLAY_COUNT"] is True
        assert enable_keys["ENABLE_PLAY_COUNT_BY_DAYOFWEEK"] is False
        assert enable_keys["ENABLE_TOP_10_USERS"] is True
        assert enable_keys["ENABLE_SAMPLE_GRAPH"] is False  # Default for sample graph

    def test_get_all_graph_enable_keys_tgraph(self) -> None:
        """Test getting all graph enable keys from TGraphBotConfig."""
        config = create_test_config_comprehensive()
        accessor = ConfigAccessor(config)

        enable_keys = accessor.get_all_graph_enable_keys()
        
        # All should be True except ENABLE_SAMPLE_GRAPH
        for key, value in enable_keys.items():
            if key == "ENABLE_SAMPLE_GRAPH":
                assert value is False
            else:
                assert value is True
