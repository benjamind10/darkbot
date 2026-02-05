"""
ModLog Cog
==========

Moderation logging and guild configuration commands.
Handles logging of moderation actions, message deletes/edits to a designated channel.
"""

import discord
from discord.ext import commands
from typing import Optional
from datetime import datetime
import psycopg2.extras


class ModLog(commands.Cog):
    """Moderation logging and configuration commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    async def get_guild_config(self, guild_id: int) -> Optional[dict]:
        """Get guild configuration from database."""
        try:
            with self.bot.db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.callproc('get_or_create_guild_config', [guild_id])
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            self.logger.error(f"ModLog | Error fetching guild config: {e}")
            return None

    async def get_modlog_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get the modlog channel for a guild."""
        config = await self.get_guild_config(guild.id)
        if not config or not config.get('modlog_channel_id'):
            return None

        channel = guild.get_channel(config['modlog_channel_id'])
        return channel if isinstance(channel, discord.TextChannel) else None

    async def log_to_modlog(self, guild: discord.Guild, embed: discord.Embed):
        """Send a log embed to the modlog channel."""
        channel = await self.get_modlog_channel(guild)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                self.logger.warning(f"ModLog | No permission to send to modlog in {guild.name}")
            except Exception as e:
                self.logger.error(f"ModLog | Error sending to modlog: {e}")

    # ==================== Configuration Commands ====================

    @commands.hybrid_group(name="modlog", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def modlog(self, ctx):
        """Moderation log configuration commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @modlog.command(name="setchannel")
    @commands.has_permissions(administrator=True)
    async def modlog_setchannel(self, ctx, channel: discord.TextChannel):
        """
        Set the modlog channel for this server.

        Args:
            channel: The channel to use for moderation logs
        """
        try:
            with self.bot.db_conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO guild_config (guild_id, modlog_channel_id) VALUES (%s, %s) "
                    "ON CONFLICT (guild_id) DO UPDATE SET modlog_channel_id = %s",
                    (ctx.guild.id, channel.id, channel.id)
                )
                self.bot.db_conn.commit()

            embed = discord.Embed(
                title="✅ Modlog Channel Set",
                description=f"Moderation logs will now be sent to {channel.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            self.logger.info(f"ModLog | Set modlog channel for {ctx.guild.name} to #{channel.name}")
        except Exception as e:
            self.logger.error(f"ModLog | Error setting modlog channel: {e}")
            await ctx.send("❌ Failed to set modlog channel. Check database connection.")

    @modlog.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def modlog_disable(self, ctx):
        """Disable moderation logging for this server."""
        try:
            with self.bot.db_conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE guild_config SET modlog_channel_id = NULL WHERE guild_id = %s",
                    (ctx.guild.id,)
                )
                self.bot.db_conn.commit()

            embed = discord.Embed(
                title="✅ Modlog Disabled",
                description="Moderation logging has been disabled for this server.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            self.logger.info(f"ModLog | Disabled modlog for {ctx.guild.name}")
        except Exception as e:
            self.logger.error(f"ModLog | Error disabling modlog: {e}")
            await ctx.send("❌ Failed to disable modlog.")

    @modlog.command(name="status")
    @commands.has_permissions(administrator=True)
    async def modlog_status(self, ctx):
        """Check the current modlog configuration."""
        config = await self.get_guild_config(ctx.guild.id)

        if not config:
            await ctx.send("❌ Failed to fetch guild configuration.")
            return

        embed = discord.Embed(
            title=f"📋 Modlog Configuration - {ctx.guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Modlog channel
        if config.get('modlog_channel_id'):
            channel = ctx.guild.get_channel(config['modlog_channel_id'])
            if channel:
                embed.add_field(
                    name="Modlog Channel",
                    value=f"✅ {channel.mention}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Modlog Channel",
                    value="❌ Configured but channel not found",
                    inline=False
                )
        else:
            embed.add_field(
                name="Modlog Channel",
                value="❌ Not configured",
                inline=False
            )

        # Welcome/goodbye channels (for future features)
        if config.get('welcome_channel_id'):
            channel = ctx.guild.get_channel(config['welcome_channel_id'])
            embed.add_field(
                name="Welcome Channel",
                value=channel.mention if channel else "❌ Channel not found",
                inline=True
            )

        # Auto-role (for future features)
        if config.get('auto_role_id'):
            role = ctx.guild.get_role(config['auto_role_id'])
            embed.add_field(
                name="Auto Role",
                value=role.mention if role else "❌ Role not found",
                inline=True
            )

        # Prefix
        embed.add_field(
            name="Prefix",
            value=f"`{config.get('prefix', '!')}`",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="cases")
    @commands.has_permissions(manage_messages=True)
    async def cases(self, ctx, member: Optional[discord.Member] = None):
        """
        View moderation cases for a member or all recent cases.

        Args:
            member: The member to view cases for (optional)
        """
        try:
            with self.bot.db_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                if member:
                    cursor.execute(
                        "SELECT * FROM moderation_logs WHERE guild_id = %s AND target_id = %s "
                        "ORDER BY case_id DESC LIMIT 10",
                        (ctx.guild.id, member.id)
                    )
                    title = f"📋 Recent Cases for {member}"
                else:
                    cursor.execute(
                        "SELECT * FROM moderation_logs WHERE guild_id = %s "
                        "ORDER BY case_id DESC LIMIT 10",
                        (ctx.guild.id,)
                    )
                    title = "📋 Recent Moderation Cases"

                cases = cursor.fetchall()

            if not cases:
                await ctx.send("No moderation cases found.")
                return

            embed = discord.Embed(
                title=title,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            for case in cases:
                moderator = ctx.guild.get_member(case['moderator_id'])
                target = ctx.guild.get_member(case['target_id']) or f"User ID: {case['target_id']}"

                value = f"**Type:** {case['action_type']}\n"
                value += f"**Moderator:** {moderator.mention if moderator else f'ID: {case['moderator_id']}'}\n"
                value += f"**Target:** {target.mention if isinstance(target, discord.Member) else target}\n"
                value += f"**Reason:** {case['reason'] or 'No reason provided'}\n"
                value += f"**Date:** {case['created_at'].strftime('%Y-%m-%d %H:%M UTC')}"

                embed.add_field(
                    name=f"Case #{case['case_id']}",
                    value=value,
                    inline=False
                )

            if len(cases) == 10:
                embed.set_footer(text="Showing 10 most recent cases")

            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"ModLog | Error fetching cases: {e}")
            await ctx.send("❌ Failed to fetch moderation cases.")


async def setup(bot):
    """Load the ModLog cog."""
    await bot.add_cog(ModLog(bot))
