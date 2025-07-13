"""
Database Cog
===============

Handles database related commands.
"""

import discord
from discord.ext import commands


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def close_db(self, cursor):
        """Utility function to close database cursor."""
        if cursor:
            cursor.close()

    @commands.command(name="listusers", help="Lists all users from the database.")
    async def list_users(self, ctx):
        cursor = None
        try:
            cursor = self.bot.db_conn.cursor()
            cursor.execute("SELECT * FROM get_enabled_users();")
            users = cursor.fetchall()

            if not users:
                await ctx.send("No users found.")
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
            await ctx.send(embed=embed)
            self.bot.logger.info("Successfully listed all users.")
        except Exception as e:
            await ctx.send("Failed to fetch users.")
            self.bot.logger.error(f"Failed to fetch users: {e}")
        finally:
            await self.close_db(cursor)

    @commands.command(
        name="adduser",
        help="Adds a new user or updates an existing one. Usage: !adduser <name> <discord_user_id> <bgg_user> <is_enabled>",
    )
    async def add_user(
        self,
        ctx,
        name: str,
        discord_user: int,
        bgg_user: str,
        is_enabled: bool = True,
    ):
        cursor = None
        try:
            discord_user_int = int(discord_user)
            cursor = self.bot.db_conn.cursor()
            cursor.execute(
                "SELECT upsert_user(%s, %s, %s, %s)",
                (name, discord_user_int, bgg_user, is_enabled),
            )
            result = cursor.fetchone()
            self.bot.db_conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Upsert Successful",
                description=f"User has been upserted successfully: {result[0]}",
            )
            await ctx.send(embed=embed)
            self.bot.logger.info("User upserted successfully.")
        except ValueError:
            await ctx.send("Please make sure the Discord User ID is a valid integer.")
            self.bot.logger.warning("Invalid input for Discord User ID.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            self.bot.logger.error(f"An error occurred during user upsert: {e}")
        finally:
            await self.close_db(cursor)

    @commands.command(
        name="disableuser",
        help="Disables a user by their ID. Usage: !disableuser <user_id>",
    )
    async def disable_user(self, ctx, user_id: int):
        cursor = None
        try:
            cursor = self.bot.db_conn.cursor()
            cursor.execute("SELECT disable_user(%s)", (user_id,))
            self.bot.db_conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Disabled",
                description=f"The user with ID {user_id} has been disabled.",
            )
            await ctx.send(embed=embed)
            self.bot.logger.info(f"User with ID {user_id} disabled successfully.")
        except Exception as e:
            await ctx.send(f"Failed to disable user: {e}")
            self.bot.logger.error(f"Failed to disable user: {e}")
        finally:
            await self.close_db(cursor)

    @commands.command(
        name="enableuser",
        help="Enables a user by their ID. Usage: !enableuser <user_id>",
    )
    async def enable_user(self, ctx, user_id: int):
        cursor = None
        try:
            cursor = self.bot.db_conn.cursor()
            cursor.execute("SELECT enable_user(%s)", (user_id,))
            result = cursor.fetchone()[0]
            self.bot.db_conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Enable Status",
                description=f"The user with ID {user_id} has been enabled.",
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Failed to enable user: {e}")
            self.bot.logger.error(f"Failed to enable user: {e}")
        finally:
            await self.close_db(cursor)

    def chunk_games(self, games, size=25):
        """Yield successive chunks from games."""
        for i in range(0, len(games), size):
            yield games[i : i + size]

    @commands.command(
        name="listboardgames",
        help="Lists all board games starting with a specified letter. Optionally filter by username.",
    )
    async def list_board_games(self, ctx, letter: str, username: str = None):
        if len(letter) != 1 or not letter.isalpha():
            await ctx.send("Please provide a single alphabetical letter.")
            self.bot.logger.warning(
                f"Invalid input for list_board_games command: '{letter}'"
            )
            return

        cursor = None
        try:
            cursor = self.bot.db_conn.cursor()

            if username:
                self.bot.logger.debug(
                    f"Executing database query for games starting with '{letter}' owned by '{username}'."
                )
                cursor.execute(
                    "SELECT * FROM get_boardgames_starting_with_and_owned_by(%s, %s)",
                    (letter, username),
                )
            else:
                self.bot.logger.debug(
                    f"Executing database query for games starting with '{letter}'."
                )
                cursor.execute(
                    "SELECT * FROM get_boardgames_starting_with(%s)", (letter,)
                )

            games = cursor.fetchall()
            total_games = len(games)
            self.bot.logger.info(f"Number of games fetched: {total_games}")

            if not games:
                await ctx.send(f"No board games found starting with '{letter}'.")
                self.bot.logger.info(f"No board games found for letter: {letter}")
                return

            game_chunks = list(self.chunk_games(games))
            self.bot.logger.debug(f"Number of chunks created: {len(game_chunks)}")

            game_count = 0
            for chunk in game_chunks:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"Board Games Starting with '{letter.upper()}'",
                    description=f"Displaying games {game_count+1} to {game_count+len(chunk)} out of {total_games}:",
                )
                for game in chunk:
                    embed.add_field(
                        name=f"{game[3]} Owned by: {game[2]} (ID: {game[4]})",
                        value=f"Rating: {game[5]}, Players: {game[15]}-{game[16]}, Playtime: {game[17]} mins, Total Plays: {game[18]}",
                        inline=False,
                    )
                    game_count += 1
                await ctx.send(embed=embed)
                self.bot.logger.info(
                    f"Embed sent for a chunk of games starting with '{letter}'. {game_count} games listed so far."
                )
        except Exception as e:
            await ctx.send(f"Failed to fetch board games: {e}")
            self.bot.logger.error(
                f"Exception occurred while fetching games starting with '{letter}': {e}"
            )
        finally:
            await self.close_db(cursor)

    @commands.command(
        name="executesql", help="Executes a custom SQL query. Owner only."
    )
    @commands.is_owner()
    async def execute_sql(self, ctx, *, query: str):
        destructive_operations = ["DROP", "DELETE", "TRUNCATE", "ALTER"]

        if any(op in query.upper() for op in destructive_operations):
            await ctx.send("This command does not support destructive operations.")
            return

        cursor = None
        try:
            cursor = self.bot.db_conn.cursor()
            cursor.execute(query)

            if cursor.description:
                results = cursor.fetchall()
                message = "\n".join([str(result) for result in results])
                if len(message) > 1900:
                    message = message[:1900] + "..."
                await ctx.send(f"Query executed successfully:\n{message}")
            else:
                self.bot.db_conn.commit()
                await ctx.send("Query executed successfully with no return.")

            self.bot.logger.info(f"SQL executed by owner: {query}")
        except Exception as e:
            await ctx.send(f"Failed to execute query: {e}")
            self.bot.logger.error(f"Exception occurred during SQL execution: {e}")
        finally:
            await self.close_db(cursor)

    async def send_paginated_embeds(self, ctx, games):
        per_page = 5
        pages = [games[i : i + per_page] for i in range(0, len(games), per_page)]
        page_number = 1

        for page in pages:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="Board Games Available for Trade (Page {})".format(page_number),
                description="Here are the games listed for trade:",
            )
            for game in page:
                embed.add_field(
                    name=f"{game[2]} (Rating: {game[3]})",
                    value=f"Own: {game[4]}, BGGeek Username: {game[1]}",
                    inline=False,
                )
            await ctx.send(embed=embed)
            page_number += 1

    @commands.command(aliases=["bgcount"])
    async def boardgame_count(self, ctx):
        """Check how many boardgames are in the DB."""
        cursor = None
        try:
            if not self.bot.db_conn:
                await ctx.send("Database connection not established.")
                self.bot.logger.warning("No DB connection during bgcount.")
                return

            cursor = self.bot.db_conn.cursor()
            cursor.execute(
                "SELECT COUNT(DISTINCT Name) FROM BoardGames WHERE own = true;"
            )
            record = cursor.fetchone()

            if record:
                await ctx.send(
                    f"There are: {record[0]} unique board games owned by users in the Database."
                )
                self.bot.logger.info(f"Boardgame count: {record[0]}")
            else:
                await ctx.send("Unable to fetch database record.")
                self.bot.logger.error("No boardgame count found.")
        except Exception as e:
            await ctx.send(f"Error checking the database: {e}")
            self.bot.logger.error(f"DB error in boardgame_count: {e}")
        finally:
            if cursor:
                cursor.close()


async def setup(bot):
    await bot.add_cog(Database(bot))
