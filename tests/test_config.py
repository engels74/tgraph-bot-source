"""Tests for configuration validation and loading.

This test suite validates the configuration system including:
- Pydantic model validation (ranges, types, patterns)
- YAML file loading (valid and invalid files)
- Environment variable overrides
- Configuration error messages
- Configuration reload functionality

Requirements tested: 3.2, 3.3, 3.4
"""

# pyright: reportArgumentType=false, reportUnusedCallResult=false

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tgraph_bot.config.models import (
    AnnotationConfig,
    AutomationConfig,
    BotConfig,
    CommandLimits,
    DataCollectionConfig,
    DiscordConfig,
    GraphColors,
    GraphDimensions,
    PrivacyConfig,
    SeabornConfig,
    SystemConfig,
    TautulliConfig,
)
from tgraph_bot.utils.errors import ConfigurationError


@pytest.fixture
def valid_tautulli_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid Tautulli configuration dictionary."""
    return {
        "api_key": "a" * 32,  # Min length 32
        "url": "https://tautulli.example.com",
    }


@pytest.fixture
def valid_discord_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid Discord configuration dictionary."""
    return {
        "token": "x" * 70,  # Discord tokens are ~70 chars
        "channel_id": 123456789012345678,  # Valid Discord channel ID
        "timestamp_format": "f",
        "ephemeral_message_delete_after": 30.0,
    }


@pytest.fixture
def valid_services_config_dict(
    valid_tautulli_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_discord_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid services configuration dictionary."""
    return {
        "tautulli": valid_tautulli_config_dict,
        "discord": valid_discord_config_dict,
    }


@pytest.fixture
def valid_automation_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid automation configuration dictionary."""
    return {
        "enabled": True,
        "update_interval_days": 7,
        "fixed_update_time": "12:00",
    }


@pytest.fixture
def valid_data_collection_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid data collection configuration dictionary."""
    return {
        "history_days": 30,
        "max_records_per_request": 1000,
    }


@pytest.fixture
def valid_privacy_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid privacy configuration dictionary."""
    return {
        "censor_usernames": False,
    }


@pytest.fixture
def valid_system_config_dict(
    valid_privacy_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid system configuration dictionary."""
    return {
        "language": "en",
        "log_level": "INFO",
        "output_directory": "./graphs",
        "keep_graphs_days": 7,
        "privacy": valid_privacy_config_dict,
    }


@pytest.fixture
def valid_graph_dimensions_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid graph dimensions dictionary."""
    return {
        "width": 12,
        "height": 8,
        "dpi": 100,
    }


@pytest.fixture
def valid_graph_colors_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid graph colors dictionary."""
    return {
        "tv": "#1f77b4",
        "movie": "#ff7f0e",
        "background": "#ffffff",
    }


@pytest.fixture
def valid_grid_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid grid configuration dictionary."""
    return {
        "enabled": True,
        "alpha": 0.3,
    }


@pytest.fixture
def valid_annotation_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid annotation configuration dictionary."""
    return {
        "color": "#000000",
        "outline_color": "#ffffff",
        "enable_outline": True,
        "font_size": 10,
    }


@pytest.fixture
def valid_seaborn_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid seaborn configuration dictionary."""
    return {
        "style": "darkgrid",
        "context": "notebook",
        "palette": "muted",
    }


@pytest.fixture
def valid_graph_appearance_config_dict(
    valid_graph_dimensions_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_graph_colors_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_grid_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_annotation_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_seaborn_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid graph appearance configuration dictionary."""
    return {
        "dimensions": valid_graph_dimensions_dict,
        "colors": valid_graph_colors_dict,
        "grid": valid_grid_config_dict,
        "annotations": valid_annotation_config_dict,
        "palettes": {},
        "seaborn": valid_seaborn_config_dict,
    }


@pytest.fixture
def valid_graph_config_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid individual graph configuration dictionary."""
    return {
        "enabled": True,
        "media_type_separation": True,
        "palette": "",
        "annotations_enabled": True,
        "peak_highlighting_enabled": False,
        "stacked": False,
    }


@pytest.fixture
def valid_graphs_config_dict(
    valid_graph_appearance_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_graph_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid graphs configuration dictionary."""
    return {
        "appearance": valid_graph_appearance_config_dict,
        "daily_play_count": valid_graph_config_dict,
        "play_count_by_day_of_week": valid_graph_config_dict,
        "play_count_by_hour_of_day": valid_graph_config_dict,
        "top_platforms": {**valid_graph_config_dict, "limit": 10},
        "top_users": {**valid_graph_config_dict, "limit": 10},
        "play_count_by_month": valid_graph_config_dict,
        "daily_play_count_by_stream_type": valid_graph_config_dict,
        "daily_concurrent_stream_count_by_stream_type": valid_graph_config_dict,
        "play_count_by_source_resolution": valid_graph_config_dict,
        "play_count_by_stream_resolution": valid_graph_config_dict,
        "play_count_by_platform_and_stream_type": valid_graph_config_dict,
        "play_count_by_user_and_stream_type": valid_graph_config_dict,
    }


@pytest.fixture
def valid_command_limits_dict() -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid command limits dictionary."""
    return {
        "user_cooldown_minutes": 5,
        "global_cooldown_seconds": 60,
    }


@pytest.fixture
def valid_rate_limiting_config_dict(
    valid_command_limits_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing valid rate limiting configuration dictionary."""
    return {
        "config": valid_command_limits_dict,
        "update_graphs": valid_command_limits_dict,
        "my_stats": valid_command_limits_dict,
    }


@pytest.fixture
def valid_full_config_dict(
    valid_services_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_automation_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_data_collection_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_system_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_graphs_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    valid_rate_limiting_config_dict: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Fixture providing complete valid configuration dictionary."""
    return {
        "services": valid_services_config_dict,
        "automation": valid_automation_config_dict,
        "data_collection": valid_data_collection_config_dict,
        "system": valid_system_config_dict,
        "graphs": valid_graphs_config_dict,
        "rate_limiting": valid_rate_limiting_config_dict,
    }


@pytest.fixture
def valid_yaml_config_file() -> str:
    """Fixture providing valid YAML configuration file content."""
    return """
services:
  tautulli:
    api_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    url: "https://tautulli.example.com"
  discord:
    token: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    channel_id: 123456789012345678
    timestamp_format: "f"
    ephemeral_message_delete_after: 30.0

automation:
  enabled: true
  update_interval_days: 7
  fixed_update_time: "12:00"

data_collection:
  history_days: 30
  max_records_per_request: 1000

system:
  language: "en"
  log_level: "INFO"
  output_directory: "./graphs"
  keep_graphs_days: 7
  privacy:
    censor_usernames: false

graphs:
  appearance:
    dimensions:
      width: 12
      height: 8
      dpi: 100
    colors:
      tv: "#1f77b4"
      movie: "#ff7f0e"
      background: "#ffffff"
    grid:
      enabled: true
      alpha: 0.3
    annotations:
      color: "#000000"
      outline_color: "#ffffff"
      enable_outline: true
      font_size: 10
    palettes: {}
    seaborn:
      style: "darkgrid"
      context: "notebook"
      palette: "muted"
  daily_play_count:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_day_of_week:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_hour_of_day:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  top_platforms:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
    limit: 10
  top_users:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
    limit: 10
  play_count_by_month:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  daily_play_count_by_stream_type:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  daily_concurrent_stream_count_by_stream_type:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_source_resolution:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_stream_resolution:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_platform_and_stream_type:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false
  play_count_by_user_and_stream_type:
    enabled: true
    media_type_separation: true
    palette: ""
    annotations_enabled: true
    peak_highlighting_enabled: false
    stacked: false

rate_limiting:
  config:
    user_cooldown_minutes: 5
    global_cooldown_seconds: 60
  update_graphs:
    user_cooldown_minutes: 5
    global_cooldown_seconds: 60
  my_stats:
    user_cooldown_minutes: 5
    global_cooldown_seconds: 60
"""


class TestTautulliConfig:
    """Tests for TautulliConfig Pydantic model validation."""

    def test_valid_tautulli_config(
        self, valid_tautulli_config_dict: dict[str, object]
    ) -> None:
        """Test creating TautulliConfig with valid values."""
        config = TautulliConfig(**valid_tautulli_config_dict)
        assert config.api_key == "a" * 32
        assert config.url == "https://tautulli.example.com"

    def test_tautulli_config_api_key_too_short(self) -> None:
        """Test TautulliConfig rejects API key shorter than 32 characters."""
        with pytest.raises(ValidationError) as exc_info:
            TautulliConfig(api_key="short", url="https://example.com")

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("api_key",) and "at least 32 characters" in error["msg"]
            for error in errors
        )

    def test_tautulli_config_invalid_url_format(self) -> None:
        """Test TautulliConfig rejects invalid URL format."""
        with pytest.raises(ValidationError) as exc_info:
            TautulliConfig(api_key="a" * 32, url="not-a-url")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("url",) for error in errors)

    def test_tautulli_config_missing_api_key(self) -> None:
        """Test TautulliConfig rejects missing api_key field."""
        with pytest.raises(ValidationError) as exc_info:
            TautulliConfig(url="https://example.com")  # pyright: ignore[reportCallIssue]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("api_key",) and error["type"] == "missing"
            for error in errors
        )

    def test_tautulli_config_missing_url(self) -> None:
        """Test TautulliConfig rejects missing url field."""
        with pytest.raises(ValidationError) as exc_info:
            TautulliConfig(api_key="a" * 32)  # pyright: ignore[reportCallIssue]

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("url",) and error["type"] == "missing"
            for error in errors
        )

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "http://192.168.1.1:8181",
            "https://tautulli.local:8080",
        ],
    )
    def test_tautulli_config_accepts_valid_urls(self, url: str) -> None:
        """Test TautulliConfig accepts various valid URL formats."""
        config = TautulliConfig(api_key="a" * 32, url=url)
        assert config.url == url


class TestDiscordConfig:
    """Tests for DiscordConfig Pydantic model validation."""

    def test_valid_discord_config(
        self, valid_discord_config_dict: dict[str, object]
    ) -> None:
        """Test creating DiscordConfig with valid values."""
        config = DiscordConfig(**valid_discord_config_dict)
        assert config.token == "x" * 70
        assert config.channel_id == 123456789012345678
        assert config.timestamp_format == "f"
        assert config.ephemeral_message_delete_after == 30.0

    def test_discord_config_token_too_short(self) -> None:
        """Test DiscordConfig rejects token shorter than 50 characters."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig(
                token="short",
                channel_id=123456789012345678,
                timestamp_format="f",
                ephemeral_message_delete_after=30.0,
            )

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("token",) and "at least 50 characters" in error["msg"]
            for error in errors
        )

    def test_discord_config_invalid_channel_id(self) -> None:
        """Test DiscordConfig rejects non-positive channel ID."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig(
                token="x" * 70,
                channel_id=0,  # Must be > 0
                timestamp_format="f",
                ephemeral_message_delete_after=30.0,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("channel_id",) for error in errors)

    @pytest.mark.parametrize(
        "invalid_format",
        ["x", "T1", "ff", "abc", ""],
    )
    def test_discord_config_invalid_timestamp_format(
        self, invalid_format: str
    ) -> None:
        """Test DiscordConfig rejects invalid timestamp format."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig(
                token="x" * 70,
                channel_id=123456789012345678,
                timestamp_format=invalid_format,
                ephemeral_message_delete_after=30.0,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp_format",) for error in errors)

    @pytest.mark.parametrize(
        "valid_format",
        ["t", "T", "d", "D", "f", "F", "R"],
    )
    def test_discord_config_accepts_valid_timestamp_formats(
        self, valid_format: str
    ) -> None:
        """Test DiscordConfig accepts all valid Discord timestamp formats."""
        config = DiscordConfig(
            token="x" * 70,
            channel_id=123456789012345678,
            timestamp_format=valid_format,
            ephemeral_message_delete_after=30.0,
        )
        assert config.timestamp_format == valid_format

    @pytest.mark.parametrize(
        "invalid_timeout",
        [0.0, 0.5, 3601.0, 5000.0],
    )
    def test_discord_config_invalid_delete_after_range(
        self, invalid_timeout: float
    ) -> None:
        """Test DiscordConfig rejects ephemeral_message_delete_after outside valid range."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig(
                token="x" * 70,
                channel_id=123456789012345678,
                timestamp_format="f",
                ephemeral_message_delete_after=invalid_timeout,
            )

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("ephemeral_message_delete_after",) for error in errors
        )

    def test_discord_config_missing_required_fields(self) -> None:
        """Test DiscordConfig rejects missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig()  # pyright: ignore[reportCallIssue]

        errors = exc_info.value.errors()
        missing_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert "token" in missing_fields
        assert "channel_id" in missing_fields


class TestAutomationConfig:
    """Tests for AutomationConfig Pydantic model validation."""

    def test_valid_automation_config(
        self, valid_automation_config_dict: dict[str, object]
    ) -> None:
        """Test creating AutomationConfig with valid values."""
        config = AutomationConfig(**valid_automation_config_dict)
        assert config.enabled is True
        assert config.update_interval_days == 7
        assert config.fixed_update_time == "12:00"

    @pytest.mark.parametrize(
        "invalid_interval",
        [0, -1, 366, 500],
    )
    def test_automation_config_invalid_update_interval(
        self, invalid_interval: int
    ) -> None:
        """Test AutomationConfig rejects update_interval_days outside 1-365 range."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationConfig(
                enabled=True,
                update_interval_days=invalid_interval,
                fixed_update_time="12:00",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("update_interval_days",) for error in errors)

    @pytest.mark.parametrize(
        "valid_time",
        ["00:00", "12:00", "23:59", "XX:XX"],
    )
    def test_automation_config_accepts_valid_times(self, valid_time: str) -> None:
        """Test AutomationConfig accepts valid time formats."""
        config = AutomationConfig(
            enabled=True, update_interval_days=7, fixed_update_time=valid_time
        )
        assert config.fixed_update_time == valid_time

    @pytest.mark.parametrize(
        "invalid_time",
        ["24:00", "12:60", "1:00", "12:", ":00", "abc", ""],
    )
    def test_automation_config_invalid_time_format(self, invalid_time: str) -> None:
        """Test AutomationConfig rejects invalid time formats."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationConfig(
                enabled=True,
                update_interval_days=7,
                fixed_update_time=invalid_time,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("fixed_update_time",) for error in errors)


class TestDataCollectionConfig:
    """Tests for DataCollectionConfig Pydantic model validation."""

    def test_valid_data_collection_config(
        self, valid_data_collection_config_dict: dict[str, object]
    ) -> None:
        """Test creating DataCollectionConfig with valid values."""
        config = DataCollectionConfig(**valid_data_collection_config_dict)
        assert config.history_days == 30
        assert config.max_records_per_request == 1000

    @pytest.mark.parametrize(
        "invalid_days",
        [0, -1, 366, 400],
    )
    def test_data_collection_config_invalid_history_days(
        self, invalid_days: int
    ) -> None:
        """Test DataCollectionConfig rejects history_days outside 1-365 range."""
        with pytest.raises(ValidationError) as exc_info:
            DataCollectionConfig(
                history_days=invalid_days, max_records_per_request=1000
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("history_days",) for error in errors)

    @pytest.mark.parametrize(
        "invalid_max",
        [0, 99, 10001, 20000],
    )
    def test_data_collection_config_invalid_max_records(
        self, invalid_max: int
    ) -> None:
        """Test DataCollectionConfig rejects max_records_per_request outside 100-10000 range."""
        with pytest.raises(ValidationError) as exc_info:
            DataCollectionConfig(history_days=30, max_records_per_request=invalid_max)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("max_records_per_request",) for error in errors)


class TestGraphDimensions:
    """Tests for GraphDimensions Pydantic model validation."""

    def test_valid_graph_dimensions(
        self, valid_graph_dimensions_dict: dict[str, object]
    ) -> None:
        """Test creating GraphDimensions with valid values."""
        config = GraphDimensions(**valid_graph_dimensions_dict)
        assert config.width == 12
        assert config.height == 8
        assert config.dpi == 100

    @pytest.mark.parametrize(
        "invalid_width",
        [5, 21, 0, -1, 100],
    )
    def test_graph_dimensions_invalid_width(self, invalid_width: int) -> None:
        """Test GraphDimensions rejects width outside 6-20 range."""
        with pytest.raises(ValidationError) as exc_info:
            GraphDimensions(width=invalid_width, height=8, dpi=100)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("width",) for error in errors)

    @pytest.mark.parametrize(
        "invalid_height",
        [3, 17, 0, -1, 50],
    )
    def test_graph_dimensions_invalid_height(self, invalid_height: int) -> None:
        """Test GraphDimensions rejects height outside 4-16 range."""
        with pytest.raises(ValidationError) as exc_info:
            GraphDimensions(width=12, height=invalid_height, dpi=100)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("height",) for error in errors)

    @pytest.mark.parametrize(
        "invalid_dpi",
        [71, 301, 0, -1, 500],
    )
    def test_graph_dimensions_invalid_dpi(self, invalid_dpi: int) -> None:
        """Test GraphDimensions rejects dpi outside 72-300 range."""
        with pytest.raises(ValidationError) as exc_info:
            GraphDimensions(width=12, height=8, dpi=invalid_dpi)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("dpi",) for error in errors)


class TestGraphColors:
    """Tests for GraphColors Pydantic model validation."""

    def test_valid_graph_colors(
        self, valid_graph_colors_dict: dict[str, object]
    ) -> None:
        """Test creating GraphColors with valid hex values."""
        config = GraphColors(**valid_graph_colors_dict)
        assert config.tv == "#1f77b4"
        assert config.movie == "#ff7f0e"
        assert config.background == "#ffffff"

    @pytest.mark.parametrize(
        "invalid_color",
        ["#fff", "#gggggg", "1f77b4", "#1f77b", "#1f77b4x", "rgb(31,119,180)", ""],
    )
    def test_graph_colors_invalid_hex_format(self, invalid_color: str) -> None:
        """Test GraphColors rejects invalid hex color formats."""
        with pytest.raises(ValidationError) as exc_info:
            GraphColors(tv=invalid_color, movie="#ff7f0e", background="#ffffff")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tv",) for error in errors)

    def test_graph_colors_case_insensitive_hex(self) -> None:
        """Test GraphColors accepts both uppercase and lowercase hex values."""
        config1 = GraphColors(tv="#AABBCC", movie="#DDEEFF", background="#112233")
        config2 = GraphColors(tv="#aabbcc", movie="#ddeeff", background="#112233")
        assert config1.tv == "#AABBCC"
        assert config2.tv == "#aabbcc"


class TestAnnotationConfig:
    """Tests for AnnotationConfig Pydantic model validation."""

    def test_valid_annotation_config(
        self, valid_annotation_config_dict: dict[str, object]
    ) -> None:
        """Test creating AnnotationConfig with valid values."""
        config = AnnotationConfig(**valid_annotation_config_dict)
        assert config.color == "#000000"
        assert config.outline_color == "#ffffff"
        assert config.enable_outline is True
        assert config.font_size == 10

    @pytest.mark.parametrize(
        "invalid_size",
        [5, 25, 0, -1, 100],
    )
    def test_annotation_config_invalid_font_size(self, invalid_size: int) -> None:
        """Test AnnotationConfig rejects font_size outside 6-24 range."""
        with pytest.raises(ValidationError) as exc_info:
            AnnotationConfig(
                color="#000000",
                outline_color="#ffffff",
                enable_outline=True,
                font_size=invalid_size,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("font_size",) for error in errors)


class TestSeabornConfig:
    """Tests for SeabornConfig Pydantic model validation."""

    def test_valid_seaborn_config(
        self, valid_seaborn_config_dict: dict[str, object]
    ) -> None:
        """Test creating SeabornConfig with valid values."""
        config = SeabornConfig(**valid_seaborn_config_dict)
        assert config.style == "darkgrid"
        assert config.context == "notebook"
        assert config.palette == "muted"

    @pytest.mark.parametrize(
        "valid_style",
        ["whitegrid", "darkgrid", "white", "dark", "ticks"],
    )
    def test_seaborn_config_accepts_valid_styles(self, valid_style: str) -> None:
        """Test SeabornConfig accepts all valid seaborn styles."""
        config = SeabornConfig(
            style=valid_style, context="notebook", palette="muted"
        )
        assert config.style == valid_style

    @pytest.mark.parametrize(
        "invalid_style",
        ["grid", "light", "custom", ""],
    )
    def test_seaborn_config_rejects_invalid_styles(self, invalid_style: str) -> None:
        """Test SeabornConfig rejects invalid style values."""
        with pytest.raises(ValidationError) as exc_info:
            SeabornConfig(style=invalid_style, context="notebook", palette="muted")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("style",) for error in errors)

    @pytest.mark.parametrize(
        "valid_context",
        ["paper", "notebook", "talk", "poster"],
    )
    def test_seaborn_config_accepts_valid_contexts(self, valid_context: str) -> None:
        """Test SeabornConfig accepts all valid seaborn contexts."""
        config = SeabornConfig(
            style="darkgrid", context=valid_context, palette="muted"
        )
        assert config.context == valid_context


class TestCommandLimits:
    """Tests for CommandLimits Pydantic model validation."""

    def test_valid_command_limits(
        self, valid_command_limits_dict: dict[str, object]
    ) -> None:
        """Test creating CommandLimits with valid values."""
        config = CommandLimits(**valid_command_limits_dict)
        assert config.user_cooldown_minutes == 5
        assert config.global_cooldown_seconds == 60

    @pytest.mark.parametrize(
        "invalid_minutes",
        [-1, 1441, 2000],
    )
    def test_command_limits_invalid_user_cooldown(self, invalid_minutes: int) -> None:
        """Test CommandLimits rejects user_cooldown_minutes outside 0-1440 range."""
        with pytest.raises(ValidationError) as exc_info:
            CommandLimits(
                user_cooldown_minutes=invalid_minutes, global_cooldown_seconds=60
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_cooldown_minutes",) for error in errors)

    @pytest.mark.parametrize(
        "invalid_seconds",
        [-1, 86401, 100000],
    )
    def test_command_limits_invalid_global_cooldown(
        self, invalid_seconds: int
    ) -> None:
        """Test CommandLimits rejects global_cooldown_seconds outside 0-86400 range."""
        with pytest.raises(ValidationError) as exc_info:
            CommandLimits(
                user_cooldown_minutes=5, global_cooldown_seconds=invalid_seconds
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("global_cooldown_seconds",) for error in errors)

    def test_command_limits_zero_cooldown_allowed(self) -> None:
        """Test CommandLimits accepts 0 to disable cooldowns."""
        config = CommandLimits(user_cooldown_minutes=0, global_cooldown_seconds=0)
        assert config.user_cooldown_minutes == 0
        assert config.global_cooldown_seconds == 0


class TestSystemConfig:
    """Tests for SystemConfig Pydantic model validation."""

    def test_valid_system_config(
        self, valid_system_config_dict: dict[str, object]
    ) -> None:
        """Test creating SystemConfig with valid values."""
        config = SystemConfig(**valid_system_config_dict)
        assert config.language == "en"
        assert config.log_level == "INFO"
        assert config.output_directory == "./graphs"
        assert config.keep_graphs_days == 7

    @pytest.mark.parametrize(
        "valid_log_level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_system_config_accepts_valid_log_levels(
        self, valid_log_level: str
    ) -> None:
        """Test SystemConfig accepts all valid log levels."""
        config = SystemConfig(
            language="en",
            log_level=valid_log_level,
            output_directory="./graphs",
            keep_graphs_days=7,
            privacy=PrivacyConfig(censor_usernames=False),
        )
        assert config.log_level == valid_log_level

    @pytest.mark.parametrize(
        "invalid_days",
        [0, -1, 366, 400],
    )
    def test_system_config_invalid_keep_graphs_days(self, invalid_days: int) -> None:
        """Test SystemConfig rejects keep_graphs_days outside 1-365 range."""
        with pytest.raises(ValidationError) as exc_info:
            SystemConfig(
                language="en",
                log_level="INFO",
                output_directory="./graphs",
                keep_graphs_days=invalid_days,
                privacy=PrivacyConfig(censor_usernames=False),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("keep_graphs_days",) for error in errors)


class TestBotConfigIntegration:
    """Integration tests for full BotConfig validation."""

    def test_valid_full_bot_config(
        self, valid_full_config_dict: dict[str, object]
    ) -> None:
        """Test creating complete BotConfig with all valid values."""
        config = BotConfig(**valid_full_config_dict)
        assert config.services.tautulli.api_key == "a" * 32
        assert config.services.discord.channel_id == 123456789012345678
        assert config.automation.update_interval_days == 7
        assert config.data_collection.history_days == 30
        assert config.system.language == "en"
        assert config.graphs.appearance.dimensions.width == 12

    def test_bot_config_missing_services_section(self) -> None:
        """Test BotConfig rejects missing services section."""
        with pytest.raises(ValidationError) as exc_info:
            BotConfig(  # pyright: ignore[reportCallIssue]
                automation=AutomationConfig(
                    enabled=True, update_interval_days=7, fixed_update_time="12:00"
                ),
                data_collection=DataCollectionConfig(
                    history_days=30, max_records_per_request=1000
                ),
                system=SystemConfig(
                    language="en",
                    log_level="INFO",
                    output_directory="./graphs",
                    keep_graphs_days=7,
                    privacy=PrivacyConfig(censor_usernames=False),
                ),
                graphs={},
                rate_limiting={},
            )

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("services",) and error["type"] == "missing"
            for error in errors
        )

    def test_bot_config_invalid_nested_value(
        self, valid_full_config_dict: dict[str, object]
    ) -> None:
        """Test BotConfig validation catches nested invalid values."""
        # Modify nested value to be invalid
        invalid_config = valid_full_config_dict.copy()
        assert isinstance(invalid_config["graphs"], dict)
        assert isinstance(invalid_config["graphs"]["appearance"], dict)
        assert isinstance(invalid_config["graphs"]["appearance"]["dimensions"], dict)
        invalid_config["graphs"]["appearance"]["dimensions"]["width"] = 100  # > 20

        with pytest.raises(ValidationError) as exc_info:
            BotConfig(**invalid_config)

        errors = exc_info.value.errors()
        assert any(
            "width" in str(error["loc"])  for error in errors
        )


class TestYAMLConfigLoading:
    """Tests for YAML configuration file loading.

    These tests verify the ConfigLoader can properly load and validate
    YAML configuration files.
    """

    def test_load_valid_yaml_file(self, valid_yaml_config_file: str) -> None:
        """Test loading a valid YAML configuration file."""
        from tgraph_bot.config.loader import ConfigLoader

        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_yaml_config_file)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            config = loader.load(temp_path)

            assert isinstance(config, BotConfig)
            assert config.services.tautulli.url == "https://tautulli.example.com"
            assert config.automation.enabled is True
            assert config.system.language == "en"
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_yaml_syntax(self) -> None:
        """Test ConfigLoader raises error for invalid YAML syntax."""
        from tgraph_bot.config.loader import ConfigLoader

        invalid_yaml = """
services:
  tautulli:
    api_key: "test"
  discord: [this is invalid yaml
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError) as exc_info:
                loader.load(temp_path)

            # Should mention YAML parsing error
            assert "YAML" in str(exc_info.value) or "parse" in str(
                exc_info.value
            ).lower()
        finally:
            Path(temp_path).unlink()

    def test_load_missing_required_field(self) -> None:
        """Test ConfigLoader raises error for missing required field."""
        from tgraph_bot.config.loader import ConfigLoader

        # Missing discord section
        incomplete_yaml = """
services:
  tautulli:
    api_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    url: "https://tautulli.example.com"
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(incomplete_yaml)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            with pytest.raises((ConfigurationError, ValidationError)):
                loader.load(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_field_value(self) -> None:
        """Test ConfigLoader raises error for field value outside valid range."""
        from tgraph_bot.config.loader import ConfigLoader

        # update_interval_days = 500 (> 365 max)
        invalid_yaml = """
services:
  tautulli:
    api_key: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    url: "https://tautulli.example.com"
  discord:
    token: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    channel_id: 123456789012345678
    timestamp_format: "f"
    ephemeral_message_delete_after: 30.0

automation:
  enabled: true
  update_interval_days: 500
  fixed_update_time: "12:00"

data_collection:
  history_days: 30
  max_records_per_request: 1000

system:
  language: "en"
  log_level: "INFO"
  output_directory: "./graphs"
  keep_graphs_days: 7
  privacy:
    censor_usernames: false

graphs: {}
rate_limiting: {}
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            loader = ConfigLoader()
            with pytest.raises((ConfigurationError, ValidationError)):
                loader.load(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self) -> None:
        """Test ConfigLoader raises error for nonexistent file."""
        from tgraph_bot.config.loader import ConfigLoader

        loader = ConfigLoader()
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load("/nonexistent/path/to/config.yaml")

        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(
            exc_info.value
        ).lower()


class TestEnvironmentVariableOverrides:
    """Tests for environment variable override functionality.

    These tests verify that sensitive configuration values can be
    overridden via environment variables.
    """

    def test_override_discord_token_from_env(
        self, valid_yaml_config_file: str
    ) -> None:
        """Test Discord token can be overridden via DISCORD_TOKEN env var."""
        from tgraph_bot.config.loader import ConfigLoader

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_yaml_config_file)
            temp_path = f.name

        try:
            # Set environment variable
            os.environ["DISCORD_TOKEN"] = "z" * 70

            loader = ConfigLoader()
            config = loader.load(temp_path)

            # Should use env var value, not YAML value
            assert config.services.discord.token == "z" * 70
        finally:
            # Clean up
            Path(temp_path).unlink()
            if "DISCORD_TOKEN" in os.environ:
                del os.environ["DISCORD_TOKEN"]

    def test_override_tautulli_api_key_from_env(
        self, valid_yaml_config_file: str
    ) -> None:
        """Test Tautulli API key can be overridden via TAUTULLI_API_KEY env var."""
        from tgraph_bot.config.loader import ConfigLoader

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_yaml_config_file)
            temp_path = f.name

        try:
            # Set environment variable
            os.environ["TAUTULLI_API_KEY"] = "b" * 32

            loader = ConfigLoader()
            config = loader.load(temp_path)

            # Should use env var value, not YAML value
            assert config.services.tautulli.api_key == "b" * 32
        finally:
            # Clean up
            Path(temp_path).unlink()
            if "TAUTULLI_API_KEY" in os.environ:
                del os.environ["TAUTULLI_API_KEY"]

    def test_override_tautulli_url_from_env(
        self, valid_yaml_config_file: str
    ) -> None:
        """Test Tautulli URL can be overridden via TAUTULLI_URL env var."""
        from tgraph_bot.config.loader import ConfigLoader

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_yaml_config_file)
            temp_path = f.name

        try:
            # Set environment variable
            os.environ["TAUTULLI_URL"] = "https://override.example.com"

            loader = ConfigLoader()
            config = loader.load(temp_path)

            # Should use env var value, not YAML value
            assert config.services.tautulli.url == "https://override.example.com"
        finally:
            # Clean up
            Path(temp_path).unlink()
            if "TAUTULLI_URL" in os.environ:
                del os.environ["TAUTULLI_URL"]

    def test_multiple_env_overrides(self, valid_yaml_config_file: str) -> None:
        """Test multiple environment variables can override config simultaneously."""
        from tgraph_bot.config.loader import ConfigLoader

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(valid_yaml_config_file)
            temp_path = f.name

        try:
            # Set multiple environment variables
            os.environ["DISCORD_TOKEN"] = "y" * 70
            os.environ["TAUTULLI_API_KEY"] = "c" * 32
            os.environ["TAUTULLI_URL"] = "https://multi.example.com"

            loader = ConfigLoader()
            config = loader.load(temp_path)

            # All should use env var values
            assert config.services.discord.token == "y" * 70
            assert config.services.tautulli.api_key == "c" * 32
            assert config.services.tautulli.url == "https://multi.example.com"
        finally:
            # Clean up
            Path(temp_path).unlink()
            for key in ["DISCORD_TOKEN", "TAUTULLI_API_KEY", "TAUTULLI_URL"]:
                if key in os.environ:
                    del os.environ[key]


class TestConfigurationErrorMessages:
    """Tests for configuration error message clarity and helpfulness.

    These tests verify that validation errors provide clear,
    actionable error messages with field names and expected values.
    """

    def test_error_message_includes_field_name(self) -> None:
        """Test validation error message includes the field name."""
        with pytest.raises(ValidationError) as exc_info:
            GraphDimensions(width=100, height=8, dpi=100)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("width",) for error in errors)
        # The error message should reference the field
        error_str = str(exc_info.value)
        assert "width" in error_str.lower()

    def test_error_message_includes_expected_range(self) -> None:
        """Test validation error message includes expected value range."""
        with pytest.raises(ValidationError) as exc_info:
            AutomationConfig(
                enabled=True, update_interval_days=500, fixed_update_time="12:00"
            )

        errors = exc_info.value.errors()
        error_msg = str(errors[0]["msg"])
        # Should mention the valid range or constraint
        assert any(
            keyword in error_msg.lower()
            for keyword in ["less", "equal", "365", "range", "maximum"]
        )

    def test_configuration_error_with_field_name_and_expected(self) -> None:
        """Test ConfigurationError can include field name and expected value."""
        error = ConfigurationError(
            "Invalid port number",
            field_name="services.discord.port",
            expected_value="1-65535",
        )

        assert error.field_name == "services.discord.port"
        assert error.expected_value == "1-65535"
        assert "Invalid port number" in str(error)

    def test_missing_field_error_message(self) -> None:
        """Test error message for missing required field is clear."""
        with pytest.raises(ValidationError) as exc_info:
            TautulliConfig(url="https://example.com")  # pyright: ignore[reportCallIssue]

        errors = exc_info.value.errors()
        missing_error = next(
            error for error in errors if error["type"] == "missing"
        )
        assert missing_error["loc"] == ("api_key",)
        assert "required" in missing_error["msg"].lower()

    def test_type_error_message(self) -> None:
        """Test error message for wrong type is clear."""
        with pytest.raises(ValidationError) as exc_info:
            DiscordConfig(
                token="x" * 70,
                channel_id="not_an_int",  # type: ignore
                timestamp_format="f",
                ephemeral_message_delete_after=30.0,
            )

        errors = exc_info.value.errors()
        # Should indicate type validation issue
        assert any(
            "int" in error["msg"].lower() or error["type"] == "int_parsing"
            for error in errors
        )
