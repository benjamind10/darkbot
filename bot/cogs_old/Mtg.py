import requests
import discord
from discord.ext import commands
from logging_files.mtg_logging import logger


class Mtg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_base_url = "https://api.magicthegathering.io/v1"

    def fetch_card(self, card_name):
        """Fetch card details by name."""
        params = {
            "name": card_name
        }  # You can use additional parameters based on your requirement
        response = requests.get(f"{self.api_base_url}/cards", params=params)
        if response.status_code == 200:
            return response.json().get("cards", [])[
                0
            ]  # Assuming the first card is the one you want
        else:
            logger.error(f"Failed to fetch card: {response.text}")
            return None

    @commands.command(
        name="card", help="Get details about a Magic: The Gathering card."
    )
    async def card(self, ctx, *, card_name):
        """A command that fetches and displays MTG card details."""
        logger.info(f"Fetching card: {card_name}")
        card_data = self.fetch_card(card_name)
        if card_data:
            embed = discord.Embed(
                title=card_data["name"],
                description=card_data.get("text", "No description available."),
            )
            embed.add_field(
                name="Mana Cost", value=card_data.get("manaCost", "N/A"), inline=False
            )
            embed.add_field(
                name="Type", value=card_data.get("type", "N/A"), inline=False
            )
            embed.set_image(url=card_data.get("imageUrl", ""))
            await ctx.send(embed=embed)
        else:
            await ctx.send("Couldn't find the card.")

    @commands.command(
        name="searchcards", help="Search for MTG cards by type and color."
    )
    async def search_cards(self, ctx, card_type: str, card_color: str):
        """Search for cards by a specific type and color."""
        logger.info(f"Searching for cards: Type={card_type}, Color={card_color}")
        params = {
            "types": card_type,
            "colors": card_color,
            "pageSize": 5,
        }  # Fetching only the top 5 results
        response = requests.get(f"{self.api_base_url}/cards", params=params)
        if response.status_code == 200:
            cards = response.json().get("cards", [])
            if cards:
                for card in cards:
                    embed = discord.Embed(
                        title=card["name"],
                        description=card.get("text", "No description available."),
                    )
                    embed.add_field(
                        name="Mana Cost",
                        value=card.get("manaCost", "N/A"),
                        inline=False,
                    )
                    embed.add_field(
                        name="Type", value=card.get("type", "N/A"), inline=False
                    )
                    embed.set_thumbnail(url=card.get("imageUrl", ""))
                    await ctx.send(embed=embed)
            else:
                await ctx.send("No cards found matching the criteria.")
        else:
            logger.error(f"Failed to search for cards: {response.text}")
            await ctx.send("Failed to fetch card data.")


async def setup(bot):
    await bot.add_cog(Mtg(bot))
