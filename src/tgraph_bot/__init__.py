"""TGraph Bot - Discord Tautulli Graph Generator.

A Discord bot that generates and posts beautiful Tautulli graphs to Discord channels.
"""


def main() -> None:
    """Entry point for the application.

    This function imports and calls the main function from __main__.py.
    The import is done here to avoid circular import issues.
    """
    from tgraph_bot.__main__ import main as _main

    _main()


__all__ = ["main"]
