# Music Bot Migration Guide

## Current Status
Your old Music cog used **Lavalink** with the `lavalink.py` library. This is still a viable solution but requires running a separate Lavalink server.

## Modern Alternatives for Discord Music Bots (2025)

### Option 1: Wavelink (Recommended) ✅
**What:** Modern Lavalink wrapper for discord.py 2.x+
**Pros:**
- Actively maintained and modern
- Built specifically for discord.py 2.0+
- Supports Spotify, Apple Music, YouTube, SoundCloud
- Better async/await patterns
- Great documentation

**Setup:**
```bash
pip install wavelink
```

**Requirements:**
- Still needs a Lavalink server running
- Can use free Lavalink hosting or self-host
- Configuration via environment variables

**Free Lavalink Nodes:**
- lavalink.eu (community node)
- lavalink.darrennathanael.com
- Self-host with Docker

### Option 2: Pomice
**What:** Another modern Lavalink wrapper
**Pros:**
- Similar to Wavelink
- Good for complex music systems
- Supports filters and effects

**Cons:**
- Smaller community than Wavelink
- Less documentation

### Option 3: yt-dlp + discord.py (Lightweight)
**What:** Direct YouTube download without external servers
**Pros:**
- No external server needed
- Simple setup
- Works for basic use cases

**Cons:**
- CPU intensive (runs on your bot server)
- Less reliable for high-traffic bots
- YouTube may rate-limit
- No queue management built-in

### Option 4: Use External Music Bot
**What:** Use dedicated music bots (Hydra, Groovy alternatives)
**Pros:**
- Zero maintenance
- Professional features

**Cons:**
- Less control
- Relies on third parties

## Recommended Implementation: Wavelink

### Why Wavelink?
1. **Best maintained** - Regular updates for discord.py changes
2. **Modern Python** - Uses modern async patterns
3. **Feature-rich** - Queues, filters, search, playlists
4. **Free nodes available** - Can test without self-hosting
5. **Easy migration** - Similar concepts to old lavalink.py

### Setup Steps

#### 1. Install Wavelink
```bash
pip install wavelink
```

#### 2. Run Lavalink Server (Choose one):

**Option A: Docker (Easiest)**
```bash
docker run -d \
  -p 2333:2333 \
  --name lavalink \
  -v $(pwd)/application.yml:/opt/Lavalink/application.yml \
  ghcr.io/lavalink-devs/lavalink:latest
```

**Option B: Use Free Node**
No setup needed - use community nodes (see below)

#### 3. Configuration File (`application.yml`)
```yaml
server:
  port: 2333
  address: 0.0.0.0

lavalink:
  server:
    password: "youshallnotpass"
    sources:
      youtube: true
      bandcamp: true
      soundcloud: true
      twitch: true
      vimeo: true
      http: true
      local: false
    filters:
      volume: true
      equalizer: true
      karaoke: true
      timescale: true
      tremolo: true
      vibrato: true
      distortion: true
      rotation: true
      channelMix: true
      lowPass: true
```

#### 4. Environment Variables (.env)
```bash
# Lavalink Configuration
LAVALINK_HOST=localhost  # or lavalink.eu for free node
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass
LAVALINK_HTTPS=False

# Spotify Integration (optional)
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

### Free Lavalink Nodes (No Setup Required)

```python
# In your Music cog:
nodes = [
    {
        "host": "lavalink.eu",
        "port": 2333,
        "password": "youshallnotpass",
        "identifier": "MAIN",
        "https": False
    }
]
```

⚠️ **Note:** Free nodes may have downtime or rate limits. For production, self-host.

## Next Steps

1. **Choose approach:**
   - Wavelink + Free Node (fastest to test)
   - Wavelink + Docker Lavalink (production ready)
   - Simple yt-dlp (if only basic playback needed)

2. **I can create:**
   - Full Wavelink Music cog with queue system
   - Docker compose setup for Lavalink
   - Migration from your old Lavalink setup

3. **Additional features to consider:**
   - Spotify integration
   - Playlists and favorites
   - DJ role permissions
   - Volume controls and filters
   - Now playing embeds

Let me know which approach you'd like to take and I'll implement it!
