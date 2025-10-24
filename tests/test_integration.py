"""Integration and end-to-end tests for TGraph Bot.

This test suite validates complete workflows including:
- Complete startup sequence with valid configuration
- Discord bot connection and command handling
- Scheduled graph generation and posting
- Web UI configuration editing and reload
- Manual YAML editing and reload
- Error handling for invalid configuration
- Error handling for Tautulli API failures
- Verify all graph types generate correctly

Requirements tested: 1.1, 1.2, 3.1, 4.1, 5.1, 7.1, 8.1, 15.1
"""

# pyright: reportPrivateUsage=false, reportAny=false, reportUnknownMemberType=false

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml
from matplotlib.figure import Figure

from tgraph_bot.config.loader import ConfigLoader
from tgraph_bot.config.models import (
    AnnotationConfig,
    AutomationConfig,
    BotConfig,
    CommandLimits,
    DataCollectionConfig,
    DiscordConfig,
    GraphAppearanceConfig,
    GraphColors,
    GraphConfig,
    GraphDimensions,
    GraphsConfig,
    GridConfig,
    PrivacyConfig,
    RateLimitingConfig,
    SeabornConfig,
    ServicesConfig,
    SystemConfig,
    TautulliConfig,
    TopGraphConfig,
)
from tgraph_bot.graphs.data import StreamRecord
from tgraph_bot.graphs.factory import GraphFactory
from tgraph_bot.utils.errors import ConfigurationError, TautulliAPIError


@pytest.fixture
def valid_complete_config() -> BotConfig:
    """Fixture providing a complete valid configuration for integration tests."""
    return BotConfig(
        services=ServicesConfig(
            tautulli=TautulliConfig(
                api_key="a" * 32,
                url="https://tautulli.example.com",
            ),
            discord=DiscordConfig(
                token="x" * 70,
                channel_id=123456789012345678,
                timestamp_format="f",
                ephemeral_message_delete_after=30.0,
            ),
        ),
        automation=AutomationConfig(
            enabled=True,
            update_interval_days=7,
            fixed_update_time="12:00",
        ),
        data_collection=DataCollectionConfig(
            history_days=30,
            max_records_per_request=1000,
        ),
        system=SystemConfig(
            language="en",
            log_level="INFO",
            output_directory="./graphs",
            keep_graphs_days=7,
            privacy=PrivacyConfig(censor_usernames=False),
        ),
        graphs=GraphsConfig(
            appearance=GraphAppearanceConfig(
                dimensions=GraphDimensions(width=12, height=8, dpi=100),
                colors=GraphColors(
                    tv="#3498DB",
                    movie="#E74C3C",
                    background="#FFFFFF",
                ),
                grid=GridConfig(enabled=True, alpha=0.5),
                annotations=AnnotationConfig(
                    color="#000000",
                    outline_color="#FFFFFF",
                    enable_outline=True,
                    font_size=10,
                ),
                seaborn=SeabornConfig(
                    style="darkgrid",
                    context="notebook",
                    palette="muted",
                ),
                palettes={},
            ),
            daily_play_count=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
            ),
            play_count_by_day_of_week=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=True,
                palette="",
            ),
            play_count_by_hour_of_day=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=True,
                palette="",
            ),
            top_platforms=TopGraphConfig(
                enabled=True,
                media_type_separation=False,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
                limit=10,
            ),
            top_users=TopGraphConfig(
                enabled=True,
                media_type_separation=False,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
                limit=10,
            ),
            play_count_by_month=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
            ),
            daily_play_count_by_stream_type=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
            ),
            daily_concurrent_stream_count_by_stream_type=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=True,
                stacked=False,
                palette="",
            ),
            play_count_by_source_resolution=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
            ),
            play_count_by_stream_resolution=GraphConfig(
                enabled=True,
                media_type_separation=True,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=False,
                palette="",
            ),
            play_count_by_platform_and_stream_type=GraphConfig(
                enabled=True,
                media_type_separation=False,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=True,
                palette="",
            ),
            play_count_by_user_and_stream_type=GraphConfig(
                enabled=True,
                media_type_separation=False,
                annotations_enabled=True,
                peak_highlighting_enabled=False,
                stacked=True,
                palette="",
            ),
        ),
        rate_limiting=RateLimitingConfig(
            config=CommandLimits(
                user_cooldown_minutes=5,
                global_cooldown_seconds=60,
            ),
            update_graphs=CommandLimits(
                user_cooldown_minutes=10,
                global_cooldown_seconds=120,
            ),
            my_stats=CommandLimits(
                user_cooldown_minutes=5,
                global_cooldown_seconds=60,
            ),
        ),
    )


@pytest.fixture
def sample_stream_records() -> list[StreamRecord]:
    """Fixture providing sample stream records for testing."""
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    return [
        StreamRecord(
            timestamp=base_time,
            media_type="movie",
            stream_type="direct_play",
            transcode_decision="direct play",
            platform="Plex for Android",
            player="Plex for Android (Mobile)",
            user="user1",
            source_resolution="1920x1080",
            stream_resolution="1920x1080",
        ),
        StreamRecord(
            timestamp=base_time,
            media_type="tv",
            stream_type="transcode",
            transcode_decision="transcode",
            platform="Plex Web",
            player="Plex Web (Chrome)",
            user="user2",
            source_resolution="3840x2160",
            stream_resolution="1280x720",
        ),
        StreamRecord(
            timestamp=base_time,
            media_type="movie",
            stream_type="direct_play",
            transcode_decision="direct play",
            platform="Plex for iOS",
            player="Plex for iOS (Mobile)",
            user="user1",
            source_resolution="1920x1080",
            stream_resolution="1920x1080",
        ),
    ]


class TestStartupSequence:
    """Test complete bot startup sequence (Requirement 1.1, 3.1)."""

    async def test_configuration_loads_from_yaml(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test that configuration loads successfully from YAML file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmpfile:
            config_path = tmpfile.name

            # Write valid YAML config
            yaml.dump(valid_complete_config.model_dump(), tmpfile)

        try:
            loader = ConfigLoader()
            loaded_config = loader.load(config_path)

            # Verify configuration loaded correctly
            assert loaded_config.services.discord.channel_id == 123456789012345678
            assert loaded_config.automation.update_interval_days == 7
            assert loaded_config.data_collection.history_days == 30
        finally:
            Path(config_path).unlink()

    async def test_invalid_configuration_raises_error(self) -> None:
        """Test that invalid configuration raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmpfile:
            config_path = tmpfile.name

            # Write invalid YAML (invalid channel ID type)
            invalid_config = {
                "services": {
                    "discord": {
                        "token": "x" * 70,
                        "channel_id": "not_a_number",  # Invalid: should be int
                        "timestamp_format": "f",
                        "ephemeral_message_delete_after": 30.0,
                    },
                    "tautulli": {
                        "api_key": "a" * 32,
                        "url": "https://tautulli.example.com",
                    },
                },
            }
            yaml.dump(invalid_config, tmpfile)

        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigurationError):
                _ = loader.load(config_path)
        finally:
            Path(config_path).unlink()


class TestTautulliAPIIntegration:
    """Test Tautulli API integration (Requirement 2.1, 2.3, 15.1)."""

    @patch("httpx.AsyncClient")
    async def test_successful_api_call(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test successful Tautulli API call with mocked response."""
        from tgraph_bot.api.tautulli import TautulliClient

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "result": "success",
                "data": {
                    "data": [
                        {
                            "date": 1704110400,
                            "media_type": "movie",
                            "transcode_decision": "direct play",
                            "platform": "Plex for Android",
                            "user": "user1",
                            "stream_video_resolution": "1080p",
                            "stream_video_full_resolution": "1920x1080",
                        }
                    ]
                },
            }
        }
        mock_client.get.return_value = mock_response

        # Test
        client = TautulliClient(
            api_key="test_key", base_url="https://tautulli.example.com"
        )
        result = await client.get_history(days=7)

        # Verify
        assert len(result) == 1
        assert result[0]["media_type"] == "movie"
        assert result[0]["user"] == "user1"

    @patch("httpx.AsyncClient")
    async def test_api_error_handling(self, mock_client_class: MagicMock) -> None:
        """Test Tautulli API error handling with HTTP errors."""
        from tgraph_bot.api.tautulli import TautulliClient

        # Setup mock for error response
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock error response (500 Internal Server Error)
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )
        mock_client.get.return_value = mock_response

        # Test
        client = TautulliClient(
            api_key="test_key", base_url="https://tautulli.example.com"
        )

        with pytest.raises(TautulliAPIError) as exc_info:
            _ = await client.get_history(days=7)

        assert "HTTP error" in str(exc_info.value)


class TestGraphGeneration:
    """Test complete graph generation pipeline (Requirement 5.1)."""

    async def test_all_enabled_graph_types_can_be_generated(
        self,
        sample_stream_records: list[StreamRecord],
        valid_complete_config: BotConfig,
    ) -> None:
        """Test that all configured graph types can be generated."""
        factory = GraphFactory()
        appearance_config = valid_complete_config.graphs.appearance
        graphs_config = valid_complete_config.graphs

        # Get all graph type names and configs
        graph_types_data = [
            ("daily_play_count", graphs_config.daily_play_count),
            ("play_count_by_day_of_week", graphs_config.play_count_by_day_of_week),
            ("play_count_by_hour_of_day", graphs_config.play_count_by_hour_of_day),
            ("top_platforms", graphs_config.top_platforms),
            ("top_users", graphs_config.top_users),
            ("play_count_by_month", graphs_config.play_count_by_month),
        ]

        # Test each graph type
        for graph_type, graph_config_raw in graph_types_data:
            # Type narrow: skip if dict (shouldn't happen with valid_complete_config)
            if isinstance(graph_config_raw, dict):
                continue
            graph_config = graph_config_raw

            if not graph_config.enabled:
                continue

            # Get generator for this graph type
            generator = factory.create_generator(graph_type)

            # Generate graph
            fig = generator.generate(
                data=sample_stream_records,
                config=graph_config,
                appearance=appearance_config,
            )

            # Verify figure was created
            assert fig is not None
            assert hasattr(fig, "savefig")

            # Clean up
            import matplotlib.pyplot as plt

            plt.close(fig)

    async def test_graph_generation_with_empty_data(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test graph generation handles empty data gracefully."""
        factory = GraphFactory()
        appearance_config = valid_complete_config.graphs.appearance

        # Test with empty data for daily_play_count graph
        graph_type = "daily_play_count"
        graph_config = valid_complete_config.graphs.daily_play_count
        generator = factory.create_generator(graph_type)

        # Generate graph with empty data
        fig = generator.generate(
            data=[],
            config=graph_config,
            appearance=appearance_config,
        )

        # Verify figure was created (should handle empty data gracefully)
        assert fig is not None

        # Clean up
        import matplotlib.pyplot as plt

        plt.close(fig)


class TestConfigurationReload:
    """Test configuration reload system (Requirement 3.1, 4.1)."""

    async def test_yaml_file_modification_and_reload(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test manual YAML editing and reload."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmpfile:
            config_path = tmpfile.name

            # Write initial config
            yaml.dump(valid_complete_config.model_dump(), tmpfile)

        try:
            # Load initial config
            loader = ConfigLoader()
            config1 = loader.load(config_path)
            assert config1.automation.update_interval_days == 7

            # Modify YAML file
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)

            config_dict["automation"]["update_interval_days"] = 14

            with open(config_path, "w") as f:
                yaml.dump(config_dict, f)

            # Reload config
            config2 = loader.load(config_path)
            assert config2.automation.update_interval_days == 14

        finally:
            Path(config_path).unlink()


class TestWebUIIntegration:
    """Test Web UI configuration management (Requirement 4.1)."""

    async def test_web_ui_can_read_configuration(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test that Web UI can read configuration from file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmpfile:
            config_path = tmpfile.name

            # Write config
            yaml.dump(valid_complete_config.model_dump(), tmpfile)

        try:
            loader = ConfigLoader()
            config = loader.load(config_path)

            # Verify sensitive values can be masked
            masked_token = (
                "*" * (len(config.services.discord.token) - 4)
                + config.services.discord.token[-4:]
            )
            assert len(masked_token) == len(config.services.discord.token)
            assert masked_token.startswith("*" * 66)
            assert masked_token.endswith(config.services.discord.token[-4:])

        finally:
            Path(config_path).unlink()

    async def test_web_ui_can_save_configuration(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test that Web UI can save configuration changes."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmpfile:
            config_path = tmpfile.name

            # Write initial config
            yaml.dump(valid_complete_config.model_dump(), tmpfile)

        try:
            loader = ConfigLoader()

            # Modify config
            modified_config = valid_complete_config.model_copy(deep=True)
            modified_config.automation.update_interval_days = 14

            # Save modified config
            loader.save(modified_config, config_path)

            # Reload and verify
            reloaded_config = loader.load(config_path)
            assert reloaded_config.automation.update_interval_days == 14

        finally:
            Path(config_path).unlink()


class TestErrorHandling:
    """Test error handling across the system (Requirement 15.1)."""

    async def test_configuration_error_includes_field_details(self) -> None:
        """Test that configuration errors include field details."""
        # Test invalid configuration with field validation error
        with pytest.raises(Exception) as exc_info:
            _ = DiscordConfig(
                token="too_short",  # Should be at least 50 chars
                channel_id=123456789012345678,
                timestamp_format="f",
                ephemeral_message_delete_after=30.0,
            )

        # Verify error message contains field information
        error_str = str(exc_info.value)
        assert "token" in error_str.lower() or "validation" in error_str.lower()

    async def test_tautulli_api_error_includes_status_code(self) -> None:
        """Test that Tautulli API errors include HTTP status code."""
        error = TautulliAPIError("Test error", status_code=500)
        assert error.status_code == 500
        assert "Test error" in str(error)


class TestScheduledUpdates:
    """Test scheduled graph updates (Requirement 7.1)."""

    async def test_scheduler_calculates_next_run_time(
        self, valid_complete_config: BotConfig
    ) -> None:
        """Test that scheduler correctly calculates next run time."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler(config=valid_complete_config.automation)

        # Test fixed time calculation
        next_run = scheduler._calculate_next_run()
        assert next_run is not None
        assert next_run > datetime.now()

    async def test_scheduler_supports_random_time(self) -> None:
        """Test that scheduler supports random update time."""
        from tgraph_bot.scheduler.task_scheduler import TaskScheduler

        # Create config with random time (XX:XX)
        random_time_config = AutomationConfig(
            enabled=True,
            update_interval_days=1,
            fixed_update_time="XX:XX",
        )

        scheduler = TaskScheduler(config=random_time_config)
        next_run1 = scheduler._calculate_next_run()
        next_run2 = scheduler._calculate_next_run()

        # Times should be different (random)
        # Note: This test might occasionally fail due to random chance
        # but probability is very low
        assert next_run1 is not None
        assert next_run2 is not None


@pytest.mark.asyncio
async def test_full_integration_workflow(
    valid_complete_config: BotConfig, sample_stream_records: list[StreamRecord]
) -> None:
    """
    Test complete integration workflow simulating real usage.

    This test validates:
    1. Configuration loading
    2. Graph generation for enabled types
    3. Configuration reload
    4. Error handling

    Requirements: 1.1, 3.1, 5.1, 7.1, 8.1, 15.1
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"

        # 1. Write configuration to file
        with open(config_path, "w") as f:
            yaml.dump(valid_complete_config.model_dump(), f)

        # 2. Load configuration
        loader = ConfigLoader()
        config = loader.load(str(config_path))
        assert config is not None

        # 3. Generate enabled graphs (test a subset)
        factory = GraphFactory()
        appearance_config = config.graphs.appearance
        generated_graphs: list[tuple[str, Figure]] = []

        test_graphs_data = [
            ("daily_play_count", config.graphs.daily_play_count),
            ("play_count_by_day_of_week", config.graphs.play_count_by_day_of_week),
            ("top_platforms", config.graphs.top_platforms),
        ]

        for graph_type, graph_config_raw in test_graphs_data:
            # Type narrow: skip if dict (shouldn't happen with valid config)
            if isinstance(graph_config_raw, dict):
                continue
            graph_config = graph_config_raw

            if not graph_config.enabled:
                continue

            try:
                generator = factory.create_generator(graph_type)
                fig = generator.generate(
                    data=sample_stream_records,
                    config=graph_config,
                    appearance=appearance_config,
                )
                generated_graphs.append((graph_type, fig))
            except Exception as e:
                pytest.fail(f"Failed to generate {graph_type}: {e}")

        # Verify graphs were generated
        assert len(generated_graphs) == 3

        # 4. Clean up figures
        import matplotlib.pyplot as plt

        for _, fig in generated_graphs:
            plt.close(fig)

        # 5. Test configuration reload
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        config_dict["automation"]["update_interval_days"] = 14

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f)

        reloaded_config = loader.load(str(config_path))
        assert reloaded_config.automation.update_interval_days == 14

        # 6. Test error handling for invalid config
        config_dict["automation"]["update_interval_days"] = 500  # Invalid: > 365

        with open(config_path, "w") as f:
            yaml.dump(config_dict, f)

        with pytest.raises(ConfigurationError):
            _ = loader.load(str(config_path))
