"""
DarkBot Main Bot Class - Refactored
===================================

Main bot class with events moved to EventManager.
"""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import Optional, Dict, Any
import os
from datetime import datetime
import psycopg2

from utils.redis_manager import RedisManager

from .exceptions import DarkBotException, ConfigurationError
from .events import EventManager


class DarkBot(commands.Bot):
    """
    Main DarkBot class extending discord.py's Bot class.

    Handles core bot functionality including:
    - Bot initialization and configuration
    - Cog loading and management
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
        self.redis_manager = RedisManager(config)

        # Default embed color used throughout the bot
        self.embed_color = discord.Color.blurple()

        # Optional: color palette for consistent themed embeds
        self.colors = {
            "info": discord.Color.blurple(),
            "success": discord.Color.green(),
            "error": discord.Color.red(),
            "warning": discord.Color.gold(),
            "neutral": discord.Color.light_grey(),
        }

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
        self.stats = {"command_count": 0, "messages_seen": 0, "errors": 0}

        # Setup logging
        self.setup_logging()

        # Initialize event manager AFTER bot is initialized
        self.event_manager = EventManager(self)

        # Validate configuration
        self._validate_config()

        self.logger.info("DarkBot initialized successfully")

    def setup_logging(self):
        """Set up logging configuration."""
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

    async def get_prefix(self, message):
        """
        Get the command prefix for a message.

        Args:
            message: The message to get prefix for

        Returns:
            str or list: Command prefix(es)
        """
        default = (
            self.config.get("prefix", "!")
            if hasattr(self.config, "get")
            else self.config.prefix
        )
        return commands.when_mentioned_or(default)(self, message)

    async def setup_hook(self):
        """
        Setup hook called when the bot is starting up.
        Used for loading cogs and other async initialization.
        """
        self.logger.info("Setting up DarkBot...")

        # Initialize Redis
        redis_success = await self.redis_manager.initialize()
        if redis_success:
            self.logger.info("Redis initialized successfully")
        else:
            self.logger.warning(
                "Redis initialization failed - continuing without Redis"
            )

        # Load all cogs
        await self.load_cogs()

        # Initialize database connection
        await self.setup_database()

        self.logger.info("DarkBot setup complete")

    async def load_cogs(self):
        """Load all cogs from the cogs directory."""
        cogs_dir = "cogs"
        cog_files = [
            f
            for f in os.listdir(cogs_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        # # Setup event handlers
        # await self.event_manager.setup()

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

            print(params)  # For debugging
            conn = psycopg2.connect(**params)
            self.db_conn = conn
            self.logger.info("Database connection established.")
        except Exception as e:
            self.logger.error(f"Database setup failed: {e}")
            raise

    # Discord event handlers - these delegate to the event manager
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        await self.event_manager.on_ready()

    async def on_message(self, message):
        """Handle incoming messages."""
        await self.event_manager.on_message(message)

    async def on_command(self, ctx):
        """Called when a command is invoked."""
        await self.event_manager.on_command(ctx)

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        await self.event_manager.on_command_error(ctx, error)

    async def on_guild_join(self, guild):
        """Handle guild join events."""
        await self.event_manager.dispatch_event("guild_join", guild)

    async def on_guild_remove(self, guild):
        """Handle guild remove events."""
        await self.event_manager.dispatch_event("guild_remove", guild)

    async def on_member_join(self, member):
        """Handle member join events."""
        await self.event_manager.dispatch_event("member_join", member)

    async def on_member_remove(self, member):
        """Handle member leave events."""
        await self.event_manager.dispatch_event("member_remove", member)

    async def on_message_delete(self, message):
        """Handle message deletion events."""
        await self.event_manager.dispatch_event("message_delete", message)

    async def on_message_edit(self, before, after):
        """Handle message edit events."""
        await self.event_manager.dispatch_event("message_edit", before, after)

    async def on_member_ban(self, guild, user):
        """Handle member ban events."""
        await self.event_manager.dispatch_event("member_ban", guild, user)

    async def on_member_unban(self, guild, user):
        """Handle member unban events."""
        await self.event_manager.dispatch_event("member_unban", guild, user)

    async def close(self):
        """Clean up resources when the bot shuts down."""
        self.logger.info("Shutting down DarkBot...")

        # Close Wavelink connection if Music cog is loaded
        try:
            import wavelink
            if wavelink.Pool.nodes:
                await wavelink.Pool.close()
                self.logger.info("Wavelink connection closed")
        except (ImportError, Exception) as e:
            pass  # Wavelink not installed or already closed

        # Close database connections
        if hasattr(self, 'db_conn') and self.db_conn:
            try:
                self.db_conn.close()
                self.logger.info("Database connection closed")
            except Exception as e:
                self.logger.error(f"Error closing database: {e}")

        # Close Redis connection
        if self.redis_manager:
            try:
                await self.redis_manager.set(
                    "bot:last_shutdown_time", str(datetime.utcnow())
                )
                await self.redis_manager.close()
            except Exception as e:
                self.logger.error(f"Error closing Redis: {e}")

        # Close event manager
        try:
            await self.event_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up event manager: {e}")

        # Call parent close
        await super().close()
        
        # Give a moment for all cleanup to finish
        await asyncio.sleep(0.5)

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

    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics, including live Redis metrics if available."""
        # Base in‐memory stats
        stats = {
            **self.stats,
            "uptime": str(self.uptime),
            "guilds": len(self.guilds),
            "users": len(self.users),
            "cogs": len(self.cogs),
        }

        # If Redis is connected, fetch those counters
        if self.redis_manager.redis:
            for key in ["command_count", "messages_seen", "errors"]:
                try:
                    stats[key] = await self.redis_manager.get_command_usage(key)
                except Exception:
                    stats[key] = "N/A"
        return stats
