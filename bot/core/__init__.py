"""
DarkBot Core Module
==================

Core functionality for the DarkBot Discord bot.
"""

from .bot import DarkBot
from .events import EventManager
from .exceptions import (
    APIError,
    BotConfigurationError,
    ConfigurationError,
    DarkBotException,
    DatabaseError,
    ValidationError,
)

__version__ = "1.0.0"
__author__ = "Shiva"

__all__ = [
    "DarkBot",
    "RedisManager",
    "EventManager",
    "DarkBotException",
    "ConfigurationError",
    "BotConfigurationError",
    "DatabaseError",
    "APIError",
    "ValidationError",
]
