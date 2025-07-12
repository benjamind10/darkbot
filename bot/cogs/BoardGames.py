import discord
from discord.ext import commands
import logging


class BoardGames(commands.Cog):
    """A Cog that handles BoardGame stuff'."""

    BASE_URL = "https://api.geekdo.com/xmlapi/"

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    async def send_paginated_embeds(self, ctx, games, title, color):
        EMBED_MAX_DESC_LENGTH = 2048
        EMBED_MAX_FIELDS = 25

        pages = []
        current_page = []
        current_length = 0

        for game in games:
            if (
                current_length + len(game) > EMBED_MAX_DESC_LENGTH
                or len(current_page) >= EMBED_MAX_FIELDS
            ):
                pages.append(current_page)
                current_page = []
                current_length = 0
            current_page.append(game)
            current_length += len(game)

        if current_page:
            pages.append(current_page)

        for i, page in enumerate(pages):
            description = "\n".join(page)
            embed = discord.Embed(
                title=f"{title} (Page {i+1} of {len(pages)})",
                description=description,
                color=color,
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Sent page {i+1} of {len(pages)} for {title}")

    @commands.command(name="hello")
    async def hello(self, ctx):
        await ctx.send("Hello, world!")
        self.logger.info(f"'hello' command used by {ctx.author} in {ctx.guild}")


async def setup(bot):
    await bot.add_cog(BoardGames(bot))
