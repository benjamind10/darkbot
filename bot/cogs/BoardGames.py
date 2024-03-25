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
            # Ensure the bot has an active database connection
            if not hasattr(self.bot, "conn"):
                await ctx.send("Database connection not established.")
                return

            # Execute a query to get the database version
            with self.bot.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM BoardGames;")
                record = cursor.fetchone()

            # Send the database version to the context channel
            if record:
                await ctx.send(f"There are: {record[0]} Board Games in the Database.")
            else:
                await ctx.send("Unable to fetch database record.")

        except Exception as e:
            await ctx.send(f"Error checking the database: {e}")

    @commands.command(aliases=["bgsearch"])
    async def search_boardgame(self, ctx, *, search_query: str):
        """Search for a board game on BoardGameGeek. Returns the top 5 results with names and object IDs."""
        search_url = f"{self.BASE_URL}search?search={search_query}"

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
                        object_id = item.get("objectid")  # Get the 'objectid' attribute
                        games.append(f"{game_name} (ID: {object_id})")

                    # Format and send the game names and IDs
                    if games:
                        games_list = "\n".join(games)
                        message = f"Top 5 search results:\n{games_list}"
                    else:
                        message = "No games found."
                    await ctx.send(message)
                else:
                    await ctx.send("Failed to retrieve search results.")

    @commands.command(aliases=["bginfo"])
    async def boardgame_info(self, ctx, game_id: str):
        """Fetch information for a board game by its BoardGameGeek ID, including ratings and recommended player count."""
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
                                break

                        age = (
                            game.find("age").text
                            if game.find("age") is not None
                            else "N/A"
                        )

                        # Calculate the recommended player count
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

                        # Extracting rating information
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
                            average_rating = "{:.2f}".format(float(average_rating))

                        # Create and send embed
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
                        await ctx.send("Game not found.")
                else:
                    await ctx.send("Failed to retrieve game information.")


async def setup(client):
    await client.add_cog(BoardGames(client))
