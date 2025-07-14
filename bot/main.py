import asyncio
import logging
import os
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
        """Set up logging configuration."""
        # 1) Figure out what level & format you want
        if hasattr(self.config, "get"):
            log_level = self.config.get("logging", {}).get("level", "INFO")
            log_format = self.config.get("logging", {}).get(
                "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            log_level = getattr(self.config, "log_level", "INFO")
            log_format = getattr(
                self.config,
                "log_format",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        # 2) Make sure the logs directory exists
        os.makedirs("logs", exist_ok=True)

        # 3) Configure console output only
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[logging.StreamHandler()],
            force=True,  # remove any previously‐registered handlers (requires Python 3.8+)
        )

        # 4) Now add a file handler to the root logger
        root = logging.getLogger()
        fh = logging.FileHandler("logs/darkbot.log", encoding="utf-8")
        fh.setLevel(getattr(logging, log_level.upper()))
        fh.setFormatter(logging.Formatter(log_format))
        root.addHandler(fh)

        # 5) Grab your named logger for the bot
        self.logger = logging.getLogger("darkbot")

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
