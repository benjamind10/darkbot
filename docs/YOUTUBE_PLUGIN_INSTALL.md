# YouTube Plugin Installation Guide

## Option 1: Use LavaSrc Plugin (Recommended - Easier)

LavaSrc is a plugin that includes YouTube support along with other sources.

1. **Download LavaSrc plugin:**
   ```bash
   cd /home/shiva/Documents/code/darkbot
   curl -L -o plugins/LavaSrc-Plugin.jar \
     'https://github.com/topi314/LavaSrc/releases/download/4.3.1/lavasrc-plugin-4.3.1.jar'
   ```

2. **Update docker-compose.yml** to mount the plugins directory:
   - Add under lavalink volumes:
     ```yaml
     - ./plugins:/opt/Lavalink/plugins
     ```

3. **Restart Lavalink:**
   ```bash
   docker-compose restart lavalink
   ```

4. **Check logs to verify plugin loaded:**
   ```bash
   docker logs lavalink | grep -i lavasrc
   ```

## Option 2: Manual YouTube Plugin Download

If GitHub releases are accessible:

1. **Visit:** https://github.com/lavalink-devs/youtube-source/releases
2. **Download:** `youtube-plugin-1.9.2.jar` (or latest version)
3. **Save to:** `/home/shiva/Documents/code/darkbot/plugins/`
4. **Mount in docker-compose.yml** (same as Option 1, step 2)
5. **Restart:** `docker-compose restart lavalink`

## Option 3: Use yt-dlp Source (Alternative)

Lavalink can use yt-dlp for YouTube playback:

1. **Install yt-dlp in container** - requires custom Dockerfile
2. **Enable in application.yml:**
   ```yaml
   lavalink:
     server:
       sources:
         youtube: true  # Re-enable with yt-dlp
   ```

## Current Workaround: SoundCloud

While setting up YouTube, use SoundCloud:
```
!play scsearch:eminem mockingbird
!play scsearch:any song name
```

SoundCloud source is already enabled and working in your config.
