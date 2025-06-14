"""Tests for configuration manager functionality."""

import tempfile
import threading
import time
from pathlib import Path
# pyright: reportPrivateUsage=false, reportAny=false
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from config.manager import ConfigManager
from config.schema import TGraphBotConfig


class TestConfigManager:
    """Test cases for ConfigManager functionality."""

    @pytest.fixture
    def temp_config_file(self) -> Path:
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config_data = {
                'TAUTULLI_API_KEY': 'test_api_key',
                'TAUTULLI_URL': 'http://localhost:8181/api/v2',
                'DISCORD_TOKEN': 'test_discord_token',
                'CHANNEL_ID': 123456789012345678,
                'UPDATE_DAYS': 14,
                'TV_COLOR': '#1f77b4',
            }
            yaml.dump(config_data, f, default_flow_style=False)
            return Path(f.name)

    @pytest.fixture
    def invalid_config_file(self) -> Path:
        """Create a temporary invalid config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            # Missing required fields
            config_data = {
                'UPDATE_DAYS': 14,
                'TV_COLOR': '#1f77b4',
            }
            yaml.dump(config_data, f, default_flow_style=False)
            return Path(f.name)

    @pytest.fixture
    def config_with_comments(self) -> Path:
        """Create a config file with comments for testing comment preservation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            content = """# Essential Settings
TAUTULLI_API_KEY: test_api_key
TAUTULLI_URL: http://localhost:8181/api/v2  # Base URL for Tautulli
DISCORD_TOKEN: test_discord_token
CHANNEL_ID: 123456789012345678

# Graph Options
UPDATE_DAYS: 14  # Number of days between updates
TV_COLOR: '#1f77b4'  # Color for TV shows
"""
            _ = f.write(content)
            return Path(f.name)

    def test_load_config_success(self, temp_config_file: Path) -> None:
        """Test successful configuration loading."""
        config = ConfigManager.load_config(temp_config_file)
        
        assert isinstance(config, TGraphBotConfig)
        assert config.TAUTULLI_API_KEY == 'test_api_key'
        assert config.TAUTULLI_URL == 'http://localhost:8181/api/v2'
        assert config.DISCORD_TOKEN == 'test_discord_token'
        assert config.CHANNEL_ID == 123456789012345678
        assert config.UPDATE_DAYS == 14
        assert config.TV_COLOR == '#1f77b4'

    def test_load_config_file_not_found(self) -> None:
        """Test loading config when file doesn't exist."""
        non_existent_path = Path('/non/existent/config.yml')
        
        with pytest.raises(FileNotFoundError):
            _ = ConfigManager.load_config(non_existent_path)

    def test_load_config_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            _ = f.write('invalid: yaml: content: [')
            invalid_yaml_path = Path(f.name)
        
        with pytest.raises(yaml.YAMLError):
            _ = ConfigManager.load_config(invalid_yaml_path)

    def test_load_config_validation_error(self, invalid_config_file: Path) -> None:
        """Test loading config with validation errors."""
        with pytest.raises(ValidationError):
            _ = ConfigManager.load_config(invalid_config_file)

    def test_save_config_success(self, temp_config_file: Path) -> None:
        """Test successful configuration saving."""
        # Load existing config
        config = ConfigManager.load_config(temp_config_file)
        
        # Modify some values
        config.UPDATE_DAYS = 21
        config.TV_COLOR = '#ff0000'
        
        # Save the config
        ConfigManager.save_config(config, temp_config_file)
        
        # Load again and verify changes
        reloaded_config = ConfigManager.load_config(temp_config_file)
        assert reloaded_config.UPDATE_DAYS == 21
        assert reloaded_config.TV_COLOR == '#ff0000'

    def test_save_config_preserves_comments(self, config_with_comments: Path) -> None:
        """Test that saving config preserves comments."""
        # Load config
        config = ConfigManager.load_config(config_with_comments)
        
        # Modify a value
        config.UPDATE_DAYS = 21
        
        # Save config
        ConfigManager.save_config(config, config_with_comments)
        
        # Read the file content and check comments are preserved
        content = config_with_comments.read_text()
        assert '# Essential Settings' in content
        assert '# Base URL for Tautulli' in content
        assert '# Graph Options' in content
        assert 'UPDATE_DAYS: 21' in content

    def test_get_default_config(self) -> None:
        """Test getting default configuration."""
        config = ConfigManager.get_default_config()
        
        assert isinstance(config, TGraphBotConfig)
        # Check some default values
        assert config.UPDATE_DAYS == 7
        assert config.FIXED_UPDATE_TIME == 'XX:XX'
        assert config.KEEP_DAYS == 7
        assert config.CENSOR_USERNAMES is True
        assert config.TV_COLOR == '#1f77b4'

    def test_validate_config_success(self, temp_config_file: Path) -> None:
        """Test successful configuration validation."""
        config = ConfigManager.load_config(temp_config_file)
        
        # Should not raise any exception
        is_valid = ConfigManager.validate_config(config)
        assert is_valid is True

    def test_validate_config_failure(self) -> None:
        """Test configuration validation failure."""
        # Create invalid config data
        invalid_data: dict[str, object] = {
            'TAUTULLI_API_KEY': '',  # Empty string should fail validation
            'TAUTULLI_URL': 'invalid_url',  # Invalid URL format
            'DISCORD_TOKEN': 'short',  # Too short
            'CHANNEL_ID': -1,  # Negative value
        }

        with pytest.raises(ValidationError):
            _ = TGraphBotConfig(**invalid_data)  # pyright: ignore[reportArgumentType]

    def test_create_sample_config(self) -> None:
        """Test creating sample configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_path = Path(temp_dir) / 'config.yml.sample'

            ConfigManager.create_sample_config(sample_path)

            assert sample_path.exists()

            # Verify the sample file contains expected content
            content = sample_path.read_text()
            assert 'TAUTULLI_API_KEY:' in content
            assert 'DISCORD_TOKEN:' in content
            assert 'CHANNEL_ID:' in content
            assert '# Essential Settings' in content

    def test_sample_config_validation(self) -> None:
        """Test that the generated sample configuration can be loaded and validated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_path = Path(temp_dir) / 'config.yml.sample'

            # Create the sample config
            ConfigManager.create_sample_config(sample_path)

            # Load the sample config - this should work without validation errors
            # since it contains valid placeholder values
            config = ConfigManager.load_config(sample_path)

            # Verify it's a valid TGraphBotConfig instance
            assert isinstance(config, TGraphBotConfig)

            # Verify some key fields have the expected placeholder values
            assert config.TAUTULLI_API_KEY == 'your_tautulli_api_key_here'
            assert config.TAUTULLI_URL == 'http://localhost:8181/api/v2'
            assert config.DISCORD_TOKEN == 'your_discord_bot_token_here'
            assert config.CHANNEL_ID == 123456789012345678

            # Verify default values are correctly set
            assert config.UPDATE_DAYS == 7
            assert config.FIXED_UPDATE_TIME == 'XX:XX'
            assert config.KEEP_DAYS == 7
            assert config.TIME_RANGE_DAYS == 30
            assert config.LANGUAGE == 'en'
            assert config.CENSOR_USERNAMES is True
            assert config.ENABLE_GRAPH_GRID is False

            # Verify color values
            assert config.TV_COLOR == '#1f77b4'
            assert config.MOVIE_COLOR == '#ff7f0e'
            assert config.GRAPH_BACKGROUND_COLOR == '#ffffff'
            assert config.ANNOTATION_COLOR == '#ff0000'
            assert config.ANNOTATION_OUTLINE_COLOR == '#000000'

            # Verify cooldown settings
            assert config.CONFIG_COOLDOWN_MINUTES == 0
            assert config.MY_STATS_COOLDOWN_MINUTES == 5
            assert config.MY_STATS_GLOBAL_COOLDOWN_SECONDS == 60

    def test_atomic_save_operation(self, temp_config_file: Path) -> None:
        """Test that save operations are atomic."""
        original_config = ConfigManager.load_config(temp_config_file)

        # Simulate a failure during save by mocking yaml.dump to raise an exception
        # Use preserve_comments=False to force the yaml.dump path
        with patch('config.manager.yaml.dump', side_effect=Exception('Simulated failure')):
            modified_config = original_config.model_copy()
            modified_config.UPDATE_DAYS = 21  # Valid value within range

            with pytest.raises(Exception, match='Simulated failure'):
                ConfigManager.save_config(modified_config, temp_config_file, preserve_comments=False)

        # Verify original file is unchanged
        current_config = ConfigManager.load_config(temp_config_file)
        assert current_config.UPDATE_DAYS == original_config.UPDATE_DAYS

    def test_config_parsing_with_match_statement(self) -> None:
        """Test configuration parsing using match statements."""
        test_cases = [
            ('FIXED_UPDATE_TIME', 'XX:XX', 'XX:XX'),
            ('FIXED_UPDATE_TIME', '12:30', '12:30'),
            ('LANGUAGE', 'en', 'en'),
            ('LANGUAGE', 'fr', 'fr'),
        ]
        
        for field_name, input_value, expected_value in test_cases:
            config_data = {
                'TAUTULLI_API_KEY': 'test_api_key',
                'TAUTULLI_URL': 'http://localhost:8181/api/v2',
                'DISCORD_TOKEN': 'test_discord_token',
                'CHANNEL_ID': 123456789012345678,
                field_name: input_value,
            }
            
            config = TGraphBotConfig(**config_data)  # pyright: ignore[reportArgumentType]
            assert getattr(config, field_name) == expected_value

    def teardown_method(self) -> None:
        """Clean up temporary files after each test."""
        # This will be called after each test method
        pass


class TestLiveConfigurationManagement:
    """Test cases for live configuration management functionality."""

    @pytest.fixture
    def temp_config_file(self) -> Path:
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config_data = {
                'TAUTULLI_API_KEY': 'test_api_key',
                'TAUTULLI_URL': 'http://localhost:8181/api/v2',
                'DISCORD_TOKEN': 'test_discord_token',
                'CHANNEL_ID': 123456789012345678,
                'UPDATE_DAYS': 14,
                'TV_COLOR': '#1f77b4',
            }
            yaml.dump(config_data, f, default_flow_style=False)
            return Path(f.name)

    def test_config_change_notification(self, temp_config_file: Path) -> None:
        """Test that configuration change notifications work."""
        manager = ConfigManager()
        callback_called = threading.Event()
        old_config = None
        new_config = None

        def config_change_callback(old_cfg: TGraphBotConfig, new_cfg: TGraphBotConfig) -> None:
            nonlocal old_config, new_config
            old_config = old_cfg
            new_config = new_cfg
            callback_called.set()

        # Register callback
        manager.register_change_callback(config_change_callback)

        # Load initial config
        initial_config = manager.load_config(temp_config_file)
        manager.set_current_config(initial_config)

        # Update configuration
        updated_config = initial_config.model_copy()
        updated_config.UPDATE_DAYS = 21

        # Trigger configuration update
        manager.update_runtime_config(updated_config)

        # Wait for callback to be called
        assert callback_called.wait(timeout=1.0), "Callback was not called within timeout"

        # Verify callback received correct values
        assert old_config is not None
        assert new_config is not None
        assert old_config.UPDATE_DAYS == 14
        assert new_config.UPDATE_DAYS == 21

    def test_runtime_config_update(self, temp_config_file: Path) -> None:
        """Test runtime configuration updates."""
        manager = ConfigManager()

        # Load initial config
        initial_config = manager.load_config(temp_config_file)
        manager.set_current_config(initial_config)

        # Update configuration at runtime
        updated_config = initial_config.model_copy()
        updated_config.UPDATE_DAYS = 21
        updated_config.TV_COLOR = '#ff0000'

        manager.update_runtime_config(updated_config)

        # Verify current config is updated
        current_config = manager.get_current_config()
        assert current_config.UPDATE_DAYS == 21
        assert current_config.TV_COLOR == '#ff0000'

    def test_file_monitoring_and_reload(self, temp_config_file: Path) -> None:
        """Test file monitoring and automatic reload functionality."""
        manager = ConfigManager()

        # Load initial config
        initial_config = manager.load_config(temp_config_file)
        manager.set_current_config(initial_config)

        # Start file monitoring
        manager.start_file_monitoring(temp_config_file)

        try:
            # Modify the config file externally
            modified_data = {
                'TAUTULLI_API_KEY': 'test_api_key',
                'TAUTULLI_URL': 'http://localhost:8181/api/v2',
                'DISCORD_TOKEN': 'test_discord_token',
                'CHANNEL_ID': 123456789012345678,
                'UPDATE_DAYS': 30,  # Changed value
                'TV_COLOR': '#00ff00',  # Changed value
            }

            with open(temp_config_file, 'w') as f:
                yaml.dump(modified_data, f, default_flow_style=False)

            # Wait for file monitoring to detect change and reload
            time.sleep(0.5)  # Give file monitor time to detect change

            # Verify config was reloaded
            current_config = manager.get_current_config()
            assert current_config.UPDATE_DAYS == 30
            assert current_config.TV_COLOR == '#00ff00'

        finally:
            # Stop file monitoring
            manager.stop_file_monitoring()

    def test_thread_safety(self, temp_config_file: Path) -> None:
        """Test thread safety of configuration access."""
        manager = ConfigManager()

        # Load initial config
        initial_config = manager.load_config(temp_config_file)
        manager.set_current_config(initial_config)

        results = []
        errors = []

        def config_reader() -> None:
            """Function to read config from multiple threads."""
            try:
                for _ in range(100):
                    config = manager.get_current_config()
                    results.append(config.UPDATE_DAYS)
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)

        def config_updater() -> None:
            """Function to update config from multiple threads."""
            try:
                for i in range(50):
                    updated_config = manager.get_current_config().model_copy()
                    updated_config.UPDATE_DAYS = 14 + (i % 10)  # Vary between 14-23
                    manager.update_runtime_config(updated_config)
                    time.sleep(0.002)  # Small delay
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=config_reader))
        for _ in range(2):
            threads.append(threading.Thread(target=config_updater))

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during thread safety test: {errors}"

        # Verify we got results from readers
        assert len(results) > 0, "No results from config readers"

    def test_callback_management(self, temp_config_file: Path) -> None:
        """Test callback registration and unregistration."""
        manager = ConfigManager()

        callback1_called = threading.Event()
        callback2_called = threading.Event()

        def callback1(_old_cfg: TGraphBotConfig, _new_cfg: TGraphBotConfig) -> None:
            callback1_called.set()

        def callback2(_old_cfg: TGraphBotConfig, _new_cfg: TGraphBotConfig) -> None:
            callback2_called.set()

        # Register both callbacks
        manager.register_change_callback(callback1)
        manager.register_change_callback(callback2)

        # Load initial config and trigger update
        initial_config = manager.load_config(temp_config_file)
        manager.set_current_config(initial_config)

        updated_config = initial_config.model_copy()
        updated_config.UPDATE_DAYS = 21
        manager.update_runtime_config(updated_config)

        # Both callbacks should be called
        assert callback1_called.wait(timeout=1.0), "Callback1 was not called"
        assert callback2_called.wait(timeout=1.0), "Callback2 was not called"

        # Reset events
        callback1_called.clear()
        callback2_called.clear()

        # Unregister callback1
        manager.unregister_change_callback(callback1)

        # Trigger another update
        updated_config2 = updated_config.model_copy()
        updated_config2.UPDATE_DAYS = 25
        manager.update_runtime_config(updated_config2)

        # Only callback2 should be called
        assert not callback1_called.wait(timeout=0.5), "Callback1 should not have been called"
        assert callback2_called.wait(timeout=1.0), "Callback2 was not called"
