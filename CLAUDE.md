# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DarkBot is a Discord bot built with discord.py 2.6.4. It uses a cog-based architecture for modular features. All commands are **hybrid commands** supporting both prefix (`!`) and slash (`/`) syntax. The bot runs in Docker alongside PostgreSQL and Redis. Music needs an external Lavalink server: `docker-compose.yml` has no Lavalink service, and compose sets `MUSIC_ENABLED=false`.

## Running the Bot

```bash
# Docker (production)
docker compose up -d          # Compose v2; the legacy docker-compose v1 breaks on container recreate
docker compose logs -f python-app

# Local development
pip install -e ".[dev]"
python bot/main.py
```

Entry point is `bot/main.py` which bootstraps via `BotRunner` -> `DarkBot`.

## Testing

```bash
pytest                              # all tests
pytest tests/test_boardgames.py     # single test file
pytest -v                           # verbose
pyright                             # type checking (configured in pyproject.toml)
```

Tests use pytest with pytest-asyncio. HTTP mocking uses aioresponses. Test files live in `tests/`.
Reusable bot, DB pool, Redis, and aiohttp/aioresponses fixtures live in `tests/conftest.py`.

## Architecture

### Bootstrap Flow

`main.py` -> `BotRunner.run()` -> creates `DarkBot` (extends `discord.py Bot`) -> `setup_hook()` initializes Redis, loads cogs dynamically from `bot/cogs/`, connects to PostgreSQL, syncs slash commands via `self.tree.sync()`.

### Key Directories

- `bot/core/` - Bot class (`bot.py`), event manager (`events.py`), custom exceptions (`exceptions.py`)
- `bot/cogs/` - Feature modules loaded dynamically at startup (12 cogs)
- `bot/config/` - `config.py` (typed dataclass configs with env->file->default fallback)
- `bot/utils/` - Shared utilities: `redis_manager.py`, `logger.py`, board game helpers, etc.
- `docs/` - Documentation (deployment, music, modlog, events, testing, configuration)

### Cogs (bot/cogs/)

| Cog | File | Features |
|-----|------|----------|
| Music | `Music.py` | Playback via Wavelink/Lavalink (play, pause, skip, queue, etc.) |
| Moderation | `Moderation.py` | Ban, kick, warn, purge, role management |
| ModLog | `ModLog.py` | Modlog channel config, case viewing |
| Events | `Events.py` | Guild event creation, RSVP tracking |
| Information | `Information.py` | Bot stats, ping, uptime, help, whois |
| Utility | `Utility.py` | Crypto, weather, translation, polls, reminders |
| BoardGames | `BoardGames.py` | BoardGameGeek search and collection |
| Chatgpt | `Chatgpt.py` | OpenAI chat integration |
| Database | `Database.py` | User management, SQL execution |
| Mtg | `Mtg.py` | Magic: The Gathering card lookup |
| Spotify | `Spotify.py` | Spotify search and playback |
| Owner | `Owner.py` | Bot owner-only commands |

### Configuration

Configuration uses a three-level fallback: environment variables (`.env`) -> JSON config file -> defaults in `config/config.py`. The `Config` class in `config/config.py` provides typed dataclass sections: `DatabaseConfig`, `RedisConfig`, `MusicConfig`, `LavalinkConfig`, `ModerationConfig`, `LoggingConfig`, `FeatureFlags`, and `ServicesConfig`.

All runtime configuration access should go through `bot.config`. Feature flags live at `bot.config.features` and external API keys/secrets live at `bot.config.services`.

See `bot/.env.example` for required environment variables, or `docs/configuration.md` for full reference.

### Services (docker-compose.yml)

- **python-app** - The bot (Python 3.12, mounts `./bot`)
- **db** - PostgreSQL 16 (schemas: `darkbot.sql`, `events_schema.sql`, `modlog_schema.sql`)
- **redis** - Redis 6 for caching/cooldowns (key prefix: `darkbot:`)

### Database Schemas

Three SQL files must be applied to PostgreSQL:

- `darkbot.sql` - Core bot tables
- `events_schema.sql` - Events and RSVPs
- `modlog_schema.sql` - Guild config, moderation logs, message cache

### Event System

`EventManager` in `core/events.py` handles Discord event delegation. It logs events to the modlog channel (if configured) for: message deletes/edits, member joins/leaves/kicks, bans/unbans. The ModLog cog provides the `log_to_modlog()` helper and guild config management.

### Music System

Uses Wavelink 3.4.1 as a client for the Lavalink server. Supports YouTube (via Lavalink plugin), Spotify, SoundCloud. The Music cog handles playback commands and Wavelink event listeners. See `docs/music.md`.

### Slash Commands

All commands use `@commands.hybrid_command` (or `@commands.hybrid_group` for subcommands). Slash commands sync to Discord during `setup_hook()` via `self.tree.sync()`. Both `/command` and `!command` work for all commands.

## Important Notes

- Database schemas must be applied manually (see above)
- Redis is optional - controlled by `REDIS_ENABLED` env var, bot gracefully falls back if unavailable
- Lavalink is not part of `docker-compose.yml`; point `LAVALINK_SERVER` at an external Lavalink host to enable music (`application.yml` is that server's config)
- Runtime code in `bot/` must import `utils.*`, `core.*` and `config.*`, never `bot.*`: the bot runs from inside `bot/` (`main.py` adds it to `sys.path`). `tests/test_runtime_imports.py` enforces this
- `./bot` is bind-mounted into the container, so code-only changes deploy with `git pull` + `docker compose restart python-app`. Rebuild (`docker compose up -d --build python-app`) when dependencies change. `.env` is loaded via `env_file`, so `.env` changes need `docker compose up -d python-app` (a restart does not reload it)
- All new commands should use `@commands.hybrid_command` to support both prefix and slash syntax
- ModLog event logging is in `bot/core/events.py`, config commands are in `bot/cogs/ModLog.py`

## Documentation

See `docs/` for detailed guides:

- `docs/configuration.md` - Environment variables and feature flags
- `docs/deployment.md` - Docker deployment, monitoring, backups
- `docs/music.md` - Music system and Lavalink setup
- `docs/modlog.md` - Moderation logging system
- `docs/events.md` - Events and RSVP system
- `docs/testing.md` - Testing guide
