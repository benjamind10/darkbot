# Music System

DarkBot uses **Wavelink 3.4.1** as a client for a self-hosted **Lavalink** server to provide music playback in voice channels.

## Architecture

```
Discord Voice <-> DarkBot (Wavelink) <-> Lavalink Server <-> YouTube/Spotify/SoundCloud
```

- **Wavelink** handles the client-side connection to Lavalink
- **Lavalink** runs as a separate Java service in Docker, configured via `application.yml`
- The **Music cog** (`bot/cogs/Music.py`) implements all playback commands

## Commands

All commands support both prefix (`!`) and slash (`/`) syntax.

| Command | Aliases | Description |
|---------|---------|-------------|
| `play <query>` | `p` | Play a song or add to queue |
| `pause` | - | Pause/resume playback |
| `skip` | `next` | Skip current track |
| `stop` | - | Stop and disconnect |
| `queue` | `q` | Show current queue |
| `nowplaying` | `np` | Show current track info |
| `volume <0-100>` | `vol` | Set playback volume |
| `disconnect` | `dc`, `leave` | Leave voice channel |
| `clear` | - | Clear the queue |
| `shuffle` | - | Shuffle the queue |

## Supported Sources

- YouTube (including playlists, via Lavalink plugin)
- YouTube Music
- Spotify (tracks and playlists)
- SoundCloud
- Bandcamp
- Twitch streams
- Vimeo
- Direct URLs

## Configuration

### Environment Variables

```bash
LAVALINK_SERVER=http://lavalink:2333  # Lavalink URI (Docker service name)
LAVALINK_PASS=youshallnotpass          # Lavalink password
```

### Lavalink (`application.yml`)

The Lavalink server is configured via `application.yml` in the project root. Key settings:

- **Port:** 2333
- **Password:** `youshallnotpass` (change in production)
- **Sources:** YouTube, SoundCloud, Bandcamp, Twitch, Vimeo, HTTP

### Docker

Lavalink runs as the `lavalink` service in `docker-compose.yml`:
- Image: `ghcr.io/lavalink-devs/lavalink:latest`
- Memory: 2GB max (`_JAVA_OPTIONS=-Xmx2G`)
- Health check on `http://localhost:2333/version`

## YouTube Plugin

YouTube support requires a Lavalink plugin. Options:

### LavaSrc Plugin (Recommended)

```bash
mkdir -p plugins
curl -L -o plugins/LavaSrc-Plugin.jar \
  'https://github.com/topi314/LavaSrc/releases/download/4.3.1/lavasrc-plugin-4.3.1.jar'
```

Mount the plugins directory in `docker-compose.yml` under the lavalink service:
```yaml
volumes:
  - ./plugins:/opt/Lavalink/plugins
```

### Manual YouTube Plugin

1. Download from https://github.com/lavalink-devs/youtube-source/releases
2. Place the `.jar` in `plugins/`
3. Mount the directory as above

### Fallback: SoundCloud

If YouTube isn't configured, use SoundCloud prefix:
```
!play scsearch:eminem mockingbird
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Wavelink not available" | Wavelink package not installed in container |
| "Failed to connect to Lavalink" | Check Lavalink is running: `docker-compose ps` |
| "No tracks found" | YouTube may be rate-limiting; try SoundCloud or a different query |
| "Not connected to voice channel" | Join a voice channel first, check bot permissions |

Check Lavalink logs:
```bash
docker-compose logs -f lavalink
```
