import random

import discord
import requests
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
            print(guild)
            for channel in guild.text_channels:
                channels = [channel.id]

            picked = random.choice(channels)
            channel = self.bot.get_channel(picked)

            embed = discord.Embed(
                color=self.bot.embed_color,
                title=f"→ Invite From Guild",
                description=f"• Invite: {await channel.create_invite(max_uses=1)}"
            )

            await ctx.author.send(embed=embed)

            logger.info(f"Owner | Sent Get Invite: {ctx.author}")
        except Exception as e:
            print(f'There was an error: {e}')


async def setup(client):
    await client.add_cog(Owner(client))
    print("Owner cog loaded")
    