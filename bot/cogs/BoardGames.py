import re
import os
import discord
from discord.ext import commands
import aiohttp
import xml.etree.ElementTree as ET  # For XML parsing

from logging_files.boardgames_logging import logger


class BoardGames(commands.Cog):
    BASE_URL = "https://api.geekdo.com/xmlapi/"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["bgcount"])
    async def boardgame_count(self, ctx):
        """Check how many boardgames are in the DB."""
        try:
            if not hasattr(self.bot, "conn"):
                await ctx.send("Database connection not established.")
                logger.warning(
                    "Attempted to access database without an established connection."
                )
                return

            with self.bot.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM BoardGames;")
                record = cursor.fetchone()

            if record:
                await ctx.send(f"There are: {record[0]} Board Games in the Database.")
                logger.info(
                    f"Successfully retrieved boardgame count: {record[0]}")
            else:
                await ctx.send("Unable to fetch database record.")
                logger.error(
                    "Failed to fetch boardgame count from the database.")
        except Exception as e:
            await ctx.send(f"Error checking the database: {e}")
            logger.error(f"Error checking the database: {e}")

    @commands.command(aliases=["bgsearch"])
    async def search_boardgame(self, ctx, *, search_query: str):
        """Search for a board game on BoardGameGeek. Returns the top 5 results with names and object IDs."""
        search_url = f"{self.BASE_URL}search?search={search_query}"
        logger.info(f"Searching for board games with query: {search_query}")

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)

                    games = []
                    for item in root.findall("boardgame")[
                        :5
                    ]:  # Limit to the first 5 results
                        game_name = (
                            item.find("name").text
                            if item.find("name") is not None
                            else "Unknown"
                        )
                        object_id = item.get("objectid")
                        games.append(f"{game_name} (ID: {object_id})")

                    if games:
                        # Create an embed for the search results
                        embed = discord.Embed(
                            color=self.bot.embed_color,
                            title=f"Top 5 search results for '{search_query}'",
                            description="",
                        )
                        for game in games:
                            # Since embed fields can't be empty, we use a zero-width space as placeholder if needed
                            embed.add_field(
                                name=game.split(" (ID: ")[0],
                                value=f"ID: {game.split(' (ID: ')[1][:-1]}",
                                inline=False,
                            )

                        await ctx.send(embed=embed)
                        logger.info("Search completed successfully.")
                    else:
                        message = "No games found."
                        logger.warning("Search completed but found no games.")
                        await ctx.send(message)
                else:
                    message = "Failed to retrieve search results."
                    await ctx.send(message)
                    logger.error(
                        f"Failed to retrieve search results from the API with status code {response.status}."
                    )

    @commands.command(aliases=["bginfo"])
    async def boardgame_info(self, ctx, game_id: str):
        """Fetch information for a board game by its BoardGameGeek ID, including ratings and recommended player count."""
        logger.info(f"Fetching info for game ID: {game_id}")
        info_url = f"{self.BASE_URL}boardgame/{game_id}?stats=1"

        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)

                    game = root.find("boardgame")
                    if game is not None:
                        game_name = "Unknown"
                        for name in game.findall("name"):
                            if name.get("primary") == "true":
                                game_name = name.text
                                logger.info(
                                    f"Game found: {game_name} (ID: {game_id})")
                                break

                        age = (
                            game.find("age").text
                            if game.find("age") is not None
                            else "N/A"
                        )

                        poll = game.find("poll[@name='suggested_numplayers']")
                        best_count = "N/A"
                        max_best_votes = -1
                        if poll is not None:
                            for results in poll.findall("results"):
                                numplayers = results.get("numplayers")
                                best_votes = int(
                                    results.find("result[@value='Best']").get(
                                        "numvotes"
                                    )
                                )
                                if best_votes > max_best_votes:
                                    max_best_votes = best_votes
                                    best_count = numplayers

                        ratings = game.find("statistics/ratings")
                        users_rated = (
                            ratings.find("usersrated").text
                            if ratings.find("usersrated") is not None
                            else "N/A"
                        )
                        average_rating = (
                            ratings.find("average").text
                            if ratings.find("average") is not None
                            else "N/A"
                        )
                        if average_rating != "N/A":
                            average_rating = "{:.2f}".format(
                                float(average_rating))

                        embed = discord.Embed(
                            color=self.bot.embed_color,
                            title=f"**{game_name}**",
                            description=(
                                f"**ID:** {game_id}\n"
                                f"**Recommended Age:** {age}+\n"
                                f"**Recommended Player Count:** {best_count}\n"
                                f"**Users Rated:** {users_rated}\n"
                                f"**Average Rating:** {average_rating}\n"
                            ),
                        )
                        await ctx.send(embed=embed)
                    else:
                        message = "Game not found."
                        await ctx.send(message)
                        logger.warning(f"Game ID {game_id} not found.")
                else:
                    await ctx.send("Failed to retrieve game information.")
                    logger.error(
                        f"Failed to retrieve game information for ID {game_id} with status code {response.status}."
                    )


async def setup(client):
    await client.add_cog(BoardGames(client))
