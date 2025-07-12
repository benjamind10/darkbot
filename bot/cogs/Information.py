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
            keys = ["commands_used", "messages_seen", "errors"]
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
        name="botstats",
        help="Displays general statistics about the bot.",
        aliases=["status", "stats"],
    )
    async def show_stats(self, ctx):
        """Return overall bot statistics."""
        basic = self.get_basic_stats()
        redis = await self.get_redis_stats()

        color = getattr(self.bot, "embed_color", discord.Color.blurple())
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=color,
            timestamp=datetime.utcnow(),
        )

        for name, value in {**basic, **redis}.items():
            embed.add_field(name=name, value=value, inline=True)

        await ctx.send(embed=embed)
        if self.logger:
            self.logger.info(f"Bot statistics sent to {ctx.author} in {ctx.guild}")


async def setup(bot):
    await bot.add_cog(Information(bot))
