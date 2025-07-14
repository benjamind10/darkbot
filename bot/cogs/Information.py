"""
Information Cog
===============

Displays general statistics and informational commands about the bot.
"""

import discord
from discord.ext import commands
from datetime import datetime
import asyncio


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = getattr(bot, "logger", None)
        self.redis = getattr(bot, "redis_manager", None)

    def get_basic_stats(self):
        """Return basic bot stats (non-async)."""
        uptime = "N/A"
        if getattr(self.bot, "start_time", None):
            uptime = str(datetime.utcnow() - self.bot.start_time)

        return {
            "Uptime": uptime,
            "Guilds": len(self.bot.guilds),
            "Users": len(self.bot.users),
            "Cogs": len(self.bot.cogs),
        }

    async def get_redis_stats(self):
        """Fetch additional Redis metrics if Redis is enabled."""
        redis_stats = {}
        if self.redis and getattr(self.redis, "redis", None):
            keys = ["command_count", "messages_seen", "errors"]
            for key in keys:
                try:
                    redis_stats[key.replace("_", " ").title()] = (
                        await self.redis.get_command_usage(key)
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to get Redis stat '{key}': {e}")
                    redis_stats[key.replace("_", " ").title()] = "N/A"
        return redis_stats

    @commands.command(
        name="botstats", help="Displays general statistics about the bot."
    )
    async def show_stats(self, ctx):
        stats = await self.bot.get_stats()

        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=self.bot.embed_color,
            timestamp=datetime.utcnow(),
        )

        # Add each stat
        for name, value in stats.items():
            embed.add_field(
                name=name.replace("_", " ").capitalize(), value=value, inline=True
            )

        await ctx.send(embed=embed)
        self.logger.info(f"Bot statistics sent to {ctx.author} in {ctx.guild}")

    @commands.command(aliases=["commands", "cmds"])
    async def robot_commands(self, ctx):
        """Show a list of available bot commands grouped by category."""
        try:
            embed = discord.Embed(
                color=self.bot.colors["info"],
                title="→ All Available Bot Commands!",
                description=(
                    "—\n"
                    "➤ Shows info about all available bot commands!\n"
                    "➤ Capitalization does not matter for the bot prefix.\n"
                    "➤ Use `!help <command>` for more details.\n"
                    "—"
                ),
            )
            embed.set_thumbnail(url="https://i.imgur.com/BUlgakY.png")

            for cog_name, cog in self.bot.cogs.items():
                command_list = [
                    f"`{ctx.prefix}{cmd.name}`"
                    for cmd in self.bot.commands
                    if cmd.cog_name == cog_name and not cmd.hidden
                ]
                if command_list:
                    embed.add_field(
                        name=f"• {cog_name} Commands!",
                        value=" ".join(command_list),
                        inline=False,
                    )

            await ctx.send(embed=embed)
            self.logger.info(f"Command list sent to {ctx.author} in {ctx.guild}")

        except Exception as e:
            await ctx.send("⚠️ Failed to show commands.")
            self.logger.exception(f"Failed to send command list to {ctx.author}: {e}")

    @commands.command(
        name="redisget",
        help="Fetch a specific Redis stat by key. Example: !redisget errors",
    )
    async def get_redis_stat(self, ctx, key: str):
        """Fetch and return the value of a specific Redis key."""
        try:
            if not self.redis or not self.redis.redis:
                await ctx.send("❌ Redis is not connected.")
                return

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


async def setup(bot):
    await bot.add_cog(Information(bot))
