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
                    "—"
                ),
            )
            embed.set_thumbnail(url="https://i.imgur.com/BUlgakY.png")

            # Example command section
            info_commands = "!commands"

            embed.add_field(
                name="• Information Commands!",
                value=info_commands,
                inline=False,
            )

            await ctx.send(embed=embed)
            self.logger.info(f"Command list sent to {ctx.author} in {ctx.guild}")
        except Exception as e:
            await ctx.send("⚠️ Failed to show commands.")
            self.logger.exception(f"Failed to send command list to {ctx.author}: {e}")


async def setup(bot):
    await bot.add_cog(Information(bot))
