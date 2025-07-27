#!/usr/bin/env python3
"""
Weblate API integration for automated synchronization.

This script provides functionality to synchronize translation files with Weblate
using the REST API. It handles component locking, pushing changes, and conflict resolution.

Usage Examples:
    Sync component with Weblate:
        python scripts/i18n/weblate_sync.py --project tgraph-bot --component tgraph-bot

    Force push even if conflicts exist:
        python scripts/i18n/weblate_sync.py --project myproject --component mycomponent --force

    Check component status:
        python scripts/i18n/weblate_sync.py --project myproject --component mycomponent --status-only
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

import httpx

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class WeblateConfig(NamedTuple):
    """Configuration for Weblate API access."""

    api_url: str
    api_key: str
    project: str
    component: str
    timeout: int = 30


class WeblateError(Exception):
    """Base exception for Weblate API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeblateClient:
    """Client for interacting with Weblate REST API."""

    def __init__(self, config: WeblateConfig) -> None:
        """
        Initialize Weblate client.

        Args:
            config: Weblate configuration
        """
        self.config = config
        self.client = httpx.Client(
            base_url=config.api_url,
            headers={
                "Authorization": f"Token {config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "TGraph-Bot-CI/1.0",
            },
            timeout=config.timeout,
        )
        self.logger = logging.getLogger(__name__)

    def __enter__(self) -> WeblateClient:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.client.close()

    def _make_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> httpx.Response:
        """
        Make HTTP request to Weblate API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response object

        Raises:
            WeblateError: If the request fails
        """
        url = f"/projects/{self.config.project}/components/{self.config.component}/{endpoint}"

        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            raise WeblateError(error_msg, e.response.status_code) from e
        except httpx.RequestError as e:
            raise WeblateError(f"Request failed: {e}") from e

    def get_component_status(self) -> dict[str, Any]:
        """
        Get component status information.

        Returns:
            Component status data

        Raises:
            WeblateError: If the request fails
        """
        response = self._make_request("GET", "")
        return response.json()  # pyright: ignore[reportAny]

    def lock_component(self) -> bool:
        """
        Lock the component to prevent concurrent modifications.

        Returns:
            True if successfully locked, False if already locked

        Raises:
            WeblateError: If the request fails
        """
        try:
            self._make_request("POST", "lock/")
            self.logger.info("🔒 Component locked successfully")
            return True
        except WeblateError as e:
            if e.status_code == 400:
                self.logger.warning("⚠️  Component is already locked")
                return False
            raise

    def unlock_component(self) -> bool:
        """
        Unlock the component.

        Returns:
            True if successfully unlocked, False if not locked

        Raises:
            WeblateError: If the request fails
        """
        try:
            self._make_request("POST", "unlock/")
            self.logger.info("🔓 Component unlocked successfully")
            return True
        except WeblateError as e:
            if e.status_code == 400:
                self.logger.warning("⚠️  Component is not locked")
                return False
            raise

    def push_changes(self) -> dict[str, Any]:
        """
        Push pending changes to the upstream repository.

        Returns:
            Push operation result

        Raises:
            WeblateError: If the request fails
        """
        response = self._make_request("POST", "push/")
        result = response.json()  # pyright: ignore[reportAny]
        self.logger.info("📤 Pushed changes to upstream repository")
        return result

    def pull_changes(self) -> dict[str, Any]:
        """
        Pull changes from the upstream repository.

        Returns:
            Pull operation result

        Raises:
            WeblateError: If the request fails
        """
        response = self._make_request("POST", "pull/")
        result = response.json()  # pyright: ignore[reportAny]
        self.logger.info("📥 Pulled changes from upstream repository")
        return result

    def update_component(self) -> dict[str, Any]:
        """
        Update component from the upstream repository.

        Returns:
            Update operation result

        Raises:
            WeblateError: If the request fails
        """
        response = self._make_request("POST", "update/")
        result = response.json()  # pyright: ignore[reportAny]
        self.logger.info("🔄 Updated component from upstream")
        return result

    def get_repository_status(self) -> dict[str, Any]:
        """
        Get repository status information.

        Returns:
            Repository status data

        Raises:
            WeblateError: If the request fails
        """
        response = self._make_request("GET", "repository/")
        return response.json()  # pyright: ignore[reportAny]

    def wait_for_idle(self, max_wait: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for component to become idle (no running tasks).

        Args:
            max_wait: Maximum time to wait in seconds
            check_interval: Check interval in seconds

        Returns:
            True if component is idle, False if timeout

        Raises:
            WeblateError: If status check fails
        """
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status = self.get_component_status()
            
            # Check if there are any pending changes or running tasks
            repo_status = self.get_repository_status()
            
            if not repo_status.get("needs_commit", False) and not repo_status.get("needs_push", False):
                self.logger.info("✅ Component is idle and ready")
                return True
            
            self.logger.info(f"⏳ Waiting for component to become idle... ({check_interval}s)")
            time.sleep(check_interval)
        
        self.logger.warning(f"⏰ Timeout waiting for component to become idle after {max_wait}s")
        return False


def setup_logging(verbose: bool = False, ci_mode: bool = False) -> None:
    """
    Set up logging configuration.

    Args:
        verbose: Enable verbose logging
        ci_mode: Enable CI-friendly logging format
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    if ci_mode:
        log_format = "::%(levelname)s::%(message)s" if verbose else "%(message)s"
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Synchronize translations with Weblate via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project tgraph-bot --component tgraph-bot
  %(prog)s --project myproject --component mycomponent --force
  %(prog)s --project myproject --component mycomponent --status-only
        """,
    )

    parser.add_argument(
        "--project",
        required=True,
        help="Weblate project name",
    )

    parser.add_argument(
        "--component",
        required=True,
        help="Weblate component name",
    )

    parser.add_argument(
        "--api-url",
        default=os.getenv("WEBLATE_API_URL", "https://hosted.weblate.org/api"),
        help="Weblate API base URL (default: %(default)s)",
    )

    parser.add_argument(
        "--api-key",
        default=os.getenv("WEBLATE_API_KEY"),
        help="Weblate API key (default: from WEBLATE_API_KEY env var)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="API request timeout in seconds (default: %(default)s)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force synchronization even if conflicts exist",
    )

    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Only check and report component status",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI-friendly logging format",
    )

    return parser.parse_args()


def sync_component(client: WeblateClient, force: bool = False) -> bool:
    """
    Synchronize component with upstream repository.

    Args:
        client: Weblate client instance
        force: Force sync even if conflicts exist

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get initial status
        status = client.get_component_status()
        repo_status = client.get_repository_status()
        
        logger.info(f"Component: {status.get('name', 'Unknown')}")
        logger.info(f"Language count: {status.get('language_count', 0)}")
        logger.info(f"Source strings: {status.get('source_strings', 0)}")
        
        # Check if component needs synchronization
        needs_commit = repo_status.get("needs_commit", False)
        needs_push = repo_status.get("needs_push", False)
        needs_merge = repo_status.get("needs_merge", False)
        
        if not (needs_commit or needs_push or needs_merge):
            logger.info("✅ Component is already synchronized")
            return True
        
        if needs_merge and not force:
            logger.error("❌ Component has merge conflicts. Use --force to override")
            return False
        
        # Lock component for synchronization
        was_locked = client.lock_component()
        
        try:
            # Wait for component to become idle
            if not client.wait_for_idle():
                logger.error("❌ Component did not become idle in time")
                return False
            
            # Push any pending changes to upstream
            if needs_commit or needs_push:
                logger.info("📤 Pushing pending changes...")
                client.push_changes()
            
            # Pull latest changes from upstream
            logger.info("📥 Pulling latest changes...")
            client.pull_changes()
            
            # Update component
            logger.info("🔄 Updating component...")
            client.update_component()
            
            logger.info("✅ Component synchronized successfully")
            return True
            
        finally:
            # Always unlock if we locked it
            if was_locked:
                client.unlock_component()
                
    except WeblateError as e:
        logger.error(f"❌ Weblate API error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during sync: {e}")
        return False


def main() -> int:
    """
    Main entry point for the Weblate sync script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    setup_logging(args.verbose, args.ci_mode)
    
    logger = logging.getLogger(__name__)
    
    # Validate API key
    if not args.api_key:
        logger.error("❌ Weblate API key is required (use --api-key or WEBLATE_API_KEY env var)")
        return 1
    
    # Create Weblate configuration
    config = WeblateConfig(
        api_url=args.api_url,
        api_key=args.api_key,
        project=args.project,
        component=args.component,
        timeout=args.timeout,
    )
    
    try:
        with WeblateClient(config) as client:
            if args.status_only:
                # Just report status
                status = client.get_component_status()
                repo_status = client.get_repository_status()
                
                logger.info("📊 Component Status Report")
                logger.info(f"  Name: {status.get('name', 'Unknown')}")
                logger.info(f"  Languages: {status.get('language_count', 0)}")
                logger.info(f"  Source strings: {status.get('source_strings', 0)}")
                logger.info(f"  Needs commit: {repo_status.get('needs_commit', False)}")
                logger.info(f"  Needs push: {repo_status.get('needs_push', False)}")
                logger.info(f"  Needs merge: {repo_status.get('needs_merge', False)}")
                
                return 0
            else:
                # Perform synchronization
                success = sync_component(client, args.force)
                return 0 if success else 1
                
    except KeyboardInterrupt:
        logger.info("❌ Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())