# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DarkBot is a Discord bot built with discord.py 2.3.2. It uses a cog-based architecture for modular features (music, moderation, events, board games, ChatGPT integration, etc.). The bot runs in Docker alongside PostgreSQL, Redis, and Lavalink (music server).

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
```

Tests use pytest with pytest-asyncio. HTTP mocking uses aioresponses. Test files live in `tests/`.

## Type Checking

```bash
pyright
```

Configured via `pyrightconfig.json`.

## Architecture

### Bootstrap Flow

`main.py` -> `BotRunner.run()` -> creates `DarkBot` (extends `discord.py Bot`) -> `setup_hook()` initializes Redis, loads cogs dynamically from `bot/cogs/`, connects to PostgreSQL.

### Key Directories

- `bot/core/` - Bot class (`bot.py`), event manager (`events.py`), custom exceptions (`exceptions.py`)
- `bot/cogs/` - Feature modules loaded dynamically at startup (Music, Moderation, Events, Utility, etc.)
- `bot/config/` - `settings.py` (constants/env vars), `config.py` (typed dataclass configs with env->file->default fallback)
- `bot/utils/` - Shared utilities: `redis_manager.py`, `logger.py`, board game helpers, etc.

### Configuration

Configuration uses a three-level fallback: environment variables (`.env`) -> JSON config file -> defaults from `config/settings.py`. The `Config` class in `config/config.py` provides typed dataclass sections: `DatabaseConfig`, `RedisConfig`, `MusicConfig`, `LavalinkConfig`, `ModerationConfig`, `LoggingConfig`.

Feature flags in `settings.py` control which subsystems are active (MUSIC_ENABLED, MODERATION_ENABLED, etc.).

See `.env.example` for required environment variables.

### Services (docker-compose.yml)

- **python-app** - The bot (Python 3.10, mounts `./bot`)
- **lavalink** - Music audio server (configured via `application.yml`)
- **db** - PostgreSQL 16 (schemas: `darkbot.sql`, `events_schema.sql`)
- **redis** - Redis 6 for caching/cooldowns (key prefix: `darkbot:`)

### Event System

`EventManager` in `core/events.py` handles Discord event delegation. DarkBot forwards events (on_ready, on_message, on_command_error, guild/member events) to EventManager which dispatches to registered handlers.

### Music System

Uses Wavelink 3.4.1 as a client for the Lavalink server. Supports YouTube (via Lavalink plugin), Spotify, SoundCloud. The Music cog handles playback commands and Wavelink event listeners.

### Cog Pattern

All cogs extend `commands.Cog`, are placed in `bot/cogs/`, and are auto-discovered and loaded by `DarkBot.load_cogs()`. Command prefix is `!`.

## Important Notes

- `bot/requirements.txt` has corrupted encoding (spaces between characters) - the Dockerfile installs additional packages explicitly to compensate
- Database schemas must be applied manually (`darkbot.sql`, `events_schema.sql`)
- Redis is optional - controlled by `REDIS_ENABLED` env var, bot gracefully falls back if unavailable
- Lavalink host defaults to `lavalink-app` (Docker service name) for containerized runs, override with `LAVALINK_SERVER`
