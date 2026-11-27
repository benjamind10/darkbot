"""
ChatGPT Cog
===========

Handles ChatGPT integration for asking questions using OpenAI's API.
"""

from discord.ext import commands
from utils.discord_context import defer_if_interaction, send_for_context

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DISCORD_MESSAGE_LIMIT = 2000


class ChatGPT(commands.Cog):
    """ChatGPT integration cog for AI-powered responses."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

        services = bot.config.services
        # OPENAI_API_KEY is preferred; config already falls back to CHATGPT_SECRET.
        self.api_key = getattr(services, "openai_api_key", None) or getattr(
            services, "chatgpt_secret", None
        )
        self.model = getattr(services, "openai_model", None) or DEFAULT_OPENAI_MODEL
        self.client = None

        if not OPENAI_AVAILABLE:
            self.logger.warning("openai package not installed - ChatGPT commands disabled")
        elif not self.api_key:
            self.logger.warning("OPENAI_API_KEY not set - ChatGPT commands will not work")
        else:
            self.client = openai.AsyncOpenAI(api_key=self.api_key, timeout=30.0)

    async def cog_unload(self):
        if self.client is not None:
            await self.client.close()

    @commands.hybrid_command(name="askgpt", help="Ask ChatGPT a question and get a response.")
    async def askgpt(self, ctx, *, question: str):
        """
        Ask ChatGPT a question and get an AI-generated response.

        Usage: !askgpt <your question>
        """
        if ctx.interaction and not ctx.interaction.response.is_done():
            await defer_if_interaction(ctx)

        if not OPENAI_AVAILABLE:
            await send_for_context(
                ctx, "❌ OpenAI package is not installed. Please install it with `pip install openai`"
            )
            return

        if self.client is None:
            await send_for_context(
                ctx, "❌ ChatGPT API key not configured. Please set the OPENAI_API_KEY environment variable."
            )
            return

        self.logger.info(f"ChatGPT | User {ctx.author} asked: {question}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": question}],
                max_tokens=500,
                temperature=0.7,
            )
            answer = (response.choices[0].message.content or "").strip()
            if not answer:
                answer = "❌ ChatGPT returned an empty response."
            if len(answer) > DISCORD_MESSAGE_LIMIT:
                answer = answer[: DISCORD_MESSAGE_LIMIT - 1] + "…"
            await send_for_context(ctx, answer)

        except openai.AuthenticationError:
            self.logger.error("ChatGPT | OpenAI rejected the API key")
            await send_for_context(ctx, "❌ ChatGPT is misconfigured (invalid API key).")
        except openai.RateLimitError:
            self.logger.warning("ChatGPT | Rate limited or out of quota")
            await send_for_context(ctx, "❌ ChatGPT is rate limited right now. Please try again later.")
        except openai.OpenAIError:
            self.logger.exception("ChatGPT | Error occurred while processing request")
            await send_for_context(ctx, "❌ Sorry, I couldn't process your request. Please try again later.")


async def setup(bot):
    """Load the ChatGPT cog."""
    await bot.add_cog(ChatGPT(bot))
