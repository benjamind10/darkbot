import asyncio
import time

import discord
import platform
from discord.ext import commands

from logging_files.information_logging import logger


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["commands_list", "cmds"])
    async def commands(self, ctx):
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


async def setup(bot):
    await bot.add_cog(Information(bot))
    print("Information cog loaded")
