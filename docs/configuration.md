# Configuration

DarkBot uses a three-level configuration fallback: **environment variables** (`.env`) > **JSON config file** > **defaults** from `bot/config/settings.py`.

## Environment Variables

Copy `bot/.env.example` to `bot/.env` and fill in your values.

### Required

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Discord bot token |
| `OWNER_ID` | Your Discord user ID |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASS` | Database password |

### Music / Lavalink

| Variable | Default | Description |
|----------|---------|-------------|
| `LAVALINK_SERVER` | `http://lavalink:2333` | Lavalink server URI |
| `LAVALINK_PASS` | `youshallnotpass` | Lavalink password |

### Redis (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_ENABLED` | `true` | Enable Redis caching |
| `REDIS_HOST` | `redis` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | - | Redis password |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_KEY_PREFIX` | `darkbot:` | Key prefix |

### API Keys (Optional)

| Variable | Feature |
|----------|---------|
| `CHATGPT_SECRET` | ChatGPT integration |
| `SPOTIFY_CLIENT_ID` | Spotify search/playback |
| `SPOTIFY_CLIENT_SECRET` | Spotify search/playback |
| `WEATHER_API_KEY` | Weather command |
| `API_COINCAP` | Cryptocurrency commands |
| `IP_INFO` | IP lookup command |
| `BGG_COOKIE` | BoardGameGeek private collections |
| `YOUTUBE_API_KEY` | YouTube API |

### Development

| Variable | Description |
|----------|-------------|
| `DEVELOPMENT_GUILD_ID` | Guild ID for instant slash command sync (dev only) |

## Feature Flags

Feature flags in `bot/config/settings.py` control which subsystems load:

- `MUSIC_ENABLED`
- `MODERATION_ENABLED`
- And others per cog

## Database Schemas

Three SQL schema files must be applied to PostgreSQL:

| File | Purpose |
|------|---------|
| `darkbot.sql` | Core bot tables (users, etc.) |
| `events_schema.sql` | Events and RSVPs |
| `modlog_schema.sql` | Guild config, moderation logs, message cache |

## Config Classes

The `Config` class in `bot/config/config.py` provides typed dataclass sections:

- `DatabaseConfig`
- `RedisConfig`
- `MusicConfig`
- `LavalinkConfig`
- `ModerationConfig`
- `LoggingConfig`
