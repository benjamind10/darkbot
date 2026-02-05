# Deployment Guide

## Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose installed
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- PostgreSQL database credentials

## Services

DarkBot runs four Docker containers via `docker-compose.yml`:

| Service | Image | Purpose |
|---------|-------|---------|
| `python-app` | Custom (Dockerfile) | The bot |
| `lavalink` | `ghcr.io/lavalink-devs/lavalink:latest` | Music audio server |
| `db` | `postgres:16` | PostgreSQL database |
| `redis` | `redis:6-alpine` | Caching and cooldowns |

## Setup

### 1. Clone and Configure

```bash
git clone https://github.com/benjamind10/darkbot.git
cd darkbot
cp bot/.env.example bot/.env
```

Edit `bot/.env` with your values. See [configuration.md](configuration.md) for details on each variable.

### 2. Apply Database Schemas

After the database container is running:

```bash
# Start just the database first
docker-compose up -d db

# Apply schemas
docker-compose exec db psql -U postgres -d darkbot < darkbot.sql
docker-compose exec db psql -U postgres -d darkbot < events_schema.sql
docker-compose exec db psql -U postgres -d darkbot < modlog_schema.sql
```

### 3. Start All Services

```bash
docker-compose up -d
```

### 4. Verify

```bash
# Check all containers are running
docker-compose ps

# Watch bot logs
docker-compose logs -f python-app
```

Look for:
```
INFO | DarkBot setup complete
INFO | Synced XX slash command(s) to Discord
```

### 5. Test in Discord

```
/ping
/play <song name>
/help
```

## Updating

```bash
git pull origin main
docker-compose build python-app
docker-compose up -d python-app
```

## Monitoring

```bash
# Live logs
docker-compose logs -f python-app
docker-compose logs -f lavalink

# Resource usage
docker stats

# Restart a service
docker-compose restart python-app
```

## Resource Limits

| Service | Limit |
|---------|-------|
| Lavalink | 2GB RAM (`_JAVA_OPTIONS=-Xmx2G`) |
| All containers | 10MB log max |
| All containers | `restart: unless-stopped` |

## Backup

```bash
# PostgreSQL data
docker run --rm -v darkbot_pgdata:/data -v $(pwd):/backup ubuntu \
  tar czf /backup/pgdata-backup.tar.gz /data

# Redis data
docker run --rm -v darkbot_redisdata:/data -v $(pwd):/backup ubuntu \
  tar czf /backup/redisdata-backup.tar.gz /data
```

## Firewall

Only expose these ports if needed:

| Port | Service | Notes |
|------|---------|-------|
| 2333 | Lavalink | Docker internal only |
| 5432 | PostgreSQL | Docker internal only (unless using remote DB) |
| 6379 | Redis | Bound to `127.0.0.1` |

## Troubleshooting

| Issue | Check |
|-------|-------|
| Bot not responding | `docker-compose ps` and `docker-compose logs python-app` |
| Music not playing | `docker-compose logs lavalink`, verify PyNaCl installed |
| Database errors | Verify `.env` credentials, check schemas are applied |
| Slash commands not appearing | Wait up to 1 hour for global sync, check `applications.commands` OAuth2 scope |
