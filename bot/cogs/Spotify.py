import os
import requests
import discord
from discord.ext import commands
from db import get_connection  # Ensure this points to your DB connection function

class Spotify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spotify_token = os.getenv("SPOTIFY_API")
        self.spotify_api_url = "https://api.spotify.com/v1"

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
        except Exception as e:
            print("Error checking user permissions:", e)
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

    @commands.command(name="spsearch", help="Search for a track on Spotify.")
    async def spsearch(self, ctx, *, query: str):
        """Searches Spotify for a track and returns details about the first result."""
        url = f"{self.spotify_api_url}/search"
        params = {
            "q": query,
            "type": "track",
            "limit": 1
        }
        headers = {
            "Authorization": f"Bearer {self.spotify_token}"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            await ctx.send("Failed to reach Spotify API. Please try again later.")
            return
        data = response.json()
        tracks = data.get("tracks", {}).get("items", [])
        if not tracks:
            await ctx.send("No tracks found.")
            return

        track = tracks[0]
        track_name = track.get("name")
        artists = ", ".join(artist["name"] for artist in track.get("artists", []))
        album = track.get("album", {}).get("name")
        preview_url = track.get("preview_url")
        external_url = track.get("external_urls", {}).get("spotify")

        embed = discord.Embed(
            title=f"{track_name} by {artists}",
            description=f"Album: {album}",
            color=0x1DB954  # Spotify green
        )
        if preview_url:
            embed.add_field(name="Preview URL", value=preview_url, inline=False)
        if external_url:
            embed.add_field(name="Listen on Spotify", value=external_url, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="spplay", help="Play a track from Spotify (placeholder).")
    async def spplay(self, ctx, *, query: str):
        """
        Searches for a track on Spotify and 'plays' it.
        Note: This is a placeholder; integrating playback with a voice client requires further implementation.
        """
        url = f"{self.spotify_api_url}/search"
        params = {
            "q": query,
            "type": "track",
            "limit": 1
        }
        headers = {
            "Authorization": f"Bearer {self.spotify_token}"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            await ctx.send("Failed to reach Spotify API. Please try again later.")
            return
        data = response.json()
        tracks = data.get("tracks", {}).get("items", [])
        if not tracks:
            await ctx.send("No tracks found.")
            return

        track = tracks[0]
        track_name = track.get("name")
        artists = ", ".join(artist["name"] for artist in track.get("artists", []))
        # Placeholder: Here you would integrate with your voice client or playback system.
        await ctx.send(f"Now playing: **{track_name}** by **{artists}** (from Spotify)")

async def setup(bot):
    await bot.add_cog(Spotify(bot))
