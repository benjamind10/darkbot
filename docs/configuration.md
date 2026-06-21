# Configuration

DarkBot uses a three-level configuration fallback: **environment variables** (`.env`) > **JSON config file** > **defaults** in `bot/config/config.py`.

The single runtime front door is the `Config` class in `bot/config/config.py`. Bot code should read configuration through `bot.config` rather than calling `os.getenv` directly.

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
| `BGG_AUTH_COOKIE` | BoardGameGeek private collections (preferred) |
| `BGG_COOKIE` | BoardGameGeek private collections (legacy alias) |
| `YOUTUBE_API_KEY` | YouTube API |

When either `BGG_AUTH_COOKIE` or `BGG_COOKIE` is set, DarkBot sends that session cookie with XML API2 collection requests so private collections can be fetched. `BGG_AUTH_COOKIE` is preferred for new setups; `BGG_COOKIE` is kept as a backward-compatible alias.

### Development

| Variable | Description |
|----------|-------------|
| `DEVELOPMENT_GUILD_ID` | Guild ID for instant slash command sync (dev only) |

## Feature Flags

Feature flags in `bot.config.features` control which subsystems load:

- `MUSIC_ENABLED`
- `MODERATION_ENABLED`
- And others per cog

## Discord Application Settings

DarkBot targets `discord.py==2.6.4` and relies on hybrid commands, gateway intents, and application command sync.

- Enable the `MESSAGE CONTENT INTENT` if you want prefix commands such as `!ping` and `!play` to work.
- Enable the `SERVER MEMBERS INTENT` so moderation and member-event features can see join/leave and role-related state.
- Enable the `GUILD SCHEDULED EVENTS` intent so the scheduled-event listeners in `bot/cogs/Events.py` receive create, update, and delete events.
- Invite the bot with the `applications.commands` scope in addition to `bot` so slash commands can sync and appear in guilds.

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
- `FeatureFlags`
- `ServicesConfig`
