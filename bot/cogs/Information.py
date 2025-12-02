"""
Information Cog
===============

Displays general statistics and informational commands about the bot.
"""

import time
import platform
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import psutil
import distro


class Information(commands.Cog):
    """
    Cog for displaying general statistics and informational commands about the bot.
    """

    def __init__(self, bot):
        """
        Initialize the Information cog.

        Args:
            bot: The instance of the DarkBot.
        """
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    @commands.command(
        name="botstats", help="Displays general statistics about the bot."
    )
    async def botstats(self, ctx):
        """
        Show a summary of in-memory and Redis-backed statistics.

        Fields include uptime, guild count, user count, cogs loaded,
        commands used, messages seen, and errors logged.
        """
        stats = await self.bot.get_stats()
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=self.bot.embed_color,
            timestamp=datetime.utcnow(),
        )
        for name, value in stats.items():
            embed.add_field(
                name=name.replace("_", " ").title(), value=value, inline=True
            )
        await ctx.send(embed=embed)
        self.logger.info(f"Bot statistics sent to {ctx.author} in {ctx.guild}")

    @commands.command(
        aliases=["commands", "cmds"], help="Shows all available commands."
    )
    async def robot_commands(self, ctx):
        """
        List every command grouped by its cog.

        Uses the current prefix to render each command name.
        """
        embed = discord.Embed(
            title="→ All Available Bot Commands!",
            color=self.bot.colors["info"],
            description=(
                "—\n"
                "➤ Shows info about all available bot commands!\n"
                "➤ Capitalization does not matter for the bot prefix.\n"
                "➤ Use `!help <command>` for more details.\n"
                "—"
            ),
        )
        embed.set_thumbnail(url="https://i.imgur.com/BUlgakY.png")
        prefix = ctx.prefix
        for cog_name, _ in self.bot.cogs.items():
            cmds = [
                f"`{prefix}{cmd.name}`"
                for cmd in self.bot.commands
                if cmd.cog_name == cog_name and not cmd.hidden
            ]
            if cmds:
                embed.add_field(
                    name=f"• {cog_name} Commands", value=" ".join(cmds), inline=False
                )
        await ctx.send(embed=embed)
        self.logger.info(f"Command list sent to {ctx.author} in {ctx.guild}")

    @commands.command(name="help", help="Shows help for a command or lists all commands.")
    async def help_command(self, ctx, *, command_name: str = None):
        """
        Display help for a specific command or list all commands.
        
        Usage: 
            !help - Shows all commands
            !help <command> - Shows detailed help for a command
        """
        if command_name is None:
            # Show all commands - delegate to robot_commands
            await self.robot_commands(ctx)
            return
        
        # Show help for specific command
        cmd = self.bot.get_command(command_name)
        if cmd is None:
            await ctx.send(f"❌ Command `{command_name}` not found.")
            return
        
        embed = discord.Embed(
            title=f"→ Help: {cmd.name}",
            color=self.bot.colors["info"],
            timestamp=datetime.utcnow(),
        )
        
        # Command description
        if cmd.help:
            embed.description = cmd.help
        elif cmd.brief:
            embed.description = cmd.brief
        else:
            embed.description = "No description available."
        
        # Usage
        usage = f"{ctx.prefix}{cmd.name}"
        if cmd.signature:
            usage += f" {cmd.signature}"
        embed.add_field(name="• Usage", value=f"`{usage}`", inline=False)
        
        # Aliases
        if cmd.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in cmd.aliases)
            embed.add_field(name="• Aliases", value=aliases, inline=False)
        
        # Cog
        if cmd.cog_name:
            embed.add_field(name="• Category", value=cmd.cog_name, inline=True)
        
        await ctx.send(embed=embed)
        self.logger.info(f"Help for '{command_name}' shown to {ctx.author}")

    @commands.command(
        name="redisget",
        help="Fetch a specific Redis stat by key. Example: !redisget errors",
    )
    async def redisget(self, ctx, key: str):
        """
        Retrieve a single Redis-backed statistic by its key.

        Returns an embed showing the key and its integer value.
        """
        if not self.redis or not self.redis.redis:
            await ctx.send("❌ Redis is not connected.")
            return
        try:
            value = await self.redis.get_command_usage(key)
            if value is None:
                await ctx.send(f"❓ Redis key `{key}` does not exist or has no value.")
            else:
                embed = discord.Embed(
                    title="📦 Redis Data Lookup",
                    description=f"**Key:** `{key}`\n**Value:** `{value}`",
                    color=self.bot.colors["info"],
                    timestamp=datetime.utcnow(),
                )
                await ctx.send(embed=embed)
                self.logger.info(
                    f"Fetched Redis key '{key}' for {ctx.author} in {ctx.guild}"
                )
        except Exception as e:
            await ctx.send("⚠️ Failed to fetch Redis key.")
            self.logger.exception(f"Error fetching Redis key '{key}': {e}")

    @commands.command(help="System & bot info overview.")
    async def info(self, ctx):
        """
        Show detailed system and bot information.

        Includes OS, CPU/RAM/Disk usage, uptime, member/guild count,
        and library versions.
        """
        try:
            distro_info = distro.os_release_info().get("pretty_name", "Unknown OS")
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().used / (1024**3)
            disk = psutil.disk_usage("/").used / (1024**3)
            uptime_td = self.bot.uptime
            users = len(self.bot.users)
            guilds = len(self.bot.guilds)

            embed = discord.Embed(
                title="→ DarkBot System Info",
                color=self.bot.embed_color,
                timestamp=datetime.utcnow(),
                description="—\n➤ To view my commands run `!commands`\n—",
            )
            embed.set_thumbnail(url="https://bit.ly/2JGhA94")
            embed.add_field(name="• Operating System", value=distro_info, inline=True)
            embed.add_field(name="• CPU Usage", value=f"{cpu:.1f}%", inline=True)
            embed.add_field(name="• RAM Used", value=f"{ram:.2f} GB", inline=True)
            embed.add_field(name="• Disk Used", value=f"{disk:.2f} GB", inline=True)
            embed.add_field(
                name="• Bot Uptime", value=str(uptime_td).split(".")[0], inline=True
            )
            embed.add_field(name="• Member Count", value=str(users), inline=True)
            embed.add_field(name="• Guild Count", value=str(guilds), inline=True)
            embed.add_field(
                name="• discord.py Version", value=discord.__version__, inline=True
            )
            embed.add_field(
                name="• Python Version", value=platform.python_version(), inline=True
            )
            embed.set_footer(text="Made by Shiva187")

            await ctx.send(embed=embed)
            self.logger.info(f"info command run by {ctx.author}")
        except Exception as e:
            await ctx.send("⚠️ Failed to gather system info.")
            self.logger.exception(f"Error in info command: {e}")

    @commands.command(help="Sends the bot invite link.")
    async def invite(self, ctx):
        """
        DM the user with an invite link for the bot.
        """
        url = "http://bit.ly/2Zm5XyP"
        embed = discord.Embed(
            title="→ Invite Me To Your Server!",
            description=f"• [**Click Here**]({url})",
            color=self.bot.embed_color,
        )
        await ctx.message.add_reaction("🤖")
        await ctx.author.send(embed=embed)
        self.logger.info(f"invite sent to {ctx.author}")

    @commands.command(help="Check the bot's websocket & API latency.")
    async def ping(self, ctx):
        """
        Measure and display the bot's WS and REST latencies.
        """
        before = time.monotonic()
        ws_ping = int(self.bot.latency * 1000)
        msg = await ctx.send("Pinging...")
        rest_ping = int((time.monotonic() - before) * 1000)
        await msg.delete()
        embed = discord.Embed(
            title="→ Ping",
            color=self.bot.embed_color,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="• WS Latency", value=f"{ws_ping} ms", inline=True)
        embed.add_field(name="• REST Latency", value=f"{rest_ping} ms", inline=True)
        await ctx.send(embed=embed)
        self.logger.info(f"Ping responded to {ctx.author}")

    @commands.command(help="Command to check the bot's and system's uptime.")
    async def uptime(self, ctx):
        """
        Display both the bot's uptime and the system's uptime.
        """
        now = time.time()
        bot_secs = int(
            now - self.bot.start_time.timestamp()
            if hasattr(self.bot.start_time, "timestamp")
            else now - self.bot.start_time
        )
        bot_up = str(timedelta(seconds=bot_secs))
        sys_secs = int(now - psutil.boot_time())
        sys_up = str(timedelta(seconds=sys_secs))
        embed = discord.Embed(
            title="→ Uptime",
            color=self.bot.embed_color,
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="• Bot Uptime", value=bot_up, inline=False)
        embed.add_field(name="• System Uptime", value=sys_up, inline=False)
        await ctx.send(embed=embed)
        self.logger.info(f"Uptime checked by {ctx.author}")

    @commands.command(aliases=["userinfo"], help="Show information about a member.")
    async def whois(self, ctx, member: discord.Member):
        """
        Display detailed information about a guild member.
        """
        status_icons = {
            "online": "🟢",
            "idle": "🌙",
            "dnd": "⛔",
            "offline": "⚪",
        }
        roles = ", ".join(
            role.name for role in member.roles if role.name != "@everyone"
        )
        embed = discord.Embed(
            title=f"→ User Info: {member}",
            color=self.bot.embed_color,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="• Username", value=str(member), inline=True)
        embed.add_field(name="• ID", value=member.id, inline=True)
        embed.add_field(name="• Nickname", value=member.nick or "None", inline=True)
        embed.add_field(
            name="• Created At",
            value=member.created_at.strftime("%Y-%m-%d"),
            inline=True,
        )
        embed.add_field(
            name="• Joined At", value=member.joined_at.strftime("%Y-%m-%d"), inline=True
        )
        embed.add_field(
            name="• Status",
            value=status_icons.get(member.status.name, member.status.name),
            inline=True,
        )
        embed.add_field(name="• Top Role", value=member.top_role.name, inline=True)
        embed.add_field(name="• Roles", value=roles or "None", inline=False)
        await ctx.send(embed=embed)
        self.logger.info(f"whois run for {member} by {ctx.author}")


async def setup(bot):
    """Register the Information cog with the bot."""
    await bot.add_cog(Information(bot))
