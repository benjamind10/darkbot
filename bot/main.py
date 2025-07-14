# main.py
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to import path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config  # ← typed dataclass
from core.bot import DarkBot
from core.exceptions import BotConfigurationError


def init_logging(cfg: Config) -> logging.Logger:
    """
    Configure root logging *once* using the typed Config object
    and return a named logger for the runner.
    """
    os.makedirs(Path(cfg.logging.file).parent, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, cfg.logging.level.upper()),
        format=cfg.logging.format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(cfg.logging.file, encoding="utf-8"),
        ],
        force=True,  # wipes any earlier basicConfig
    )
    return logging.getLogger("darkbot.runner")


class BotRunner:
    """Responsible for bootstrapping, running and shutting down the bot."""

    def __init__(self) -> None:
        # ① Load config immediately so it’s available for logging & bot
        self.config: Config = Config()

        # ② Set up logging before anything else
        self.logger = init_logging(self.config)

        # ③ Will be created in `setup_bot`
        self.bot: DarkBot | None = None

    # ------------------------------------------------------------------ #
    # bootstrap helpers
    # ------------------------------------------------------------------ #
    async def setup_bot(self) -> None:
        """Instantiate DarkBot with the already-loaded Config."""
        if not self.config.token:
            raise BotConfigurationError("DISCORD_TOKEN is missing in .env")

        self.bot = DarkBot(config=self.config)
        self.logger.info("Bot object created; attempting Discord login…")

    async def start_bot(self) -> None:
        """Connect to Discord and begin polling events."""
        assert self.bot is not None
        await self.bot.start(self.config.token)

    async def shutdown_bot(self) -> None:
        """Gracefully close the bot and all resources."""
        if self.bot is None:
            return

        self.logger.info("Shutdown initiated – closing bot session…")
        try:
            await self.bot.close()
            self.logger.info("Bot closed cleanly")
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Error during shutdown", exc_info=exc)

    # ------------------------------------------------------------------ #
    # public entry-point
    # ------------------------------------------------------------------ #
    async def run(self) -> None:
        """Top-level coroutine (called by asyncio.run)."""
        # Handle SIGINT / SIGTERM so docker & CTRL-C work
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self._on_signal(s))
            )

        try:
            await self.setup_bot()
            await self.start_bot()  # blocks until disconnect / error
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            await self.shutdown_bot()

    async def _on_signal(self, signum: signal.Signals) -> None:  # noqa: D401
        """Handle POSIX signals by shutting down the bot."""
        self.logger.warning("Received %s – shutting down…", signum.name)
        await self.shutdown_bot()


# ---------------------------------------------------------------------- #
# CLI wrapper – keeps `python main.py` nice and short
# ---------------------------------------------------------------------- #
def run_bot() -> None:
    """Run the asynchronous runner inside the event loop."""
    try:
        asyncio.run(BotRunner().run())
    except Exception as exc:  # noqa: BLE001
        # Any error here means even the logger failed – last-chance print
        print("Fatal error starting bot:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_bot()
