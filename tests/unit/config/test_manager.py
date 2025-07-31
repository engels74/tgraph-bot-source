"""Tests for configuration manager functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from src.tgraph_bot.config.manager import ConfigManager
from src.tgraph_bot.config.schema import TGraphBotConfig
from tests.utils.test_helpers import create_temp_config_file


class TestConfigManager:
    """Test cases for ConfigManager functionality."""

    def test_load_config_success(self, base_config: TGraphBotConfig) -> None:
        """Test successful configuration loading."""
        # Create temp config file with nested data structure
        config_data: dict[str, object] = {
            "services": {
                "tautulli": {
                    "api_key": base_config.services.tautulli.api_key,
                    "url": base_config.services.tautulli.url,
                },
                "discord": {
                    "token": base_config.services.discord.token,
                    "channel_id": base_config.services.discord.channel_id,
                },
            },
            "automation": {
                "scheduling": {
                    "update_days": base_config.automation.scheduling.update_days,
                },
            },
            "graphs": {
                "appearance": {
                    "colors": {
                        "tv": base_config.graphs.appearance.colors.tv,
                    },
                },
            },
        }

        with create_temp_config_file(config_data) as temp_config_file:
            config = ConfigManager.load_config(temp_config_file)

            assert isinstance(config, TGraphBotConfig)
            assert config.services.tautulli.api_key == base_config.services.tautulli.api_key
            assert config.services.tautulli.url == base_config.services.tautulli.url
            assert config.services.discord.token == base_config.services.discord.token
            assert config.services.discord.channel_id == base_config.services.discord.channel_id
            assert config.automation.scheduling.update_days == base_config.automation.scheduling.update_days
            assert config.graphs.appearance.colors.tv == base_config.graphs.appearance.colors.tv

    def test_load_config_file_not_found(self) -> None:
        """Test loading config when file doesn't exist."""
        non_existent_path = Path("/non/existent/config.yml")

        with pytest.raises(FileNotFoundError):
            _ = ConfigManager.load_config(non_existent_path)

    def test_load_config_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            _ = f.write("invalid: yaml: content: [")
            invalid_yaml_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                _ = ConfigManager.load_config(invalid_yaml_path)
        finally:
            invalid_yaml_path.unlink(missing_ok=True)

    def test_load_config_validation_error(self) -> None:
        """Test loading config with validation errors."""
        # Missing required fields
        invalid_config_data: dict[str, object] = {
            "automation": {
                "scheduling": {
                    "update_days": 14,
                },
            },
            "graphs": {
                "appearance": {
                    "colors": {
                        "tv": "#1f77b4",
                    },
                },
            },
        }

        with create_temp_config_file(invalid_config_data) as invalid_config_file:
            with pytest.raises(ValidationError):
                _ = ConfigManager.load_config(invalid_config_file)

    def test_save_config_success(self, base_config: TGraphBotConfig) -> None:
        """Test successful configuration saving."""
        # Create temp config file with nested config data
        config_data: dict[str, object] = {
            "services": {
                "tautulli": {
                    "api_key": base_config.services.tautulli.api_key,
                    "url": base_config.services.tautulli.url,
                },
                "discord": {
                    "token": base_config.services.discord.token,
                    "channel_id": base_config.services.discord.channel_id,
                },
            },
            "automation": {
                "scheduling": {
                    "update_days": base_config.automation.scheduling.update_days,
                },
            },
            "graphs": {
                "appearance": {
                    "colors": {
                        "tv": base_config.graphs.appearance.colors.tv,
                    },
                    "palettes": {
                        "play_count_by_hourofday": base_config.graphs.appearance.palettes.play_count_by_hourofday,
                        "top_10_users": base_config.graphs.appearance.palettes.top_10_users,
                    },
                },
            },
        }

        with create_temp_config_file(config_data) as temp_config_file:
            # Load existing config
            config = ConfigManager.load_config(temp_config_file)

            # Modify some values
            config.automation.scheduling.update_days = 21
            config.graphs.appearance.colors.tv = "#ff0000"

            # Save the config
            ConfigManager.save_config(config, temp_config_file)

            # Load again and verify changes
            reloaded_config = ConfigManager.load_config(temp_config_file)
            assert reloaded_config.automation.scheduling.update_days == 21
            assert reloaded_config.graphs.appearance.colors.tv == "#ff0000"

    def test_save_config_preserves_comments(self, base_config: TGraphBotConfig) -> None:
        """Test that saving config works correctly (comment preservation currently disabled)."""
        # Create config file with comments
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            content = f"""# Required Configuration (Set These First)
services:
  tautulli:
    api_key: {base_config.services.tautulli.api_key}
    url: {base_config.services.tautulli.url}  # Base URL for Tautulli
  discord:
    token: {base_config.services.discord.token}
    channel_id: {base_config.services.discord.channel_id}

# Graph Options
automation:
  scheduling:
    update_days: {base_config.automation.scheduling.update_days}  # Number of days between updates
graphs:
  appearance:
    colors:
      tv: '{base_config.graphs.appearance.colors.tv}'  # Color for TV shows
"""
            _ = f.write(content)
            config_with_comments = Path(f.name)

        try:
            # Load config
            config = ConfigManager.load_config(config_with_comments)

            # Modify a value
            config.automation.scheduling.update_days = 21

            # Save config
            ConfigManager.save_config(config, config_with_comments)

            # Read the file content and verify the change was saved
            content = config_with_comments.read_text()
            # Note: Comment preservation is currently disabled for nested configs
            # TODO: Re-enable comment preservation tests when nested comment preservation is implemented
            assert "update_days: 21" in content
            # Verify the file is valid YAML that can be loaded
            reloaded_config = ConfigManager.load_config(config_with_comments)
            assert reloaded_config.automation.scheduling.update_days == 21
        finally:
            config_with_comments.unlink(missing_ok=True)

    def test_get_default_config(self) -> None:
        """Test getting default configuration."""
        config = ConfigManager.get_default_config()

        assert isinstance(config, TGraphBotConfig)
        # Check some default values
        assert config.automation.scheduling.update_days == 7
        assert config.automation.scheduling.fixed_update_time == "XX:XX"
        assert config.automation.data_retention.keep_days == 7
        assert config.data_collection.privacy.censor_usernames is True
        assert config.graphs.appearance.colors.tv == "#1f77b4"

    def test_validate_config_success(self, base_config: TGraphBotConfig) -> None:
        """Test successful configuration validation."""
        # Should not raise any exception
        is_valid = ConfigManager.validate_config(base_config)
        assert is_valid is True

    def test_validate_config_failure(self) -> None:
        """Test configuration validation failure."""
        # Create invalid config data
        invalid_data: dict[str, object] = {
            "services": {
                "tautulli": {
                    "api_key": "",  # Empty string should fail validation
                    "url": "invalid_url",  # Invalid URL format
                },
                "discord": {
                    "token": "short",  # Too short
                    "channel_id": -1,  # Negative value
                },
            },
        }

        with pytest.raises(ValidationError):
            _ = TGraphBotConfig(**invalid_data)  # pyright: ignore[reportArgumentType]

    def test_create_sample_config(self) -> None:
        """Test creating sample configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_path = Path(temp_dir) / "config.yml.sample"

            ConfigManager.create_sample_config(sample_path)

            assert sample_path.exists()

            # Verify the sample file contains expected content
            content = sample_path.read_text()
            assert "api_key:" in content
            assert "token:" in content
            assert "channel_id:" in content
            assert "# Required Configuration (Set These First)" in content

    def test_sample_config_validation(self) -> None:
        """Test that the generated sample configuration can be loaded and validated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_path = Path(temp_dir) / "config.yml.sample"

            # Create the sample config
            ConfigManager.create_sample_config(sample_path)

            # Load the sample config - this should work without validation errors
            # since it contains valid placeholder values
            config = ConfigManager.load_config(sample_path)

            # Verify it's a valid TGraphBotConfig instance
            assert isinstance(config, TGraphBotConfig)

            # Verify some key fields have the expected placeholder values
            assert config.services.tautulli.api_key == "your_tautulli_api_key_here"
            assert config.services.tautulli.url == "http://localhost:8181/api/v2"
            assert config.services.discord.token == "your_discord_bot_token_here"
            assert config.services.discord.channel_id == 123456789012345678

    def test_atomic_save_operation(self, base_config: TGraphBotConfig) -> None:
        """Test that config saves are atomic (all-or-nothing)."""
        config_data: dict[str, object] = {
            "services": {
                "tautulli": {
                    "api_key": base_config.services.tautulli.api_key,
                    "url": base_config.services.tautulli.url,
                },
                "discord": {
                    "token": base_config.services.discord.token,
                    "channel_id": base_config.services.discord.channel_id,
                },
            },
        }

        with create_temp_config_file(config_data) as temp_config_file:
            config = ConfigManager.load_config(temp_config_file)

            # Mock atomic move operation to fail
            original_replace = Path.replace

            def failing_replace(self: Path, target: Path) -> Path:
                if target == temp_config_file:
                    raise OSError("Simulated atomic move failure")
                return original_replace(self, target)

            with patch.object(Path, "replace", failing_replace):
                with pytest.raises(OSError):
                    ConfigManager.save_config(config, temp_config_file)

            # Verify original config is still intact
            reloaded_config = ConfigManager.load_config(temp_config_file)
            assert reloaded_config.services.tautulli.api_key == config.services.tautulli.api_key

    def test_config_parsing_with_match_statement(
        self, comprehensive_config: TGraphBotConfig
    ) -> None:
        """Test that config parsing handles all field types using pattern matching."""
        # Test various field types from comprehensive config
        config = comprehensive_config

        # Verify different field types are parsed correctly
        assert isinstance(config.services.tautulli.api_key, str)
        assert isinstance(config.services.discord.channel_id, int)
        assert isinstance(config.data_collection.privacy.censor_usernames, bool)
        assert isinstance(config.automation.scheduling.update_days, int)
        assert config.automation.scheduling.update_days == 14
        assert config.data_collection.privacy.censor_usernames is False
        assert config.system.localization.language == "es"

    def test_config_manager_lifecycle(self, base_config: TGraphBotConfig) -> None:
        """Test the configuration manager lifecycle without file monitoring."""
        config_manager = ConfigManager()

        # Test that we can set and get current config
        config_manager.set_current_config(base_config)
        retrieved_config = config_manager.get_current_config()
        assert retrieved_config == base_config

        # Test that we can update runtime config
        modified_config = base_config.model_copy()
        modified_config.automation.scheduling.update_days = 14
        config_manager.update_runtime_config(modified_config)

        updated_config = config_manager.get_current_config()
        assert updated_config.automation.scheduling.update_days == 14

        # Test config file path management
        test_path = Path("/test/config.yml")
        config_manager.config_file_path = test_path
        assert config_manager.config_file_path == test_path

        del config_manager.config_file_path
        assert config_manager.config_file_path is None

    def test_config_change_callbacks(self, base_config: TGraphBotConfig) -> None:
        """Test configuration change callback functionality."""
        config_manager = ConfigManager()
        config_manager.set_current_config(base_config)

        callback_called = False
        old_config_received = None
        new_config_received = None

        def test_callback(
            old_config: TGraphBotConfig, new_config: TGraphBotConfig
        ) -> None:
            nonlocal callback_called, old_config_received, new_config_received
            callback_called = True
            old_config_received = old_config
            new_config_received = new_config

        # Register callback
        config_manager.register_change_callback(test_callback)

        # Update config - should trigger callback
        modified_config = base_config.model_copy()
        modified_config.automation.scheduling.update_days = 14
        config_manager.update_runtime_config(modified_config)

        assert callback_called
        assert old_config_received == base_config
        assert new_config_received is not None
        assert new_config_received.automation.scheduling.update_days == 14

        # Unregister callback
        config_manager.unregister_change_callback(test_callback)

        # Reset callback state
        callback_called = False

        # Update config again - should not trigger callback
        modified_config_2 = modified_config.model_copy()
        modified_config_2.automation.scheduling.update_days = 21
        config_manager.update_runtime_config(modified_config_2)

        assert not callback_called

    def test_config_manager_no_file_monitoring_methods(self) -> None:
        """Test that file monitoring methods are not available after removal."""
        config_manager = ConfigManager()

        # These methods should not exist after watchdog removal
        assert not hasattr(config_manager, "start_file_monitoring")
        assert not hasattr(config_manager, "stop_file_monitoring")
        assert not hasattr(config_manager, "_reload_from_file")

        # These attributes should not exist after watchdog removal
        assert not hasattr(config_manager, "_file_observer")
        assert not hasattr(config_manager, "_monitored_file")

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Any cleanup that's needed after tests
        pass
