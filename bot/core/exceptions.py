"""
DarkBot Custom Exceptions
========================

Custom exception classes for the DarkBot application.
"""

from typing import Optional, Any


class DarkBotException(Exception):
    """
    Base exception class for all DarkBot-related errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize the exception.

        Args:
            message: Error message
            code: Optional error code
            details: Optional additional details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self):
        """Return string representation of the exception."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def to_dict(self):
        """Convert exception to dictionary."""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }


class ConfigurationError(DarkBotException):
    """
    Raised when there's an error with bot configuration.

    Examples:
    - Missing required configuration keys
    - Invalid configuration values
    - Configuration file parsing errors
    """

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key
        if config_key:
            self.details['config_key'] = config_key


class BotConfigurationError(ConfigurationError):
    """
    Raised when there's an error with bot-specific configuration.

    This is an alias for ConfigurationError to maintain compatibility
    with existing imports and provide more specific naming.

    Examples:
    - Missing bot token
    - Invalid bot permissions
    - Bot setup failures
    """

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        """
        Initialize bot configuration error.

        Args:
            message: Error message
            config_key: The configuration key that caused the error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, config_key=config_key, **kwargs)
        self.code = "BOT_CONFIG_ERROR"


class DatabaseError(DarkBotException):
    """
    Raised when there's an error with database operations.

    Examples:
    - Connection failures
    - Query execution errors
    - Data validation errors
    - Migration failures
    """

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """
        Initialize database error.

        Args:
            message: Error message
            operation: The database operation that failed
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="DB_ERROR", **kwargs)
        self.operation = operation
        if operation:
            self.details['operation'] = operation


class APIError(DarkBotException):
    """
    Raised when there's an error with external API calls.

    Examples:
    - HTTP request failures
    - Rate limiting
    - Authentication errors
    - Invalid responses
    """

    def __init__(self, message: str, api_name: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        """
        Initialize API error.

        Args:
            message: Error message
            api_name: Name of the API that failed
            status_code: HTTP status code if applicable
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="API_ERROR", **kwargs)
        self.api_name = api_name
        self.status_code = status_code

        if api_name:
            self.details['api_name'] = api_name
        if status_code:
            self.details['status_code'] = status_code


class ValidationError(DarkBotException):
    """
    Raised when data validation fails.

    Examples:
    - Invalid user input
    - Data type mismatches
    - Required field missing
    - Value out of range
    """

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: The field that failed validation
            value: The invalid value
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)
        self.field = field
        self.value = value

        if field:
            self.details['field'] = field
        if value is not None:
            self.details['value'] = str(value)


class PermissionError(DarkBotException):
    """
    Raised when a user lacks required permissions.

    Examples:
    - Missing Discord permissions
    - Insufficient bot permissions
    - Role hierarchy issues
    """

    def __init__(self, message: str, required_permission: Optional[str] = None, **kwargs):
        """
        Initialize permission error.

        Args:
            message: Error message
            required_permission: The permission that was missing
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="PERMISSION_ERROR", **kwargs)
        self.required_permission = required_permission
        if required_permission:
            self.details['required_permission'] = required_permission


class CogError(DarkBotException):
    """
    Raised when there's an error with cog operations.

    Examples:
    - Cog loading failures
    - Cog unloading failures
    - Missing cog dependencies
    """

    def __init__(self, message: str, cog_name: Optional[str] = None, **kwargs):
        """
        Initialize cog error.

        Args:
            message: Error message
            cog_name: Name of the cog that caused the error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="COG_ERROR", **kwargs)
        self.cog_name = cog_name
        if cog_name:
            self.details['cog_name'] = cog_name


class RateLimitError(DarkBotException):
    """
    Raised when a rate limit is exceeded.

    Examples:
    - Discord API rate limits
    - Custom command rate limits
    - Database query rate limits
    """

    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds until the rate limit resets
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="RATE_LIMIT_ERROR", **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details['retry_after'] = retry_after


class ModuleError(DarkBotException):
    """
    Raised when there's an error with module operations.

    Examples:
    - Module import failures
    - Module initialization errors
    - Module dependency issues
    """

    def __init__(self, message: str, module_name: Optional[str] = None, **kwargs):
        """
        Initialize module error.

        Args:
            message: Error message
            module_name: Name of the module that caused the error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="MODULE_ERROR", **kwargs)
        self.module_name = module_name
        if module_name:
            self.details['module_name'] = module_name


class CommandError(DarkBotException):
    """
    Raised when there's an error with command execution.

    Examples:
    - Command parsing errors
    - Command execution failures
    - Invalid command arguments
    """

    def __init__(self, message: str, command_name: Optional[str] = None, **kwargs):
        """
        Initialize command error.

        Args:
            message: Error message
            command_name: Name of the command that caused the error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, code="COMMAND_ERROR", **kwargs)
        self.command_name = command_name
        if command_name:
            self.details['command_name'] = command_name


# Convenience functions for common error scenarios

def raise_config_error(message: str, config_key: Optional[str] = None):
    """Raise a configuration error with consistent formatting."""
    raise ConfigurationError(message, config_key=config_key)


def raise_bot_config_error(message: str, config_key: Optional[str] = None):
    """Raise a bot configuration error with consistent formatting."""
    raise BotConfigurationError(message, config_key=config_key)


def raise_db_error(message: str, operation: Optional[str] = None):
    """Raise a database error with consistent formatting."""
    raise DatabaseError(message, operation=operation)


def raise_api_error(message: str, api_name: Optional[str] = None, status_code: Optional[int] = None):
    """Raise an API error with consistent formatting."""
    raise APIError(message, api_name=api_name, status_code=status_code)


def raise_validation_error(message: str, field: Optional[str] = None, value: Optional[Any] = None):
    """Raise a validation error with consistent formatting."""
    raise ValidationError(message, field=field, value=value)


def raise_permission_error(message: str, required_permission: Optional[str] = None):
    """Raise a permission error with consistent formatting."""
    raise PermissionError(message, required_permission=required_permission)


# Error handler decorator
def handle_errors(error_type: type = DarkBotException):
    """
    Decorator to handle specific types of errors.

    Args:
        error_type: Type of error to handle
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_type as e:
                # Log the error
                import logging
                logger = logging.getLogger('darkbot.errors')
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator