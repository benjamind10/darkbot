"""
BoardGames Cog
===============

Handles board game related commands, including integration with BoardGameGeek (BGG).
"""

import discord
from discord.ext import commands
from bot.utils.discord_context import defer_if_interaction, send_for_context
from bot.utils import boardgames as bg_utils


class BoardGames(commands.Cog):
    API2_BASE_URL = bg_utils.API2_BASE_URL
    HTML_BASE_URL = bg_utils.HTML_BASE_URL

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis_manager

    def _build_bgg_info_embed(self, game):
        return discord.Embed(
            color=self.bot.embed_color,
            title=f"**{game['name']}**",
            description=(
                f"**ID:** {game['bggid']}\n"
                f"**Published:** {game['yearpublished']}\n"
                f"**Recommended Age:** {game['minage']}+\n"
                f"**Best Player Count:** {game['best_count']}\n"
                f"**Users Rated:** {game['users_rated']}\n"
                f"**Average Rating:** {game['avg_rating']}"
            ),
        )

    def _build_bgg_search_results_embed(self, search_query, games):
        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"Top 5 search results for '{search_query}'",
        )
        for game in games:
            embed.add_field(
                name=f"{game['name']} ({game['yearpublished']})",
                value=f"ID: {game['bggid']}",
                inline=False,
            )
        return embed

    async def _send_bgg_info_result(self, ctx, game, status, game_id):
        if status == 200 and game is not None:
            await send_for_context(ctx, embed=self._build_bgg_info_embed(game))
            return

        if status in (401, 403):
            await send_for_context(
                ctx,
                f"Failed to retrieve game info for {game_id}. BGG returned {status}; try again later or configure a valid BGG session cookie.",
            )
            self.bot.logger.warning("BGG info lookup for %s returned %s", game_id, status)
            return

        if status is None:
            await send_for_context(ctx, f"Failed to retrieve game info for {game_id}.")
            self.bot.logger.error("BGG info fetch failed for %s with no status", game_id)
            return

        await send_for_context(ctx, f"Failed to retrieve game info from BGG.")
        self.bot.logger.error("BGG info fetch failed for %s, status: %s", game_id, status)

    async def _send_paginated_embeds(self, ctx, games, title, color):
        """
        Helper function to send a paginated embed message list to Discord.

        Args:
            ctx (commands.Context): The command context.
            games (List[str]): List of game description strings.
            title (str): Embed title.
            color (discord.Color): Embed color.
        """
        EMBED_MAX_DESC_LENGTH = 2048
        EMBED_MAX_FIELDS = 25

        pages = []
        current_page = []
        current_length = 0

        for game in games:
            if (
                current_length + len(game) > EMBED_MAX_DESC_LENGTH
                or len(current_page) >= EMBED_MAX_FIELDS
            ):
                pages.append(current_page)
                current_page = []
                current_length = 0
            current_page.append(game)
            current_length += len(game)

        if current_page:
            pages.append(current_page)

        for i, page in enumerate(pages):
            description = "\n".join(page)
            embed = discord.Embed(
                title=f"{title} (Page {i + 1} of {len(pages)})",
                description=description,
                color=color,
            )
            await send_for_context(ctx, embed=embed)
            self.bot.logger.info(f"Sent page {i + 1} of {len(pages)} for {title}")

    @commands.hybrid_command(
        name="bgsearch", help="Search BGG for board games. Example: !bgsearch Catan"
    )
    async def search_boardgame(self, ctx, *, search_query: str):
        """
        Searches the BoardGameGeek (BGG) API for a board game by name.

        Args:
            ctx (commands.Context): The command context.
            search_query (str): The name or keyword to search.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        self.bot.logger.info(f"BGG search query: {search_query}")
        games, source, status = await bg_utils.search_bgg_games(
            self.bot.http_session,
            search_query,
            self.bot.logger,
        )
        games = games[:5]

        if not games:
            if status == 200:
                await send_for_context(ctx, "No games found.")
                self.bot.logger.warning("No results from BGG %s search", source or "unknown")
            else:
                await send_for_context(ctx, "Failed to retrieve search results from BGG.")
            return

        top_game = bg_utils.select_bgg_search_result(search_query, games) or games[0]
        self.bot.logger.info(
            "BGG search top result selected: %s (%s)",
            top_game["bggid"],
            top_game["name"],
        )
        game, game_status = await bg_utils.fetch_bgg_thing(
            self.bot.http_session,
            top_game["bggid"],
            self.bot.logger,
            cookie_value=self.bot.config.services.bgg_cookie,
        )
        if game is not None and game_status == 200:
            await send_for_context(ctx, embed=self._build_bgg_info_embed(game))
            return

        embed = self._build_bgg_search_results_embed(search_query, games)
        embed.set_footer(text="Could not fetch details for the top result.")
        await send_for_context(ctx, embed=embed)

    @commands.hybrid_command(
        name="bginfo", help="Get BGG board game details by ID. Example: !bginfo 12345"
    )
    async def boardgame_info(self, ctx, game_id: str):
        """
        Fetches detailed info from BGG by a game's object ID.

        Args:
            ctx (commands.Context): The command context.
            game_id (str): The BGG object ID.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        self.bot.logger.info(f"Fetching BGG info for ID: {game_id}")
        game, status = await bg_utils.fetch_bgg_thing(
            self.bot.http_session,
            game_id,
            self.bot.logger,
            cookie_value=self.bot.config.services.bgg_cookie,
        )
        if game is None and status == 200:
            await send_for_context(ctx, "Game not found.")
            self.bot.logger.warning(f"No game found for ID {game_id}")
            return

        await self._send_bgg_info_result(ctx, game, status, game_id)

    @commands.hybrid_command(
        name="bggcollection", help="Fetch a BGG user's collection by username."
    )
    async def bgg_collection(self, ctx, username: str):
        """
        Fetches the board game collection of a BGG user who owns games.

        Args:
            ctx (commands.Context): The command context.
            username (str): BGG username.
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        self.bot.logger.info(f"Fetching BGG collection for: {username}")

        try:
            xml_data, status = await bg_utils.fetch_bgg_collection(
                username,
                self.bot.logger,
                self.bot.http_session,
                cookie_value=self.bot.config.services.bgg_cookie,
            )

            if status == 200 and xml_data:
                games = bg_utils.parse_bgg_collection(xml_data)
                formatted_games = []
                for item in games:
                    min_players = item.get("minplayers", "N/A")
                    max_players = item.get("maxplayers", "N/A")
                    max_playtime = item.get("maxplaytime", "N/A")
                    formatted_games.append(
                        f"{item.get('name', 'Unknown')} (ID: {item.get('bggid', 'N/A')}, Avg Rating: {item.get('avgrating', 'N/A')}, Players: {min_players}-{max_players}, Playtime: {max_playtime} mins)"
                    )

                await self._send_paginated_embeds(
                    ctx, formatted_games, f"{username}'s BGG Collection", self.bot.embed_color
                )
                self.bot.logger.info(f"Collection fetched for {username}")
            elif status == 202 or status == 429 or status is None:
                await send_for_context(
                    ctx, f"Collection for {username} is being prepared. Try again later."
                )
                self.bot.logger.warning(f"BGG collection preparing for {username}")
            elif status in (401, 403):
                await send_for_context(
                    ctx,
                    f"Collection for {username} appears private. Ask the user to make it public or provide a valid BGG session cookie.",
                )
                self.bot.logger.warning(f"BGG collection private or unauthorized for {username}")
            else:
                await send_for_context(ctx, "Failed to fetch collection.")
                self.bot.logger.error(f"Failed fetch for BGG {username}, status: {status}")
        except Exception as e:
            self.bot.logger.exception(f"Error fetching BGG collection for {username}: {e}")
            await send_for_context(ctx, "An error occurred during fetch.")

    @commands.hybrid_command(
        name="manualbggupdate", help="Trigger manual BGG update for all users."
    )
    async def manual_bgg_update(self, ctx):
        """
        Manually triggers the process to update all users' BGG collections.
        """
        await send_for_context(ctx, "Starting manual update of BGG collections. Please wait...")
        try:
            await bg_utils.process_bgg_users(
                self.bot.db_pool,
                self.bot.http_session,
                self.bot.logger,
                cookie_value=self.bot.config.services.bgg_cookie,
            )
            await send_for_context(ctx, "BGG collections updated successfully.")
            self.bot.logger.info("Manual BGG update completed.")
        except Exception as e:
            await send_for_context(ctx, f"Failed to update BGG collections: {str(e)}")
            self.bot.logger.error(f"Manual BGG update failed: {str(e)}")


async def setup(bot):
    """Register the Boardgames cog with the bot."""
    await bot.add_cog(BoardGames(bot))
