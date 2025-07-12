"""
DarkBot - Discord Bot Main Entry Point
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the bot directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from core.bot import DarkBot
from core.exceptions import BotConfigurationError
from utils.logger import setup_logging


async def main():
    """Main entry point for the bot."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting DarkBot...")

        # Load configuration
        config = Config()

        # Validate required configuration
        if not config.token:
            raise BotConfigurationError("Discord token is required")

        # Create and configure the bot
        bot = DarkBot(config=config)

        # Start the bot
        logger.info("Bot configuration loaded successfully")
        logger.info("Attempting to connect to Discord...")

        await bot.start(config.token)

    except BotConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


async def shutdown_handler(bot: DarkBot):
    """Handle graceful shutdown of the bot."""
    logger = logging.getLogger(__name__)
    logger.info("Received shutdown signal. Closing bot...")

    try:
        await bot.close()
        logger.info("Bot closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def run_bot():
    """Run the bot with proper error handling and cleanup."""
    try:
        # Run the main coroutine
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user")
    except Exception as e:
        logging.getLogger(__name__).error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
