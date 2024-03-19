import asyncio
import time
import discord
import platform
import distro
import psutil
from discord.ext import commands
from datetime import datetime, timedelta
from logging_files.information_logging import logger


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = time.time()

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

            embed.add_field(name="• Information Commands!", inline=False, value=information)
            print(ctx.author.guild_permissions)
            print(ctx.channel.permissions_for(ctx.author))
            await ctx.send(embed=embed)

            logger.info(f"Information | Sent Commands: {ctx.author}")
        except Exception as e:
            print(f'There was an error: {e}')

    @commands.command()
    async def info(self, ctx):
        try:
            users = str(len(self.bot.users))
            guilds = str(len(self.bot.guilds))
            cpu = str(psutil.cpu_percent())
            ram = str(psutil.virtual_memory()[3] / 1000000000)
            ram_round = ram[:3]
            disk = str(psutil.disk_usage('/')[1] / 1000000000)
            disk_round = disk[:4]
            boot_time = str(psutil.boot_time() / 100000000)
            boot_time_round = boot_time[:4]
            linux_distro = distro.os_release_info()
            # get_news = self.bot.cursor.execute("SELECT rowid, * FROM bot_information")
            # news = get_news.fetchall()[0][3]

            embed = discord.Embed(
                color=self.bot.embed_color,
                title=f"→ DarkBot",
                description=f"— "
                            f"\n ➤ To view my commands run, `!commands`"
                            + "\n—"
            )
            embed.set_thumbnail(url="https://bit.ly/2JGhA94")
            embed.add_field(name=f"• OPERATING System:", inline=True, value=f":computer: — {linux_distro['pretty_name']}")
            embed.add_field(name=f"• CPU Usage:", inline=True, value=f":heavy_plus_sign: — {cpu} Percent used")
            embed.add_field(name=f"• RAM Usage:", inline=True,
                            value=f":closed_book:  —  {ram_round}  / 4  Gigabytes used")
            embed.add_field(name=f"• DISK Usage:", inline=True, value=f":white_circle: — {disk_round} / 40 Gigabytes")
            embed.add_field(name=f"• BOOT Time: ", inline=True, value=f":boot: —  {boot_time_round} seconds")
            embed.add_field(name=f"• MEMBER Count:", inline=True, value=f":bust_in_silhouette: —  {users} users")
            embed.add_field(name=f"• GUILD Count:", inline=True, value=f":house: — {guilds} connected guilds")
            embed.add_field(name=f"• LIBRARY Version:", inline=True,
                            value=f":gear: — discord.py version {discord.__version__}")
            embed.add_field(name=f"• PYTHON Version:", inline=True,
                            value=f":snake:  — Python version {platform.python_version()}")
            embed.set_footer(text=f"\n\nMade by Shiva187") #icon_url=f"\n\nhttps://i.imgur.com/TiUqRH8.gif")

            await ctx.send(embed=embed)

            logger.info(f"Information | Sent stats: {ctx.author}")
        except Exception as e:
            print(f'There was an error: {e}')

    @commands.command()
    async def invite(self, ctx):
        url = "(http://bit.ly/2Zm5XyP)"
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invite Me To Your Server!",
            description=f"• [**Click Here**]{url}"
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
            system_uptime_duration = str(timedelta(seconds=int(round(current_time - boot_time_timestamp))))

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Uptime",
            )
            embed.add_field(name="Bot Uptime", value=f"→ I have been running for: {bot_uptime_duration}", inline=False)
            embed.add_field(name="System Uptime", value=f"→ System has been running for: {system_uptime_duration}",
                            inline=False)

            await ctx.send(embed=embed)

            logger.info(f"Information | Uptime checked: {ctx.author}")
        except Exception as e:
            print(f'There was an error: {e}')

    @commands.command(aliases=['userinfo'])
    async def whois(self, ctx, member: discord.Member):
        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"→ Userinfo For {member}",
            description="— "
                        "\n➤ Shows all information about a user. "
                        "\n➤ The information will be listed below!"
                        "\n —"
        )

        status = {
            "online": "<:online:648195346186502145>",
            "idle": "<:idle:648195345800757260>",
            "offline": "<:offline:648195346127912970>",
            "dnd": "<:dnd:648195345985175554>"
        }

        roles = [role for role in member.roles]
        roles = " ".join([f"`{role.name}`" for role in roles])

        embed.set_thumbnail(url=member.avatar_url_as(size=1024, format=None, static_format="png"))
        embed.add_field(name="• Account name: ", value=str(member))
        embed.add_field(name="• Discord ID: ", value=str(member.id))
        embed.add_field(name="• Nickname: ", value=member.nick or "No nickname!")
        embed.add_field(name="• Account created at: ", value=member.created_at.strftime("%A %d, %B %Y."))
        embed.add_field(name="• Account joined at: ", value=member.joined_at.strftime("%A %d, %B %Y"))

        # - TODO: See why this is returning "None" even though there is an if statement to check this
        if member.activity is None:
            embed.add_field(name="• Activity: ", value="No activity!")
        else:
            embed.add_field(name="• Activity: ", value=member.activity.name)
        if member.bot is True:
            embed.add_field(name="• Discord bot? ",
                            value="<:bot_tag:648198074094583831> = <:tick_yes:648198008076238862>")
        else:
            embed.add_field(name="• Discord bot?",
                            value="<:bot_tag:648198074094583831> = <:tick_no:648198035435945985>")
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
                description="• Please mention a valid member! Example: `l!whois @user`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!whois @user`"
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
            description=f"• My status has been updated to: `{online_status.lower()}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Owner | Sent Status: {ctx.author} | Online Status: {online_status}")

    @status.error
    async def change_status_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!status <online status>`"
            )
            await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command()
    async def name(self, ctx, name):
        await self.bot.user.edit(username=name)

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Bot Name Changed!",
            description=f"• My name has been updated to: `{name}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Owner | Sent Name: {ctx.author} | Name: {name}")

    @name.error
    async def name_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `l!name <name>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandError):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Unknown Error Has Occurred ",
                description=f"```python"
                            f"{error}"
                            f"```"
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Information(bot))
