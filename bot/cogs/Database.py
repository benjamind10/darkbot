import discord
from discord.ext import commands
from db import get_connection


from logging_files.database_logging import logger


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # DB STUFF
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    @commands.command(name="listusers", help="Lists all users from the database.")
    async def list_users(self, ctx):
        """Command to fetch all users from the database and display them in an embed."""
        try:
            # Use the existing cursor to perform a query
            self.cursor.execute("SELECT * FROM Users WHERE IsEnabled = true")
            users = self.cursor.fetchall()

            # Building the embed to send back
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="List of All Users",
                description="Here are all the users in the database:",
            )

            for user in users:
                embed.add_field(
                    name=f"User ID: {user[0]}",
                    value=f"Name: {user[1]}, Email: {user[2]}, Discord: {user[3]}, BGG: {user[4]}, Enabled: {user[5]}, Modified: {user[6]}",
                    inline=False,
                )

            # Send the embed response back to Discord
            await ctx.send(embed=embed)
            logger.info("Successfully listed all users.")
        except Exception as e:
            await ctx.send("Failed to fetch users.")
            logger.error(f"Failed to fetch users: {e}")

    @commands.command(
        name="adduser",
        help="Adds a new user or updates an existing one. Usage: !adduser <name> <email> <discord_user_id> <bgg_user> <is_enabled>",
    )
    async def add_user(
        self,
        ctx,
        name: str,
        email: str,
        discord_user: str,
        bgg_user: str,
        is_enabled: bool = True,
    ):
        """Command to add or update a user in the database, with styled embed response."""
        try:
            # Convert discord_user to int manually
            discord_user_int = int(discord_user)
        except ValueError:
            await ctx.send("Please make sure the Discord User ID is a valid integer.")
            logger.warning("Invalid input for Discord User ID.")
            return

        try:
            # Establish database connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT upsert_user(%s, %s, %s, %s, %s)",
                (name, email, discord_user_int, bgg_user, is_enabled),
            )
            result = cursor.fetchone()
            conn.commit()  # Commit to save changes in the database

            # Provide feedback using an embed
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Upsert Successful",
                description=f"User has been upserted successfully: {result[0]}",
            )
            await ctx.send(embed=embed)
            logger.info("User upserted successfully.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            logger.error(f"An error occurred during user upsert: {e}")

    @commands.command(
        name="disableuser",
        help="Disables a user by their ID. Usage: !disableuser <user_id>",
    )
    async def disable_user(self, ctx, user_id: int):
        """Command to disable a user in the database."""
        try:
            # Establish database connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT disable_user(%s)", (user_id,))
            conn.commit()  # Commit the changes to the database

            # Provide feedback
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

    @commands.command(
        name="enableuser",
        help="Enables a user by their ID. Usage: !enableuser <user_id>",
    )
    async def enable_user(self, ctx, user_id: int):
        """Command to enable a user in the database."""
        try:
            # Establish database connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT enable_user(%s)", (user_id,))
            result = cursor.fetchone()[
                0
            ]  # Fetch the response message from the function
            conn.commit()  # Commit the changes to the database

            # Provide feedback
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="User Enable Status",
                description=result,
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Failed to enable user: {e}")


async def setup(client):
    await client.add_cog(Database(client))
