import os
import openai
import discord
from discord.ext import commands
from logging_files.bot_logging import (
    logger,
)  # Adjust the import based on your logging setup

# Fetch the OpenAI API key from the environment
openai.api_key = os.getenv("CHATGPT_SECRET")


class ChatGPT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="askgpt", help="Ask ChatGPT a question and get a response.")
    async def askgpt(self, ctx, *, question: str):
        """Handles the command for asking ChatGPT a question."""
        logger.info(f"User {ctx.author} asked: {question}")

        try:
            # Make a request to the OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Make sure to replace 'gpt-4' with your desired model
                messages=[{"role": "user", "content": question}],
                max_tokens=150,  # Adjust max tokens as needed
                temperature=0.7,  # You can adjust this for more creative or focused responses
            )

            # Extract the response text
            answer = response.choices[0].message["content"]
            await ctx.send(answer)

        except Exception as e:
            logger.error(f"Error occurred while processing ChatGPT request: {e}")
            await ctx.send(
                "Sorry, I couldn't process your request. Please try again later."
            )


async def setup(bot):
    await bot.add_cog(ChatGPT(bot))
