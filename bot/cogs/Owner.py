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

    @commands.hybrid_command(help="Change the bot's presence status (owner only).")
    @commands.is_owner()
    async def status(self, ctx, new_status: str):
        """
        Change the bot's overall presence status.
        Usage: !status <online|idle|dnd|offline>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

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

    @commands.hybrid_command(help="Change the bot's username (owner only).")
    @commands.is_owner()
    async def name(self, ctx, *, new_name: str):
        """
        Change the bot's username.
        Usage: !name <new_username>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        await self.bot.user.edit(username=new_name)
        await ctx.send(f"✅ Username changed to `{new_name}`.")
        self.logger.info(f"Username changed to {new_name} by {ctx.author}")

    @commands.hybrid_command(help="Sync slash commands to this server (owner only).")
    @commands.is_owner()
    async def sync(self, ctx):
        """
        Sync slash commands to the current guild for immediate availability.
        Usage: !sync
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Synced {len(synced)} slash command(s) to this server.")
        self.logger.info(f"Synced {len(synced)} commands to {ctx.guild.name} by {ctx.author}")

    @commands.hybrid_command(help="Change the bot's playing message (owner only).")
    @commands.is_owner()
    async def playing(self, ctx, *, message: str):
        """
        Change the bot's "Playing ..." activity.
        Usage: !playing <message>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        await self.bot.change_presence(activity=discord.Game(name=message))
        await ctx.send(f"✅ Playing message set to: `{message}`")
        self.logger.info(f"Playing message changed to '{message}' by {ctx.author}")

    @commands.hybrid_command(help="Show last N bot log entries (owner only).")
    @commands.is_owner()
    async def logs(self, ctx, n: int = 20):
        """
        Display the last N log entries from the bot's in-memory buffer.
        Usage: !logs [n]  (default 20, max 100)
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()

        n = max(1, min(n, 100))
        entries = self.bot.log_buffer.get_entries(n)

        if not entries:
            await ctx.send("No log entries recorded yet.")
            return

        text = "\n".join(entries)
        chunks = []
        while text:
            if len(text) <= 1990:
                chunks.append(text)
                break
            split_at = text.rfind("\n", 0, 1990)
            if split_at == -1:
                split_at = 1990
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip("\n")

        for chunk in chunks:
            await ctx.send(f"```\n{chunk}\n```")


async def setup(bot):
    """Register the Owner cog with the bot."""
    await bot.add_cog(Owner(bot))
