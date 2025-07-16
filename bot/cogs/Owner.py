"""
Owner Cog
=========

Handles owner-only commands such as changing the bot's presence status,
username, and playing message.
"""

import discord
from discord.ext import commands


class Owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    @commands.command(help="Change the bot's presence status (owner only).")
    @commands.is_owner()
    async def status(self, ctx, new_status: str):
        """
        Change the bot's overall presence status.
        Usage: !status <online|idle|dnd|offline>
        """
        st = new_status.lower()
        mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "offline": discord.Status.offline,
        }
        if st in mapping:
            await self.bot.change_presence(status=mapping[st])
            await ctx.send(f"✅ Status changed to `{st}`.")
            self.logger.info(f"Status changed to {st} by {ctx.author}")
        else:
            await ctx.send("❌ Invalid status. Choose: online, idle, dnd, offline.")

    @commands.command(help="Change the bot's username (owner only).")
    @commands.is_owner()
    async def name(self, ctx, *, new_name: str):
        """
        Change the bot's username.
        Usage: !name <new_username>
        """
        await self.bot.user.edit(username=new_name)
        await ctx.send(f"✅ Username changed to `{new_name}`.")
        self.logger.info(f"Username changed to {new_name} by {ctx.author}")

    @commands.command(help="Change the bot's playing message (owner only).")
    @commands.is_owner()
    async def playing(self, ctx, *, message: str):
        """
        Change the bot's "Playing ..." activity.
        Usage: !playing <message>
        """
        await self.bot.change_presence(activity=discord.Game(name=message))
        await ctx.send(f"✅ Playing message set to: `{message}`")
        self.logger.info(f"Playing message changed to '{message}' by {ctx.author}")


async def setup(bot):
    """Register the Owner cog with the bot."""
    await bot.add_cog(Owner(bot))
