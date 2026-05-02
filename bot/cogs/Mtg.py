"""
MTG Cog
=======

Handles Magic: The Gathering card lookup commands using the MTG API.
"""

import aiohttp
import discord
from discord.ext import commands


class Mtg(commands.Cog):
    """Magic: The Gathering card lookup integration."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        self.api_base_url = "https://api.magicthegathering.io/v1"

    async def fetch_card(self, card_name):
        """Fetch card details by name from MTG API."""
        try:
            params = {"name": card_name}
            async with self.bot.http_session.get(
                f"{self.api_base_url}/cards",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    cards = body.get("cards", [])
                    if cards:
                        return cards[0]
                else:
                    self.logger.error(f"MTG | Failed to fetch card: {resp.status}")
        except Exception as e:
            self.logger.error(f"MTG | Error fetching card '{card_name}': {e}")
        return None

    @commands.hybrid_command(name="card", help="Get details about a Magic: The Gathering card.")
    async def card(self, ctx, *, card_name):
        """Fetch and display MTG card details."""
        self.logger.info(f"MTG | Fetching card: {card_name}")
        card_data = await self.fetch_card(card_name)

        if card_data:
            embed = discord.Embed(
                title=card_data["name"],
                description=card_data.get("text", "No description available."),
                color=self.bot.embed_color,
            )
            embed.add_field(name="Mana Cost", value=card_data.get("manaCost", "N/A"), inline=False)
            embed.add_field(name="Type", value=card_data.get("type", "N/A"), inline=False)

            image_url = card_data.get("imageUrl", "")
            if image_url:
                embed.set_image(url=image_url)

            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Couldn't find the card.")

    @commands.hybrid_command(name="searchcards", help="Search for MTG cards by type and color.")
    async def search_cards(self, ctx, card_type: str, card_color: str):
        """Search for cards by type and color."""
        self.logger.info(f"MTG | Searching for cards: Type={card_type}, Color={card_color}")

        try:
            params = {
                "types": card_type,
                "colors": card_color,
                "pageSize": 5,
            }
            async with self.bot.http_session.get(
                f"{self.api_base_url}/cards",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    self.logger.error(f"MTG | Failed to search for cards: {resp.status}")
                    await ctx.send("❌ Failed to fetch card data.")
                    return
                body = await resp.json()

            cards = body.get("cards", [])
            if not cards:
                await ctx.send("❌ No cards found matching the criteria.")
                return

            for card in cards:
                embed = discord.Embed(
                    title=card["name"],
                    description=card.get("text", "No description available."),
                    color=self.bot.embed_color,
                )
                embed.add_field(
                    name="Mana Cost",
                    value=card.get("manaCost", "N/A"),
                    inline=False,
                )
                embed.add_field(name="Type", value=card.get("type", "N/A"), inline=False)

                image_url = card.get("imageUrl", "")
                if image_url:
                    embed.set_thumbnail(url=image_url)

                await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"MTG | Error searching cards: {e}")
            await ctx.send("❌ An error occurred while searching for cards.")


async def setup(bot):
    """Load the MTG cog."""
    await bot.add_cog(Mtg(bot))
