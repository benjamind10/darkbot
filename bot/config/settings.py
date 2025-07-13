# python
"""
DarkBot Settings and Constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BOT_DIR = PROJECT_ROOT / "bot"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = BOT_DIR / "config"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

# Bot configuration
DEFAULT_PREFIX = "!"
DEFAULT_DESCRIPTION = "DarkBot - A powerful Discord bot"
DEFAULT_ACTIVITY_NAME = "with discord.py"
DEFAULT_ACTIVITY_TYPE = "listening"  # playing, watching, listening, streaming

# Redis Config
REDIS_ENABLED = os.getenv("REDIS_ENABLED", False)
REDDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDDIS_DB = int(os.getenv("REDIS_DB", 0))
REDDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "darkbot:")

# Discord API limits
MAX_MESSAGE_LENGTH = 2000
MAX_EMBED_TITLE_LENGTH = 256
MAX_EMBED_DESCRIPTION_LENGTH = 4096
MAX_EMBED_FIELD_VALUE_LENGTH = 1024
MAX_EMBED_FIELDS = 25
MAX_EMBED_TOTAL_LENGTH = 6000

# Database configuration
DATABASE_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_PORT = int(os.getenv("DB_PORT", 5432))
DATABASE_NAME = os.getenv("DB_NAME", "darkbot")
DATABASE_USER = os.getenv("DB_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DB_PASS", "")
DATABASE_URL_DEFAULT = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
DATABASE_POOL_TIMEOUT = 30

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = LOGS_DIR / "darkbot.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5


# Music configuration
MUSIC_DEFAULT_VOLUME = 0.5
MUSIC_MAX_VOLUME = 1.0
MUSIC_QUEUE_LIMIT = 100
MUSIC_SEARCH_LIMIT = 10
MUSIC_FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# Lavalink configuration
LAVALINK_DEFAULT_HOST = os.getenv("LAVALILNK_SERVER", "lavalink-app")
LAVALINK_DEFAULT_PORT = 2333
LAVALINK_DEFAULT_PASSWORD = os.getenv("LAVALINK_PASS", "youshallnotpass")
LAVALINK_DEFAULT_REGION = "us"

# Moderation configuration
MODERATION_DEFAULT_REASON = "No reason provided"
MODERATION_LOG_CHANNEL = None  # Set via environment or config
MODERATION_MAX_WARN_COUNT = 3
MODERATION_AUTO_TIMEOUT_DURATION = 600  # 10 minutes in seconds

# Rate limiting
RATE_LIMIT_DEFAULT_COOLDOWN = 5  # seconds
RATE_LIMIT_DEFAULT_USES = 1
RATE_LIMIT_BUCKET_TYPE = "user"  # user, guild, channel, member

# API Keys and external services
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0)) if os.getenv("OWNER_ID") else None
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_EMAIL = os.getenv("YOUTUBE_EMAIL")
YOUTUBE_PASSWORD = os.getenv("YOUTUBE_PASS")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASS")
LAVALINK_SERVER = os.getenv("LAVALILNK_SERVER", "lavalink-app")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
CHATGPT_SECRET = os.getenv("CHATGPT_SECRET")
OPENAI_API_KEY = os.getenv("CHATGPT_SECRET")  # Alias for OpenAI API key
API_COINCAP = os.getenv("API_COINCAP")
IP_INFO = os.getenv("IP_INFO")
KSOFT_API = os.getenv("KSOFT_APT")

# Permission levels
PERMISSION_LEVELS = {
    "OWNER": 10,
    "ADMIN": 8,
    "MODERATOR": 6,
    "TRUSTED": 4,
    "MEMBER": 2,
    "EVERYONE": 0,
}

# Embed colors (hex values)
EMBED_COLORS = {
    "DEFAULT": 0x2F3136,
    "SUCCESS": 0x00FF00,
    "ERROR": 0xFF0000,
    "WARNING": 0xFFFF00,
    "INFO": 0x0099FF,
    "MUSIC": 0x1DB954,
    "MODERATION": 0xFF6B00,
}

# Emojis (can be custom or unicode)
EMOJIS = {
    "SUCCESS": "✅",
    "ERROR": "❌",
    "WARNING": "⚠️",
    "INFO": "ℹ️",
    "MUSIC": "🎵",
    "LOADING": "⏳",
    "NEXT": "⏭️",
    "PREVIOUS": "⏮️",
    "PLAY": "▶️",
    "PAUSE": "⏸️",
    "STOP": "⏹️",
    "VOLUME_UP": "🔊",
    "VOLUME_DOWN": "🔉",
    "MUTE": "🔇",
    "LOOP": "🔄",
    "SHUFFLE": "🔀",
}

# Cog settings
# COGS_TO_LOAD = ["cogs.moderation", "cogs.music", "cogs.utility", "cogs.admin"]

# Development settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DEVELOPMENT_GUILD_ID = os.getenv("DEVELOPMENT_GUILD_ID")
SYNC_COMMANDS_ON_STARTUP = (
    os.getenv("SYNC_COMMANDS_ON_STARTUP", "False").lower() == "true"
)

# Feature flags
FEATURES = {
    "MUSIC_ENABLED": os.getenv("MUSIC_ENABLED", "True").lower() == "true",
    "MODERATION_ENABLED": os.getenv("MODERATION_ENABLED", "True").lower() == "true",
    "ECONOMY_ENABLED": os.getenv("ECONOMY_ENABLED", "False").lower() == "true",
    "LEVELING_ENABLED": os.getenv("LEVELING_ENABLED", "False").lower() == "true",
    "AUTOMOD_ENABLED": os.getenv("AUTOMOD_ENABLED", "False").lower() == "true",
}

# Security settings
ALLOWED_MENTIONS_EVERYONE = False
ALLOWED_MENTIONS_USERS = True
ALLOWED_MENTIONS_ROLES = False
ALLOWED_MENTIONS_REPLIED_USER = True

# Cache settings
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_SIZE = 1000
