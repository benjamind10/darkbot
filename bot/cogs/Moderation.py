"""
Moderation Cog
==============

Handles moderation commands like ban, kick, warn, role management, and message purging.
"""

import traceback
import discord
from discord.ext import commands


class Moderation(commands.Cog):
    """Moderation commands for managing server members and content."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    # ========== Role Management Commands ==========

    @commands.hybrid_command(aliases=["addrole"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def add_role(self, ctx, role: discord.Role, member: discord.Member):
        """
        Add a role to a member.
        
        Usage: !addrole <role> <member>
        Requires: Manage Roles permission
        """
        if ctx.guild.me.top_role < member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than me!"
            )
            await ctx.send(embed=embed)
        elif ctx.author.top_role <= member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than you or equal permissions!"
            )
            await ctx.send(embed=embed)
        elif ctx.guild.me.top_role > member.top_role:
            await member.add_roles(role)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="• Add Role Command!",
                description=f"{member.mention} → Has been given the role `{role}`"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Moderation | Sent Addrole: {ctx.author} | Role added: {role} | To: {member}")
        else:
            traceback.print_exc()

    @add_role.error
    async def add_role_error(self, ctx, error):
        """Handle errors for add_role command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Role / Member!",
                description="• Please select a valid role / member! Example: `!addrole <role ID / rolename> @user`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!addrole <Role ID / Rolename> @user`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["removerole", "delrole"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def remove_role(self, ctx, role: discord.Role, member: discord.Member):
        """
        Remove a role from a member.
        
        Usage: !removerole <role> <member>
        Requires: Manage Roles permission
        """
        if ctx.guild.me.top_role < member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than me!"
            )
            await ctx.send(embed=embed)
        elif ctx.author.top_role <= member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than you or equal permissions!"
            )
            await ctx.send(embed=embed)
        elif ctx.guild.me.top_role > member.top_role:
            await member.remove_roles(role)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="• Remove Role Command",
                description=f"{member.mention} → Lost the role `{role}`"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Moderation | Sent Remove Role: {ctx.author} | Removed Role: {role} | To: {member}")
        else:
            traceback.print_exc()

    @remove_role.error
    async def remove_role_error(self, ctx, error):
        """Handle errors for remove_role command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Role / Member!",
                description="• Please select a valid role / member! Example: `!delrole <role ID / rolename> @user`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!delrole <Role ID / Rolename> @user`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    # ========== Ban Commands ==========

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided!"):
        """
        Ban a member from the server.
        
        Usage: !ban <member> [reason]
        Requires: Ban Members permission
        """
        if ctx.guild.me.top_role < member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than me!"
            )
            await ctx.send(embed=embed)
        elif ctx.author.top_role <= member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than you or equal permissions!"
            )
            await ctx.send(embed=embed)
        elif ctx.guild.me.top_role > member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="• Ban command",
                description=f"{member.mention} → has been **Banned!** Bye bye! :wave:"
            )
            sender = ctx.author
            
            # Try to DM the user before banning
            try:
                embed2 = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"{member} → You Have Been Banned!"
                )
                embed2.add_field(name=f"• Moderator", value=f"{sender}")
                embed2.add_field(name="• Reason", value=f"{reason}")
                embed2.set_footer(text=f"Banned from: {ctx.guild}")
                await member.send(embed=embed2)
            except:
                pass  # User has DMs disabled
            
            await member.ban(reason=reason)
            await ctx.send(embed=embed)
            
            self.logger.info(f"Moderation | Sent Ban: {ctx.author} | Banned: {member} | Reason: {reason}")
        else:
            traceback.print_exc()

    @ban.error
    async def ban_error(self, ctx, error):
        """Handle errors for ban command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Member!",
                description="• Please mention a valid member! Example: `!ban @user [reason]`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!ban @user [reason]`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def forceban(self, ctx, *, id: int):
        """
        Ban a user by ID (even if not in server).
        
        Usage: !forceban <user_id>
        Requires: Ban Members permission
        """
        await ctx.guild.ban(discord.Object(id))
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="• Forceban Command",
            description=f"<@{id}> → has been **Forcefully banned!** Bye bye! :wave:"
        )
        await ctx.send(embed=embed)
        self.logger.info(f"Moderation | Sent Force Ban: {ctx.author} | Force Banned: {id}")

    @forceban.error
    async def forceban_error(self, ctx, error):
        """Handle errors for forceban command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid ID!",
                description="• Please use a valid Discord ID! Example: `!forceban <ID>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid argument! Example: `!forceban <ID>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, *, id: int):
        """
        Unban a user by ID.
        
        Usage: !unban <user_id>
        Requires: Ban Members permission
        """
        await ctx.guild.unban(discord.Object(id))
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="• Unban Command",
            description=f"<@{id}> → has been **Unbanned!** Welcome back! :wave:"
        )
        await ctx.send(embed=embed)
        self.logger.info(f"Moderation | Sent Unban: {ctx.author} | Unbanned: {id}")

    @unban.error
    async def unban_error(self, ctx, error):
        """Handle errors for unban command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid ID!",
                description="• Please use a valid Discord ID! Example: `!unban <ID>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid Discord ID! Example: `!unban 546812331213062144`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    # ========== Kick Commands ==========

    @commands.hybrid_command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided!"):
        """
        Kick a member from the server.
        
        Usage: !kick <member> [reason]
        Requires: Kick Members permission
        """
        if ctx.guild.me.top_role < member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than me!"
            )
            await ctx.send(embed=embed)
        elif ctx.author.top_role <= member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than you or equal permissions!"
            )
            await ctx.send(embed=embed)
        elif ctx.guild.me.top_role > member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="• Kick Command",
                description=f"{member.mention} → has been **kicked!** Bye bye! :wave:"
            )
            sender = ctx.author
            
            # Try to DM the user before kicking
            try:
                embed2 = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"{member} → You have been kicked!"
                )
                embed2.add_field(name=f"• Moderator", value=f"{sender}")
                embed2.add_field(name="• Reason", value=f"{reason}")
                embed2.set_footer(text=f"Kicked from: {ctx.guild}")
                await member.send(embed=embed2)
            except:
                pass  # User has DMs disabled
            
            await member.kick(reason=reason)
            await ctx.send(embed=embed)
            
            self.logger.info(f"Moderation | Sent Kick: {ctx.author} | Kicked: {member} | Reason: {reason}")
        else:
            traceback.print_exc()

    @kick.error
    async def kick_error(self, ctx, error):
        """Handle errors for kick command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Member!",
                description="• Please mention a valid member! Example: `!kick @user [reason]`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!kick @user [reason]`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)
        else:
            raise error

    # ========== Warning Commands ==========

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided!"):
        """
        Warn a member.
        
        Usage: !warn <member> [reason]
        Requires: Manage Messages permission
        """
        if ctx.guild.me.top_role < member.top_role:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ User Information",
                description="• The user has higher permissions than me!"
            )
            await ctx.send(embed=embed)
        elif ctx.guild.me.top_role > member.top_role:
            sender = ctx.author
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="• Warn Command",
                description=f"{member.mention} → has been **Warned!**"
            )
            await ctx.send(embed=embed)

            try:
                embed2 = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"{member} → You have been warned!"
                )
                embed2.add_field(name=f"• Moderator", value=f"`{sender}`")
                embed2.add_field(name="• Reason", value=f"`{reason}`")
                embed2.set_footer(text=f"Warning sent from: {ctx.guild}")
                await member.send(embed=embed2)
            except:
                pass  # User has DMs disabled

            self.logger.info(f"Moderation | Sent Warn: {ctx.author} | Warned: {member} | Reason: {reason}")

    @warn.error
    async def warn_error(self, ctx, error):
        """Handle errors for warn command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Member!",
                description="• Please mention a valid member! Example: `!warn @user [reason]`"
            )
            await ctx.send(embed=embed)
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!warn @user [reason]`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    # ========== Message Management ==========

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """
        Delete multiple messages at once.
        
        Usage: !purge <amount>
        Requires: Manage Messages permission
        """
        await ctx.channel.purge(limit=amount)
        self.logger.info(f"Moderation | Sent Purge: {ctx.author} | Purged: {amount} messages")

    @purge.error
    async def purge_error(self, ctx, error):
        """Handle errors for purge command."""
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Amount Of Messages!",
                description="• Please put a valid number! Example: `!purge <number>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!purge <number>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Missing Permissions",
                description="• You do not have permissions to run this command!"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Bot Missing Permissions!",
                description="• Please give me permissions to use this command!"
            )
            await ctx.send(embed=embed)

    # ========== Voice Channel Management ==========

    @commands.hybrid_command()
    @commands.has_permissions(move_members=True)
    async def dc_voice(self, ctx, member: discord.Member):
        """
        Disconnect a user from a voice channel.
        
        Usage: !dc_voice <member>
        Requires: Move Members permission
        """
        if member.voice is None or member.voice.channel is None:
            await ctx.send(f"{member.mention} is not in a voice channel!")
            return

        await member.move_to(None)
        await ctx.send(f"Disconnected {member.mention} from their voice channel.")
        self.logger.info(f"Moderation | Disconnected: {member} | By: {ctx.author}")


async def setup(bot):
    """Load the Moderation cog."""
    await bot.add_cog(Moderation(bot))
