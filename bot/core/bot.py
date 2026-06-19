"""
DarkBot Main Bot Class - Refactored
===================================

Main bot class with events moved to EventManager.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import discord
import psycopg_pool
from discord.ext import commands
from utils.log_buffer import RollingLogHandler
from utils.redis_manager import RedisManager

from .events import EventManager
from .exceptions import ConfigurationError, DarkBotException


@dataclass(frozen=True)
class CogLoadResult:
    name: str
    loaded: bool
    required: bool
    error: Exception | None = None


class DarkBot(commands.Bot):
    """
    Main DarkBot class extending discord.py's Bot class.

    Handles core bot functionality including:
    - Bot initialization and configuration
    - Cog loading and management
    - Database connections
    - Error handling
    """

    REQUIRED_COGS = {
        "cogs.BoardGames",
        "cogs.Chatgpt",
        "cogs.Database",
        "cogs.Events",
        "cogs.Information",
        "cogs.ModLog",
        "cogs.Moderation",
        "cogs.Mtg",
        "cogs.Owner",
        "cogs.Spotify",
        "cogs.Utility",
    }
    OPTIONAL_COGS = {"cogs.Music"}

    def __init__(self, config: dict[str, Any], **kwargs):
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
        intents.guild_scheduled_events = True  # Required for !events command

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

        # Quick environment check - warn about missing API tokens
        try:
            self._log_missing_env_tokens()
        except Exception:
            # Don't crash on diagnostics
            self.logger.debug("Environment diagnostics failed", exc_info=True)
        # Validate configuration
        self._validate_config()

        self.logger.info("DarkBot initialized successfully")

    def setup_logging(self):
        """Set up logging configuration."""
        self.logger = logging.getLogger("darkbot")
        self.log_buffer = RollingLogHandler(maxlen=500)
        self.logger.addHandler(self.log_buffer)

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
                raise ConfigurationError("Missing required configuration attribute: token")
            if not hasattr(self.config, "database"):
                raise ConfigurationError("Missing required configuration attribute: database")
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
            self.config.get("prefix", "!") if hasattr(self.config, "get") else self.config.prefix
        )
        return commands.when_mentioned_or(default)(self, message)

    async def setup_hook(self):
        """
        Setup hook called when the bot is starting up.
        Used for loading cogs and other async initialization.
        """
        self.logger.info("Setting up DarkBot...")

        # Print a concise diagnostics summary to make token issues visible early
        try:
            self._log_missing_env_tokens()
        except Exception:
            self.logger.debug("Environment diagnostics failed", exc_info=True)
        # Initialize Redis
        redis_success = await self.redis_manager.initialize()
        if redis_success:
            self.logger.info("Redis initialized successfully")
        else:
            self.logger.warning("Redis initialization failed - continuing without Redis")

        # Initialize database connection pool
        await self.setup_database()

        # Shared aiohttp session for all cogs
        self.http_session = aiohttp.ClientSession()

        # Load all cogs
        await self.load_cogs()

        # Sync slash commands to Discord
        await self.sync_command_tree()

        self.logger.info("DarkBot setup complete")

    def _log_missing_env_tokens(self) -> None:
        """Log warnings for any API tokens or important env variables that are missing.

        This gives clearer feedback at startup which keys to check in .env or deployment.
        """
        music_enabled = self.config.music.enabled and self.config.lavalink.enabled
        youtube_configured = self.config.services.youtube_api_key or (
            self.config.services.youtube_email and self.config.services.youtube_password
        )
        checks = {
            "DISCORD_TOKEN": self.config.token,
            "LAVALINK_PASS": self.config.lavalink.password if music_enabled else True,
            "LAVALINK_SERVER": self.config.lavalink.host if music_enabled else True,
            "SPOTIFY_CLIENTS": (
                self.config.services.spotify_client_id and self.config.services.spotify_client_secret
            )
            if music_enabled
            else True,
            "CHATGPT_SECRET": self.config.services.chatgpt_secret,
            "KSOFT_API": self.config.services.ksoft_api,
            "IP_INFO": self.config.services.ip_info,
            "YOUTUBE_API_KEY or YOUTUBE_EMAIL/YOUTUBE_PASS": youtube_configured,
        }

        missing = [k for k, v in checks.items() if not v]
        if missing:
            self.logger.warning("Missing API tokens / env keys: %s", ", ".join(missing))
        else:
            self.logger.info("All expected API env keys appear present")

    async def load_cogs(self) -> list[CogLoadResult]:
        """Load all cogs from the cogs directory."""
        cogs_dir = "cogs"
        cog_files = [
            f for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("__")
        ]
        results: list[CogLoadResult] = []
        # # Setup event handlers
        # await self.event_manager.setup()

        for cog_file in cog_files:
            cog_name = f"cogs.{cog_file[:-3]}"
            required = cog_name in self.REQUIRED_COGS or cog_name not in self.OPTIONAL_COGS
            try:
                await self.load_extension(cog_name)
                self.logger.info(f"Loaded cog: {cog_name}")
                results.append(CogLoadResult(cog_name, True, required))
            except Exception as exc:
                results.append(CogLoadResult(cog_name, False, required, exc))
                if required:
                    self.logger.exception("Failed to load required cog %s", cog_name)
                else:
                    self.logger.warning("Optional cog %s failed to load", cog_name, exc_info=True)

        failed_required = sorted(result.name for result in results if result.required and not result.loaded)
        if failed_required:
            raise DarkBotException("Required cog(s) failed to load: " + ", ".join(failed_required))

        return results

    async def sync_command_tree(self) -> int:
        """Sync application commands and return the number of synced commands."""
        try:
            synced = await self.tree.sync()
        except discord.HTTPException:
            self.logger.exception("Discord rejected slash command sync")
            return 0
        except Exception:
            self.logger.exception("Failed to sync slash commands")
            return 0

        self.logger.info("Synced %s slash command(s) to Discord", len(synced))
        return len(synced)

    async def setup_database(self):
        """Initialize database connection pool."""
        try:
            db_config = getattr(self.config, "database", None)
            if not db_config:
                raise ConfigurationError("Database configuration missing.")

            if not getattr(db_config, "url", None):
                raise ConfigurationError("Database connection URL not found in config.")

            self.db_pool = psycopg_pool.AsyncConnectionPool(
                conninfo=db_config.url,
                min_size=1,
                max_size=10,
                open=False,
            )
            await self.db_pool.open()
            self.logger.info("Database connection pool established.")
        except Exception:
            self.logger.exception("Database setup failed")
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

        # Wavelink shutdown is owned by Music.cog_unload (runs during super().close())

        # Close shared aiohttp session
        if hasattr(self, "http_session") and self.http_session:
            try:
                await self.http_session.close()
                self.logger.info("HTTP session closed")
            except Exception:
                # Boundary guard: keep shutdown progressing
                self.logger.exception("Error closing HTTP session")

        # Close database connection pool
        if hasattr(self, "db_pool") and self.db_pool:
            try:
                await self.db_pool.close()
                self.logger.info("Database pool closed")
            except Exception:
                # Boundary guard: keep shutdown progressing
                self.logger.exception("Error closing database")

        # Close Redis connection
        if self.redis_manager:
            try:
                await self.redis_manager.set("bot:last_shutdown_time", str(datetime.utcnow()))
                await self.redis_manager.close()
            except Exception:
                # Boundary guard: keep shutdown progressing
                self.logger.exception("Error closing Redis")

        # Close event manager
        try:
            await self.event_manager.cleanup()
        except Exception:
            # Boundary guard: keep shutdown progressing
            self.logger.exception("Error cleaning up event manager")

        # Call parent close
        await super().close()

        # Give a moment for all cleanup to finish
        await asyncio.sleep(0.5)

    def run_bot(self):
        """Run the bot with the configured token."""
        try:
            # Handle both dict and Config object
            token = self.config["token"] if hasattr(self.config, "get") else self.config.token

            self.run(token)
        except Exception as e:
            self.logger.exception("Failed to start bot")
            raise DarkBotException(f"Bot startup failed: {e}") from e

    @property
    def uptime(self):
        """Get the bot's uptime."""
        return datetime.utcnow() - self.start_time

    async def get_stats(self) -> dict[str, Any]:
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
                except Exception:  # boundary guard: degrade stats gracefully on Redis failure
                    stats[key] = "N/A"
        return stats
