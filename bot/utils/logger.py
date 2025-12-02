"""
DarkBot Logging Utilities
=========================

Logging configuration and utilities for the DarkBot application.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path

from core.exceptions import ConfigurationError


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels for console output.
    """

    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record):
        """Format the log record with colors."""
        # Get the original formatted message
        formatted = super().format(record)

        # Add colors if this is a console handler
        if hasattr(self, '_use_colors') and self._use_colors:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            formatted = f"{color}{formatted}{reset}"

        return formatted


class DarkBotLogger:
    """
    Custom logger class for DarkBot with advanced features.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize the DarkBot logger.

        Args:
            name: Logger name
            config: Logging configuration dictionary
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Set up the logger with handlers and formatters."""
        # Clear any existing handlers
        self.logger.handlers.clear()

        # Set log level
        level = self.config.get('level', 'INFO').upper()
        self.logger.setLevel(getattr(logging, level))

        # Add console handler
        if self.config.get('console', True):
            self._add_console_handler()

        # Add file handler
        if self.config.get('file', True):
            self._add_file_handler()

        # Add rotating file handler
        if self.config.get('rotating_file', False):
            self._add_rotating_file_handler()

        # Add error file handler
        if self.config.get('error_file', True):
            self._add_error_file_handler()

    def _add_console_handler(self):
        """Add console handler to the logger."""
        console_handler = logging.StreamHandler(sys.stdout)

        # Create formatter
        formatter = ColoredFormatter(
            fmt=self.config.get('console_format',
                                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            datefmt=self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        # Enable colors for console
        formatter._use_colors = True

        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.config.get('console_level', 'INFO'))

        self.logger.addHandler(console_handler)

    def _add_file_handler(self):
        """Add file handler to the logger."""
        log_dir = Path(self.config.get('log_directory', 'logs'))
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / self.config.get('log_file', 'darkbot.log')

        file_handler = logging.FileHandler(log_file, encoding='utf-8')

        # Create formatter (no colors for file)
        formatter = logging.Formatter(
            fmt=self.config.get('file_format',
                                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'),
            datefmt=self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.config.get('file_level', 'DEBUG'))

        self.logger.addHandler(file_handler)

    def _add_rotating_file_handler(self):
        """Add rotating file handler to the logger."""
        log_dir = Path(self.config.get('log_directory', 'logs'))
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / self.config.get('rotating_log_file', 'darkbot_rotating.log')

        rotating_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.get('max_file_size', 10 * 1024 * 1024),  # 10MB
            backupCount=self.config.get('backup_count', 5),
            encoding='utf-8'
        )

        formatter = logging.Formatter(
            fmt=self.config.get('file_format',
                                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'),
            datefmt=self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        rotating_handler.setFormatter(formatter)
        rotating_handler.setLevel(self.config.get('rotating_file_level', 'DEBUG'))

        self.logger.addHandler(rotating_handler)

    def _add_error_file_handler(self):
        """Add error-only file handler to the logger."""
        log_dir = Path(self.config.get('log_directory', 'logs'))
        log_dir.mkdir(exist_ok=True)

        error_file = log_dir / self.config.get('error_file_name', 'darkbot_errors.log')

        error_handler = logging.FileHandler(error_file, encoding='utf-8')

        formatter = logging.Formatter(
            fmt=self.config.get('error_format',
                                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s'),
            datefmt=self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)

        self.logger.addHandler(error_handler)

    def get_logger(self):
        """Get the configured logger instance."""
        return self.logger


def setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Set up logging for the DarkBot application.

    Args:
        config: Optional logging configuration dictionary

    Returns:
        logging.Logger: Configured logger instance

    Raises:
        ConfigurationError: If logging configuration is invalid
    """
    if config is None:
        config = get_default_logging_config()

    # Validate configuration
    _validate_logging_config(config)

    # Create logs directory if it doesn't exist
    log_dir = Path(config.get('log_directory', 'logs'))
    log_dir.mkdir(exist_ok=True)

    # Create DarkBot logger
    darkbot_logger = DarkBotLogger('darkbot', config)

    # Also set up discord.py logger
    discord_config = config.copy()
    discord_config['console_level'] = config.get('discord_level', 'WARNING')
    discord_logger = DarkBotLogger('discord', discord_config)

    # Set up asyncio logger (reduce noise)
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.WARNING)

    # Log startup message
    main_logger = darkbot_logger.get_logger()
    main_logger.info("DarkBot logging system initialized")
    main_logger.info(f"Log directory: {log_dir.absolute()}")
    main_logger.info(f"Log level: {config.get('level', 'INFO')}")

    return main_logger


def get_default_logging_config() -> Dict[str, Any]:
    """
    Get the default logging configuration.

    Returns:
        Dict[str, Any]: Default logging configuration
    """
    return {
        'level': 'INFO',
        'console': True,
        'console_level': 'INFO',
        'console_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': True,
        'file_level': 'DEBUG',
        'file_format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        'rotating_file': False,
        'rotating_file_level': 'DEBUG',
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5,
        'error_file': True,
        'error_format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s',
        'log_directory': 'logs',
        'log_file': 'darkbot.log',
        'rotating_log_file': 'darkbot_rotating.log',
        'error_file_name': 'darkbot_errors.log',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'discord_level': 'WARNING'
    }


def _validate_logging_config(config: Dict[str, Any]):
    """
    Validate the logging configuration.

    Args:
        config: Logging configuration to validate

    Raises:
        ConfigurationError: If configuration is invalid
    """
    required_keys = ['level', 'log_directory']

    for key in required_keys:
        if key not in config:
            raise ConfigurationError(f"Missing required logging configuration key: {key}")

    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if config['level'].upper() not in valid_levels:
        raise ConfigurationError(f"Invalid log level: {config['level']}. Must be one of: {valid_levels}")

    # Validate log directory
    log_dir = Path(config['log_directory'])
    try:
        log_dir.mkdir(exist_ok=True)
    except Exception as e:
        raise ConfigurationError(f"Cannot create log directory '{log_dir}': {e}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance by name.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log function calls.

    Args:
        logger: Logger instance to use
        level: Log level to use
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.log(level, f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed with error: {e}")
                raise

        return wrapper

    return decorator


def log_async_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log async function calls.

    Args:
        logger: Logger instance to use
        level: Log level to use
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger.log(level, f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"Async {func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Async {func.__name__} failed with error: {e}")
                raise

        return wrapper

    return decorator


class LogContext:
    """
    Context manager for logging with additional context.
    """

    def __init__(self, logger: logging.Logger, context: str, level: int = logging.INFO):
        """
        Initialize the log context.

        Args:
            logger: Logger instance
            context: Context description
            level: Log level to use
        """
        self.logger = logger
        self.context = context
        self.level = level
        self.start_time = None

    def __enter__(self):
        """Enter the context."""
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting {self.context}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        duration = datetime.now() - self.start_time
        if exc_type:
            self.logger.error(f"{self.context} failed after {duration.total_seconds():.2f}s: {exc_val}")
        else:
            self.logger.log(self.level, f"{self.context} completed in {duration.total_seconds():.2f}s")


# Example usage functions
def example_usage():
    """Example of how to use the logging system."""
    # Basic setup
    logger = setup_logging()

    # Basic logging
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # With context manager
    with LogContext(logger, "Database operation"):
        logger.info("Performing database query")
        # Simulate work
        import time
        time.sleep(1)

    # With decorators
    @log_function_call(logger)
    def example_function(x, y):
        return x + y

    result = example_function(5, 3)
    logger.info(f"Result: {result}")


if __name__ == "__main__":
    example_usage()