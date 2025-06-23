"""
Tests for Weblate configuration validation.

This module tests the Weblate configuration file and related functionality
to ensure proper setup for collaborative translation management.
"""

from __future__ import annotations

import configparser
import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from scripts.validate_weblate_config import (
    check_locale_structure,
    validate_weblate_config,
)


class TestWeblateConfigValidation:
    """Test Weblate configuration validation functionality."""

    def test_validate_existing_config(self) -> None:
        """Test validation of the existing .weblate configuration file."""
        config_path = Path('.weblate')
        
        # The actual config file should exist and be valid
        assert config_path.exists(), "Weblate configuration file should exist"
        
        # Validate the configuration
        result = validate_weblate_config(config_path)
        assert result is True, "Weblate configuration should be valid"

    def test_validate_missing_config(self) -> None:
        """Test validation when configuration file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_config = Path(temp_dir) / 'nonexistent.weblate'
            result = validate_weblate_config(missing_config)
            assert result is False

    def test_validate_invalid_config(self) -> None:
        """Test validation with invalid configuration content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.weblate', delete=False) as f:
            # Write invalid config (missing required sections)
            _ = f.write("[invalid]\nkey = value\n")
            f.flush()
            
            config_path = Path(f.name)
            try:
                result = validate_weblate_config(config_path)
                assert result is False
            finally:
                _ = config_path.unlink()

    def test_validate_minimal_valid_config(self) -> None:
        """Test validation with minimal valid configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.weblate', delete=False) as f:
            # Write minimal valid config
            _ = f.write("""[weblate]
url = https://hosted.weblate.org/

[component "test"]
name = Test Component
slug = test
repo = https://github.com/test/repo.git
push = git@github.com:test/repo.git
branch = main
filemask = locale/*/LC_MESSAGES/messages.po
template = locale/messages.pot
file_format = po
""")
            f.flush()
            
            config_path = Path(f.name)
            try:
                result = validate_weblate_config(config_path)
                assert result is True
            finally:
                _ = config_path.unlink()

    def test_config_file_structure(self) -> None:
        """Test that the actual config file has the expected structure."""
        config = configparser.ConfigParser()
        _ = config.read('.weblate')
        
        # Check main weblate section
        assert 'weblate' in config
        assert 'url' in config['weblate']
        assert config['weblate']['url'] == 'https://hosted.weblate.org/'
        
        # Check for expected components
        all_sections: list[str] = list(config.sections())
        components: list[str] = [section for section in all_sections 
                                if section.startswith('component ')]
        assert len(components) >= 1, "Should have at least one component"
        
        # Check main bot component
        bot_component: str | None = None
        for component in components:
            if 'tgraph-bot' in component and 'readme' not in component.lower():
                bot_component = component
                break
        
        assert bot_component is not None, "Should have main bot component"
        
        bot_config = config[bot_component]
        required_fields = ['name', 'slug', 'repo', 'push', 'branch', 
                          'filemask', 'template', 'file_format']
        
        for field in required_fields:
            assert field in bot_config, f"Missing required field: {field}"
        
        # Verify specific values
        assert bot_config['file_format'] == 'po'
        assert 'locale/' in bot_config['filemask']
        assert bot_config['template'] == 'locale/messages.pot'


class TestLocaleStructureValidation:
    """Test locale directory structure validation."""

    def test_check_existing_locale_structure(self) -> None:
        """Test validation of existing locale directory structure."""
        # This should pass with the current project structure
        result = check_locale_structure()
        assert result is True

    @patch('scripts.validate_weblate_config.Path')
    def test_check_missing_locale_directory(self, mock_path_class: MagicMock) -> None:
        """Test validation when locale directory is missing."""
        # Mock the Path class to return a mock object
        mock_path_instance = cast(MagicMock, mock_path_class.return_value)
        mock_locale_dir: MagicMock = mock_path_instance
        mock_exists = MagicMock(return_value=False)
        mock_locale_dir.exists = mock_exists

        result = check_locale_structure()
        assert result is False

    def test_locale_directory_contents(self) -> None:
        """Test that locale directory has expected contents."""
        locale_dir = Path('locale')
        assert locale_dir.exists(), "Locale directory should exist"
        
        # Check for template file
        pot_file = locale_dir / 'messages.pot'
        assert pot_file.exists(), "Template file should exist"
        
        # Check for language directories
        language_dirs = [d for d in locale_dir.iterdir() 
                        if d.is_dir() and d.name != '__pycache__']
        
        # Should have at least English
        assert len(language_dirs) >= 1, "Should have at least one language directory"
        
        # Check English directory structure
        en_dir = locale_dir / 'en'
        if en_dir.exists():
            lc_messages = en_dir / 'LC_MESSAGES'
            assert lc_messages.exists(), "LC_MESSAGES directory should exist"
            
            po_file = lc_messages / 'messages.po'
            assert po_file.exists(), "English .po file should exist"


class TestWeblateIntegration:
    """Test Weblate integration aspects."""

    def test_filemask_pattern_validity(self) -> None:
        """Test that filemask patterns are valid."""
        config = configparser.ConfigParser()
        _ = config.read('.weblate')
        
        section_names: list[str] = list(config.sections())
        for section_name in section_names:
            if not section_name.startswith('component '):
                continue
                
            section = config[section_name]
            if 'filemask' not in section:
                continue
                
            filemask: str = section['filemask']
            
            # Should contain wildcard for language
            assert '*' in filemask, f"Filemask should contain wildcard: {filemask}"
            
            # Should be a reasonable path pattern
            assert '/' in filemask, f"Filemask should contain path separator: {filemask}"

    def test_template_file_references(self) -> None:
        """Test that template files referenced in config exist."""
        config = configparser.ConfigParser()
        _ = config.read('.weblate')

        section_names: list[str] = list(config.sections())
        for section_name in section_names:
            if not section_name.startswith('component '):
                continue
                
            section = config[section_name]
            if 'template' not in section:
                continue
                
            template_path = Path(section['template'])
            
            # Template should exist (or be reasonable)
            if 'locale/messages.pot' in str(template_path):
                assert template_path.exists(), f"Template file should exist: {template_path}"
            elif 'README.md' in str(template_path):
                assert template_path.exists(), f"README template should exist: {template_path}"

    def test_repository_configuration(self) -> None:
        """Test repository configuration in Weblate config."""
        config = configparser.ConfigParser()
        _ = config.read('.weblate')

        section_names: list[str] = list(config.sections())
        for section_name in section_names:
            if not section_name.startswith('component '):
                continue
                
            section = config[section_name]
            
            # Should have repository configuration
            assert 'repo' in section, "Component should have repo URL"
            assert 'push' in section, "Component should have push URL"
            assert 'branch' in section, "Component should have branch"
            
            # URLs should be reasonable
            repo_url: str = section['repo']
            push_url: str = section['push']
            
            assert 'github.com' in repo_url, "Should use GitHub"
            assert 'tgraph-bot-source' in repo_url, "Should reference correct repository"
            
            # Push URL should be SSH for write access
            assert push_url.startswith('git@'), "Push URL should use SSH"


if __name__ == '__main__':
    _ = pytest.main([__file__])
