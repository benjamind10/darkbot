"""
DarkBot Configuration Management
"""

import os
import json
from pathlib import Path
import ssl
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from dotenv import load_dotenv

from .settings import (
    PROJECT_ROOT,
    CONFIG_DIR,
    DEFAULT_PREFIX,
    DEFAULT_DESCRIPTION,
    DEFAULT_ACTIVITY_NAME,
    DEFAULT_ACTIVITY_TYPE,
    DATABASE_URL_DEFAULT,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_NAME,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DISCORD_TOKEN,
    OWNER_ID,
    LAVALINK_DEFAULT_HOST,
    LAVALINK_DEFAULT_PORT,
    LAVALINK_DEFAULT_PASSWORD,
    COGS_TO_LOAD,
    FEATURES,
    EMBED_COLORS,
    EMOJIS,
    PERMISSION_LEVELS,
    REDIS_ENABLED,
    REDDIS_PORT,
    REDDIS_DB,
    REDDIS_PASSWORD,
    REDDIS_HOST,
    REDIS_KEY_PREFIX,
)


@dataclass
class DatabaseConfig:
    """Database configuration."""

    url: str = DATABASE_URL_DEFAULT
    host: str = DATABASE_HOST
    port: int = DATABASE_PORT
    name: str = DATABASE_NAME
    user: str = DATABASE_USER
    password: str = DATABASE_PASSWORD
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False
    params: dict = field(default_factory=dict)


@dataclass
class RedisConfig:
    """Redis configuration."""

    enabled: bool = REDIS_ENABLED
    host: str = REDDIS_HOST
    port: int = REDDIS_PORT
    password: Optional[str] = REDDIS_PASSWORD
    db: int = REDDIS_DB
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    connection_pool_max_connections: int = 10
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    prefix: str = REDIS_KEY_PREFIX
    ssl_context: Optional[ssl.SSLContext] = None
    # ssl: bool = False
    # ssl_cert_reqs: str = "required"
    # ssl_ca_certs: Optional[str] = None
    # ssl_certfile: Optional[str] = None
    # ssl_keyfile: Optional[str] = None


@dataclass
class MusicConfig:
    """Music configuration."""

    enabled: bool = True
    default_volume: float = 0.5
    max_volume: float = 1.0
    queue_limit: int = 100
    search_limit: int = 10
    ffmpeg_options: Dict[str, str] = field(
        default_factory=lambda: {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }
    )


@dataclass
class LavalinkConfig:
    """Lavalink configuration."""

    enabled: bool = True
    host: str = LAVALINK_DEFAULT_HOST
    port: int = LAVALINK_DEFAULT_PORT
    password: str = LAVALINK_DEFAULT_PASSWORD
    region: str = "us"
    secure: bool = False


@dataclass
class ModerationConfig:
    """Moderation configuration."""

    enabled: bool = True
    default_reason: str = "No reason provided"
    log_channel_id: Optional[int] = None
    max_warn_count: int = 3
    auto_timeout_duration: int = 600


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_path: str = str(PROJECT_ROOT / "logs" / "darkbot.log")
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class Config:
    """Main configuration class for DarkBot."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_file: Path to optional JSON config file
        """
        # Load environment variables
        load_dotenv(PROJECT_ROOT / ".env")

        # Load configuration from file if provided
        self._file_config = {}
        if config_file:
            self._load_config_file(config_file)

        # Initialize configuration sections
        self._initialize_config()

    def print_config(self):
        for attr in dir(self):
            if not attr.startswith("_"):
                value = getattr(self, attr)
                print(f"{attr}: {value}")

    def _load_config_file(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = CONFIG_DIR / config_path

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._file_config = json.load(f)
        except FileNotFoundError:
            print(f"Config file not found: {config_path}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in config file: {e}")

    def _initialize_redis_config(self) -> RedisConfig:
        """Initialize Redis configuration."""
        return RedisConfig(
            enabled=self._get_bool_config("REDIS_ENABLED", "redis.enabled", True),
            host=self._get_config("REDIS_HOST", "redis.host", "redis"),
            port=self._get_int_config("REDIS_PORT", "redis.port", 6379),
            password=None,
            # password=self._get_config("REDIS_PASSWORD", "redis.password"),
            db=self._get_int_config("REDIS_DB", "redis.db", 0),
            decode_responses=self._get_bool_config(
                "REDIS_DECODE_RESPONSES", "redis.decode_responses", True
            ),
            socket_timeout=self._get_int_config(
                "REDIS_SOCKET_TIMEOUT", "redis.socket_timeout", 5
            ),
            socket_connect_timeout=self._get_int_config(
                "REDIS_SOCKET_CONNECT_TIMEOUT", "redis.socket_connect_timeout", 5
            ),
            socket_keepalive=self._get_bool_config(
                "REDIS_SOCKET_KEEPALIVE", "redis.socket_keepalive", True
            ),
            socket_keepalive_options=self._get_config(
                "REDIS_SOCKET_KEEPALIVE_OPTIONS", "redis.socket_keepalive_options", {}
            ),
            connection_pool_max_connections=self._get_int_config(
                "REDIS_CONNECTION_POOL_MAX_CONNECTIONS",
                "redis.connection_pool_max_connections",
                10,
            ),
            retry_on_timeout=self._get_bool_config(
                "REDIS_RETRY_ON_TIMEOUT", "redis.retry_on_timeout", True
            ),
            health_check_interval=self._get_int_config(
                "REDIS_HEALTH_CHECK_INTERVAL", "redis.health_check_interval", 30
            ),
            prefix=self._get_config("REDIS_KEY_PREFIX", "redis.prefix", "darkbot:"),
            ssl_context=None,  # You can implement SSL context if needed
        )

    def _initialize_config(self) -> None:
        """Initialize all configuration sections."""
        # Bot basic settings
        self.token = self._get_config("DISCORD_TOKEN", "token", DISCORD_TOKEN)
        self.prefix = self._get_config("BOT_PREFIX", "prefix", DEFAULT_PREFIX)
        self.description = self._get_config(
            "BOT_DESCRIPTION", "description", DEFAULT_DESCRIPTION
        )

        # Owner configuration
        owner_id = self._get_config("OWNER_ID", "owner_id", OWNER_ID)
        self.owner_ids = [int(owner_id)] if owner_id else []

        # Bot activity
        self.activity_name = self._get_config(
            "ACTIVITY_NAME", "activity_name", DEFAULT_ACTIVITY_NAME
        )
        self.activity_type = self._get_config(
            "ACTIVITY_TYPE", "activity_type", DEFAULT_ACTIVITY_TYPE
        )

        # Development settings
        self.debug = self._get_bool_config("DEBUG", "debug", False)
        self.development_guild_id = self._get_int_config(
            "DEVELOPMENT_GUILD_ID", "development_guild_id"
        )
        self.sync_commands = self._get_bool_config(
            "SYNC_COMMANDS_ON_STARTUP", "sync_commands", False
        )

        # Configuration objects
        self.database = self._initialize_database_config()
        self.redis = self._initialize_redis_config()  # Redis disabled
        self.music = self._initialize_music_config()
        self.lavalink = self._initialize_lavalink_config()
        self.moderation = self._initialize_moderation_config()
        self.logging = self._initialize_logging_config()

        # Features
        self.features = self._initialize_features()

        # Cogs
        self.cogs_to_load = self._get_list_config(
            "COGS_TO_LOAD", "cogs_to_load", COGS_TO_LOAD
        )

        # Colors and emojis
        self.colors = EMBED_COLORS.copy()
        self.emojis = EMOJIS.copy()

        # Permission levels
        self.permission_levels = PERMISSION_LEVELS.copy()

        # API Keys
        self.weather_api_key = self._get_config("WEATHER_API_KEY", "weather_api_key")
        self.youtube_api_key = self._get_config("YOUTUBE_API_KEY", "youtube_api_key")
        self.youtube_email = self._get_config("YOUTUBE_EMAIL", "youtube_email")
        self.youtube_password = self._get_config("YOUTUBE_PASS", "youtube_password")
        self.lavalink_password = self._get_config("LAVALINK_PASS", "lavalink_password")
        self.lavalink_server = self._get_config("LAVALILNK_SERVER", "lavalink_server")
        self.spotify_client_id = self._get_config(
            "SPOTIFY_CLIENT_ID", "spotify_client_id"
        )
        self.spotify_client_secret = self._get_config(
            "SPOTIFY_CLIENT_SECRET", "spotify_client_secret"
        )
        self.chatgpt_secret = self._get_config("CHATGPT_SECRET", "chatgpt_secret")
        self.openai_api_key = self._get_config(
            "CHATGPT_SECRET", "openai_api_key"
        )  # Alias
        self.api_coincap = self._get_config("API_COINCAP", "api_coincap")
        self.ip_info = self._get_config("IP_INFO", "ip_info")
        self.ksoft_api = self._get_config("KSOFT_APT", "ksoft_api")

    def _initialize_database_config(self) -> DatabaseConfig:
        """Initialize database configuration."""
        # Prefer DATABASE_URL if provided
        db_url = self._get_config("DATABASE_URL_DEFAULT", "database.url")
        host = self._get_config("DB_HOST", "database.host", DATABASE_HOST)
        port = self._get_int_config("DB_PORT", "database.port", DATABASE_PORT)
        name = self._get_config("DB_NAME", "database.name", DATABASE_NAME)
        user = self._get_config("DB_USER", "database.user", DATABASE_USER)
        password = self._get_config("DB_PASS", "database.password", DATABASE_PASSWORD)

        # Build a valid PostgreSQL URL if not provided
        if not db_url and all([host, port, name, user, password]):
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        elif not db_url:
            db_url = DATABASE_URL_DEFAULT

        # Create params dict for psycopg2
        params = {
            "dbname": name,
            "user": user,
            "password": password,
            "host": host,
            "port": port,
        }

        # Return DatabaseConfig with url and params
        return DatabaseConfig(
            url=db_url,
            host=host,
            port=port,
            name=name,
            user=user,
            password=password,
            pool_size=self._get_int_config(
                "DATABASE_POOL_SIZE", "database.pool_size", 10
            ),
            max_overflow=self._get_int_config(
                "DATABASE_MAX_OVERFLOW", "database.max_overflow", 20
            ),
            pool_timeout=self._get_int_config(
                "DATABASE_POOL_TIMEOUT", "database.pool_timeout", 30
            ),
            echo=self._get_bool_config("DATABASE_ECHO", "database.echo", False),
            params=params,  # Add this field to your DatabaseConfig dataclass
        )

    def _initialize_lavalink_config(self) -> LavalinkConfig:
        """Initialize Lavalink configuration."""
        return LavalinkConfig(
            enabled=self._get_bool_config("LAVALINK_ENABLED", "lavalink.enabled", True),
            host=self._get_config(
                "LAVALILNK_SERVER", "lavalink.host", LAVALINK_DEFAULT_HOST
            ),
            port=self._get_int_config(
                "LAVALINK_PORT", "lavalink.port", LAVALINK_DEFAULT_PORT
            ),
            password=self._get_config(
                "LAVALINK_PASS", "lavalink.password", LAVALINK_DEFAULT_PASSWORD
            ),
            region=self._get_config("LAVALINK_REGION", "lavalink.region", "us"),
            secure=self._get_bool_config("LAVALINK_SECURE", "lavalink.secure", False),
        )

    def _initialize_music_config(self) -> MusicConfig:
        """Initialize music configuration."""
        return MusicConfig(
            enabled=self._get_bool_config("MUSIC_ENABLED", "music.enabled", True),
            default_volume=self._get_float_config(
                "MUSIC_DEFAULT_VOLUME", "music.default_volume", 0.5
            ),
            max_volume=self._get_float_config(
                "MUSIC_MAX_VOLUME", "music.max_volume", 1.0
            ),
            queue_limit=self._get_int_config(
                "MUSIC_QUEUE_LIMIT", "music.queue_limit", 100
            ),
            search_limit=self._get_int_config(
                "MUSIC_SEARCH_LIMIT", "music.search_limit", 10
            ),
        )

    def _initialize_moderation_config(self) -> ModerationConfig:
        """Initialize moderation configuration."""
        return ModerationConfig(
            enabled=self._get_bool_config(
                "MODERATION_ENABLED", "moderation.enabled", True
            ),
            default_reason=self._get_config(
                "MODERATION_DEFAULT_REASON",
                "moderation.default_reason",
                "No reason provided",
            ),
            log_channel_id=self._get_int_config(
                "MODERATION_LOG_CHANNEL", "moderation.log_channel_id"
            ),
            max_warn_count=self._get_int_config(
                "MODERATION_MAX_WARN_COUNT", "moderation.max_warn_count", 3
            ),
            auto_timeout_duration=self._get_int_config(
                "MODERATION_AUTO_TIMEOUT_DURATION",
                "moderation.auto_timeout_duration",
                600,
            ),
        )

    def _initialize_logging_config(self) -> LoggingConfig:
        """Initialize logging configuration."""
        return LoggingConfig(
            level=self._get_config("LOG_LEVEL", "logging.level", "INFO"),
            format=self._get_config(
                "LOG_FORMAT",
                "logging.format",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            date_format=self._get_config(
                "LOG_DATE_FORMAT", "logging.date_format", "%Y-%m-%d %H:%M:%S"
            ),
            file_path=self._get_config(
                "LOG_FILE",
                "logging.file_path",
                str(PROJECT_ROOT / "logs" / "darkbot.log"),
            ),
            max_bytes=self._get_int_config(
                "LOG_MAX_BYTES", "logging.max_bytes", 10 * 1024 * 1024
            ),
            backup_count=self._get_int_config(
                "LOG_BACKUP_COUNT", "logging.backup_count", 5
            ),
        )

    def _initialize_features(self) -> Dict[str, bool]:
        """Initialize feature flags."""
        features = {}
        for feature, default in FEATURES.items():
            features[feature] = self._get_bool_config(
                feature, f"features.{feature.lower()}", default
            )
        return features

    def _get_config(self, env_key: str, file_key: str, default: Any = None) -> Any:
        """Get configuration value from environment or file."""
        # First check environment variables
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Then check file config
        if file_key in self._file_config:
            return self._file_config[file_key]

        # Check nested file config
        if "." in file_key:
            keys = file_key.split(".")
            value = self._file_config
            try:
                for key in keys:
                    value = value[key]
                return value
            except (KeyError, TypeError):
                pass

        return default

    def _get_bool_config(
        self, env_key: str, file_key: str, default: bool = False
    ) -> bool:
        """Get boolean configuration value."""
        value = self._get_config(env_key, file_key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _get_int_config(
        self, env_key: str, file_key: str, default: Optional[int] = None
    ) -> Optional[int]:
        """Get integer configuration value."""
        value = self._get_config(env_key, file_key, default)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _get_float_config(
        self, env_key: str, file_key: str, default: float = 0.0
    ) -> float:
        """Get float configuration value."""
        value = self._get_config(env_key, file_key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _get_list_config(
        self, env_key: str, file_key: str, default: List[Any] = None
    ) -> List[Any]:
        """Get list configuration value."""
        if default is None:
            default = []

        value = self._get_config(env_key, file_key, default)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to parse as comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]
        return default

    def reload(self) -> None:
        """Reload configuration from environment and file."""
        self._initialize_config()

    def is_owner(self, user_id: int) -> bool:
        """Check if user is a bot owner."""
        return user_id in self.owner_ids

    def get_permission_level(self, level_name: str) -> int:
        """Get permission level by name."""
        return self.permission_levels.get(level_name.upper(), 0)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.token:
            errors.append("Discord token is required")

        if not self.prefix:
            errors.append("Bot prefix cannot be empty")

        if self.music.enabled and not self.music.default_volume:
            errors.append("Music default volume must be set when music is enabled")

        return errors
