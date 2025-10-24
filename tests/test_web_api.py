"""Tests for Web UI API endpoints.

This test suite validates the Web UI API endpoints including:
- GET /api/config endpoint with sensitive value masking
- POST /api/config with validation and conflict detection
- POST /api/config/reload endpoint
- GET /api/config/file-modified endpoint for external modification detection

Requirements tested: 4.2, 4.3, 4.4, 4.5
"""

# pyright: reportExplicitAny=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportUnusedCallResult=false
# pyright: reportUnusedParameter=false

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tgraph_bot.config.loader import ConfigLoader


# Fixtures


@pytest.fixture
def valid_config_dict() -> dict[str, Any]:
    """Fixture providing a valid configuration dictionary."""
    graph_config = {
        "enabled": True,
        "media_type_separation": True,
        "palette": "",
        "annotations_enabled": True,
        "peak_highlighting_enabled": False,
        "stacked": False,
    }

    return {
        "services": {
            "tautulli": {
                "api_key": "a" * 32,  # Min length 32
                "url": "https://tautulli.example.com",
            },
            "discord": {
                "token": "x" * 70,  # Min length 50
                "channel_id": 123456789,
                "timestamp_format": "f",
                "ephemeral_message_delete_after": 30.0,
            },
        },
        "automation": {
            "enabled": True,
            "update_interval_days": 7,
            "fixed_update_time": "XX:XX",
        },
        "data_collection": {
            "history_days": 30,
            "max_records_per_request": 1000,
        },
        "system": {
            "language": "en",
            "log_level": "INFO",
            "output_directory": "./graphs",
            "keep_graphs_days": 30,
            "privacy": {
                "censor_usernames": False,
            },
        },
        "graphs": {
            "appearance": {
                "dimensions": {
                    "width": 12,
                    "height": 8,
                    "dpi": 100,
                },
                "colors": {
                    "tv": "#FF5733",
                    "movie": "#33FF57",
                    "background": "#FFFFFF",
                },
                "grid": {
                    "enabled": True,
                    "alpha": 0.5,
                },
                "annotations": {
                    "color": "#000000",
                    "outline_color": "#FFFFFF",
                    "enable_outline": True,
                    "font_size": 10,
                },
                "palettes": {},
                "seaborn": {
                    "style": "darkgrid",
                    "context": "notebook",
                    "palette": "muted",
                },
            },
            "daily_play_count": graph_config,
            "play_count_by_day_of_week": graph_config,
            "play_count_by_hour_of_day": graph_config,
            "top_platforms": {**graph_config, "limit": 10},
            "top_users": {**graph_config, "limit": 10},
            "play_count_by_month": graph_config,
            "daily_play_count_by_stream_type": graph_config,
            "daily_concurrent_stream_count_by_stream_type": graph_config,
            "play_count_by_source_resolution": graph_config,
            "play_count_by_stream_resolution": graph_config,
            "play_count_by_platform_and_stream_type": graph_config,
            "play_count_by_user_and_stream_type": graph_config,
        },
        "rate_limiting": {
            "config": {
                "user_cooldown_minutes": 5,
                "global_cooldown_seconds": 60,
            },
            "update_graphs": {
                "user_cooldown_minutes": 10,
                "global_cooldown_seconds": 120,
            },
            "my_stats": {
                "user_cooldown_minutes": 5,
                "global_cooldown_seconds": 60,
            },
        },
    }


@pytest.fixture
def temp_config_file(valid_config_dict: dict[str, Any]) -> Generator[str, None, None]:
    """Fixture providing a temporary YAML configuration file."""
    from ruamel.yaml import YAML

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml = YAML()
        yaml.dump(valid_config_dict, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def config_loader() -> ConfigLoader:
    """Fixture providing a ConfigLoader instance."""
    return ConfigLoader()


@pytest.fixture
def mock_bot_instance() -> MagicMock:
    """Fixture providing a mock bot instance with reload_configuration method."""
    bot = MagicMock()
    bot.reload_configuration = AsyncMock()
    return bot


# Test Classes


class TestGetConfigEndpoint:
    """Tests for GET /api/config endpoint.

    Requirements: 4.2, 4.5
    """

    @pytest.mark.asyncio
    async def test_get_config_success(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test successful retrieval of configuration (Requirement 4.2)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert "config" in data
            assert "file_modified" in data
            assert isinstance(data["config"], dict)
            assert isinstance(data["file_modified"], (int, float))

    @pytest.mark.asyncio
    async def test_get_config_masks_sensitive_values(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that sensitive values are masked in response (Requirement 4.5)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()

            # Check that Discord token is masked
            discord_token = data["config"]["services"]["discord"]["token"]
            assert discord_token.startswith("*")
            assert discord_token.endswith("xxxx")  # Last 4 chars of 'x' * 70

            # Check that Tautulli API key is masked
            tautulli_key = data["config"]["services"]["tautulli"]["api_key"]
            assert tautulli_key.startswith("*")
            assert tautulli_key.endswith("aaaa")  # Last 4 chars of 'a' * 32

    @pytest.mark.asyncio
    async def test_get_config_includes_file_timestamp(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that response includes file modification timestamp."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Get actual file timestamp
            expected_timestamp = Path(temp_config_file).stat().st_mtime

            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert "file_modified" in data
            assert data["file_modified"] == expected_timestamp


class TestPostConfigEndpoint:
    """Tests for POST /api/config endpoint.

    Requirements: 4.3, 4.4, 4.5
    """

    @pytest.mark.asyncio
    async def test_post_config_success(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
        valid_config_dict: dict[str, Any],
    ) -> None:
        """Test successful configuration update (Requirement 4.4)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Get current file timestamp
            file_timestamp = Path(temp_config_file).stat().st_mtime

            # Modify config slightly
            modified_config = valid_config_dict.copy()
            modified_config["system"]["language"] = "da"

            # Make request
            resp = await client.post(
                "/api/config",
                json={"config": modified_config, "file_modified": file_timestamp},
            )

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert "message" in data

    @pytest.mark.asyncio
    async def test_post_config_validation_error(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test validation error handling (Requirement 4.3, 4.5)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Create invalid config (missing required field)
            invalid_config = {"services": {}}

            # Make request
            resp = await client.post("/api/config", json={"config": invalid_config})

            # Verify response
            assert resp.status == 400
            data = await resp.json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_post_config_triggers_reload(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
        valid_config_dict: dict[str, Any],
    ) -> None:
        """Test that successful update triggers bot reload (Requirement 4.4)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Get current file timestamp
            file_timestamp = Path(temp_config_file).stat().st_mtime

            # Make request
            resp = await client.post(
                "/api/config",
                json={"config": valid_config_dict, "file_modified": file_timestamp},
            )

            # Verify response
            assert resp.status == 200

            # Verify bot reload was called
            mock_bot_instance.reload_configuration.assert_called_once()


class TestConflictDetection:
    """Tests for conflict detection when file modified externally.

    Requirements: 4.4
    """

    @pytest.mark.asyncio
    async def test_conflict_detection_file_modified(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
        valid_config_dict: dict[str, Any],
    ) -> None:
        """Test conflict detection when file modified externally (Requirement 4.4)."""
        import time
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Get old file timestamp
            old_timestamp = Path(temp_config_file).stat().st_mtime

            # Wait a bit to ensure timestamp changes
            time.sleep(0.1)

            # Modify file externally (simulate manual edit)
            Path(temp_config_file).touch()

            # Try to update with old timestamp
            resp = await client.post(
                "/api/config",
                json={"config": valid_config_dict, "file_modified": old_timestamp},
            )

            # Verify conflict detected
            assert resp.status == 409
            data = await resp.json()
            assert "conflict" in data
            assert data["conflict"] is True

    @pytest.mark.asyncio
    async def test_conflict_returns_409_status(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
        valid_config_dict: dict[str, Any],
    ) -> None:
        """Test that conflict returns 409 status code."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Get old timestamp
            old_timestamp = Path(temp_config_file).stat().st_mtime - 1.0

            # Make request with old timestamp
            resp = await client.post(
                "/api/config",
                json={"config": valid_config_dict, "file_modified": old_timestamp},
            )

            # Verify 409 status
            assert resp.status == 409

    @pytest.mark.asyncio
    async def test_conflict_includes_conflict_flag(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
        valid_config_dict: dict[str, Any],
    ) -> None:
        """Test that conflict response includes conflict flag."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config", server.update_config)

        async with TestClient(TestServer(app)) as client:
            # Get old timestamp
            old_timestamp = Path(temp_config_file).stat().st_mtime - 1.0

            # Make request
            resp = await client.post(
                "/api/config",
                json={"config": valid_config_dict, "file_modified": old_timestamp},
            )

            # Verify conflict flag
            data = await resp.json()
            assert "conflict" in data
            assert data["conflict"] is True
            assert "error" in data


class TestReloadConfigEndpoint:
    """Tests for POST /api/config/reload endpoint.

    Requirements: 4.4
    """

    @pytest.mark.asyncio
    async def test_reload_config_success(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test successful configuration reload (Requirement 4.4)."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config/reload", server.reload_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.post("/api/config/reload")

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True
            assert "message" in data

            # Verify bot reload was called
            mock_bot_instance.reload_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_reload_config_error_handling(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test error handling during reload."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Make reload raise an exception
        mock_bot_instance.reload_configuration.side_effect = Exception("Reload failed")

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_post("/api/config/reload", server.reload_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.post("/api/config/reload")

            # Verify error response
            assert resp.status == 500
            data = await resp.json()
            assert "error" in data


class TestFileModifiedEndpoint:
    """Tests for GET /api/config/file-modified endpoint.

    Requirements: 4.4
    """

    @pytest.mark.asyncio
    async def test_file_modified_detection(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test detection of file modification."""
        import time
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config/file-modified", server.check_file_modified)

        async with TestClient(TestServer(app)) as client:
            # Get old timestamp
            old_timestamp = Path(temp_config_file).stat().st_mtime

            # Wait and modify file
            time.sleep(0.1)
            Path(temp_config_file).touch()

            # Make request with old timestamp
            resp = await client.get(
                f"/api/config/file-modified?timestamp={old_timestamp}"
            )

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert data["modified"] is True

    @pytest.mark.asyncio
    async def test_file_modified_timestamp_comparison(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test timestamp comparison for modification detection."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config/file-modified", server.check_file_modified)

        async with TestClient(TestServer(app)) as client:
            # Get expected timestamp
            expected_timestamp = Path(temp_config_file).stat().st_mtime

            # Make request
            resp = await client.get("/api/config/file-modified?timestamp=0")

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert "current_timestamp" in data
            assert data["current_timestamp"] == expected_timestamp

    @pytest.mark.asyncio
    async def test_file_not_modified(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test response when file has not been modified."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config/file-modified", server.check_file_modified)

        async with TestClient(TestServer(app)) as client:
            # Get current timestamp
            current_timestamp = Path(temp_config_file).stat().st_mtime

            # Make request with current timestamp
            resp = await client.get(
                f"/api/config/file-modified?timestamp={current_timestamp}"
            )

            # Verify response
            assert resp.status == 200
            data = await resp.json()
            assert data["modified"] is False


class TestSensitiveValueMasking:
    """Tests for sensitive value masking in API responses.

    Requirements: 4.5, 26.3
    """

    @pytest.mark.asyncio
    async def test_mask_discord_token(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that Discord token is masked in responses."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()

            # Check that Discord token is masked
            discord_token = data["config"]["services"]["discord"]["token"]
            assert discord_token.startswith("*")
            assert not discord_token.startswith("test_discord_token")

    @pytest.mark.asyncio
    async def test_mask_tautulli_api_key(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that Tautulli API key is masked in responses."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()

            # Check that Tautulli API key is masked
            tautulli_key = data["config"]["services"]["tautulli"]["api_key"]
            assert tautulli_key.startswith("*")
            assert not tautulli_key.startswith("test_tautulli_api_key")

    @pytest.mark.asyncio
    async def test_mask_shows_last_4_characters(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that masking shows only last 4 characters."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()

            # Check that Discord token shows last 4 characters
            discord_token = data["config"]["services"]["discord"]["token"]
            assert discord_token.endswith("xxxx")  # Last 4 chars of 'x' * 70

            # Check that Tautulli API key shows last 4 characters
            tautulli_key = data["config"]["services"]["tautulli"]["api_key"]
            assert tautulli_key.endswith("aaaa")  # Last 4 chars of 'a' * 32

    @pytest.mark.asyncio
    async def test_non_sensitive_values_not_masked(
        self,
        temp_config_file: str,
        config_loader: ConfigLoader,
        mock_bot_instance: MagicMock,
    ) -> None:
        """Test that non-sensitive values are not masked."""
        from pathlib import Path

        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer

        from tgraph_bot.web.server import WebUIServer

        # Create server instance
        server = WebUIServer(
            config_loader=config_loader,
            config_path=Path(temp_config_file),
            host="127.0.0.1",
            port=8080,
            bot_instance=mock_bot_instance,
        )

        # Create test client
        app = web.Application()
        app.router.add_get("/api/config", server.get_config)

        async with TestClient(TestServer(app)) as client:
            # Make request
            resp = await client.get("/api/config")

            # Verify response
            assert resp.status == 200
            data = await resp.json()

            # Check that non-sensitive values are not masked
            assert data["config"]["services"]["discord"]["channel_id"] == 123456789
            assert data["config"]["system"]["language"] == "en"
            assert data["config"]["automation"]["enabled"] is True

