"""
TGraph Bot - A Discord bot for automatically generating and posting Tautulli graphs.
"""

import asyncio
import sys
from .main import main as async_main


def main() -> None:
    """Synchronous entry point that runs the async main function."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        # Logging is set up in main(), so this should work
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Bot stopped by user")
    except Exception as e:
        # If logging isn't set up yet, fall back to basic logging
        try:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception(f"Failed to start bot: {e}")
        except Exception:  # noqa: BLE001
            # Logger not available, use basic print
            print(f"Failed to start bot: {e}", file=sys.stderr)
        sys.exit(1)


__all__ = ["main"]
