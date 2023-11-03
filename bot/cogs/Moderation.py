import traceback

import discord
from discord.ext import commands

from logging_files.moderation_logging import logger


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["addrole"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def add_role(self, ctx, role: discord.Role, member: discord.Member,):
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

            logger.info(f"Moderation | Sent Addrole: {ctx.author} | Role added: {role} | To: {member}")
        else:
            traceback.print_exc()

    @add_role.error
    async def add_role_error(self, ctx, error):
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

    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided!"):
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
            await member.ban(reason=reason)

            await ctx.send(embed=embed)

            embed2 = discord.Embed(
                color=self.bot.embed_color,
                title=f"{member} → You Have Been Banned!"
            )
            embed2.add_field(name=f"• Moderator", value=f"{sender}")
            embed2.add_field(name="• Reason", value=f"{reason}")
            embed2.set_footer(text=f"Banned from: {ctx.guild}")

            await member.send(embed=embed2)

            logger.info(f"Moderation | Sent Ban: {ctx.author} | Banned: {member} | Reason: {reason}")
        else:
            traceback.print_exc()

    @ban.error
    async def ban_error(self, ctx, error):
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


async def setup(bot):
    await bot.add_cog(Moderation(bot))
    print("Moderation cog loaded")