"""
DarkBot Event Management
=======================

Event handlers and management for the DarkBot.
"""

import discord
import logging
from typing import Dict, List, Callable, Any
from datetime import datetime
import asyncio

from .exceptions import DarkBotException


class EventManager:
    """
    Manages custom events and event handlers for DarkBot.

    Provides functionality for:
    - Custom event registration
    - Event dispatching
    - Event logging
    - Event statistics
    """

    def __init__(self, bot):
        """
        Initialize the EventManager.

        Args:
            bot: The DarkBot instance
        """
        self.bot = bot
        self.logger = logging.getLogger('darkbot.events')
        self.events: Dict[str, List[Callable]] = {}
        self.event_stats: Dict[str, int] = {}

        # Register built-in event handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register built-in event handlers."""
        # Guild events
        self.register_event('guild_join', self.on_guild_join)
        self.register_event('guild_remove', self.on_guild_remove)

        # Member events
        self.register_event('member_join', self.on_member_join)
        self.register_event('member_remove', self.on_member_remove)

        # Message events
        self.register_event('message_delete', self.on_message_delete)
        self.register_event('message_edit', self.on_message_edit)

        # Moderation events
        self.register_event('member_ban', self.on_member_ban)
        self.register_event('member_unban', self.on_member_unban)

    def register_event(self, event_name: str, handler: Callable):
        """
        Register an event handler.

        Args:
            event_name: Name of the event
            handler: Function to handle the event
        """
        if event_name not in self.events:
            self.events[event_name] = []

        self.events[event_name].append(handler)
        self.logger.debug(f"Registered handler for event: {event_name}")

    def unregister_event(self, event_name: str, handler: Callable):
        """
        Unregister an event handler.

        Args:
            event_name: Name of the event
            handler: Function to unregister
        """
        if event_name in self.events and handler in self.events[event_name]:
            self.events[event_name].remove(handler)
            self.logger.debug(f"Unregistered handler for event: {event_name}")

    async def dispatch_event(self, event_name: str, *args, **kwargs):
        """
        Dispatch an event to all registered handlers.

        Args:
            event_name: Name of the event to dispatch
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers
        """
        if event_name not in self.events:
            return

        # Update statistics
        self.event_stats[event_name] = self.event_stats.get(event_name, 0) + 1

        # Run all handlers for this event
        for handler in self.events[event_name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in event handler {handler.__name__} for {event_name}: {e}")

    async def setup(self):
        """Setup the event manager."""
        self.logger.info("Event manager setup complete")

    async def cleanup(self):
        """Clean up the event manager."""
        self.events.clear()
        self.logger.info("Event manager cleanup complete")

    # Built-in event handlers

    async def on_guild_join(self, guild: discord.Guild):
        """Handle guild join events."""
        self.logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")

        # TODO: Add guild to database
        # TODO: Send welcome message to system channel

    async def on_guild_remove(self, guild: discord.Guild):
        """Handle guild remove events."""
        self.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

        # TODO: Clean up guild data from database

    async def on_member_join(self, member: discord.Member):
        """Handle member join events."""
        self.logger.info(f"Member joined {member.guild.name}: {member} (ID: {member.id})")

        # TODO: Check for auto-role assignment
        # TODO: Send welcome message if configured
        # TODO: Log to modlog if configured

    async def on_member_remove(self, member: discord.Member):
        """Handle member leave events."""
        self.logger.info(f"Member left {member.guild.name}: {member} (ID: {member.id})")

        # TODO: Send goodbye message if configured
        # TODO: Log to modlog if configured

    async def on_message_delete(self, message: discord.Message):
        """Handle message deletion events."""
        if message.author.bot:
            return

        self.logger.debug(f"Message deleted in {message.guild.name}: {message.content[:50]}...")

        # TODO: Log to modlog if configured
        # TODO: Store in message cache for snipe commands

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Handle message edit events."""
        if before.author.bot or before.content == after.content:
            return

        self.logger.debug(f"Message edited in {before.guild.name}: {before.author}")

        # TODO: Log to modlog if configured
        # TODO: Store in message cache for edit snipe commands

    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Handle member ban events."""
        self.logger.info(f"Member banned from {guild.name}: {user} (ID: {user.id})")

        # TODO: Log to modlog if configured
        # TODO: Update moderation case database

    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Handle member unban events."""
        self.logger.info(f"Member unbanned from {guild.name}: {user} (ID: {user.id})")

        # TODO: Log to modlog if configured
        # TODO: Update moderation case database

    def get_event_stats(self) -> Dict[str, int]:
        """Get event statistics."""
        return self.event_stats.copy()

    def get_registered_events(self) -> List[str]:
        """Get list of registered events."""
        return list(self.events.keys())


class EventLogger:
    """
    Logger specifically for Discord events.

    Provides structured logging for Discord events with
    configurable log levels and formatting.
    """

    def __init__(self, bot):
        """
        Initialize the EventLogger.

        Args:
            bot: The DarkBot instance
        """
        self.bot = bot
        self.logger = logging.getLogger('darkbot.events.logger')
        self.log_events = bot.config.get('logging', {}).get('events', [])

    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event with structured data.

        Args:
            event_type: Type of event
            data: Event data dictionary
        """
        if event_type not in self.log_events:
            return

        timestamp = datetime.utcnow().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'data': data
        }

        self.logger.info(f"Event logged: {event_type}", extra=log_entry)

    async def log_guild_event(self, guild: discord.Guild, event_type: str, **kwargs):
        """Log a guild-specific event."""
        data = {
            'guild_id': guild.id,
            'guild_name': guild.name,
            **kwargs
        }
        await self.log_event(event_type, data)

    async def log_member_event(self, member: discord.Member, event_type: str, **kwargs):
        """Log a member-specific event."""
        data = {
            'guild_id': member.guild.id,
            'guild_name': member.guild.name,
            'user_id': member.id,
            'username': str(member),
            **kwargs
        }
        await self.log_event(event_type, data)

    async def log_message_event(self, message: discord.Message, event_type: str, **kwargs):
        """Log a message-specific event."""
        data = {
            'guild_id': message.guild.id if message.guild else None,
            'channel_id': message.channel.id,
            'user_id': message.author.id,
            'message_id': message.id,
            **kwargs
        }
        await self.log_event(event_type, data)