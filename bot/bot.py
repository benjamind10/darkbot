import discord
import os
import sys

from discord import client
from discord.ext import commands
from dotenv import load_dotenv
from colorama import Style, Fore
from datetime import datetime
from db import get_connection
from logging_files.bot_logging import logger


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

cogs = [
    "Information",
    "Owner",
    # "Music",
    "Moderation",
    "Utility",
    "Events",
    "BoardGames",
    "Database",
    "Mtg",
    "Chatgpt",
    "Spotify",
]


class DarkBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            owner_id=int(OWNER_ID),
            reconnect=True,
            case_insensitive=False,
        )

        self.embed_color = 0xF15A24
        self.console_info_format = f"{Fore.BLUE}{datetime.now().strftime('%H:%M:%S')}{Fore.RESET} {Style.BRIGHT}[{Fore.BLUE}INFO{Fore.RESET}]{Style.RESET_ALL}"

        # DB STUFF
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    async def on_connect(self):
        os.system("clear")
        # DB STUFF
        self.cursor.execute("SELECT version();")
        record = self.cursor.fetchone()
        logger.info(f"Connected to - {record}")
        logger.info("DarkBot is starting up...")

    # async def on_message(self, message):
    #     self.cursor.execute("SELECT version();")
    #     record = self.cursor.fetchone()
    #     await message.channel.send(record)

    async def on_ready(self):
        await self.wait_until_ready()
        activity = discord.Game(name="Type !help for a list of commands.")
        await self.change_presence(activity=activity)
        os.system("clear")

        try:
            for cog in cogs:
                logger.info(f"Cog loaded: {cog}")
                await self.load_extension(f"cogs.{cog}")
        except Exception as e:
            logger.info(f"Could not load extension {e}")

        logger.info("Loaded commands:")
        for command in self.commands:
            logger.info(command)

        logger.info(
            f"{self.console_info_format} ---------------DarkBot---------------------"
            f"\n{self.console_info_format} Bot is online and connected to {self.user}"
            f"\n{self.console_info_format} Created by Shiva187"
            f"\n{self.console_info_format} Detected Operating System: {sys.platform.title()}"
            f"\n{self.console_info_format} --------------------------------------------"
        )


DarkBot().run(TOKEN)
