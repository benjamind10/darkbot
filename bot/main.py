import asyncio
import logging
import sys
import signal
from pathlib import Path

# Add the bot directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config
from core.bot import DarkBot
from core.exceptions import BotConfigurationError


class BotRunner:
    """Bot runner class to handle bot lifecycle."""

    def __init__(self):
        self.bot = None
        self.config = None
        self.logger = None

    def setup_logging(self):
        """Setup basic logging before bot initialization."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger("darkbot.runner")

    async def setup_bot(self):
        """Setup and configure the bot."""
        try:
            # Load configuration
            self.config = Config()

            # Validate required configuration
            if not self.config.token:
                raise BotConfigurationError("Discord token is required")

            # Create and configure the bot
            self.bot = DarkBot(config=self.config)

            # Log startup messages
            self.bot.logger.info("Bot configuration loaded successfully")
            self.bot.logger.info("Attempting to connect to Discord...")

            return True

        except BotConfigurationError as e:
            if self.logger:
                self.logger.error(f"Configuration error: {e}")
            else:
                print(f"Configuration error: {e}")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error during setup: {e}", exc_info=True)
            else:
                print(f"Unexpected error during setup: {e}")
            return False

    async def start_bot(self):
        """Start the bot."""
        if not self.bot:
            raise RuntimeError("Bot not initialized. Call setup_bot() first.")

        try:
            await self.bot.start(self.config.token)
        except Exception as e:
            self.bot.logger.error(f"Error starting bot: {e}", exc_info=True)
            raise

    async def shutdown_bot(self):
        """Handle graceful shutdown of the bot."""
        if self.bot:
            self.bot.logger.info("Received shutdown signal. Closing bot...")
            try:
                await self.bot.close()
                self.bot.logger.info("Bot closed successfully")
            except Exception as e:
                self.bot.logger.error(f"Error during shutdown: {e}")
        else:
            if self.logger:
                self.logger.info("Shutdown requested but bot was not initialized")

    async def run(self):
        """Main bot runner method."""
        # Setup basic logging
        self.setup_logging()

        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}. Initiating shutdown...")
            if self.bot:
                asyncio.create_task(self.shutdown_bot())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Setup bot
        if not await self.setup_bot():
            sys.exit(1)

        # Start bot
        try:
            await self.start_bot()
        except KeyboardInterrupt:
            self.bot.logger.info("Bot stopped by user")
        except Exception as e:
            self.bot.logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            await self.shutdown_bot()


async def main():
    """Main entry point for the bot."""
    runner = BotRunner()
    await runner.run()


def run_bot():
    """Run the bot with proper error handling and cleanup."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
