import asyncio
import re
import time
import discord
import platform
import distro
import psutil
import aiohttp
from discord.ext import commands
from datetime import datetime, timedelta
from logging_files.information_logging import logger


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = time.time()

        self.keywords = ["Worldstone", "Chaos Sanctuary"]
        self.last_announced = None
        self.channel_id = 1379906383255834786
        self.api_headers = {
            "D2R-Contact": "benjamind10@pm.me",
            "D2R-Platform": "Discord",
            "D2R-Repo": "https://github.com/benjamind10/darkbot.git",
        }
        self.last_zone_poll = None
        self.scraping_task = bot.loop.create_task(self.poll_terror_zone_api())
        self.hourly_task = None

    def cog_unload(self):
        self.scraping_task.cancel()
        if self.hourly_task:
            self.hourly_task.cancel()

    def matches_keyword(self, zone_name: str) -> bool:
        normalized = re.sub(r"\W+", "", zone_name.lower())
        return any(
            re.sub(r"\W+", "", keyword.lower()) in normalized
            for keyword in self.keywords
        )

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
                            if (
                                self.matches_keyword(current_zone)
                                and current_zone != self.last_announced
                            ):
                                self.last_announced = current_zone
                                channel = self.bot.get_channel(self.channel_id)
                                if channel:
                                    await channel.send(
                                        f"🔥 **{current_zone}** is now the active Terror Zone!"
                                    )
                                    logger.info(
                                        f"Scraper | Notification sent for: {current_zone}"
                                    )
                        else:
                            logger.warning(
                                f"Scraper | API returned status {response.status}"
                            )
            except Exception as e:
                logger.error(f"Scraper | Exception during API poll: {e}")
            await asyncio.sleep(300)

    async def world_stone_reminders(self, next_zone):
        logger.info(f"Reminder | {next_zone} is coming up, waiting before reminders...")

        await asyncio.sleep(30)  # Short delay to avoid false early detection

        for i in range(5):
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

                            logger.info(f"[REMINDER] Loop {i+1} check: {current_zone}")

                            if (
                                current_zone.lower() == next_zone.lower()
                                or self.matches_keyword(current_zone)
                            ):
                                logger.info(
                                    "Reminder | Tracked zone is now active. Stopping reminders."
                                )
                                return

                            channel = self.bot.get_channel(self.channel_id)
                            if channel:
                                await channel.send(
                                    f"⚠️ Reminder: **{next_zone}** is coming up soon. Be ready!"
                                )
                                logger.info(
                                    f"Reminder | Sent reminder {i+1} for: {next_zone}"
                                )
            except Exception as e:
                logger.error(f"Reminder | Exception in reminder loop: {e}")

            await asyncio.sleep(600)  # Wait 10 mins before next reminder

    async def start_hourly_tz_updates(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.utcnow()
            next_poll_time = (now + timedelta(hours=1)).replace(
                minute=10, second=0, microsecond=0
            )
            wait_seconds = (next_poll_time - now).total_seconds()
            logger.info(
                f"[TZUPDATES] Sleeping {wait_seconds:.0f}s until {next_poll_time.isoformat()}"
            )
            await asyncio.sleep(wait_seconds)

            async def fetch_and_post_tz_update():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            "https://d2runewizard.com/api/terror-zone",
                            headers=self.api_headers,
                        ) as response:
                            if response.status == 200:
                                data = await response.json()

                                current = data.get("currentTerrorZone", {}).get(
                                    "zone", "Unknown"
                                )
                                current_act = data.get("currentTerrorZone", {}).get(
                                    "act", "Unknown"
                                )
                                next_zone = data.get("nextTerrorZone", {}).get(
                                    "zone", "Unknown"
                                )
                                next_act = data.get("nextTerrorZone", {}).get(
                                    "act", "Unknown"
                                )

                                is_stale = current == self.last_announced

                                channel = self.bot.get_channel(self.channel_id)
                                if not channel:
                                    logger.warning("TZUPDATES | Channel not found.")
                                    return False, current, is_stale

                                embed = discord.Embed(
                                    color=self.bot.embed_color,
                                    title="⏰ Hourly Terror Zone Update",
                                    description=(
                                        f"**Current TZ:** {current} ({current_act})\n"
                                        f"**Next TZ:** {next_zone} ({next_act})"
                                    ),
                                )
                                await channel.send(embed=embed)
                                logger.info(
                                    f"[TZUPDATES] Sent hourly update: {current} -> {next_zone}"
                                )

                                if self.matches_keyword(current):
                                    await channel.send(
                                        f"🔥 **{current}** is now the active Terror Zone!"
                                    )
                                    logger.info(
                                        f"[TZUPDATES] Alert: {current} is active now."
                                    )

                                if self.matches_keyword(next_zone):
                                    logger.info(
                                        f"[TZUPDATES] {next_zone} is coming next. Starting reminders."
                                    )
                                    self.bot.loop.create_task(
                                        self.world_stone_reminders(next_zone)
                                    )

                                self.last_announced = current
                                return True, current, is_stale
                            else:
                                logger.warning(
                                    f"[TZUPDATES] API error: {response.status}"
                                )
                                return False, None, False
                except Exception as e:
                    logger.error(f"[TZUPDATES] fetch_and_post_tz_update() error: {e}")
                    return False, None, False

            # Fetch API data
            success, current_zone, is_stale = await fetch_and_post_tz_update()

            # If the zone hasn't changed from last poll, retry in 90s
            should_retry = False
            if self.last_zone_poll == current_zone:
                logger.warning(
                    f"[TZUPDATES] Zone still '{current_zone}' from last poll — retrying in 90s..."
                )
                should_retry = True

            # Update last poll value
            self.last_zone_poll = current_zone

            if should_retry:
                await asyncio.sleep(90)
                await fetch_and_post_tz_update()

    @commands.command(
        name="tzupdates", help="Start hourly TZ update messages in notifier channel."
    )
    @commands.is_owner()
    async def tzupdates(self, ctx):
        if self.hourly_task and not self.hourly_task.done():
            self.hourly_task.cancel()
            await ctx.send("⏹️ Hourly Terror Zone updates stopped.")
            logger.info("Hourly Update | Task stopped.")
        else:
            self.hourly_task = self.bot.loop.create_task(self.start_hourly_tz_updates())
            await ctx.send("✅ Hourly Terror Zone updates started.")
            logger.info("Hourly Update | Task started.")

    @commands.command()
    @commands.is_owner()
    async def testreminder(self, ctx):
        await self.world_stone_reminders("Test Zone")

    @commands.command(name="currenttz", help="Check the current and next Terror Zone")
    async def current_tz(self, ctx):
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

    @commands.command(aliases=["commands", "cmds"])
    async def robot_commands(self, ctx):
        try:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ All available bot commands!",
                description="— "
                "\n➤ Shows info about all available bot commands!"
                "\n➤ Capitalization does not matter for the bot prefix." + "\n—",
            )
            embed.set_thumbnail(url="https://i.imgur.com/BUlgakY.png")
            information = "!commands"

            embed.add_field(
                name="• Information Commands!", inline=False, value=information
            )
            print(ctx.author.guild_permissions)
            print(ctx.channel.permissions_for(ctx.author))
            await ctx.send(embed=embed)

            logger.info(f"Information | Sent Commands: {ctx.author}")
        except Exception as e:
            print(f"There was an error: {e}")

    @commands.command()
    async def info(self, ctx):
        try:
            users = str(len(self.bot.users))
            guilds = str(len(self.bot.guilds))
            cpu = str(psutil.cpu_percent())
            ram = str(psutil.virtual_memory()[3] / 1000000000)
            ram_round = ram[:3]
            disk = str(psutil.disk_usage("/")[1] / 1000000000)
            disk_round = disk[:4]
            boot_time = str(psutil.boot_time() / 100000000)
            boot_time_round = boot_time[:4]
            linux_distro = distro.os_release_info()
            # get_news = self.bot.cursor.execute("SELECT rowid, * FROM bot_information")
            # news = get_news.fetchall()[0][3]

            embed = discord.Embed(
                color=self.bot.embed_color,
                title=f"→ DarkBot",
                description=f"— " f"\n ➤ To view my commands run, `!commands`" + "\n—",
            )
            embed.set_thumbnail(url="https://bit.ly/2JGhA94")
            embed.add_field(
                name=f"• OPERATING System:",
                inline=True,
                value=f":computer: — {linux_distro['pretty_name']}",
            )
            embed.add_field(
                name=f"• CPU Usage:",
                inline=True,
                value=f":heavy_plus_sign: — {cpu} Percent used",
            )
            embed.add_field(
                name=f"• RAM Usage:",
                inline=True,
                value=f":closed_book:  —  {ram_round}  / 4  Gigabytes used",
            )
            embed.add_field(
                name=f"• DISK Usage:",
                inline=True,
                value=f":white_circle: — {disk_round} / 40 Gigabytes",
            )
            embed.add_field(
                name=f"• BOOT Time: ",
                inline=True,
                value=f":boot: —  {boot_time_round} seconds",
            )
            embed.add_field(
                name=f"• MEMBER Count:",
                inline=True,
                value=f":bust_in_silhouette: —  {users} users",
            )
            embed.add_field(
                name=f"• GUILD Count:",
                inline=True,
                value=f":house: — {guilds} connected guilds",
            )
            embed.add_field(
                name=f"• LIBRARY Version:",
                inline=True,
                value=f":gear: — discord.py version {discord.__version__}",
            )
            embed.add_field(
                name=f"• PYTHON Version:",
                inline=True,
                value=f":snake:  — Python version {platform.python_version()}",
            )
            embed.set_footer(
                text=f"\n\nMade by Shiva187"
            )  # icon_url=f"\n\nhttps://i.imgur.com/TiUqRH8.gif")

            await ctx.send(embed=embed)

            logger.info(f"Information | Sent stats: {ctx.author}")
        except Exception as e:
            print(f"There was an error: {e}")

    @commands.command()
    async def invite(self, ctx):
        url = "(http://bit.ly/2Zm5XyP)"
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invite Me To Your Server!",
            description=f"• [**Click Here**]{url}",
        )
        await ctx.message.add_reaction(self.bot.get_emoji(648198008076238862))

        await ctx.author.send(embed=embed)

        logger.info(f"Information | Sent Invite: {ctx.author}")

    @commands.command()
    async def ping(self, ctx):
        before = time.monotonic()
        pong = int(round(self.bot.latency * 1000, 1))

        message = await ctx.send("• **Pong** — :ping_pong:")

        ping = (time.monotonic() - before) * 1000
        await message.delete(delay=1)
        await asyncio.sleep(1)

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Ping Command",
        )
        embed.add_field(name="• WS:", value=f"{pong}ms")
        embed.add_field(name="• REST:", value=f"{int(ping)}ms")
        await ctx.send(embed=embed)

        logger.info(f"Information | Sent Ping: {ctx.author}")

    @commands.command()
    async def uptime(self, ctx):
        """Command to check the bot's and system's uptime."""
        try:
            # Bot Uptime
            current_time = time.time()
            bot_difference = int(round(current_time - self.bot_start_time))
            bot_uptime_duration = str(timedelta(seconds=bot_difference))

            # System Uptime
            boot_time_timestamp = psutil.boot_time()
            boot_time = datetime.fromtimestamp(boot_time_timestamp)
            system_uptime_duration = str(
                timedelta(seconds=int(round(current_time - boot_time_timestamp)))
            )

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Uptime",
            )
            embed.add_field(
                name="Bot Uptime",
                value=f"→ I have been running for: {bot_uptime_duration}",
                inline=False,
            )
            embed.add_field(
                name="System Uptime",
                value=f"→ System has been running for: {system_uptime_duration}",
                inline=False,
            )

            await ctx.send(embed=embed)

            logger.info(f"Information | Uptime checked: {ctx.author}")
        except Exception as e:
            print(f"There was an error: {e}")

    @commands.command(aliases=["userinfo"])
    async def whois(self, ctx, member: discord.Member):
        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"→ Userinfo For {member}",
            description="— "
            "\n➤ Shows all information about a user. "
            "\n➤ The information will be listed below!"
            "\n —",
        )

        status = {
            "online": "<:online:648195346186502145>",
            "idle": "<:idle:648195345800757260>",
            "offline": "<:offline:648195346127912970>",
            "dnd": "<:dnd:648195345985175554>",
        }

        roles = [role for role in member.roles]
        roles = " ".join([f"`{role.name}`" for role in roles])

        embed.set_thumbnail(
            url=member.avatar_url_as(size=1024, format=None, static_format="png")
        )
        embed.add_field(name="• Account name: ", value=str(member))
        embed.add_field(name="• Discord ID: ", value=str(member.id))
        embed.add_field(name="• Nickname: ", value=member.nick or "No nickname!")
        embed.add_field(
            name="• Account created at: ",
            value=member.created_at.strftime("%A %d, %B %Y."),
        )
        embed.add_field(
            name="• Account joined at: ",
            value=member.joined_at.strftime("%A %d, %B %Y"),
        )

        # - TODO: See why this is returning "None" even though there is an if statement to check this
        if member.activity is None:
            embed.add_field(name="• Activity: ", value="No activity!")
        else:
            embed.add_field(name="• Activity: ", value=member.activity.name)
        if member.bot is True:
            embed.add_field(
                name="• Discord bot? ",
                value="<:bot_tag:648198074094583831> = <:tick_yes:648198008076238862>",
            )
        else:
            embed.add_field(
                name="• Discord bot?",
                value="<:bot_tag:648198074094583831> = <:tick_no:648198035435945985>",
            )
        if member.is_on_mobile() is True:
            embed.add_field(name="• On mobile? ", value=":iphone:")
        else:
            embed.add_field(name="• On mobile? ", value=":no_mobile_phones:")

        embed.add_field(name="• Status: ", value=status[member.status.name])
        embed.add_field(name="• Top role: ", value=f"`{member.top_role.name}`")
        embed.add_field(name="• Roles: ", inline=False, value=roles)

        await ctx.send(embed=embed)

        logger.info(f"Information | Sent Whois: {ctx.author}")

    @whois.error
    async def whois_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Member!",
                description="• Please mention a valid member! Example: `l!whois @user`",
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!whois @user`",
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def status(self, ctx, online_status):
        if str(online_status).lower() == "dnd":
            await self.bot.change_presence(status=discord.Status.dnd)
        elif str(online_status).lower() == "idle":
            await self.bot.change_presence(status=discord.Status.idle)
        elif str(online_status).lower() == "offline":
            await self.bot.change_presence(status=discord.Status.offline)
        else:
            await self.bot.change_presence(status=discord.Status.online)

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Online Status Changed!",
            description=f"• My status has been updated to: `{online_status.lower()}`",
        )

        await ctx.send(embed=embed)

        logger.info(
            f"Owner | Sent Status: {ctx.author} | Online Status: {online_status}"
        )

    @status.error
    async def change_status_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!status <online status>`",
            )
            await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def name(self, ctx, name):
        await self.bot.user.edit(username=name)

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Bot Name Changed!",
            description=f"• My name has been updated to: `{name}`",
        )

        await ctx.send(embed=embed)

        logger.info(f"Owner | Sent Name: {ctx.author} | Name: {name}")

    @name.error
    async def name_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!name <name>`",
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandError):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Unknown Error Has Occurred ",
                description=f"```python" f"{error}" f"```",
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Information(bot))
