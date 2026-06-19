"""
Database Cog
===============

Handles database related commands.
"""

import discord
import psycopg
from discord.ext import commands
from utils.discord_context import defer_if_interaction, send_for_context


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="listusers", help="Lists all users from the database.")
    async def list_users(self, ctx):
        """
        Retrieves and lists all enabled users in the database.
        Displays user ID, name, Discord ID, BGG username, and enabled status.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT * FROM get_enabled_users();")
                    users = await cursor.fetchall()

            if not users:
                await send_for_context(ctx, "No users found.")
                self.bot.logger.info("No users found in the database.")
                return

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="List of All Users",
                description="Here are all the users in the database:",
            )
            for user in users:
                embed.add_field(
                    name=f"User ID: {user[0]}",
                    value=f"Name: {user[1]}, Discord: {user[2]}, BGG: {user[3]}, Enabled: {user[4]}",
                    inline=False,
                )
            await send_for_context(ctx, embed=embed)
            self.bot.logger.info("Successfully listed all users.")
        except psycopg.Error:
            await send_for_context(ctx, "Failed to fetch users.")
            self.bot.logger.exception("Failed to fetch users")

    @commands.hybrid_command(
        name="adduser",
        help="Adds a new user or updates an existing one.",
    )
    async def add_user(
        self,
        ctx,
        name: str,
        discord_user: int,
        bgg_user: str,
        is_enabled: bool = True,
    ):
        """
        Inserts or updates a user record in the database.

        Args:
            name (str): The user's name.
            discord_user (int): Discord ID.
            bgg_user (str): BGG username.
            is_enabled (bool): Whether the user is active.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        try:
            discord_user_int = int(discord_user)
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT upsert_user(%s, %s, %s, %s)",
                        (name, discord_user_int, bgg_user, is_enabled),
                    )
                    result = await cursor.fetchone()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Upsert Successful",
                description=f"User has been upserted successfully: {result[0]}",
            )
            await send_for_context(ctx, embed=embed)
            self.bot.logger.info("User upserted successfully.")
        except ValueError:
            await send_for_context(ctx, "Please make sure the Discord User ID is a valid integer.")
            self.bot.logger.warning("Invalid input for Discord User ID.")
        except psycopg.Error as e:
            await send_for_context(ctx, f"An error occurred: {e}")
            self.bot.logger.exception("An error occurred during user upsert")

    @commands.hybrid_command(
        name="disableuser",
        help="Disables a user by their ID. Usage: !disableuser <user_id>",
    )
    async def disable_user(self, ctx, user_id: int):
        """
        Disables an existing user by their database ID.

        Args:
            user_id (int): The internal DB user ID.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT disable_user(%s)", (user_id,))

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Disabled",
                description=f"The user with ID {user_id} has been disabled.",
            )
            await send_for_context(ctx, embed=embed)
            self.bot.logger.info(f"User with ID {user_id} disabled successfully.")
        except psycopg.Error as e:
            await send_for_context(ctx, f"Failed to disable user: {e}")
            self.bot.logger.exception("Failed to disable user")

    @commands.hybrid_command(
        name="enableuser",
        help="Enables a user by their ID. Usage: !enableuser <user_id>",
    )
    async def enable_user(self, ctx, user_id: int):
        """
        Enables a previously disabled user by their database ID.

        Args:
            user_id (int): The internal DB user ID.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT enable_user(%s)", (user_id,))
                    await cursor.fetchone()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Enable Status",
                description=f"The user with ID {user_id} has been enabled.",
            )
            await send_for_context(ctx, embed=embed)
        except psycopg.Error as e:
            await send_for_context(ctx, f"Failed to enable user: {e}")
            self.bot.logger.exception("Failed to enable user")

    def chunk_games(self, games, size=25):
        """Yield successive chunks from games."""
        for i in range(0, len(games), size):
            yield games[i : i + size]

    @commands.hybrid_command(
        name="listboardgames",
        help="Lists all board games starting with a specified letter. Optionally filter by username.",
    )
    async def list_board_games(self, ctx, letter: str, username: str = None):
        """
        Fetches and lists board games from the DB starting with a specified letter.

        Args:
            letter (str): The starting letter to filter game names.
            username (str, optional): Filter games owned by a specific user.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        if len(letter) != 1 or not letter.isalpha():
            await send_for_context(ctx, "Please provide a single alphabetical letter.")
            self.bot.logger.warning(f"Invalid input for list_board_games command: '{letter}'")
            return

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    if username:
                        self.bot.logger.debug(
                            f"Executing database query for games starting with '{letter}' owned by '{username}'."
                        )
                        await cursor.execute(
                            "SELECT * FROM get_boardgames_starting_with_and_owned_by(%s, %s)",
                            (letter, username),
                        )
                    else:
                        self.bot.logger.debug(
                            f"Executing database query for games starting with '{letter}'."
                        )
                        await cursor.execute(
                            "SELECT * FROM get_boardgames_starting_with(%s)", (letter,)
                        )

                    games = await cursor.fetchall()

            total_games = len(games)
            self.bot.logger.info(f"Number of games fetched: {total_games}")

            if not games:
                await send_for_context(ctx, f"No board games found starting with '{letter}'.")
                self.bot.logger.info(f"No board games found for letter: {letter}")
                return

            game_chunks = list(self.chunk_games(games))
            self.bot.logger.debug(f"Number of chunks created: {len(game_chunks)}")

            game_count = 0
            for chunk in game_chunks:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"Board Games Starting with '{letter.upper()}'",
                    description=f"Displaying games {game_count + 1} to {game_count + len(chunk)} out of {total_games}:",
                )
                for game in chunk:
                    embed.add_field(
                        name=f"{game[3]} Owned by: {game[2]} (ID: {game[4]})",
                        value=f"Rating: {game[5]}, Players: {game[15]}-{game[16]}, Playtime: {game[17]} mins, Total Plays: {game[18]}",
                        inline=False,
                    )
                    game_count += 1
                await send_for_context(ctx, embed=embed)
                self.bot.logger.info(
                    f"Embed sent for a chunk of games starting with '{letter}'. {game_count} games listed so far."
                )
        except psycopg.Error as e:
            await send_for_context(ctx, f"Failed to fetch board games: {e}")
            self.bot.logger.exception(
                "Exception occurred while fetching games starting with '%s'", letter
            )

    @commands.hybrid_command(name="executesql", help="Executes a custom SQL query. Owner only.")
    @commands.is_owner()
    async def execute_sql(self, ctx, *, query: str):
        """
        Executes a raw SQL query (non-destructive only). Only the bot owner may use this.

        Args:
            query (str): The SQL statement to execute.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        destructive_operations = ["DROP", "DELETE", "TRUNCATE", "ALTER"]

        if any(op in query.upper() for op in destructive_operations):
            await send_for_context(ctx, "This command does not support destructive operations.")
            return

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)

                    if cursor.description:
                        results = await cursor.fetchall()
                        message = "\n".join([str(result) for result in results])
                        if len(message) > 1900:
                            message = message[:1900] + "..."
                        await send_for_context(ctx, f"Query executed successfully:\n{message}")
                    else:
                        await send_for_context(ctx, "Query executed successfully with no return.")

            self.bot.logger.info(f"SQL executed by owner: {query}")
        except psycopg.Error as e:
            await send_for_context(ctx, f"Failed to execute query: {e}")
            self.bot.logger.exception("Exception occurred during SQL execution")

    async def send_paginated_embeds(self, ctx, games):
        """
        Utility method to paginate and send a long list of board games in multiple embeds.

        Args:
            ctx (Context): The command context.
            games (list): A list of game tuples to paginate.
        """
        per_page = 5
        pages = [games[i : i + per_page] for i in range(0, len(games), per_page)]
        page_number = 1

        for page in pages:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title=f"Board Games Available for Trade (Page {page_number})",
                description="Here are the games listed for trade:",
            )
            for game in page:
                embed.add_field(
                    name=f"{game[2]} (Rating: {game[3]})",
                    value=f"Own: {game[4]}, BGGeek Username: {game[1]}",
                    inline=False,
                )
            await send_for_context(ctx, embed=embed)
            page_number += 1

    @commands.hybrid_command(aliases=["bgcount"])
    async def boardgame_count(self, ctx):
        """
        Counts how many unique board games are marked as owned in the database.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        try:
            async with self.bot.db_pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT COUNT(DISTINCT Name) FROM BoardGames WHERE own = true;"
                    )
                    record = await cursor.fetchone()

            if record:
                await send_for_context(ctx, 
                    f"There are: {record[0]} unique board games owned by users in the Database."
                )
                self.bot.logger.info(f"Boardgame count: {record[0]}")
            else:
                await send_for_context(ctx, "Unable to fetch database record.")
                self.bot.logger.error("No boardgame count found.")
        except psycopg.Error as e:
            await send_for_context(ctx, f"Error checking the database: {e}")
            self.bot.logger.exception("DB error in boardgame_count")


async def setup(bot):
    """Register the Database cog with the bot."""
    await bot.add_cog(Database(bot))
