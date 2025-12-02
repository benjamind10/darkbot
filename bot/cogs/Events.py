"""
Events Cog
==========

Handles Discord events like guild joins and removals.
"""

import discord
from discord.ext import commands


class Events(commands.Cog):
    """Event listener cog for Discord bot events."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Triggered when the bot joins a new guild.
        
        Args:
            guild (discord.Guild): The guild that was joined.
        """
        welcome_channel = guild.system_channel

        # Future: Send welcome message
        # embed = discord.Embed(
        #     color=self.bot.embed_color,
        #     title="→ Thanks for inviting me!",
        #     description="• Please use `!help` for more information on the bot."
        # )
        # if welcome_channel is not None:
        #     await welcome_channel.send(embed=embed)

        self.logger.info(f"Events | Joined Guild: {guild.name} | ID: {guild.id}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """
        Triggered when the bot is removed from a guild.
        
        Args:
            guild (discord.Guild): The guild that was left.
        """
        self.logger.info(f"Events | Left Guild: {guild.name} | ID: {guild.id}")


async def setup(bot):
    """Load the Events cog."""
    await bot.add_cog(Events(bot))
