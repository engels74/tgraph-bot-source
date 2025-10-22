"""Configuration loader for YAML files with environment variable overrides.

This module handles loading and saving configuration from YAML files,
with support for environment variable overrides for sensitive values.

This is a stub implementation to support test development (TDD approach).
Full implementation will be added in task 4.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from tgraph_bot.config.models import BotConfig
from tgraph_bot.utils.errors import ConfigurationError


class ConfigLoader:
    """Handles loading and saving configuration files."""

    def load(self, path: str) -> BotConfig:
        """Load configuration from YAML file with environment variable overrides.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated BotConfig instance

        Raises:
            ConfigurationError: If file not found, YAML invalid, or validation fails
        """
        file_path = Path(path)

        # Check if file exists
        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                field_name="config_file",
                expected_value="valid file path",
            )

        try:
            # Load YAML file
            yaml_parser = YAML()
            with open(file_path) as f:
                config_data: Any = yaml_parser.load(f)

            if not isinstance(config_data, dict):
                raise ConfigurationError(
                    "Configuration file must contain a YAML dictionary",
                    field_name="config_file",
                )

            # Type is now confirmed to be dict
            config_dict: dict[str, Any] = config_data

            # Apply environment variable overrides
            self._apply_env_overrides(config_dict)

            # Validate with Pydantic
            config = BotConfig(**config_dict)
            return config

        except YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration: {e}",
                field_name="config_file",
                expected_value="valid YAML syntax",
            ) from e
        except ValidationError as e:
            # Re-raise validation errors as ConfigurationError
            error_details = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in e.errors()
            )
            raise ConfigurationError(
                f"Configuration validation failed: {error_details}",
                field_name="configuration",
                expected_value="valid configuration values",
            ) from e

    def _apply_env_overrides(self, config_dict: dict[str, Any]) -> None:
        """Apply environment variable overrides to configuration dictionary.

        Modifies config_dict in place.

        Environment variables supported:
        - DISCORD_TOKEN: overrides services.discord.token
        - TAUTULLI_API_KEY: overrides services.tautulli.api_key
        - TAUTULLI_URL: overrides services.tautulli.url
        """
        # Override Discord token
        if discord_token := os.getenv("DISCORD_TOKEN"):
            if "services" not in config_dict:
                config_dict["services"] = {}
            services = config_dict["services"]
            if not isinstance(services, dict):
                return
            if "discord" not in services:
                services["discord"] = {}
            discord_config = services["discord"]
            if isinstance(discord_config, dict):
                discord_config["token"] = discord_token

        # Override Tautulli API key
        if tautulli_key := os.getenv("TAUTULLI_API_KEY"):
            if "services" not in config_dict:
                config_dict["services"] = {}
            services = config_dict["services"]
            if not isinstance(services, dict):
                return
            if "tautulli" not in services:
                services["tautulli"] = {}
            tautulli_config = services["tautulli"]
            if isinstance(tautulli_config, dict):
                tautulli_config["api_key"] = tautulli_key

        # Override Tautulli URL
        if tautulli_url := os.getenv("TAUTULLI_URL"):
            if "services" not in config_dict:
                config_dict["services"] = {}
            services = config_dict["services"]
            if not isinstance(services, dict):
                return
            if "tautulli" not in services:
                services["tautulli"] = {}
            tautulli_config = services["tautulli"]
            if isinstance(tautulli_config, dict):
                tautulli_config["url"] = tautulli_url

    def save(self, _config: BotConfig, _path: str) -> None:
        """Save configuration to YAML file.

        Args:
            _config: BotConfig instance to save
            _path: Path to save the YAML file

        Raises:
            ConfigurationError: If save fails
        """
        # Stub implementation - will be fully implemented in task 4
        raise NotImplementedError("Configuration saving will be implemented in task 4")
