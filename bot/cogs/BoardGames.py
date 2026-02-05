"""
BoardGames Cog
===============

Handles board game related commands, including integration with BoardGameGeek (BGG).
"""

import re
import discord
from discord.ext import commands
import aiohttp
import xml.etree.ElementTree as ET

from utils import boardgames as bg_utils


class BoardGames(commands.Cog):
    BASE_URL = "https://api.geekdo.com/xmlapi/"

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis_manager

    async def _send_paginated_embeds(self, ctx, games, title, color):
        """
        Helper function to send a paginated embed message list to Discord.

        Args:
            ctx (commands.Context): The command context.
            games (List[str]): List of game description strings.
            title (str): Embed title.
            color (discord.Color): Embed color.
        """
        EMBED_MAX_DESC_LENGTH = 2048
        EMBED_MAX_FIELDS = 25

        pages = []
        current_page = []
        current_length = 0

        for game in games:
            if (
                current_length + len(game) > EMBED_MAX_DESC_LENGTH
                or len(current_page) >= EMBED_MAX_FIELDS
            ):
                pages.append(current_page)
                current_page = []
                current_length = 0
            current_page.append(game)
            current_length += len(game)

        if current_page:
            pages.append(current_page)

        for i, page in enumerate(pages):
            description = "\n".join(page)
            embed = discord.Embed(
                title=f"{title} (Page {i+1} of {len(pages)})",
                description=description,
                color=color,
            )
            await ctx.send(embed=embed)
            self.bot.logger.info(f"Sent page {i+1} of {len(pages)} for {title}")

    @commands.hybrid_command(
        name="bgsearch", help="Search BGG for board games. Example: !bgsearch Catan"
    )
    async def search_boardgame(self, ctx, *, search_query: str):
        """
        Searches the BoardGameGeek (BGG) API for a board game by name.

        Args:
            ctx (commands.Context): The command context.
            search_query (str): The name or keyword to search.
        """
        search_url = f"{self.BASE_URL}search?search={search_query}"
        self.bot.logger.info(f"BGG search query: {search_query}")

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    games = []
                    for item in root.findall("boardgame")[:5]:
                        name = item.find("name")
                        game_name = name.text if name is not None else "Unknown"
                        object_id = item.get("objectid")
                        games.append((game_name, object_id))

                    if games:
                        embed = discord.Embed(
                            color=self.bot.embed_color,
                            title=f"Top 5 search results for '{search_query}'",
                        )
                        for game_name, obj_id in games:
                            embed.add_field(
                                name=game_name,
                                value=f"ID: {obj_id}",
                                inline=False,
                            )
                        await ctx.send(embed=embed)
                        self.bot.logger.info("BGG search succeeded")
                    else:
                        await ctx.send("No games found.")
                        self.bot.logger.warning("No results from BGG search")
                else:
                    self.bot.logger.error(
                        f"BGG search failed, status: {response.status}"
                    )
                    await ctx.send("Failed to retrieve search results from BGG.")

    @commands.hybrid_command(
        name="bginfo", help="Get BGG board game details by ID. Example: !bginfo 12345"
    )
    async def boardgame_info(self, ctx, game_id: str):
        """
        Fetches detailed info from BGG by a game's object ID.

        Args:
            ctx (commands.Context): The command context.
            game_id (str): The BGG object ID.
        """
        self.bot.logger.info(f"Fetching BGG info for ID: {game_id}")
        info_url = f"{self.BASE_URL}boardgame/{game_id}?stats=1"

        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    game = root.find("boardgame")
                    if game is not None:
                        game_name = next(
                            (
                                n.text
                                for n in game.findall("name")
                                if n.get("primary") == "true"
                            ),
                            "Unknown",
                        )
                        age = game.findtext("age", default="N/A")
                        poll = game.find("poll[@name='suggested_numplayers']")
                        best_count = "N/A"
                        max_votes = -1
                        if poll:
                            for res in poll.findall("results"):
                                votes = int(
                                    res.find("result[@value='Best']").get("numvotes")
                                )
                                if votes > max_votes:
                                    max_votes = votes
                                    best_count = res.get("numplayers")

                        ratings = game.find("statistics/ratings")
                        users_rated = ratings.findtext("usersrated", default="N/A")
                        avg_rating = ratings.findtext("average", default="N/A")
                        avg_rating = (
                            f"{float(avg_rating):.2f}"
                            if avg_rating != "N/A"
                            else avg_rating
                        )

                        embed = discord.Embed(
                            color=self.bot.embed_color,
                            title=f"**{game_name}**",
                            description=(
                                f"**ID:** {game_id}\n"
                                f"**Recommended Age:** {age}+\n"
                                f"**Best Player Count:** {best_count}\n"
                                f"**Users Rated:** {users_rated}\n"
                                f"**Average Rating:** {avg_rating}"
                            ),
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Game not found.")
                        self.bot.logger.warning(f"No game found for ID {game_id}")
                else:
                    await ctx.send("Failed to retrieve game info from BGG.")
                    self.bot.logger.error(
                        f"BGG info fetch failed for {game_id}, status: {response.status}"
                    )

    @commands.hybrid_command(
        name="bggcollection", help="Fetch a BGG user's collection by username."
    )
    async def bgg_collection(self, ctx, username: str):
        """
        Fetches the board game collection of a BGG user who owns games.

        Args:
            ctx (commands.Context): The command context.
            username (str): BGG username.
        """
        collection_url = f"{self.BASE_URL}collection/{username}?own=1&stats=1"
        self.bot.logger.info(f"Fetching BGG collection for: {username}")

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(collection_url)
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)
                    games = []
                    for item in root.findall("item"):
                        name = item.findtext("name", default="Unknown")
                        bggid = item.attrib.get("objectid", "N/A")
                        stats = item.find("stats")
                        avg_rating_elem = item.find("statistics/ratings/average")
                        avg_rating = (
                            avg_rating_elem.attrib.get("value", "N/A")
                            if avg_rating_elem is not None
                            else "N/A"
                        )
                        min_players = stats.attrib.get("minplayers", "N/A")
                        max_players = stats.attrib.get("maxplayers", "N/A")
                        max_playtime = stats.attrib.get("maxplaytime", "N/A")
                        games.append(
                            f"{name} (ID: {bggid}, Avg Rating: {avg_rating}, Players: {min_players}-{max_players}, Playtime: {max_playtime} mins)"
                        )

                    await self._send_paginated_embeds(
                        ctx, games, f"{username}'s BGG Collection", self.bot.embed_color
                    )
                    self.bot.logger.info(f"Collection fetched for {username}")
                elif response.status == 202:
                    await ctx.send(
                        f"Collection for {username} is being prepared. Try again later."
                    )
                    self.bot.logger.warning(f"BGG collection preparing for {username}")
                else:
                    await ctx.send("Failed to fetch collection.")
                    self.bot.logger.error(
                        f"Failed fetch for BGG {username}, status: {response.status}"
                    )
            except Exception as e:
                self.bot.logger.exception(
                    f"Error fetching BGG collection for {username}: {e}"
                )
                await ctx.send("An error occurred during fetch.")

    @commands.hybrid_command(
        name="manualbggupdate", help="Trigger manual BGG update for all users."
    )
    async def manual_bgg_update(self, ctx):
        """
        Manually triggers the process to update all users' BGG collections.
        """
        await ctx.send("Starting manual update of BGG collections. Please wait...")
        try:
            await bg_utils.process_bgg_users(self.bot.db_conn, self.bot.logger)
            await ctx.send("BGG collections updated successfully.")
            self.bot.logger.info("Manual BGG update completed.")
        except Exception as e:
            await ctx.send(f"Failed to update BGG collections: {str(e)}")
            self.bot.logger.error(f"Manual BGG update failed: {str(e)}")


async def setup(bot):
    """Register the Boardgames cog with the bot."""
    await bot.add_cog(BoardGames(bot))
