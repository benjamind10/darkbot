# redis_manager.py
"""
Redis Manager for DarkBot
"""

import asyncio
import json
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError
from config.config import Config

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection and utility manager."""

    def __init__(self, config: Config):
        self.config = config
        self.redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if not self.config.redis.enabled:
            logger.info("Redis is disabled in configuration")
            return False

        try:
            # Base pool parameters
            pool_kwargs = {
                "host": self.config.redis.host,
                "port": self.config.redis.port,
                "db": self.config.redis.db,
                "password": self.config.redis.password,
                "decode_responses": self.config.redis.decode_responses,
                "socket_timeout": self.config.redis.socket_timeout,
                "socket_connect_timeout": self.config.redis.socket_connect_timeout,
                "socket_keepalive": self.config.redis.socket_keepalive,
                "socket_keepalive_options": self.config.redis.socket_keepalive_options,
                "max_connections": self.config.redis.connection_pool_max_connections,
                "retry_on_timeout": self.config.redis.retry_on_timeout,
                "health_check_interval": self.config.redis.health_check_interval,
            }

            # Only include SSL/TLS args if you’ve configured a real SSLContext
            if self.config.redis.ssl_context is not None:
                pool_kwargs.update(
                    {
                        "ssl": True,
                        "ssl_context": self.config.redis.ssl_context,
                    }
                )

            # Create connection pool
            self._connection_pool = redis.ConnectionPool(**pool_kwargs)

            # Create Redis client
            self.redis = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self.redis.ping()
            logger.info(
                f"Redis connected successfully to {self.config.redis.host}:{self.config.redis.port}"
            )
            return True

        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    def _get_key(self, key: str) -> str:
        """Get prefixed key."""
        return f"{self.config.redis.prefix}{key}"

    # Basic Operations
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await self.redis.set(prefixed_key, value, ex=expire)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        if not self.redis:
            return default

        try:
            prefixed_key = self._get_key(key)
            value = await self.redis.get(prefixed_key)

            if value is None:
                return default

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return default

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.delete(prefixed_key)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.exists(prefixed_key)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.expire(prefixed_key, seconds)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    # Hash Operations
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set a hash field."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await self.redis.hset(prefixed_key, field, value)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis HSET error for key {key}, field {field}: {e}")
            return False

    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """Get a hash field."""
        if not self.redis:
            return default

        try:
            prefixed_key = self._get_key(key)
            value = await self.redis.hget(prefixed_key, field)

            if value is None:
                return default

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except RedisError as e:
            logger.error(f"Redis HGET error for key {key}, field {field}: {e}")
            return default

    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields."""
        if not self.redis:
            return {}

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.hgetall(prefixed_key)

            # Try to parse JSON values
            parsed_result = {}
            for field, value in result.items():
                try:
                    parsed_result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_result[field] = value

            return parsed_result
        except RedisError as e:
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return {}

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.hdel(prefixed_key, *fields)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis HDEL error for key {key}, fields {fields}: {e}")
            return 0

    # List Operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)

            result = await self.redis.lpush(prefixed_key, *serialized_values)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return 0

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to the right of a list."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)

            result = await self.redis.rpush(prefixed_key, *serialized_values)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            return 0

    async def lpop(self, key: str) -> Any:
        """Pop a value from the left of a list."""
        if not self.redis:
            return None

        try:
            prefixed_key = self._get_key(key)
            value = await self.redis.lpop(prefixed_key)

            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except RedisError as e:
            logger.error(f"Redis LPOP error for key {key}: {e}")
            return None

    async def rpop(self, key: str) -> Any:
        """Pop a value from the right of a list."""
        if not self.redis:
            return None

        try:
            prefixed_key = self._get_key(key)
            value = await self.redis.rpop(prefixed_key)

            if value is None:
                return None

            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except RedisError as e:
            logger.error(f"Redis RPOP error for key {key}: {e}")
            return None

    async def llen(self, key: str) -> int:
        """Get the length of a list."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.llen(prefixed_key)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0

    # Set Operations
    async def sadd(self, key: str, *values: Any) -> int:
        """Add values to a set."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)

            result = await self.redis.sadd(prefixed_key, *serialized_values)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return 0

    async def srem(self, key: str, *values: Any) -> int:
        """Remove values from a set."""
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)

            result = await self.redis.srem(prefixed_key, *serialized_values)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis SREM error for key {key}: {e}")
            return 0

    async def smembers(self, key: str) -> set:
        """Get all members of a set."""
        if not self.redis:
            return set()

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.smembers(prefixed_key)

            # Try to parse JSON values
            parsed_result = set()
            for value in result:
                try:
                    parsed_result.add(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    parsed_result.add(value)

            return parsed_result
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return set()

    async def sismember(self, key: str, value: Any) -> bool:
        """Check if value is a member of a set."""
        if not self.redis:
            return False

        try:
            prefixed_key = self._get_key(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            result = await self.redis.sismember(prefixed_key, value)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
            return False

    # Utility Methods for Discord Bot
    async def set_user_cooldown(
        self, user_id: int, command: str, cooldown_seconds: int
    ) -> bool:
        """Set a cooldown for a user command."""
        key = f"cooldown:{user_id}:{command}"
        return await self.set(key, True, expire=cooldown_seconds)

    async def is_user_on_cooldown(self, user_id: int, command: str) -> bool:
        """Check if user is on cooldown for a command."""
        key = f"cooldown:{user_id}:{command}"
        return await self.exists(key)

    async def set_user_data(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Set user data."""
        key = f"user:{user_id}"
        return await self.set(key, data)

    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user data."""
        key = f"user:{user_id}"
        return await self.get(key, {})

    async def set_guild_data(self, guild_id: int, data: Dict[str, Any]) -> bool:
        """Set guild data."""
        key = f"guild:{guild_id}"
        return await self.set(key, data)

    async def get_guild_data(self, guild_id: int) -> Dict[str, Any]:
        """Get guild data."""
        key = f"guild:{guild_id}"
        return await self.get(key, {})

    async def increment_command_usage(self, command: str) -> int:
        """Increment command usage counter."""
        key = f"stats:command:{command}"
        if not self.redis:
            return 0

        try:
            prefixed_key = self._get_key(key)
            result = await self.redis.incr(prefixed_key)
            return int(result)
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0

    async def get_command_usage(self, command: str) -> int:
        """Get command usage count."""
        key = f"stats:command:{command}"
        result = await self.get(key, 0)
        return int(result) if result else 0
