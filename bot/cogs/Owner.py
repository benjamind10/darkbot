"""
Owner Cog
=========

Handles owner-only commands such as changing the bot's presence status,
username, playing message, and guild/member utilities.
"""

import random

import discord
from discord.ext import commands
from utils.discord_context import defer_if_interaction, send_for_context


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
            await defer_if_interaction(ctx)

        st = new_status.lower()
        mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "offline": discord.Status.offline,
        }
        if st in mapping:
            await self.bot.change_presence(status=mapping[st])
            await send_for_context(ctx, f"✅ Status changed to `{st}`.")
            self.logger.info(f"Status changed to {st} by {ctx.author}")
        else:
            await send_for_context(ctx, "❌ Invalid status. Choose: online, idle, dnd, offline.")

    @commands.hybrid_command(help="Change the bot's username (owner only).")
    @commands.is_owner()
    async def name(self, ctx, *, new_name: str):
        """
        Change the bot's username.
        Usage: !name <new_username>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        await self.bot.user.edit(username=new_name)
        await send_for_context(ctx, f"✅ Username changed to `{new_name}`.")
        self.logger.info(f"Username changed to {new_name} by {ctx.author}")

    @commands.hybrid_command(help="Sync slash commands to this server (owner only).")
    @commands.is_owner()
    async def sync(self, ctx):
        """
        Sync slash commands to the current guild for immediate availability.
        Usage: !sync
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)
        await send_for_context(ctx, f"✅ Synced {len(synced)} slash command(s) to this server.")
        self.logger.info(f"Synced {len(synced)} commands to {ctx.guild.name} by {ctx.author}")

    @commands.hybrid_command(help="Change the bot's playing message (owner only).")
    @commands.is_owner()
    async def playing(self, ctx, *, message: str):
        """
        Change the bot's "Playing ..." activity.
        Usage: !playing <message>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        await self.bot.change_presence(activity=discord.Game(name=message))
        await send_for_context(ctx, f"✅ Playing message set to: `{message}`")
        self.logger.info(f"Playing message changed to '{message}' by {ctx.author}")

    @commands.hybrid_command(help="Show last N bot log entries (owner only).")
    @commands.is_owner()
    async def logs(self, ctx, n: int = 20):
        """
        Display the last N log entries from the bot's in-memory buffer.
        Usage: !logs [n]  (default 20, max 100)
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        n = max(1, min(n, 100))
        entries = self.bot.log_buffer.get_entries(n)

        if not entries:
            await send_for_context(ctx, "No log entries recorded yet.")
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
            await send_for_context(ctx, f"```\n{chunk}\n```")

    @commands.hybrid_command(help="Generate a single-use invite from a guild (owner only).")
    @commands.is_owner()
    async def get_invite(self, ctx, id: int):
        """
        Create a single-use invite from a random text channel in the target guild.
        Usage: !get_invite <guild_id>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx, ephemeral=True)

        guild = self.bot.get_guild(id)
        if guild is None:
            await send_for_context(ctx, "❌ Guild not found.")
            return

        channels = [c.id for c in guild.text_channels]
        if not channels:
            await send_for_context(ctx, "❌ No text channels available.")
            return

        channel = self.bot.get_channel(random.choice(channels))
        invite = await channel.create_invite(max_uses=1)
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="Invite From Guild",
            description=f"• Invite: {invite}",
        )
        await ctx.author.send(embed=embed)
        await send_for_context(ctx, "✅ Invite sent to your DMs.")
        self.logger.info(f"get_invite for guild {id} by {ctx.author}")

    @commands.hybrid_command(help="List all roles for a member (owner only).")
    @commands.is_owner()
    async def check_roles(self, ctx, user: discord.Member):
        """
        Display all roles assigned to a guild member.
        Usage: !check_roles <member>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        role_mentions = [r.mention for r in user.roles if r != ctx.guild.default_role]
        description = " ".join(role_mentions) if role_mentions else "This user has no roles."
        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"Roles for {user.display_name}",
            description=description,
        )
        await send_for_context(ctx, embed=embed)
        self.logger.info(f"check_roles for {user} by {ctx.author}")

    @commands.hybrid_command(help="List all permissions for a member (owner only).")
    @commands.is_owner()
    async def check_permissions(self, ctx, user: discord.Member):
        """
        Display all guild permissions granted to a member.
        Usage: !check_permissions <member>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        true_perms = [p[0] for p in user.guild_permissions if p[1]]
        description = ", ".join(true_perms).replace("_", " ").title() or "No permissions."
        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"Permissions for {user.display_name}",
            description=description,
        )
        await send_for_context(ctx, embed=embed)
        self.logger.info(f"check_permissions for {user} by {ctx.author}")


async def setup(bot):
    """Register the Owner cog with the bot."""
    await bot.add_cog(Owner(bot))
