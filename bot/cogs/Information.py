import asyncio
import time
import discord
import platform
import distro
import psutil
from discord.ext import commands

from logging_files.information_logging import logger


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            # linux_distro = distro.os_release_info()
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
            # embed.add_field(name=f"• OPERATING System:", inline=True, value=f":computer: — {linux_distro['pretty_name']}")
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


async def setup(bot):
    await bot.add_cog(Information(bot))
    print("Information cog loaded")