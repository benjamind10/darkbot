# Digital Ocean Deployment Guide

## ✅ Pre-Deployment Checklist

Your refactor branch is ready for production! Here's what's configured:

### Working Features
- ✅ All 12 cogs migrated and functional
- ✅ Music bot with YouTube support (Wavelink + Lavalink)
- ✅ PostgreSQL database integration
- ✅ Redis caching
- ✅ Docker Compose setup
- ✅ PyNaCl for voice support
- ✅ Custom help command
- ✅ Event system & error handling

### Required Dependencies
All installed in `bot/requirements.txt`:
- discord.py==2.3.2
- wavelink==3.4.1
- PyNaCl==1.6.1 (for voice)
- psycopg2==2.9.1 (PostgreSQL)
- redis==6.2.0
- All utility dependencies

## 🚀 Deployment Steps

### 1. Merge to Main Branch

```bash
git add .
git commit -m "Refactor complete: all cogs migrated, music bot working"
git push origin refactor

# On GitHub, create PR from refactor -> main and merge
# OR merge locally:
git checkout main
git merge refactor
git push origin main
```

### 2. Digital Ocean Setup

On your Digital Ocean droplet:

```bash
# SSH into your server
ssh root@your-droplet-ip

# Clone/pull your repository
cd /opt
git clone https://github.com/benjamind10/darkbot.git
# OR if already exists:
cd /opt/darkbot
git pull origin main

# Create .env file
cp bot/.env.example bot/.env
nano bot/.env  # Fill in your actual values
```

### 3. Environment Variables

Edit `bot/.env` with your production values:

```bash
# Discord
DISCORD_TOKEN=your_discord_bot_token
OWNER_ID=your_discord_user_id

# Database (use your existing Digital Ocean PostgreSQL)
DB_HOST=104.236.193.213
DB_PORT=5432
DB_NAME=darkbot
DB_USER=postgres
DB_PASS=your_db_password

# Redis (will use Docker container)
REDIS_ENABLED=true
REDIS_HOST=redis  # Docker service name
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Optional APIs
IP_INFO=your_ipinfo_token
API_COINCAP=your_coincap_key
# ... other API keys
```

### 4. Docker Deployment

```bash
cd /opt/darkbot

# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f python-app
docker-compose logs -f lavalink

# Verify all containers running
docker-compose ps
```

### 5. Verify Deployment

Test these commands in Discord:
- `!help` - Should show all commands
- `!info` - Bot stats
- `!play eminem` - Music playback
- `!ping` - Check latency

## 🔧 Production Considerations

### 1. Database
You're using your existing PostgreSQL at `104.236.193.213:5432`. The docker-compose includes a postgres service but you can remove it if you only want to use your remote DB.

### 2. Lavalink Password
Change the default password in:
- `application.yml`: `password: "youshallnotpass"`
- `bot/cogs/Music.py`: `password="youshallnotpass"`
- Or use environment variable (recommended)

### 3. Firewall Rules
Ensure these ports are accessible:
- Lavalink: 2333 (only from localhost/Docker network)
- PostgreSQL: 5432 (only if using Docker DB)
- Redis: 6379 (only from localhost/Docker network)

### 4. Resource Limits
Current setup:
- Lavalink: 2GB RAM (`_JAVA_OPTIONS=-Xmx2G`)
- Logs: max 10MB per container
- Restart policy: `unless-stopped` (auto-restart on crash)

### 5. Monitoring

```bash
# View logs
docker-compose logs -f python-app
docker-compose logs -f lavalink

# Check resource usage
docker stats

# Restart specific service
docker-compose restart python-app
docker-compose restart lavalink
```

## 🆘 Troubleshooting

### Music not playing
1. Check PyNaCl installed: `docker exec -it darkbot-python-app-1 pip list | grep PyNaCl`
2. Check Lavalink logs: `docker logs lavalink`
3. Verify YouTube plugin loaded: `docker logs lavalink | grep youtube`

### Database connection issues
1. Verify `.env` has correct DB credentials
2. Test connection: `docker exec -it darkbot-python-app-1 python -c "import psycopg2; print('OK')"`
3. Check PostgreSQL is accepting connections from your droplet IP

### Bot not responding
1. Check bot is running: `docker-compose ps`
2. Check logs for errors: `docker-compose logs python-app`
3. Restart: `docker-compose restart python-app`

## 📝 Maintenance

### Update bot code
```bash
cd /opt/darkbot
git pull origin main
docker-compose restart python-app
```

### Update dependencies
```bash
# Rebuild the image
docker-compose build python-app
docker-compose up -d python-app
```

### Backup
```bash
# Backup volumes
docker run --rm -v darkbot_pgdata:/data -v $(pwd):/backup ubuntu tar czf /backup/pgdata-backup.tar.gz /data
docker run --rm -v darkbot_redisdata:/data -v $(pwd):/backup ubuntu tar czf /backup/redisdata-backup.tar.gz /data
```

## ✨ What Changed in Refactor

### New Cogs
- `Chatgpt.py` - OpenAI integration
- `Events.py` - Guild join/leave tracking
- `Moderation.py` - Full moderation suite
- `Mtg.py` - Magic: The Gathering card lookup
- `Music.py` - Modern Wavelink-based music bot
- `Spotify.py` - Spotify integration
- `Utility.py` - Crypto, weather, translation, etc.

### Enhanced Cogs
- `Information.py` - Added custom help command

### Infrastructure
- Modern Wavelink 3.4.1 (replaced deprecated Lavalink library)
- Local Lavalink server with YouTube plugin
- Improved shutdown handling
- Better error handling and logging

## 🎉 You're Ready!

Everything is configured and tested. When you deploy to Digital Ocean:
1. All cogs will load automatically
2. Music bot will work out of the box
3. Database/Redis connections will work via Docker networking
4. Auto-restart on crashes

Good luck with your deployment! 🚀
