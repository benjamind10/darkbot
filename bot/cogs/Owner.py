import random
import discord
import aiohttp
import asyncio
from discord.ext import commands
from logging_files.owner_logging import logger


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keywords = [
            "World Stone",
            "Plains of Despair",
            "Forgotten Tower",
        ]  # Add more keywords as needed
        self.scraping_task = bot.loop.create_task(self.scrape_tz_site())

    def cog_unload(self):
        self.scraping_task.cancel()

    async def scrape_tz_site(self):
        await self.bot.wait_until_ready()
        matched_keywords = set()

        while not self.bot.is_closed():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://d2emu.com/tz") as response:
                        if response.status == 200:
                            content = await response.text()
                            logger.info("Scraper | Successfully fetched d2emu.com/tz")

                            content_lower = content.lower()
                            for keyword in self.keywords:
                                if (
                                    keyword.lower() in content_lower
                                    and keyword not in matched_keywords
                                ):
                                    matched_keywords.add(keyword)
                                    channel = self.bot.get_channel(1120385235813675103)
                                    if channel:
                                        await channel.send(
                                            f"🔍 **{keyword}** found on [https://d2emu.com/tz](https://d2emu.com/tz)!"
                                        )
                                        logger.info(
                                            f"Scraper | '{keyword}' match found and notification sent."
                                        )
                        else:
                            logger.warning(
                                f"Scraper | Failed to fetch site. Status code: {response.status}"
                            )
            except Exception as e:
                logger.error(f"Scraper | Error occurred during scraping: {e}")

            await asyncio.sleep(60)

    @commands.is_owner()
    @commands.command()
    async def get_invite(self, ctx, id: int):
        try:
            guild = self.bot.get_guild(id)
            print(guild)
            for channel in guild.text_channels:
                channels = [channel.id]

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
