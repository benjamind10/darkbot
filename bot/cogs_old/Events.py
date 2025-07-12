import discord
from discord.ext import commands

from logging_files.events_logging import logger


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        welcome_channel = guild.system_channel

        # embed = discord.Embed(
        #     color=self.bot.embed_color,
        #     title="→ Thanks for inviting me!",
        #     description="• Please use `l!help` for more information on the bot."
        # )

        # if welcome_channel is not None:
        #     await welcome_channel.send(embed=embed)
        # else:
        #     pass

        logger.info(f"Events | Joined Guild: {guild.name} | ID: {guild.id}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        logger.info(f"Events | Left Guild: {guild.name} | ID: {guild.id}")


async def setup(bot):
    await bot.add_cog(Events(bot))
