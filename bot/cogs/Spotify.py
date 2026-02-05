"""
Spotify Cog
===========

Handles Spotify integration for searching and playing tracks.
Uses the Spotify Web API for search and LavaSrc (Lavalink plugin)
for resolving Spotify URLs to playable audio via Wavelink.
"""

import os
import time
import discord
from discord.ext import commands
from typing import cast

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import wavelink
    WAVELINK_AVAILABLE = True
except ImportError:
    WAVELINK_AVAILABLE = False


class Spotify(commands.Cog):
    """Spotify integration for track search and playback commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        self.spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.spotify_api_url = "https://api.spotify.com/v1"
        self._spotify_token = None
        self._spotify_token_expires = 0

    async def _fetch_spotify_token(self):
        """
        Fetch a Spotify access token using the OAuth2 client credentials flow.

        Returns:
            str or None: The access token, or None on failure.
        """
        if not self.spotify_client_id or not self.spotify_client_secret:
            return None

        # Return cached token if still valid (with 60s buffer)
        if self._spotify_token and time.time() < self._spotify_token_expires - 60:
            return self._spotify_token

        url = "https://accounts.spotify.com/api/token"
        data = {"grant_type": "client_credentials"}
        auth = aiohttp.BasicAuth(self.spotify_client_id, self.spotify_client_secret)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, auth=auth, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        self.logger.error(f"Spotify | Token request failed: {resp.status}")
                        return None
                    body = await resp.json()
                    self._spotify_token = body["access_token"]
                    self._spotify_token_expires = time.time() + body.get("expires_in", 3600)
                    self.logger.info("Spotify | Obtained access token via client credentials")
                    return self._spotify_token
        except Exception as e:
            self.logger.error(f"Spotify | Failed to fetch token: {e}")
            return None

    async def _get_token(self, ctx):
        """Get a valid Spotify token, sending an error message if unavailable."""
        if not AIOHTTP_AVAILABLE:
            await ctx.send("Missing `aiohttp` library.")
            return None

        token = await self._fetch_spotify_token()
        if not token:
            await ctx.send("Spotify API credentials not configured. Set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.")
            return None
        return token

    async def _ensure_voice(self, ctx):
        """
        Ensure the bot is connected to the user's voice channel.

        Returns:
            wavelink.Player or None
        """
        if not WAVELINK_AVAILABLE:
            await ctx.send("Wavelink is not available.")
            return None

        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel to play music!")
            return None

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                self.logger.info(f"Spotify | Connected to voice channel: {ctx.author.voice.channel.name}")
            except Exception as e:
                await ctx.send(f"Failed to connect to voice channel: {e}")
                self.logger.error(f"Spotify | Failed to connect: {e}")
                return None

        player.autoplay = wavelink.AutoPlayMode.enabled
        return player

    @commands.hybrid_command(name="spsearch", help="Search for a track on Spotify.")
    async def spsearch(self, ctx, *, query: str):
        """
        Search Spotify for a track and display information.

        Usage: !spsearch <track name or artist>
        """
        token = await self._get_token(ctx)
        if not token:
            return

        try:
            url = f"{self.spotify_api_url}/search"
            params = {"q": query, "type": "track", "limit": 1}
            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        await ctx.send("Failed to reach Spotify API. Please try again later.")
                        self.logger.error(f"Spotify | API error: {resp.status}")
                        return
                    data = await resp.json()

            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                await ctx.send("No tracks found.")
                return

            track = tracks[0]
            track_name = track.get("name")
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            album = track.get("album", {}).get("name")
            external_url = track.get("external_urls", {}).get("spotify")
            album_art = track.get("album", {}).get("images", [{}])[0].get("url")

            embed = discord.Embed(
                title=track_name,
                description=f"by **{artists}**",
                color=0x1DB954,
            )
            embed.add_field(name="Album", value=album, inline=False)
            if external_url:
                embed.add_field(
                    name="Listen on Spotify",
                    value=f"[Open in Spotify]({external_url})",
                    inline=False,
                )
                embed.add_field(
                    name="Play it",
                    value=f"`!play {external_url}`",
                    inline=False,
                )
            if album_art:
                embed.set_thumbnail(url=album_art)

            await ctx.send(embed=embed)
            self.logger.info(f"Spotify | Search: {ctx.author} | Query: {query}")

        except Exception as e:
            await ctx.send("An error occurred while searching Spotify.")
            self.logger.error(f"Spotify | Search error: {e}")

    @commands.hybrid_command(name="spplay", help="Search Spotify and play a track.")
    async def spplay(self, ctx, *, query: str):
        """
        Search Spotify for a track and play it via Wavelink/Lavalink.

        Usage: !spplay <track name>
        """
        token = await self._get_token(ctx)
        if not token:
            return

        player = await self._ensure_voice(ctx)
        if not player:
            return

        # Search Spotify API for the track
        try:
            url = f"{self.spotify_api_url}/search"
            params = {"q": query, "type": "track", "limit": 1}
            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        await ctx.send("Failed to reach Spotify API. Please try again later.")
                        return
                    data = await resp.json()

            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                await ctx.send(f"No tracks found for: `{query}`")
                return

            track_info = tracks[0]
            spotify_url = track_info.get("external_urls", {}).get("spotify")
            track_name = track_info.get("name")
            artists = ", ".join(a["name"] for a in track_info.get("artists", []))

            if not spotify_url:
                await ctx.send("Could not get Spotify URL for this track.")
                return

        except Exception as e:
            await ctx.send("An error occurred while searching Spotify.")
            self.logger.error(f"Spotify | Search error: {e}")
            return

        # Resolve and play via Wavelink (LavaSrc handles Spotify URL resolution)
        try:
            results: wavelink.Search = await wavelink.Playable.search(spotify_url)

            if not results:
                await ctx.send(f"Could not resolve a playable source for **{track_name}** by **{artists}**.")
                return

            if isinstance(results, wavelink.Playlist):
                added: int = await player.queue.put_wait(results)
                await ctx.send(f"Added playlist **{results.name}** with `{added}` tracks to the queue.")
                if not player.playing:
                    await player.play(player.queue.get(), volume=30)
            else:
                track: wavelink.Playable = results[0]
                if player.playing:
                    await player.queue.put_wait(track)
                    await ctx.send(f"Added to queue: **{track_name}** by **{artists}**")
                else:
                    await player.play(track, volume=30)
                    await ctx.send(f"Now playing: **{track_name}** by **{artists}**")

            self.logger.info(f"Spotify | Playing: {ctx.author} | Track: {track_name} by {artists}")

        except Exception as e:
            await ctx.send(f"Failed to play **{track_name}** by **{artists}**: {e}")
            self.logger.error(f"Spotify | Play error: {e}")


async def setup(bot):
    """Load the Spotify cog."""
    await bot.add_cog(Spotify(bot))
