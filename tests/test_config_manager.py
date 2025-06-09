"""Tests for configuration manager functionality."""

import tempfile
from pathlib import Path
from typing import Any
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
            f.write(content)
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
            ConfigManager.load_config(non_existent_path)

    def test_load_config_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write('invalid: yaml: content: [')
            invalid_yaml_path = Path(f.name)
        
        with pytest.raises(yaml.YAMLError):
            ConfigManager.load_config(invalid_yaml_path)

    def test_load_config_validation_error(self, invalid_config_file: Path) -> None:
        """Test loading config with validation errors."""
        with pytest.raises(ValidationError):
            ConfigManager.load_config(invalid_config_file)

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
        invalid_data: dict[str, Any] = {
            'TAUTULLI_API_KEY': '',  # Empty string should fail validation
            'TAUTULLI_URL': 'invalid_url',  # Invalid URL format
            'DISCORD_TOKEN': 'short',  # Too short
            'CHANNEL_ID': -1,  # Negative value
        }

        with pytest.raises(ValidationError):
            TGraphBotConfig(**invalid_data)

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
            
            config = TGraphBotConfig(**config_data)
            assert getattr(config, field_name) == expected_value

    def teardown_method(self) -> None:
        """Clean up temporary files after each test."""
        # This will be called after each test method
        pass
