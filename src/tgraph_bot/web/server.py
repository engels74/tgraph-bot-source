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
        _ = self._app.router.add_get("/api/config", self.get_config)
        _ = self._app.router.add_post("/api/config", self.update_config)
        _ = self._app.router.add_post("/api/config/reload", self.reload_config)
        _ = self._app.router.add_get(
            "/api/config/file-modified", self.check_file_modified
        )

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

    async def get_config(self, _request: web.Request) -> web.Response:
        """API endpoint to get current configuration from file.

        Always reads from the YAML file to get the latest state,
        supporting manual edits alongside Web UI changes.

        Returns JSON with:
        - config: Configuration dictionary with sensitive values masked
        - file_modified: File modification timestamp for conflict detection

        Args:
            _request: aiohttp request object (unused)

        Returns:
            JSON response with configuration and timestamp

        Requirements: 4.2, 4.5
        """
        try:
            # Always read from file to get latest state
            config = self.config_loader.load(str(self.config_path))

            # Convert to dictionary
            config_dict = config.model_dump()

            # Mask sensitive values
            masked_config = self._mask_sensitive_values(config_dict)

            # Get file modification timestamp
            file_modified = self.config_path.stat().st_mtime

            return web.json_response(
                {"config": masked_config, "file_modified": file_modified}
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}", exc_info=True)
            return web.json_response(
                {"error": f"Failed to load configuration: {e}"}, status=500
            )

    async def update_config(self, request: web.Request) -> web.Response:
        """API endpoint to update configuration.

        Validates new configuration, checks for file conflicts,
        saves to YAML file, and triggers bot reload.

        Expected request JSON:
        - config: New configuration dictionary
        - file_modified: Client's last known file timestamp (optional)

        Returns JSON with:
        - success: True if update succeeded
        - message: Success message
        - error: Error message if failed
        - conflict: True if file was modified externally

        Args:
            request: aiohttp request object with JSON body

        Returns:
            JSON response with update status

        Requirements: 4.3, 4.4, 4.5
        """
        try:
            # Parse request body - aiohttp returns object which could be anything
            from typing import cast

            data_raw: object = await request.json()  # pyright: ignore[reportAny]  # aiohttp returns Any

            # Type narrow to dict
            if not isinstance(data_raw, dict):
                return web.json_response(
                    {"error": "Invalid request format: expected JSON object"},
                    status=400,
                )

            # Now we know it's a dict, cast to dict[str, object]
            data = cast(dict[str, object], data_raw)

            # Check if file was modified since user loaded it
            client_timestamp: float | None = None
            if "file_modified" in data:
                file_modified_value: object = data["file_modified"]
                if file_modified_value is not None:
                    if isinstance(file_modified_value, (int, float)):
                        client_timestamp = float(file_modified_value)
                    else:
                        return web.json_response(
                            {"error": "Invalid file_modified: expected number"},
                            status=400,
                        )

            current_timestamp = self.config_path.stat().st_mtime

            if client_timestamp and client_timestamp < current_timestamp:
                return web.json_response(
                    {
                        "error": "Configuration file was modified externally. Please reload.",
                        "conflict": True,
                    },
                    status=409,
                )

            # Validate new configuration
            from tgraph_bot.config.models import BotConfig

            if "config" not in data:
                return web.json_response(
                    {"error": "Missing required field: config"}, status=400
                )

            config_data_raw: object = data["config"]
            if not isinstance(config_data_raw, dict):
                return web.json_response(
                    {"error": "Invalid config format: expected dictionary"}, status=400
                )

            # Use model_validate for runtime validation from dict
            new_config = BotConfig.model_validate(config_data_raw)

            # Save to YAML file (preserving format)
            self.config_loader.save(new_config, str(self.config_path))

            # Trigger bot reload if bot instance is available
            if self.bot_instance:
                await self.bot_instance.reload_configuration(new_config)

            logger.info(
                "Configuration updated successfully via Web UI",
                extra={"config_path": str(self.config_path)},
            )

            return web.json_response(
                {"success": True, "message": "Configuration saved and reloaded"}
            )

        except KeyError as e:
            return web.json_response(
                {"error": f"Missing required field: {e}"}, status=400
            )
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=400)

    async def reload_config(self, _request: web.Request) -> web.Response:
        """API endpoint to reload configuration from file.

        Triggers bot to reload configuration from the YAML file,
        useful after manual edits.

        Args:
            _request: aiohttp request object (unused)

        Returns:
            JSON response with reload status

        Requirements: 4.4
        """
        try:
            # Load configuration from file
            config = self.config_loader.load(str(self.config_path))

            # Trigger bot reload if bot instance is available
            if self.bot_instance:
                await self.bot_instance.reload_configuration(config)
                logger.info(
                    "Configuration reloaded from file via Web UI",
                    extra={"config_path": str(self.config_path)},
                )
                return web.json_response(
                    {"success": True, "message": "Configuration reloaded from file"}
                )
            else:
                return web.json_response(
                    {"error": "Bot instance not available for reload"}, status=503
                )

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

    async def check_file_modified(self, request: web.Request) -> web.Response:
        """Check if config file was modified externally.

        Compares client's timestamp with current file timestamp
        to detect external modifications.

        Query parameters:
        - timestamp: Client's last known file timestamp

        Returns JSON with:
        - modified: True if file was modified since client timestamp
        - current_timestamp: Current file modification timestamp

        Args:
            request: aiohttp request object with query parameters

        Returns:
            JSON response with modification status

        Requirements: 4.4
        """
        try:
            # Get client timestamp from query parameters
            client_timestamp_str = request.query.get("timestamp", "0")
            client_timestamp = float(client_timestamp_str)

            # Get current file timestamp
            current_timestamp = self.config_path.stat().st_mtime

            return web.json_response(
                {
                    "modified": current_timestamp > client_timestamp,
                    "current_timestamp": current_timestamp,
                }
            )

        except ValueError as e:
            return web.json_response(
                {"error": f"Invalid timestamp parameter: {e}"}, status=400
            )
        except Exception as e:
            logger.error(f"Failed to check file modification: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=500)

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
