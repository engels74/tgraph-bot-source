#!/usr/bin/env python3
"""
Weblate API Helper Script for TGraph Bot.

This script provides utilities for interacting with the Weblate API
to manage translations, check status, and perform administrative tasks.

Usage:
    python scripts/weblate/api.py [command] [options]

Commands:
    status      - Show component and translation status
    stats       - Display translation statistics
    languages   - List all languages with completion percentages
    sync        - Force sync with Git repository
    commit      - Commit pending changes in Weblate
    lock        - Lock/unlock component for maintenance
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, TypedDict, cast

try:
    import httpx
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Please install required packages: uv pip install httpx rich")
    sys.exit(1)

console = Console()


class TranslationStat(TypedDict):
    """Type definition for translation statistics."""

    language: str
    language_name: str
    translated: int
    translated_percent: float
    untranslated: int
    fuzzy: int
    total: int
    last_change: str | None
    last_author: str | None


class TranslationData(TypedDict, total=False):
    """Type definition for translation data from Weblate API."""

    language_code: str
    language: dict[str, str]
    translated: int
    translated_percent: float
    untranslated: int
    fuzzy: int
    total: int
    last_change: str | None
    last_author: str | None


class ComponentData(TypedDict, total=False):
    """Type definition for component data from Weblate API."""

    name: str
    slug: str
    repo: str
    branch: str
    filemask: str
    template: str
    last_change: str
    translations_url: str
    repository: dict[str, bool]


class WeblateAPI:
    """Weblate API client for TGraph Bot translations."""

    api_url: str
    headers: dict[str, str]
    client: httpx.Client

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/")
        self.headers = {"Authorization": f"Token {api_token}"}
        self.client = httpx.Client(headers=self.headers, timeout=30.0)

    def __enter__(self) -> WeblateAPI:
        return self

    def __exit__(self, *args: object) -> None:
        self.client.close()

    def get(self, endpoint: str) -> Any:  # pyright: ignore[reportExplicitAny,reportAny]
        """Make GET request to Weblate API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            response = self.client.get(url)
            _ = response.raise_for_status()
            return response.json()  # pyright: ignore[reportAny]
        except httpx.HTTPError as e:
            console.print(f"[red]API Error: {e}[/red]")
            sys.exit(1)

    def post(self, endpoint: str, data: dict[str, Any] | None = None) -> Any:  # pyright: ignore[reportExplicitAny,reportAny]
        """Make POST request to Weblate API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            response = self.client.post(url, json=data)
            _ = response.raise_for_status()
            return response.json()  # pyright: ignore[reportAny]
        except httpx.HTTPError as e:
            console.print(f"[red]API Error: {e}[/red]")
            sys.exit(1)

    def get_component_status(self) -> ComponentData:
        """Get component status."""
        return cast(ComponentData, self.get("components/tgraph-bot/main/"))

    def get_translations(self) -> list[TranslationData]:
        """Get all translations for the component."""
        component = self.get_component_status()
        translations_url = str(component.get("translations_url", "")).replace(
            self.api_url, ""
        )
        result = self.get(translations_url)  # pyright: ignore[reportAny]
        # Weblate API returns a list of translations
        return cast(list[TranslationData], result if isinstance(result, list) else [])

    def get_translation_stats(self) -> list[TranslationStat]:
        """Get detailed translation statistics."""
        translations = self.get_translations()
        stats: list[TranslationStat] = []

        for trans in translations:
            language_data = trans.get("language", {})
            language_name = str(language_data.get("name", "")) if language_data else ""

            stats.append(
                {
                    "language": str(trans.get("language_code", "")),
                    "language_name": language_name,
                    "translated": int(trans.get("translated", 0)),
                    "translated_percent": float(trans.get("translated_percent", 0.0)),
                    "untranslated": int(trans.get("untranslated", 0)),
                    "fuzzy": int(trans.get("fuzzy", 0)),
                    "total": int(trans.get("total", 0)),
                    "last_change": str(trans.get("last_change"))
                    if trans.get("last_change")
                    else None,
                    "last_author": str(trans.get("last_author"))
                    if trans.get("last_author")
                    else None,
                }
            )

        return sorted(stats, key=lambda x: x["translated_percent"], reverse=True)

    def sync_repository(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Force sync with Git repository."""
        return cast(
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            self.post("components/tgraph-bot/main/repository/", {"operation": "pull"}),
        )

    def commit_changes(self) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Commit pending changes."""
        return cast(
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            self.post(
                "components/tgraph-bot/main/repository/", {"operation": "commit"}
            ),
        )

    def lock_component(self, lock: bool = True) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
        """Lock or unlock component."""
        return cast(
            dict[str, Any],  # pyright: ignore[reportExplicitAny]
            self.post("components/tgraph-bot/main/lock/", {"lock": lock}),
        )


def cmd_status(api: WeblateAPI, _args: argparse.Namespace) -> None:
    """Show component and repository status."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching component status...", total=None)

        component = api.get_component_status()

        progress.update(task, completed=True)

    console.print("\n[bold]Component Status[/bold]")
    console.print(f"Name: {component.get('name', 'N/A')}")
    console.print(f"Slug: {component.get('slug', 'N/A')}")
    console.print(f"Repository: {component.get('repo', 'N/A')}")
    console.print(f"Branch: {component.get('branch', 'N/A')}")
    console.print(f"File mask: {component.get('filemask', 'N/A')}")
    console.print(f"Template: {component.get('template', 'N/A')}")
    console.print(f"Last change: {component.get('last_change', 'N/A')}")

    # Repository status
    repo_info = component.get("repository", {})
    if repo_info:
        console.print("\n[bold]Repository Status[/bold]")
        console.print(f"Needs commit: {repo_info.get('needs_commit', False)}")
        console.print(f"Needs merge: {repo_info.get('needs_merge', False)}")
        console.print(f"Needs push: {repo_info.get('needs_push', False)}")


def cmd_stats(api: WeblateAPI, _args: argparse.Namespace) -> None:
    """Display translation statistics."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching translation statistics...", total=None)

        stats = api.get_translation_stats()

        progress.update(task, completed=True)

    # Create table
    table = Table(title="Translation Statistics")
    table.add_column("Language", style="cyan")
    table.add_column("Progress", justify="right")
    table.add_column("Translated", justify="right", style="green")
    table.add_column("Untranslated", justify="right", style="red")
    table.add_column("Fuzzy", justify="right", style="yellow")
    table.add_column("Last Author")
    table.add_column("Last Change")

    for stat in stats:
        # Progress bar
        percent = stat["translated_percent"]
        bar_width = 20
        filled = int(bar_width * percent / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Format last change date
        last_change = stat["last_change"]
        if last_change:
            dt = datetime.fromisoformat(last_change.replace("Z", "+00:00"))
            last_change_str = dt.strftime("%Y-%m-%d")
        else:
            last_change_str = "Never"

        table.add_row(
            stat["language_name"],
            f"{bar} {percent:.1f}%",
            str(stat["translated"]),
            str(stat["untranslated"]),
            str(stat["fuzzy"]),
            stat["last_author"] or "N/A",
            last_change_str,
        )

    console.print("\n")
    console.print(table)

    # Summary
    total_languages = len(stats)
    completed = sum(1 for s in stats if s["translated_percent"] == 100)
    in_progress = sum(1 for s in stats if 0 < s["translated_percent"] < 100)
    not_started = sum(1 for s in stats if s["translated_percent"] == 0)

    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total languages: {total_languages}")
    console.print(f"Completed (100%): {completed} [green]✓[/green]")
    console.print(f"In progress: {in_progress} [yellow]⚡[/yellow]")
    console.print(f"Not started: {not_started} [red]✗[/red]")


def cmd_languages(api: WeblateAPI, args: argparse.Namespace) -> None:
    """List all languages with completion status."""
    stats = api.get_translation_stats()

    format_type = getattr(args, "format", "text")
    if format_type == "json":
        output: list[dict[str, str | float | int]] = []
        for stat in stats:
            output.append(
                {
                    "code": stat["language"],
                    "name": stat["language_name"],
                    "percent": stat["translated_percent"],
                    "translated": stat["translated"],
                    "total": stat["total"],
                }
            )
        print(json.dumps(output, indent=2))
    else:
        for stat in stats:
            percent = stat["translated_percent"]
            status = "✓" if percent == 100 else "○"
            # Using parentheses to avoid implicit concatenation
            line = (
                f"{status} {stat['language']:5} - {stat['language_name']:20} "
                f"[{percent:6.1f}%] "
                f"({stat['translated']}/{stat['total']})"
            )
            console.print(line)


def cmd_sync(api: WeblateAPI, _args: argparse.Namespace) -> None:
    """Force sync with Git repository."""
    console.print("[yellow]Syncing with Git repository...[/yellow]")

    try:
        result = api.sync_repository()
        console.print("[green]✓ Repository synced successfully![/green]")

        if result.get("result"):
            console.print(f"Result: {result.get('result')}")
    except Exception as e:
        console.print(f"[red]✗ Sync failed: {e}[/red]")


def cmd_commit(api: WeblateAPI, _args: argparse.Namespace) -> None:
    """Commit pending changes in Weblate."""
    console.print("[yellow]Committing pending changes...[/yellow]")

    try:
        result = api.commit_changes()
        console.print("[green]✓ Changes committed successfully![/green]")

        if result.get("result"):
            console.print(f"Result: {result.get('result')}")
    except Exception as e:
        console.print(f"[red]✗ Commit failed: {e}[/red]")


def cmd_lock(api: WeblateAPI, args: argparse.Namespace) -> None:
    """Lock or unlock component."""
    lock_flag = bool(getattr(args, "lock", True))
    action = "Locking" if lock_flag else "Unlocking"
    console.print(f"[yellow]{action} component...[/yellow]")

    try:
        _ = api.lock_component(lock_flag)
        console.print(
            f"[green]✓ Component {'locked' if lock_flag else 'unlocked'} successfully![/green]"
        )
    except Exception as e:
        console.print(f"[red]✗ {action} failed: {e}[/red]")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weblate API helper for TGraph Bot translations"
    )

    # Global arguments
    _ = parser.add_argument(
        "--api-url",
        default=os.environ.get("WEBLATE_API_URL", "https://weblate.engels74.net/api/"),
        help="Weblate API URL",
    )
    _ = parser.add_argument(
        "--api-token",
        default=os.environ.get("WEBLATE_API_TOKEN"),
        help="Weblate API token",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    _ = subparsers.add_parser("status", help="Show component status")

    # Stats command
    _ = subparsers.add_parser("stats", help="Display translation statistics")

    # Languages command
    lang_parser = subparsers.add_parser("languages", help="List all languages")
    _ = lang_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # Sync command
    _ = subparsers.add_parser("sync", help="Force sync with Git")

    # Commit command
    _ = subparsers.add_parser("commit", help="Commit pending changes")

    # Lock command
    lock_parser = subparsers.add_parser("lock", help="Lock component")
    _ = lock_parser.add_argument(
        "--unlock", dest="lock", action="store_false", help="Unlock instead of lock"
    )

    args = parser.parse_args()

    # Check for API token
    api_token = getattr(args, "api_token", None)
    if not api_token:
        console.print("[red]Error: WEBLATE_API_TOKEN not set![/red]")
        console.print("Set it via environment variable or --api-token argument")
        return 1

    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 1

    # Execute command
    try:
        api_url = str(getattr(args, "api_url", "https://weblate.engels74.net/api/"))
        if isinstance(api_token, str):
            api_token_str = api_token
        else:
            api_token_str = ""
        with WeblateAPI(api_url, api_token_str) as api:
            cmd_func = globals()[f"cmd_{command}"]  # pyright: ignore[reportAny]
            cmd_func(api, args)
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
