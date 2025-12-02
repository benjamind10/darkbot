"""
ChatGPT Cog
===========

Handles ChatGPT integration for asking questions using OpenAI's API.
"""

import os
import discord
from discord.ext import commands

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ChatGPT(commands.Cog):
    """ChatGPT integration cog for AI-powered responses."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        
        if OPENAI_AVAILABLE:
            # Fetch the OpenAI API key from the environment
            openai.api_key = os.getenv("CHATGPT_SECRET")
            if not openai.api_key:
                self.logger.warning("CHATGPT_SECRET not set - ChatGPT commands will not work")
        else:
            self.logger.warning("openai package not installed - ChatGPT commands disabled")

    @commands.command(name="askgpt", help="Ask ChatGPT a question and get a response.")
    async def askgpt(self, ctx, *, question: str):
        """
        Ask ChatGPT a question and get an AI-generated response.
        
        Usage: !askgpt <your question>
        """
        if not OPENAI_AVAILABLE:
            await ctx.send("❌ OpenAI package is not installed. Please install it with `pip install openai`")
            return
            
        if not openai.api_key:
            await ctx.send("❌ ChatGPT API key not configured. Please set CHATGPT_SECRET environment variable.")
            return

        self.logger.info(f"ChatGPT | User {ctx.author} asked: {question}")

        try:
            # Make a request to the OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": question}],
                max_tokens=150,
                temperature=0.7,
            )

            # Extract the response text
            answer = response.choices[0].message["content"]
            await ctx.send(answer)

        except Exception as e:
            self.logger.error(f"ChatGPT | Error occurred while processing request: {e}")
            await ctx.send(
                "❌ Sorry, I couldn't process your request. Please try again later."
            )


async def setup(bot):
    """Load the ChatGPT cog."""
    await bot.add_cog(ChatGPT(bot))
