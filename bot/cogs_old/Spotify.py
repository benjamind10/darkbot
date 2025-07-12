import os
import base64
import logging
import datetime
import aiohttp
import discord
from discord.ext import commands
from db import get_connection

logger = logging.getLogger(__name__)


class Spotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.spotify_api_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/api/token"
        self.token = None
        self.token_expires = None  # datetime of token expiration
        # aiohttp session for reuse
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        # Close aiohttp session when cog is unloaded
        await self.session.close()

    async def get_spotify_token(self) -> str:
        """
        Retrieves and caches a Spotify access token using Client Credentials flow.
        """
        now = datetime.datetime.utcnow()
        # Return cached token if still valid
        if self.token and self.token_expires and now < self.token_expires:
            return self.token

        # Encode credentials
        if not self.client_id or not self.client_secret:
            logger.error("Spotify client credentials not set.")
            raise commands.CommandError("Spotify credentials are not configured.")
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        try:
            async with self.session.post(
                self.auth_url, headers=headers, data=data
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Failed to get Spotify token: {resp.status} {text}")
                    raise commands.CommandError("Could not authenticate with Spotify.")
                obj = await resp.json()
                self.token = obj.get("access_token")
                expires_in = obj.get("expires_in", 3600)
                # Set expiry a bit earlier to account for delays
                self.token_expires = now + datetime.timedelta(seconds=expires_in - 60)
                return self.token
        except Exception as e:
            logger.exception("Exception while fetching Spotify token")
            raise commands.CommandError("Error retrieving Spotify token.")

    def is_allowed_user(self, discord_user_id: int) -> bool:
        """
        Checks the database to see if the user has the 'music' role.
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
            SELECT r.name FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.discorduser = %s AND u.isenabled = true;
            """
            cursor.execute(query, (discord_user_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row and row[0].lower() == "music":
                return True
        except Exception:
            logger.exception("Error checking user permissions")
        return False

    async def cog_check(self, ctx):
        """
        Allows only the bot owner or users with the 'music' role to use these commands.
        """
        owner_id = os.getenv("OWNER_ID")
        if str(ctx.author.id) == owner_id:
            return True
        if self.is_allowed_user(ctx.author.id):
            return True
        await ctx.send("You do not have permission to use Spotify commands.")
        return False

    async def join_voice(self, ctx) -> discord.VoiceClient:
        """
        Ensures the bot joins the author's voice channel.
        """
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError("Join a voice channel first.")
        if ctx.voice_client is None:
            return await ctx.author.voice.channel.connect()
        return ctx.voice_client

    @commands.command(name="spsearch", help="Search for a track on Spotify.")
    async def spsearch(self, ctx, *, query: str):
        """Searches Spotify for a track and returns details about the first result."""
        try:
            token = await self.get_spotify_token()
            url = f"{self.spotify_api_url}/search"
            params = {"q": query, "type": "track", "limit": 1}
            headers = {"Authorization": f"Bearer {token}"}

            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Spotify search failed: {resp.status} {text}")
                    return await ctx.send(
                        "Failed to reach Spotify API. Please try again later."
                    )
                data = await resp.json()

            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                return await ctx.send("No tracks found.")

            track = tracks[0]
            track_name = track.get("name")
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            album = track.get("album", {}).get("name")
            preview_url = track.get("preview_url")
            external_url = track.get("external_urls", {}).get("spotify")

            embed = discord.Embed(
                title=f"{track_name} by {artists}",
                description=f"Album: {album}",
                color=0x1DB954,
            )
            if preview_url:
                embed.add_field(name="Preview URL", value=preview_url, inline=False)
            if external_url:
                embed.add_field(
                    name="Listen on Spotify", value=external_url, inline=False
                )
            await ctx.send(embed=embed)
        except commands.CommandError as e:
            await ctx.send(str(e))
        except Exception:
            logger.exception("Error in spsearch command")
            await ctx.send("An unexpected error occurred while searching Spotify.")

    @commands.command(
        name="spplay", help="Play a track from Spotify (via YouTube fallback)."
    )
    async def spplay(self, ctx, *, query: str):
        """
        Searches for a track on Spotify, finds a YouTube match, and plays it in the voice channel.
        """
        try:
            voice = await self.join_voice(ctx)
            token = await self.get_spotify_token()
            url = f"{self.spotify_api_url}/search"
            params = {"q": query, "type": "track", "limit": 1}
            headers = {"Authorization": f"Bearer {token}"}

            # Search Spotify
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Spotify search failed: {resp.status} {text}")
                    return await ctx.send(
                        "Failed to reach Spotify API. Please try again later."
                    )
                data = await resp.json()

            tracks = data.get("tracks", {}).get("items", [])
            if not tracks:
                return await ctx.send("No tracks found.")

            track = tracks[0]
            title = f"{track['name']} - {track['artists'][0]['name']}"

            # Fallback to YouTube search
            youtube_url = await self.search_youtube_url(title)
            if not youtube_url:
                return await ctx.send("Could not find the track on YouTube.")

            # Play in voice
            voice.play(discord.FFmpegPCMAudio(youtube_url))
            await ctx.send(f"Now playing: **{title}**")
        except commands.CommandError as e:
            await ctx.send(str(e))
        except Exception:
            logger.exception("Error in spplay command")
            await ctx.send(
                "An unexpected error occurred while attempting to play music."
            )

    async def search_youtube_url(self, query: str) -> str:
        """
        Searches YouTube for the query and returns the direct audio URL using yt_dlp.
        """
        import yt_dlp

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                entries = info.get("entries")
                if entries:
                    return entries[0].get("url")
        except Exception:
            logger.exception("YouTube search failed")
        return None


async def setup(bot):
    await bot.add_cog(Spotify(bot))
