import asyncio
import logging
import sys
from pathlib import Path

# Add the bot directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from core.bot import DarkBot
from core.exceptions import BotConfigurationError

# Use the same logger as the bot
logger = logging.getLogger("darkbot")


async def main():
    """Main entry point for the bot."""
    try:
        # Load configuration
        config = Config()

        # Validate required configuration
        if not config.token:
            raise BotConfigurationError("Discord token is required")

        # Create and configure the bot (this also sets up logging)
        bot = DarkBot(config=config)

        # Log startup messages
        logger.info("Bot configuration loaded successfully")
        logger.info("Attempting to connect to Discord...")

        # Start the bot
        await bot.start(config.token)

    except BotConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


async def shutdown_handler(bot: DarkBot):
    """Handle graceful shutdown of the bot."""
    bot.logger.info("Received shutdown signal. Closing bot...")
    try:
        await bot.close()
        bot.logger.info("Bot closed successfully")
    except Exception as e:
        bot.logger.error(f"Error during shutdown: {e}")


def run_bot():
    """Run the bot with proper error handling and cleanup."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
