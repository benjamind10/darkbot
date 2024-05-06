import discord
from discord.ext import commands
from db import get_connection
from logging_files.database_logging import logger


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def close_db(self, conn, cursor):
        """Utility function to close database connection and cursor."""
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    @commands.command(name="listusers", help="Lists all users from the database.")
    async def list_users(self, ctx):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_enabled_users();")
            users = cursor.fetchall()

            if not users:
                await ctx.send("No users found.")
                logger.info("No users found in the database.")
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
            logger.info("Successfully listed all users.")
        except Exception as e:
            await ctx.send("Failed to fetch users.")
            logger.error(f"Failed to fetch users: {e}")
        finally:
            await self.close_db(conn, cursor)

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
        conn = None
        cursor = None
        try:
            discord_user_int = int(discord_user)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT upsert_user(%s, %s, %s, %s)",
                (name, discord_user_int, bgg_user, is_enabled),
            )
            result = cursor.fetchone()
            conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Upsert Successful",
                description=f"User has been upserted successfully: {result[0]}",
            )
            await ctx.send(embed=embed)
            logger.info("User upserted successfully.")
        except ValueError:
            await ctx.send("Please make sure the Discord User ID is a valid integer.")
            logger.warning("Invalid input for Discord User ID.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            logger.error(f"An error occurred during user upsert: {e}")
        finally:
            await self.close_db(conn, cursor)

    @commands.command(
        name="disableuser",
        help="Disables a user by their ID. Usage: !disableuser <user_id>",
    )
    async def disable_user(self, ctx, user_id: int):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT disable_user(%s)", (user_id,))
            conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Disabled",
                description=f"The user with ID {user_id} has been disabled.",
            )
            await ctx.send(embed=embed)
            logger.info(f"User with ID {user_id} disabled successfully.")
        except Exception as e:
            await ctx.send(f"Failed to disable user: {e}")
            logger.error(f"Failed to disable user: {e}")
        finally:
            await self.close_db(conn, cursor)

    @commands.command(
        name="enableuser",
        help="Enables a user by their ID. Usage: !enableuser <user_id>",
    )
    async def enable_user(self, ctx, user_id: int):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT enable_user(%s)", (user_id,))
            result = cursor.fetchone()[0]
            conn.commit()

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Enable Status",
                description=result,
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Failed to enable user: {e}")
        finally:
            await self.close_db(conn, cursor)

    def chunk_games(self, games, size=25):
        """Yield successive chunks from games."""
        for i in range(0, len(games), size):
            yield games[i : i + size]

    @commands.command(
        name="listboardgames",
        help="Lists all board games starting with a specified letter.",
    )
    async def list_board_games(self, ctx, letter: str):
        if len(letter) != 1 or not letter.isalpha():
            await ctx.send("Please provide a single alphabetical letter.")
            logger.warning(f"Invalid input for list_board_games command: '{letter}'")
            return

        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            logger.debug(
                f"Executing database query for games starting with '{letter}'."
            )
            cursor.execute("SELECT * FROM get_boardgames_starting_with(%s)", (letter,))
            games = cursor.fetchall()
            logger.info(f"Number of games fetched: {len(games)}")

            if not games:
                await ctx.send(f"No board games found starting with '{letter}'.")
                logger.info(f"No board games found for letter: {letter}")
                return

            game_chunks = list(self.chunk_games(games))
            logger.debug(f"Number of chunks created: {len(game_chunks)}")

            for chunk in game_chunks:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"Board Games Starting with '{letter.upper()}'",
                    description="Here are the games:",
                )
                for game in chunk:
                    embed.add_field(
                        name=f"{game[3]} Owned by: {game[2]} (ID: {game[4]})",  # game name, username, game ID
                        value=f"Rating: {game[5]}, Players: {game[15]}-{game[16]}, Playtime: {game[17]} mins, Total Plays: {game[18]}",
                        inline=False,
                    )
                await ctx.send(embed=embed)
                logger.info(
                    f"Embed sent for a chunk of games starting with '{letter}'."
                )
        except Exception as e:
            await ctx.send(f"Failed to fetch board games: {e}")
            logger.error(
                f"Exception occurred while fetching games starting with '{letter}': {e}"
            )
        finally:
            if cursor:
                cursor.close()
                logger.debug("Database cursor closed.")
            if conn:
                conn.close()
                logger.debug("Database connection closed.")

    @commands.command(
        name="executesql", help="Executes a custom SQL query. Owner only."
    )
    @commands.is_owner()  # This decorator ensures that only the bot owner can run this command
    async def execute_sql(self, ctx, *, query: str):
        """Executes a raw SQL query directly on the database."""
        if "DROP" in query.upper() or "DELETE" in query.upper():
            await ctx.send("This command does not support destructive operations.")
            return

        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            if cursor.description:  # If there is something to fetch
                results = cursor.fetchall()
                message = "\n".join([str(result) for result in results])
                if (
                    len(message) > 1900
                ):  # Discord has a limit on message length (2000 characters)
                    message = message[:1900] + "..."
                await ctx.send(f"Query executed successfully:\n{message}")
            else:
                conn.commit()
                await ctx.send("Query executed successfully with no return.")
            logger.info(f"SQL executed by owner: {query}")
        except Exception as e:
            await ctx.send(f"Failed to execute query: {e}")
            logger.error(f"Exception occurred during SQL execution: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


async def setup(client):
    await client.add_cog(Database(client))
