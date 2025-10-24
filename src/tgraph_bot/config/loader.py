"""Configuration loader for YAML files with environment variable overrides.

This module handles loading and saving configuration from YAML files,
with support for environment variable overrides for sensitive values.
"""

import os
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from tgraph_bot.config.models import BotConfig
from tgraph_bot.utils.errors import ConfigurationError

# Type aliases using PEP 695 syntax
type ValidationErrors = list[str]
type ConfigDict = dict[str, object]


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
                config_data: object = yaml_parser.load(f)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]  # ruamel.yaml incomplete stubs

            if not isinstance(config_data, dict):
                raise ConfigurationError(
                    "Configuration file must contain a YAML dictionary",
                    field_name="config_file",
                )

            # Type is now confirmed to be dict[str, object]
            config_dict: dict[str, object] = config_data  # pyright: ignore[reportUnknownVariableType]

            # Apply environment variable overrides
            self._apply_env_overrides(config_dict)

            # Validate with Pydantic
            config = BotConfig(**config_dict)  # pyright: ignore[reportArgumentType]
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

    def _apply_env_overrides(self, config_dict: dict[str, object]) -> None:
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
            discord_config = services["discord"]  # pyright: ignore[reportUnknownVariableType]
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
            tautulli_config = services["tautulli"]  # pyright: ignore[reportUnknownVariableType]
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
            tautulli_config = services["tautulli"]  # pyright: ignore[reportUnknownVariableType]
            if isinstance(tautulli_config, dict):
                tautulli_config["url"] = tautulli_url

    def save(self, config: BotConfig, path: str) -> None:
        """Save configuration to YAML file while preserving comments and formatting.

        Args:
            config: BotConfig instance to save
            path: Path to save the YAML file

        Raises:
            ConfigurationError: If save fails
        """
        file_path = Path(path)

        try:
            # Initialize YAML with round-trip mode for format preservation
            yaml_writer = YAML()
            yaml_writer.preserve_quotes = True
            yaml_writer.default_flow_style = False
            # Set indentation for clean formatting
            yaml_writer.indent(mapping=2, sequence=2, offset=0)  # pyright: ignore[reportUnknownMemberType]  # ruamel.yaml incomplete stubs

            # Load existing YAML to preserve comments and structure
            yaml_data: dict[str, object]
            if file_path.exists():
                with open(file_path) as f:
                    loaded_data: object = yaml_writer.load(f)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]  # ruamel.yaml incomplete stubs
                if isinstance(loaded_data, dict):
                    yaml_data = loaded_data  # pyright: ignore[reportUnknownVariableType]
                else:
                    yaml_data = {}
            else:
                yaml_data = {}

            # Convert Pydantic model to dictionary
            updated_data = config.model_dump()

            # Merge updated values while preserving structure
            self._merge_preserving_structure(yaml_data, updated_data)

            # Write back to file
            with open(file_path, "w") as f:
                yaml_writer.dump(yaml_data, f)  # pyright: ignore[reportUnknownMemberType]  # ruamel.yaml incomplete stubs

        except OSError as e:
            raise ConfigurationError(
                f"Failed to save configuration file: {e}",
                field_name="config_file",
                expected_value="writable file path",
            ) from e
        except YAMLError as e:
            raise ConfigurationError(
                f"Failed to write YAML configuration: {e}",
                field_name="config_file",
                expected_value="valid YAML structure",
            ) from e

    def _merge_preserving_structure(
        self, target: ConfigDict, source: ConfigDict
    ) -> None:
        """Merge source dictionary into target while preserving target's structure.

        This method updates values in target with values from source,
        preserving any comments and formatting in the target.

        Args:
            target: Target dictionary to update (modified in place)
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if (
                isinstance(value, dict)
                and key in target
                and isinstance(target[key], dict)
            ):
                # Recursively merge nested dictionaries
                self._merge_preserving_structure(target[key], value)  # pyright: ignore[reportArgumentType, reportUnknownArgumentType]
            else:
                # Update or add the value
                target[key] = value

    def validate(self, config: BotConfig) -> ValidationErrors:
        """Validate configuration and return list of error messages.

        Args:
            config: BotConfig instance to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        try:
            # Pydantic validation happens during model construction
            # Re-validate by converting to dict and back
            config_dict = config.model_dump()
            _ = BotConfig(**config_dict)  # pyright: ignore[reportAny]
        except ValidationError as e:
            # Extract error messages
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                error_msg = f"{field_path}: {error['msg']}"
                errors.append(error_msg)

        return errors
