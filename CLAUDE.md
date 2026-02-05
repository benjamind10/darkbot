# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DarkBot is a Discord bot built with discord.py 2.3.2. It uses a cog-based architecture for modular features. All commands are **hybrid commands** supporting both prefix (`!`) and slash (`/`) syntax. The bot runs in Docker alongside PostgreSQL, Redis, and Lavalink (music server).

## Running the Bot

```bash
# Docker (production)
docker-compose up -d
docker-compose logs -f python-app

# Local development
python bot/main.py
```

Entry point is `bot/main.py` which bootstraps via `BotRunner` -> `DarkBot`.

## Testing

```bash
pytest                              # all tests
pytest tests/test_boardgames.py     # single test file
pytest -v                           # verbose
pyright                             # type checking (pyrightconfig.json)
```

Tests use pytest with pytest-asyncio. HTTP mocking uses aioresponses. Test files live in `tests/`.

## Architecture

### Bootstrap Flow

`main.py` -> `BotRunner.run()` -> creates `DarkBot` (extends `discord.py Bot`) -> `setup_hook()` initializes Redis, loads cogs dynamically from `bot/cogs/`, connects to PostgreSQL, syncs slash commands via `self.tree.sync()`.

### Key Directories

- `bot/core/` - Bot class (`bot.py`), event manager (`events.py`), custom exceptions (`exceptions.py`)
- `bot/cogs/` - Feature modules loaded dynamically at startup (13 cogs)
- `bot/config/` - `settings.py` (constants/env vars), `config.py` (typed dataclass configs with env->file->default fallback)
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

Configuration uses a three-level fallback: environment variables (`.env`) -> JSON config file -> defaults from `config/settings.py`. The `Config` class in `config/config.py` provides typed dataclass sections: `DatabaseConfig`, `RedisConfig`, `MusicConfig`, `LavalinkConfig`, `ModerationConfig`, `LoggingConfig`.

Feature flags in `settings.py` control which subsystems are active (MUSIC_ENABLED, MODERATION_ENABLED, etc.).

See `bot/.env.example` for required environment variables, or `docs/configuration.md` for full reference.

### Services (docker-compose.yml)

- **python-app** - The bot (Python 3.10, mounts `./bot`)
- **lavalink** - Music audio server (configured via `application.yml`)
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

- `bot/requirements.txt` has corrupted encoding (spaces between characters) - the Dockerfile installs additional packages explicitly to compensate
- Database schemas must be applied manually (see above)
- Redis is optional - controlled by `REDIS_ENABLED` env var, bot gracefully falls back if unavailable
- Lavalink host defaults to `lavalink` (Docker service name) for containerized runs, override with `LAVALINK_SERVER`
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
