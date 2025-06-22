#!/usr/bin/env python3
"""
Weblate API Helper Script for TGraph Bot.

This script provides utilities for interacting with the Weblate API
to manage translations, check status, and perform administrative tasks.

Usage:
    python scripts/weblate_api.py [command] [options]

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
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
    from rich.console import Console  # pyright: ignore[reportMissingImports]
    from rich.table import Table  # pyright: ignore[reportMissingImports]
    from rich.progress import Progress, SpinnerColumn, TextColumn  # pyright: ignore[reportMissingImports]
except ImportError:
    print("Please install required packages: uv pip install httpx rich")
    sys.exit(1)

console = Console()


class WeblateAPI:
    """Weblate API client for TGraph Bot translations."""
    
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {'Authorization': f'Token {api_token}'}
        self.client = httpx.Client(headers=self.headers, timeout=30.0)
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.client.close()
    
    def get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to Weblate API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]API Error: {e}[/red]")
            sys.exit(1)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request to Weblate API."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        try:
            response = self.client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]API Error: {e}[/red]")
            sys.exit(1)
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get component status."""
        return self.get('components/tgraph-bot/main/')
    
    def get_translations(self) -> List[Dict[str, Any]]:
        """Get all translations for the component."""
        component = self.get_component_status()
        translations_url = component['translations_url'].replace(self.api_url, '')
        result = self.get(translations_url)
        # Weblate API returns a list of translations
        return result if isinstance(result, list) else []
    
    def get_translation_stats(self) -> List[Dict[str, Any]]:
        """Get detailed translation statistics."""
        translations = self.get_translations()
        stats = []
        
        for trans in translations:
            stats.append({
                'language': trans['language_code'],
                'language_name': trans['language']['name'],
                'translated': trans['translated'],
                'translated_percent': trans['translated_percent'],
                'untranslated': trans['untranslated'],
                'fuzzy': trans['fuzzy'],
                'total': trans['total'],
                'last_change': trans['last_change'],
                'last_author': trans['last_author'],
            })
        
        return sorted(stats, key=lambda x: x['translated_percent'], reverse=True)
    
    def sync_repository(self) -> Dict[str, Any]:
        """Force sync with Git repository."""
        return self.post('components/tgraph-bot/main/repository/', {'operation': 'pull'})
    
    def commit_changes(self) -> Dict[str, Any]:
        """Commit pending changes."""
        return self.post('components/tgraph-bot/main/repository/', {'operation': 'commit'})
    
    def lock_component(self, lock: bool = True) -> Dict[str, Any]:
        """Lock or unlock component."""
        return self.post('components/tgraph-bot/main/lock/', {'lock': lock})


def cmd_status(api: WeblateAPI, args: argparse.Namespace) -> None:
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
    console.print(f"Name: {component['name']}")
    console.print(f"Slug: {component['slug']}")
    console.print(f"Repository: {component['repo']}")
    console.print(f"Branch: {component['branch']}")
    console.print(f"File mask: {component['filemask']}")
    console.print(f"Template: {component['template']}")
    console.print(f"Last change: {component['last_change']}")
    
    # Repository status
    repo_info = component.get('repository', {})
    if repo_info:
        console.print("\n[bold]Repository Status[/bold]")
        console.print(f"Needs commit: {repo_info.get('needs_commit', False)}")
        console.print(f"Needs merge: {repo_info.get('needs_merge', False)}")
        console.print(f"Needs push: {repo_info.get('needs_push', False)}")


def cmd_stats(api: WeblateAPI, args: argparse.Namespace) -> None:
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
        percent = stat['translated_percent']
        bar_width = 20
        filled = int(bar_width * percent / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Format last change date
        last_change = stat['last_change']
        if last_change:
            dt = datetime.fromisoformat(last_change.replace('Z', '+00:00'))
            last_change = dt.strftime('%Y-%m-%d')
        else:
            last_change = "Never"
        
        table.add_row(
            stat['language_name'],
            f"{bar} {percent:.1f}%",
            str(stat['translated']),
            str(stat['untranslated']),
            str(stat['fuzzy']),
            stat['last_author'] or "N/A",
            last_change
        )
    
    console.print("\n")
    console.print(table)
    
    # Summary
    total_languages = len(stats)
    completed = sum(1 for s in stats if s['translated_percent'] == 100)
    in_progress = sum(1 for s in stats if 0 < s['translated_percent'] < 100)
    not_started = sum(1 for s in stats if s['translated_percent'] == 0)
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"Total languages: {total_languages}")
    console.print(f"Completed (100%): {completed} [green]✓[/green]")
    console.print(f"In progress: {in_progress} [yellow]⚡[/yellow]")
    console.print(f"Not started: {not_started} [red]✗[/red]")


def cmd_languages(api: WeblateAPI, args: argparse.Namespace) -> None:
    """List all languages with completion status."""
    stats = api.get_translation_stats()
    
    if args.format == 'json':
        output = []
        for stat in stats:
            output.append({
                'code': stat['language'],
                'name': stat['language_name'],
                'percent': stat['translated_percent'],
                'translated': stat['translated'],
                'total': stat['total']
            })
        print(json.dumps(output, indent=2))
    else:
        for stat in stats:
            status = "✓" if stat['translated_percent'] == 100 else "○"
            console.print(
                f"{status} {stat['language']:5} - {stat['language_name']:20} "
                f"[{stat['translated_percent']:6.1f}%] "
                f"({stat['translated']}/{stat['total']})"
            )


def cmd_sync(api: WeblateAPI, args: argparse.Namespace) -> None:
    """Force sync with Git repository."""
    console.print("[yellow]Syncing with Git repository...[/yellow]")
    
    try:
        result = api.sync_repository()
        console.print("[green]✓ Repository synced successfully![/green]")
        
        if result.get('result'):
            console.print(f"Result: {result['result']}")
    except Exception as e:
        console.print(f"[red]✗ Sync failed: {e}[/red]")


def cmd_commit(api: WeblateAPI, args: argparse.Namespace) -> None:
    """Commit pending changes in Weblate."""
    console.print("[yellow]Committing pending changes...[/yellow]")
    
    try:
        result = api.commit_changes()
        console.print("[green]✓ Changes committed successfully![/green]")
        
        if result.get('result'):
            console.print(f"Result: {result['result']}")
    except Exception as e:
        console.print(f"[red]✗ Commit failed: {e}[/red]")


def cmd_lock(api: WeblateAPI, args: argparse.Namespace) -> None:
    """Lock or unlock component."""
    action = "Locking" if args.lock else "Unlocking"
    console.print(f"[yellow]{action} component...[/yellow]")
    
    try:
        api.lock_component(args.lock)
        console.print(f"[green]✓ Component {'locked' if args.lock else 'unlocked'} successfully![/green]")
    except Exception as e:
        console.print(f"[red]✗ {action} failed: {e}[/red]")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weblate API helper for TGraph Bot translations"
    )
    
    # Global arguments
    parser.add_argument(
        '--api-url',
        default=os.environ.get('WEBLATE_API_URL', 'https://weblate.cccp.ps/api/'),
        help='Weblate API URL'
    )
    parser.add_argument(
        '--api-token',
        default=os.environ.get('WEBLATE_API_TOKEN'),
        help='Weblate API token'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show component status')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Display translation statistics')
    
    # Languages command
    lang_parser = subparsers.add_parser('languages', help='List all languages')
    lang_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format'
    )
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Force sync with Git')
    
    # Commit command
    commit_parser = subparsers.add_parser('commit', help='Commit pending changes')
    
    # Lock command
    lock_parser = subparsers.add_parser('lock', help='Lock component')
    lock_parser.add_argument(
        '--unlock',
        dest='lock',
        action='store_false',
        help='Unlock instead of lock'
    )
    
    args = parser.parse_args()
    
    # Check for API token
    if not args.api_token:
        console.print("[red]Error: WEBLATE_API_TOKEN not set![/red]")
        console.print("Set it via environment variable or --api-token argument")
        return 1
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        with WeblateAPI(args.api_url, args.api_token) as api:
            cmd_func = globals()[f'cmd_{args.command}']
            cmd_func(api, args)
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 