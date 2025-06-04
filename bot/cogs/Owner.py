import random
import time
import discord
from discord.ext import commands
import aiohttp
from logging_files.owner_logging import logger


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = time.time()

        self.keywords = ["World Stone"]
        self.last_announced = None
        self.channel_id = 1120385235813675103
        self.api_headers = {
            "D2R-Contact": "benjamind10@pm.me",  # ← change this
            "D2R-Platform": "Discord",
            "D2R-Repo": "https://github.com/benjamind10/darkbot.git",
        }
        self.scraping_task = bot.loop.create_task(self.poll_terror_zone_api())

    def cog_unload(self):
        self.scraping_task.cancel()

    async def poll_terror_zone_api(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://d2runewizard.com/api/terror-zone",
                        headers=self.api_headers,
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            current_zone = (
                                data.get("currentTerrorZone", {})
                                .get("zone", "")
                                .strip()
                            )

                            logger.info(
                                f"Scraper | Fetched current zone: {current_zone}"
                            )

                            for keyword in self.keywords:
                                if (
                                    keyword.lower() in current_zone.lower()
                                    and keyword != self.last_announced
                                ):
                                    self.last_announced = keyword
                                    channel = self.bot.get_channel(self.channel_id)
                                    if channel:
                                        await channel.send(
                                            f"🔥 **{keyword}** is now the active Terror Zone!"
                                        )
                                        logger.info(
                                            f"Scraper | Notification sent for: {keyword}"
                                        )
                                    break
                        else:
                            logger.warning(
                                f"Scraper | API returned status {response.status}"
                            )
            except Exception as e:
                logger.error(f"Scraper | Exception during API poll: {e}")

            await asyncio.sleep(60)

    @commands.command(name="currenttz", help="Check the current and next Terror Zone")
    async def current_tz(self, ctx):
        """Fetch and display the current and next terror zones."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://d2runewizard.com/api/terror-zone", headers=self.api_headers
                ) as response:
                    if response.status != 200:
                        await ctx.send("⚠️ Failed to fetch terror zone data.")
                        logger.warning(f"currenttz | API returned {response.status}")
                        return

                    data = await response.json()
                    logger.info(f"RAW API DATA: {data}")

                    current = data.get("currentTerrorZone", {}).get("zone", "Unknown")
                    current_act = data.get("currentTerrorZone", {}).get(
                        "act", "Unknown"
                    )
                    next_zone = data.get("nextTerrorZone", {}).get("zone", "Unknown")
                    next_act = data.get("nextTerrorZone", {}).get("act", "Unknown")

                    embed = discord.Embed(
                        color=self.bot.embed_color,
                        title="🔥 Terror Zone Info",
                        description=(
                            f"**Current TZ:** {current} ({current_act})\n"
                            f"**Next TZ:** {next_zone} ({next_act})"
                        ),
                    )
                    await ctx.send(embed=embed)
                    logger.info(
                        f"currenttz | Current: {current} | Next: {next_zone} ({next_act})"
                    )

        except Exception as e:
            logger.error(f"currenttz | Error: {e}")
            await ctx.send("❌ An error occurred while fetching TZ info.")

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
