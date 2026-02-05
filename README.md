# DarkBot

A feature-rich Discord bot built with [discord.py](https://discordpy.readthedocs.io/) 2.3.2. Supports both slash commands (`/command`) and prefix commands (`!command`).

## Features

- **Music** - Play from YouTube, Spotify, SoundCloud, and more via Lavalink/Wavelink
- **Moderation** - Ban, kick, warn, purge, role management with full audit logging
- **ModLog** - Automatic logging of message deletes/edits, joins/leaves, bans/kicks to a designated channel
- **Events** - Create server events with RSVP tracking and capacity limits
- **Board Games** - BoardGameGeek collection and search integration
- **Magic: The Gathering** - Card lookup via Scryfall
- **Spotify** - Search and playback controls
- **ChatGPT** - AI chat integration
- **Utility** - Cryptocurrency prices, weather, translation, polls, reminders, and more
- **Info** - Bot stats, ping, uptime, user info

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose

### Setup

```bash
git clone https://github.com/benjamind10/darkbot.git
cd darkbot

# Configure environment
cp bot/.env.example bot/.env
# Edit bot/.env with your Discord token and other credentials

# Start all services
docker-compose up -d

# Apply database schemas
docker-compose exec db psql -U postgres -d darkbot < darkbot.sql
docker-compose exec db psql -U postgres -d darkbot < events_schema.sql
docker-compose exec db psql -U postgres -d darkbot < modlog_schema.sql

# Check logs
docker-compose logs -f python-app
```

### Local Development

```bash
python bot/main.py
```

## Services

| Service | Description |
|---------|-------------|
| `python-app` | The bot (Python 3.10) |
| `lavalink` | Music audio server |
| `db` | PostgreSQL 16 |
| `redis` | Redis 6 (caching/cooldowns) |

## Documentation

| Guide | Description |
|-------|-------------|
| [Configuration](docs/configuration.md) | Environment variables, feature flags, database schemas |
| [Deployment](docs/deployment.md) | Docker setup, monitoring, backups |
| [Music](docs/music.md) | Music system, Lavalink setup, YouTube plugin |
| [ModLog](docs/modlog.md) | Moderation logging, case system, setup |
| [Events](docs/events.md) | Event creation, RSVP system |
| [Testing](docs/testing.md) | Running tests, manual testing, troubleshooting |

## Testing

```bash
pytest              # all tests
pytest -v           # verbose
pyright             # type checking
```

## Contributing

Fork the project, open a PR, or submit issues for suggestions and bugs.

## Contact

- Discord: Shiva187#4664
- Email: benjamind10@pm.me
