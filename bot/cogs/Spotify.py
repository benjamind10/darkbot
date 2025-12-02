"""
Spotify Cog
===========

Handles Spotify integration for searching and displaying track information.
Requires SPOTIFY_API token and database role permissions.
"""

import os
import discord
from discord.ext import commands

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class Spotify(commands.Cog):
    """Spotify integration for track search and playback commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        self.spotify_token = os.getenv("SPOTIFY_API")
        self.spotify_api_url = "https://api.spotify.com/v1"
        self.owner_id = os.getenv("OWNER_ID")

    def is_allowed_user(self, discord_user_id: int) -> bool:
        """
        Check if user has 'music' role in database.
        
        Args:
            discord_user_id (int): Discord user ID to check.
            
        Returns:
            bool: True if user has music role and is enabled.
        """
        try:
            # Use bot's database connection
            if not hasattr(self.bot, 'db_conn'):
                self.logger.warning("Spotify | Database connection not available")
                return False
                
            cursor = self.bot.db_conn.cursor()
            query = """
            SELECT r.name FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.discorduser = %s AND u.isenabled = true;
            """
            cursor.execute(query, (discord_user_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if row and row[0].lower() == "music":
                return True
        except Exception as e:
            self.logger.error(f"Spotify | Error checking user permissions: {e}")
        return False

    async def cog_check(self, ctx):
        """
        Permission check for Spotify commands.
        Only bot owner or users with 'music' role can use these commands.
        """
        if str(ctx.author.id) == self.owner_id:
            return True
        if self.is_allowed_user(ctx.author.id):
            return True
        await ctx.send("❌ You do not have permission to use Spotify commands.")
        return False

    @commands.command(name="spsearch", help="Search for a track on Spotify.")
    async def spsearch(self, ctx, *, query: str):
        """
        Search Spotify for a track and display information.
        
        Usage: !spsearch <track name or artist>
        Example: !spsearch Bohemian Rhapsody
        """
        if not REQUESTS_AVAILABLE:
            await ctx.send("❌ Requests library not installed.")
            return

        if not self.spotify_token:
            await ctx.send("❌ Spotify API token not configured (SPOTIFY_API).")
            return

        try:
            url = f"{self.spotify_api_url}/search"
            params = {
                "q": query,
                "type": "track",
                "limit": 1
            }
            headers = {
                "Authorization": f"Bearer {self.spotify_token}"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                await ctx.send("❌ Failed to reach Spotify API. Please try again later.")
                self.logger.error(f"Spotify | API error: {response.status_code}")
                return
            
            data = response.json()
            tracks = data.get("tracks", {}).get("items", [])
            
            if not tracks:
                await ctx.send("❌ No tracks found.")
                return

            track = tracks[0]
            track_name = track.get("name")
            artists = ", ".join(artist["name"] for artist in track.get("artists", []))
            album = track.get("album", {}).get("name")
            preview_url = track.get("preview_url")
            external_url = track.get("external_urls", {}).get("spotify")
            album_art = track.get("album", {}).get("images", [{}])[0].get("url")

            embed = discord.Embed(
                title=f"{track_name}",
                description=f"by **{artists}**",
                color=0x1DB954  # Spotify green
            )
            embed.add_field(name="Album", value=album, inline=False)
            
            if preview_url:
                embed.add_field(name="Preview URL", value=preview_url, inline=False)
            if external_url:
                embed.add_field(name="Listen on Spotify", value=f"[Open in Spotify]({external_url})", inline=False)
            if album_art:
                embed.set_thumbnail(url=album_art)
            
            await ctx.send(embed=embed)
            self.logger.info(f"Spotify | Search: {ctx.author} | Query: {query}")

        except Exception as e:
            await ctx.send("❌ An error occurred while searching Spotify.")
            self.logger.error(f"Spotify | Search error: {e}")

    @commands.command(name="spplay", help="Play a track from Spotify (placeholder).")
    async def spplay(self, ctx, *, query: str):
        """
        Search for and 'play' a Spotify track.
        
        Note: This is a placeholder command. Full music playback requires
        integration with a music bot like Wavelink or Lavalink.
        
        Usage: !spplay <track name>
        """
        if not REQUESTS_AVAILABLE:
            await ctx.send("❌ Requests library not installed.")
            return

        if not self.spotify_token:
            await ctx.send("❌ Spotify API token not configured (SPOTIFY_API).")
            return

        try:
            url = f"{self.spotify_api_url}/search"
            params = {
                "q": query,
                "type": "track",
                "limit": 1
            }
            headers = {
                "Authorization": f"Bearer {self.spotify_token}"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                await ctx.send("❌ Failed to reach Spotify API. Please try again later.")
                return
            
            data = response.json()
            tracks = data.get("tracks", {}).get("items", [])
            
            if not tracks:
                await ctx.send("❌ No tracks found.")
                return

            track = tracks[0]
            track_name = track.get("name")
            artists = ", ".join(artist["name"] for artist in track.get("artists", []))
            
            # Placeholder - actual playback requires voice client integration
            await ctx.send(f"🎵 Now playing: **{track_name}** by **{artists}** (from Spotify)\n\n⚠️ Note: Full music playback not yet implemented. Use !spsearch to get Spotify links.")
            self.logger.info(f"Spotify | Play request: {ctx.author} | Track: {track_name}")

        except Exception as e:
            await ctx.send("❌ An error occurred while searching Spotify.")
            self.logger.error(f"Spotify | Play error: {e}")


async def setup(bot):
    """Load the Spotify cog."""
    await bot.add_cog(Spotify(bot))
