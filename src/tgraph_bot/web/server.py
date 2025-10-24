"""Web UI server for configuration management.

This module implements the aiohttp-based web server that provides:
- Web-based configuration management interface
- REST API for configuration CRUD operations
- Static file serving for CSS/JS assets
- Health check endpoint for monitoring

Requirements: 4.1, 21.2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp_jinja2
import jinja2
from aiohttp import web

from tgraph_bot.config.loader import ConfigLoader
from tgraph_bot.utils.logging import get_logger

if TYPE_CHECKING:
    from tgraph_bot.bot import TGraphBot

logger = get_logger(__name__)


@dataclass(slots=True)
class WebUIServer:
    """Web server for configuration management.

    This class provides a web-based interface for managing bot configuration
    alongside manual YAML editing. It supports:
    - Reading current configuration from file
    - Detecting external file modifications
    - Serving HTML/CSS/JS for the configuration interface
    - Health check endpoint for monitoring

    Attributes:
        config_loader: ConfigLoader instance for loading/saving configuration
        config_path: Path to the YAML configuration file
        host: IP address to bind the server to
        port: Port number to bind the server to
        bot_instance: Reference to TGraphBot for triggering reloads (optional)

    Requirements: 4.1, 21.2
    """

    config_loader: ConfigLoader
    config_path: Path
    host: str
    port: int
    bot_instance: TGraphBot | None = None  # TGraphBot instance (optional, for reload)

    # Internal state
    _app: web.Application | None = None
    _runner: web.AppRunner | None = None
    _site: web.TCPSite | None = None
    _start_time: datetime | None = None

    async def start(self) -> None:
        """Start the web server.

        Sets up the aiohttp application with:
        - Jinja2 templating
        - Route registration
        - Static file serving

        Requirements: 4.1
        """
        logger.info(
            f"Starting Web UI server on {self.host}:{self.port}",
            extra={"host": self.host, "port": self.port},
        )

        # Record start time for uptime tracking
        self._start_time = datetime.now()

        # Create aiohttp application
        self._app = web.Application()

        # Setup Jinja2 templates
        templates_dir = Path(__file__).parent / "templates"
        _ = aiohttp_jinja2.setup(
            self._app, loader=jinja2.FileSystemLoader(str(templates_dir))
        )

        # Register routes
        _ = self._app.router.add_get("/", self.index)
        _ = self._app.router.add_get("/health", self.health_check)

        # Add static file serving
        static_dir = Path(__file__).parent / "static"
        _ = self._app.router.add_static("/static", static_dir)

        # Start the server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        logger.info(
            f"Web UI server started successfully at http://{self.host}:{self.port}",
            extra={"url": f"http://{self.host}:{self.port}"},
        )

    async def stop(self) -> None:
        """Stop the web server gracefully.

        Cleans up all resources including the runner and site.
        """
        logger.info("Stopping Web UI server")

        if self._site:
            await self._site.stop()
            self._site = None

        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        self._app = None
        logger.info("Web UI server stopped")

    @aiohttp_jinja2.template("index.html")
    async def index(self, _request: web.Request) -> dict[str, str | float]:
        """Render main configuration page.

        Returns template context with:
        - config_path: Path to the configuration file
        - last_modified: File modification timestamp

        Args:
            _request: aiohttp request object (unused)

        Returns:
            Template context dictionary

        Requirements: 4.1
        """
        return {
            "config_path": str(self.config_path),
            "last_modified": self.config_path.stat().st_mtime,
        }

    async def health_check(self, _request: web.Request) -> web.Response:
        """Health check endpoint for monitoring.

        Returns server status and basic health information including:
        - status: 'healthy' or 'unhealthy'
        - uptime_seconds: Time since server started
        - config_file_exists: Whether the config file is accessible

        Args:
            request: aiohttp request object

        Returns:
            JSON response with health status

        Requirements: 4.1
        """
        # Calculate uptime
        uptime_seconds = 0.0
        if self._start_time:
            uptime_seconds = (datetime.now() - self._start_time).total_seconds()

        # Check if config file exists
        config_file_exists = self.config_path.exists()

        # Determine overall health status
        status = "healthy" if config_file_exists else "unhealthy"

        health_data = {
            "status": status,
            "uptime_seconds": uptime_seconds,
            "config_file_exists": config_file_exists,
            "config_path": str(self.config_path),
        }

        # Return 200 for healthy, 503 for unhealthy
        status_code = 200 if status == "healthy" else 503

        return web.json_response(health_data, status=status_code)

    def _mask_sensitive_values(
        self, config_dict: dict[str, object]
    ) -> dict[str, object]:
        """Mask sensitive configuration values.

        Masks API keys and tokens showing only the last 4 characters.

        Args:
            config_dict: Configuration dictionary to mask

        Returns:
            Configuration dictionary with masked sensitive values

        Requirements: 4.5
        """
        # Create a copy to avoid modifying the original
        masked_config = config_dict.copy()

        # Mask Discord token
        # Working with untyped YAML dict structure - type checking is limited
        if "services" in masked_config:
            services = masked_config["services"]
            if isinstance(services, dict):
                if "discord" in services:
                    discord_config = services["discord"]  # pyright: ignore[reportUnknownVariableType]
                    if isinstance(discord_config, dict):
                        token = discord_config.get("token")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        if token is not None:
                            discord_config["token"] = self._mask(str(token))  # pyright: ignore[reportUnknownArgumentType]

                # Mask Tautulli API key
                if "tautulli" in services:
                    tautulli_config = services["tautulli"]  # pyright: ignore[reportUnknownVariableType]
                    if isinstance(tautulli_config, dict):
                        api_key = tautulli_config.get("api_key")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                        if api_key is not None:
                            tautulli_config["api_key"] = self._mask(str(api_key))  # pyright: ignore[reportUnknownArgumentType]

        return masked_config

    def _mask(self, value: str) -> str:
        """Mask all but last 4 characters of a string.

        Args:
            value: String to mask

        Returns:
            Masked string showing only last 4 characters

        Requirements: 4.5
        """
        if len(value) <= 4:
            return "****"
        return "*" * (len(value) - 4) + value[-4:]

