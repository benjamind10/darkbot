# Music Bot Setup Guide

## Quick Start (Using Free Lavalink Node)

The Music cog is configured to use a **free public Lavalink node** by default, so you can start using it immediately!

### Install Wavelink

```bash
cd /home/shiva/Documents/code/darkbot
./venv/bin/pip install wavelink
```

### Restart Bot

```bash
cd bot
python main.py
```

### Test Commands

Join a voice channel and try:
```
!play Never Gonna Give You Up
!queue
!skip
!stop
```

---

## Self-Hosted Lavalink (Recommended for Production)

### Option 1: Docker (Easiest)

The Lavalink server is already configured in `docker-compose.yml`.

**Start everything:**
```bash
cd /home/shiva/Documents/code/darkbot
docker-compose up -d
```

**Update Music cog to use local server:**
Edit `bot/cogs/Music.py` line ~36:
```python
nodes = [
    wavelink.Node(
        uri="http://lavalink:2333",  # Change from lavalink.eu
        password="youshallnotpass",
        identifier="MAIN"
    )
]
```

### Option 2: Standalone Lavalink

**Download and run:**
```bash
cd /home/shiva/Documents/code/darkbot
wget https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar
java -jar Lavalink.jar
```

**Update Music cog:**
```python
nodes = [
    wavelink.Node(
        uri="http://localhost:2333",
        password="youshallnotpass",
        identifier="MAIN"
    )
]
```

---

## Configuration

### application.yml

The Lavalink config is in `/home/shiva/Documents/code/darkbot/application.yml`

Key settings:
- **Port:** 2333 (default)
- **Password:** `youshallnotpass` (change in production!)
- **Sources:** YouTube, SoundCloud, Bandcamp, etc.

### Environment Variables (.env)

Optional environment-based config:
```bash
LAVALINK_HOST=localhost
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass
```

---

## Available Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `!play <query>` | `!p` | Play a song or add to queue |
| `!pause` | - | Pause/resume playback |
| `!skip` | `!next` | Skip current track |
| `!stop` | - | Stop and disconnect |
| `!queue` | `!q` | Show queue |
| `!nowplaying` | `!np` | Show current track |
| `!volume <0-100>` | `!vol` | Set volume |
| `!disconnect` | `!dc`, `!leave` | Leave voice |
| `!clear` | - | Clear queue |
| `!shuffle` | - | Shuffle queue |

---

## Supported Sources

✅ YouTube (including playlists)  
✅ YouTube Music  
✅ Spotify (tracks and playlists)  
✅ SoundCloud  
✅ Bandcamp  
✅ Twitch streams  
✅ Vimeo  
✅ Direct URLs  

---

## Troubleshooting

### "Wavelink not installed"
```bash
./venv/bin/pip install wavelink
```

### "Failed to connect to Lavalink"
- **Using free node:** Check if lavalink.eu is up
- **Self-hosted:** Ensure Lavalink is running (`docker-compose ps` or check Java process)
- **Port blocked:** Make sure port 2333 is accessible

### "No tracks found"
- YouTube may be rate-limiting
- Try a different search query
- Check Lavalink logs for errors

### "Not connected to voice channel"
- Bot needs permission to join voice channels
- Check bot's role permissions in Discord

---

## Free Public Nodes

If lavalink.eu is down, try these alternatives:

```python
# In bot/cogs/Music.py, update the nodes list:
nodes = [
    wavelink.Node(
        uri="http://lavalink.darrennathanael.com:80",
        password="whatislavalink",
        identifier="DNAT"
    )
]
```

⚠️ **Note:** Public nodes may have:
- Rate limits
- Downtime
- Restricted features
- Higher latency

For production bots, always self-host Lavalink!

---

## Performance Tips

1. **Self-host Lavalink** for best performance
2. **Adjust buffer settings** in application.yml for your network
3. **Use Redis** for session persistence
4. **Monitor memory** - Lavalink uses ~1-2GB RAM
5. **Enable autoplay** - Already configured in the cog

---

## Next Steps

1. Install wavelink: `./venv/bin/pip install wavelink`
2. Restart bot: `python main.py`
3. Test: Join voice → `!play test song`
4. (Optional) Set up self-hosted Lavalink for production

Enjoy your music bot! 🎵
