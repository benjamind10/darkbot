import random
import discord
from discord.ext import commands
from logging_files.owner_logging import logger


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def get_invite(self, ctx, id: int):
        try:
            guild = self.bot.get_guild(id)
            channels = [channel.id for channel in guild.text_channels]
            picked = random.choice(channels)
            channel = self.bot.get_channel(picked)

            embed = discord.Embed(
                color=self.bot.embed_color,
                title=f"→ Invite From Guild",
                description=f"• Invite: {await channel.create_invite(max_uses=1)}",
            )

            await ctx.author.send(embed=embed)
            logger.info(f"Owner | Sent Get Invite: {ctx.author}")
        except Exception as e:
            print(f"There was an error: {e}")

    @commands.is_owner()
    @commands.command()
    async def check_roles(self, ctx, user: discord.Member):
        role_mentions = [
            role.mention for role in user.roles if role != ctx.guild.default_role
        ]
        roles_text = (
            " ".join(role_mentions) if role_mentions else "This user has no roles."
        )

        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"Roles for {user.display_name}",
            description=roles_text,
        )
        await ctx.send(embed=embed)
        logger.info(f"Owner | Checked Roles for User: {user} - {ctx.author}")

    @commands.is_owner()
    @commands.command()
    async def check_permissions(self, ctx, user: discord.Member):
        permissions = user.guild_permissions
        true_permissions = [perm[0] for perm in permissions if perm[1]]
        formatted_permissions = ", ".join(true_permissions).replace("_", " ").title()

        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"Permissions for {user.display_name}",
            description=formatted_permissions,
        )
        await ctx.send(embed=embed)
        logger.info(f"Owner | Checked Permissions for User: {user} - {ctx.author}")

    @commands.is_owner()
    @commands.command()
    async def dbcheck(self, ctx):
        try:
            if not hasattr(self.bot, "conn"):
                await ctx.send("Database connection not established.")
                return

            with self.bot.conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                record = cursor.fetchone()

            if record:
                await ctx.send(f"Database version: {record[0]}")
            else:
                await ctx.send("Unable to fetch database version.")
        except Exception as e:
            await ctx.send(f"Error checking database version: {e}")


async def setup(client):
    await client.add_cog(Owner(client))
