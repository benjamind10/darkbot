"""
DarkBot Main Bot Class
=====================

Main bot class that handles Discord client initialization and core functionality.
"""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional, Dict, Any
import os
from datetime import datetime

from .exceptions import DarkBotException, ConfigurationError
from .events import EventManager


class DarkBot(commands.Bot):
    """
    Main DarkBot class extending discord.py's Bot class.

    Handles core bot functionality including:
    - Bot initialization and configuration
    - Cog loading and management
    - Event handling
    - Database connections
    - Error handling
    """

    def __init__(self, config: Dict[str, Any], **kwargs):
        """
        Initialize the DarkBot instance.

        Args:
            config: Configuration dictionary
            **kwargs: Additional keyword arguments for discord.Bot
        """
        self.config = config
        self.start_time = datetime.utcnow()
        self.event_manager = EventManager(self)

        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        # Initialize bot with configuration
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            **kwargs,
        )

        # Bot statistics
        self.stats = {"commands_used": 0, "messages_seen": 0, "errors": 0}

        # Setup logging
        self.setup_logging()

        # Validate configuration
        self._validate_config()

        self.logger.info("DarkBot initialized successfully")

    def setup_logging(self):
        """Set up logging configuration."""
        # Handle both dict and Config object
        if hasattr(self.config, "get"):
            # Dictionary-like object
            log_level = self.config.get("logging", {}).get("level", "INFO")
            log_format = self.config.get("logging", {}).get(
                "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            # Config object with attributes
            log_level = getattr(self.config, "log_level", "INFO")
            log_format = getattr(
                self.config,
                "log_format",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        # Create logs directory if it doesn't exist

        os.makedirs("logs", exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[logging.FileHandler("logs/darkbot.log"), logging.StreamHandler()],
        )

        self.logger = logging.getLogger("darkbot")

    def _validate_config(self):
        """Validate the bot configuration."""
        # Handle both dict and Config object
        if hasattr(self.config, "get"):
            # Dictionary-like object
            if "token" not in self.config:
                raise ConfigurationError("Missing required configuration key: token")
            if "database" not in self.config:
                raise ConfigurationError("Missing required configuration key: database")
            if not self.config["token"]:
                raise ConfigurationError("Bot token cannot be empty")
        else:
            # Config object with attributes
            if not hasattr(self.config, "token"):
                raise ConfigurationError(
                    "Missing required configuration attribute: token"
                )
            if not hasattr(self.config, "database"):
                raise ConfigurationError(
                    "Missing required configuration attribute: database"
                )
            if not self.config.token:
                raise ConfigurationError("Bot token cannot be empty")

    async def get_prefix(self, bot, message):
        """
        Get the command prefix for a message.

        Args:
            bot: The bot instance
            message: The message to get prefix for

        Returns:
            str or list: Command prefix(es)
        """
        # Handle both dict and Config object
        if hasattr(self.config, "get"):
            default_prefix = self.config.get("prefix", "!")
        else:
            default_prefix = getattr(self.config, "prefix", "!")

        # TODO: Add database lookup for custom guild prefixes
        # For now, return default prefix
        return commands.when_mentioned_or(default_prefix)(bot, message)

    async def setup_hook(self):
        """
        Setup hook called when the bot is starting up.
        Used for loading cogs and other async initialization.
        """
        self.logger.info("Setting up DarkBot...")

        # Load all cogs
        await self.load_cogs()

        # Initialize database connection
        # await self.setup_database()

        # Setup event handlers
        await self.event_manager.setup()

        self.logger.info("DarkBot setup complete")

    async def load_cogs(self):
        """Load all cogs from the cogs directory."""
        cogs_dir = "cogs"
        cog_files = [
            f
            for f in os.listdir(cogs_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]

        for cog_file in cog_files:
            cog_name = f"cogs.{cog_file[:-3]}"
            try:
                await self.load_extension(cog_name)
                self.logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                self.logger.error(f"Failed to load cog {cog_name}: {e}")

    async def setup_database(self):
        """Initialize database connection."""
        try:
            db_config = getattr(self.config, "database", None)
            if not db_config:
                raise ConfigurationError("Database configuration missing.")

            # Use params dict for psycopg2
            if hasattr(db_config, "params"):
                params = db_config.params
            else:
                raise ConfigurationError(
                    "Database connection parameters not found in config."
                )

            import psycopg2

            print(params)  # For debugging
            conn = psycopg2.connect(**params)
            self.db_conn = conn
            self.logger.info("Database connection established.")
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        self.logger.info(f"DarkBot is ready!")
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")

        # Set bot status - handle both dict and Config object
        if hasattr(self.config, "get"):
            activity_name = self.config.get("activity", "with darkness")
        else:
            activity_name = getattr(self.config, "activity", "with darkness")

        activity = discord.Game(name=activity_name)
        await self.change_presence(activity=activity)

    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author.bot:
            return

        self.stats["messages_seen"] += 1

        # Process commands
        await self.process_commands(message)

    async def on_command(self, ctx):
        """Called when a command is invoked."""
        self.stats["commands_used"] += 1
        self.logger.info(f"Command '{ctx.command}' used by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        self.stats["errors"] += 1

        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "❌ I don't have the required permissions to execute this command."
            )

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds."
            )

        else:
            # Log unexpected errors
            self.logger.error(f"Unexpected error in command '{ctx.command}': {error}")
            await ctx.send("❌ An unexpected error occurred. Please try again later.")

    async def close(self):
        """Clean up resources when the bot shuts down."""
        self.logger.info("Shutting down DarkBot...")

        # Close database connections
        # TODO: Implement database cleanup

        # Close event manager
        await self.event_manager.cleanup()

        await super().close()

    def run_bot(self):
        """Run the bot with the configured token."""
        try:
            # Handle both dict and Config object
            if hasattr(self.config, "get"):
                token = self.config["token"]
            else:
                token = self.config.token

            self.run(token)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise DarkBotException(f"Bot startup failed: {e}")

    @property
    def uptime(self):
        """Get the bot's uptime."""
        return datetime.utcnow() - self.start_time

    def get_stats(self):
        """Get bot statistics."""
        return {
            **self.stats,
            "uptime": str(self.uptime),
            "guilds": len(self.guilds),
            "users": len(self.users),
            "cogs": len(self.cogs),
        }
