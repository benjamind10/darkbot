import discord
from discord.ext import commands
import logging


class BoardGames(commands.Cog):
    """A Cog that handles BoardGame stuff."""

    BASE_URL = "https://api.geekdo.com/xmlapi/"

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @commands.command(name="hello")
    async def hello(self, ctx):
        await ctx.send("Hello, world!")
        self.logger.info(f"'hello' command used by {ctx.author} in {ctx.guild}")


async def setup(bot):
    await bot.add_cog(BoardGames(bot))
