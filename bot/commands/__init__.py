# bot/commands/__init__.py

"""
TGraph Bot Commands Package.

This package contains all Discord slash commands for the TGraph Bot.
Each command is implemented as a separate Cog in its own module to ensure
clean separation of concerns and maintainable code structure.

Available commands:
- about: Display bot information
- config: View and modify bot configuration
- my_stats: Generate and view personal Plex statistics
- update_graphs: Manually update and post graphs
- uptime: Show bot uptime
"""

from .about import AboutCog
from .config import ConfigCog
from .my_stats import MyStatsCog
from .update_graphs import UpdateGraphsCog
from .uptime import UptimeCog

# Export all Cog classes
__all__ = [
    'AboutCog',
    'ConfigCog',
    'MyStatsCog',
    'UpdateGraphsCog',
    'UptimeCog'
]
