import re
import os
import discord
from discord.ext import commands
import aiohttp
import asyncio #testing
import xml.etree.ElementTree as ET

from utils import boardgames as bg_utils
from logging_files.boardgames_logging import logger


async def send_paginated_embeds(ctx, games, title, color):
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
        logger.info(f"Sent page {i+1} of {len(pages)} for {title}")


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
                logger.info(f"Successfully retrieved boardgame count: {record[0]}")
            else:
                await ctx.send("Unable to fetch database record.")
                logger.error("Failed to fetch boardgame count from the database.")
        except Exception as e:
            await ctx.send(f"Error checking the database: {e}")
            logger.error(f"Error checking the database: {e}")

    @commands.command(
        name="bgsearch",
        help="Searches for board games on BoardGameGeek. Example: `!bgsearch Catan`",
        brief="Search for board games by name.",
    )
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

    @commands.command(
        name="bginfo",
        help="Fetches detailed information about a board game from BoardGameGeek by its ID. Example: `!bginfo 12345`",
        brief="Get detailed info about a board game.",
    )
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
                                logger.info(f"Game found: {game_name} (ID: {game_id})")
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
                            average_rating = "{:.2f}".format(float(average_rating))

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

    @commands.command(
        name="bggcollection",
        help="Displays a BoardGameGeek user's collection by username. Example: `!bggcollection username`",
        brief="Get BGG user's collection.",
    )
    async def bgg_collection(self, ctx, username: str):
        """Fetches and displays a user's board game collection from BoardGameGeek including additional game statistics."""
        collection_url = f"{self.BASE_URL}collection/{username}?own=1&stats=1"
        logger.info(f"Starting collection fetch for BGG username: {username}")

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(collection_url)
                if response.status == 200:
                    xml_data = await response.text()
                    root = ET.fromstring(xml_data)

                    games = []
                    for item in root.findall("item"):
                        game_name = (
                            item.find("name").text
                            if item.find("name") is not None
                            else "Unknown"
                        )
                        bggid = item.attrib.get("objectid", "N/A")
                        avg_rating_element = item.find(".//average")
                        avg_rating = (
                            avg_rating_element.attrib.get("value", "N/A")
                            if avg_rating_element is not None
                            else "N/A"
                        )

                        # Extract additional stats
                        stats = item.find("stats")
                        min_players = stats.attrib.get("minplayers", "N/A")
                        max_players = stats.attrib.get("maxplayers", "N/A")
                        max_playtime = stats.attrib.get("maxplaytime", "N/A")

                        games.append(
                            f"{game_name} (ID: {bggid}, Avg Rating: {avg_rating}, Min Players: {min_players}, Max Players: {max_players}, Max Playtime: {max_playtime} mins)"
                        )

                    await send_paginated_embeds(
                        ctx,
                        games,
                        f"{username}'s Board Game Collection",
                        self.bot.embed_color,
                    )
                    logger.info(f"Successfully displayed collection for {username}")
                elif response.status == 202:
                    await ctx.send(
                        f"Collection data for {username} is being prepared, please wait a few moments."
                    )
                    logger.warning(
                        f"Data preparation in progress for {username}, response stats 202"
                    )
                else:
                    logger.error(
                        f"Failed to retrieve collection with status code {response.status} for {username}"
                    )
                    await ctx.send("Failed to retrieve collection.")
            except Exception as e:
                logger.exception(
                    f"An error occurred while fetching collection for {username}: {str(e)}"
                )
                await ctx.send("An error occurred while processing your request.")

    @commands.command(
        name="manualbggupdate",
        help="Manually triggers an update of board game data from BoardGameGeek for all users.",
        brief="Trigger manual BGG data update.",
    )
    async def manual_bgg_update(self, ctx):
        """This command starts the manual update process for BGG collections."""
        await ctx.send("Starting manual update of BGG collections. Please wait...")
        try:
            res = await bg_utils.process_bgg_users()
            await ctx.send("BGG collections updated successfully.")
        except Exception as e:
            await ctx.send(f"Failed to update BGG collections: {str(e)}")
            logger.error(f"Failed to update BGG collections: {str(e)}")


async def setup(client):
    await client.add_cog(BoardGames(client))
