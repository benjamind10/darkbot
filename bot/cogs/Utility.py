import asyncio
import datetime
import os
import random
import smtplib
from email.message import EmailMessage
import aiogoogletrans
import aiohttp
import asyncurban
import discord
import ipinfo
import requests
import strgen
from bitlyshortener import Shortener
from discord.ext import commands
from dotenv import load_dotenv
from forex_python.bitcoin import BtcConverter
from forex_python.converter import CurrencyRates
# from mcstatus import MinecraftServer

from logging_files.utility_logging import logger
from utils.color_converting import *
from utils.default import uptime
from utils.decimal_formatting import truncate

load_dotenv()

COINCAP_TOKEN = os.getenv("API_COINCAP")
KSOFT_API = os.getenv("KSOFT_APT")
IP_INFO = os.getenv("IP_INFO")


class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.u = asyncurban.UrbanDictionary()
        self.t = aiogoogletrans.Translator
        self.bot_start_time = datetime.datetime.now()

    @commands.command(aliases=["btc"])
    async def bitcoin(self, ctx, currency="USD"):
        try:
            b = BtcConverter()
            amount = round(b.get_latest_price(currency), 2)
        except:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency error!",
                description="• Not a valid currency type!"
                            "\n• Example: `!bitcoin CAD`"
            )
            await ctx.send(embed=embed)
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ BTC to Currency",
            description=f"• One Bitcoin is: `{amount}` {currency}"
        )
        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Bitcoin: {ctx.author}")

    @commands.command(aliases=["ltc"])
    async def litecoin(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://api.coincap.io/v2/rates/litecoin") as r:
                res = await r.json()
                litecoin_price = res['data']['rateUsd']
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title="→ Current Litecoin Price",
                    description=f"• One Litecoin is: `{litecoin_price[:-14]}` USD"
                )

                await ctx.send(embed=embed)

                logger.info(f"Utility | Sent Litecoin: {ctx.author}")

    @commands.command(aliases=["convert"])
    async def currency(self, ctx, amount, currency1, currency2):
        try:
            c = CurrencyRates()
            amount = float(amount)
        except:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Money Error!",
                description="• Not a valid amount of money!"
            )
            await ctx.send(embed=embed)
        try:
            amount2 = float(c.convert(currency1, currency2, amount))
        except:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency Error!",
                description="• Not a valid currency type!"
                            "\n• Example: `!currency 10 USD CAD`"
            )
            await ctx.send(embed=embed)
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Currency Converting",
            description=f"• {amount} {currency1} is about {truncate(amount2, 2)} {currency2}!"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Currency: {ctx.author}")

    @currency.error
    async def currency_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a valid option! Example: `!currency 10 USD CAD`"
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["tobtc"])
    async def currency_to_bitcoin(self, ctx, amount, currency="USD"):
        try:
            b = BtcConverter()
            amount = int(amount)
        except:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Money Error!",
                description="• Not a valid amount of money!"
            )
            await ctx.send(embed=embed)
        try:
            btc = round(b.convert_to_btc(amount, currency), 4)
        except:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency Error!",
                description="• Not a valid currency!"
                            "\n• Example: `!tobtc 10 CAD`"
                            "\n• Pro Tip: `If you use USD currency, you do not have to specify the currency in the command.`"
            )
            await ctx.send(embed=embed)
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Currency To Bitcoin!",
            description=f"• {amount} {currency} is around {btc} Bitcoin!"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Currency_To_btc: {ctx.author}")

    @currency_to_bitcoin.error
    async def currency_to_bitcoin_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a valid option! Example: `!tobtc 10 CAD`"
                            "\n• Pro Tip: `If you use USD currency, you do not have to specify the currency in the command.`")
            await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def word(self, ctx):
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invalid Argument!",
            description="• Please put in a valid option! Example: `!word <random / search> [Word name]`"
        )
        await ctx.send(embed=embed)

    @word.command()
    async def random(self, ctx):
        word = await self.u.get_random()
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Random Word",
            description=f"Word: `{word}`"
                        f"\n Definition: `{word.definition}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Word Random: {ctx.author}")

    @word.command()
    async def search(self, ctx, *, query):
        word = await self.u.get_word(query)
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Searched word",
            description=f"Word: `{word}`"
                        f"\n Definition: `{word.definition}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Word Search: {ctx.author} | Searched: {query}")

    @commands.command(aliases=["ip"])
    async def ip_lookup(self, ctx, ip):
        try:
            token = IP_INFO
            handler = ipinfo.getHandler(token)
            ip_address = ip
            details = handler.getDetails(ip_address)
            info = details.all

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ IP Address Lookup"
            )
            embed.set_footer(text="— Note: Locations and Latitude & Longitude may not be 100% accurate.")
            embed.add_field(name="• IP Address:", value=f"`{info['ip']}`")

            if not len(info["latitude"]) and not len(info["longitude"]):
                embed.add_field(name="• Latitude & Longitude", value="`Latitude & Longitude not found!`")
            else:
                embed.add_field(name="• Latitude & Longitude", value=f"`{info['latitude']}, {info['longitude']}`")
            if not len(info["city"]):
                embed.add_field(name="• City:", value="`City not found!`")
            else:
                embed.add_field(name="• City:", value=f"`{info['city']}`")
            if not len(info["region"]):
                embed.add_field(name="• Region / State:", value="`Region / State not found!`")
            else:
                embed.add_field(name="• Region / State:", value=f"`{info['region']}`")
            if not len(info["country_name"]):
                embed.add_field(name="• Country", value="`Country not found!`")
            else:
                embed.add_field(name="• Country:", value=f"`{info['country_name']}`")
            try:
                embed.add_field(name="• Postal code:", value=f"`{info['postal']}`")
            except KeyError:
                embed.add_field(name="• Postal code:", value="`Postal code not found!`")
            if not len(info["org"]):
                embed.add_field(name="• ISP-Name:", value="`ISP-Name not found!`")
            else:
                embed.add_field(name="• ISP-Name:", value=f"`{info['org']}`")

            await ctx.send(embed=embed)

            logger.info(f"Utility | Sent IP: {ctx.author} | IP Address: {ip}")

        except Exception:
            embed_error = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid IP Address!",
                description="• The IP address you entered is not valid."
            )

            await ctx.send(embed=embed_error)

    @ip_lookup.error
    async def ip_lookup_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a IP Address! Example: `!ip 172.217.2.238`"
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def poll(self, ctx, channel: discord.TextChannel, *, question):
        sender = ctx.author
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Quick Poll 📊"
        )
        embed.add_field(name="• Question", inline=False, value=question)
        embed.set_footer(text=f"— Poll from {sender}", icon_url=ctx.author.avatar_url)
        await ctx.message.delete()

        message = await channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")

        logger.info(f"Utility | Sent Poll: {ctx.author}")

    @poll.error
    async def poll_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Channel!",
                description="• Please put in a channel! Example: `!poll #channel <question>`"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a valid option! Example: `!poll #channel <question>`"
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["randomcolor"])
    async def random_color(self, ctx):
        r = lambda: random.randint(0, 255)
        hex_color = f'{f"{r():x}":0>2}{f"{r():x}":0>2}{f"{r():x}":0>2}'
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        embed = discord.Embed(
            color=(discord.Color(int(f"0x{hex_color}", 16))),
            title="→ Random Color"
        )
        embed.set_thumbnail(url="https://www.script-tutorials.com/demos/315/images/colorwheel1.png")
        embed.set_footer(text="— Note: CMYK, HSV, HSL Colors are converted from RGB.")
        embed.add_field(name='• HEX value:', inline=True, value=f"`#{hex_color}`")
        embed.add_field(name='• RGB value:', inline=True, value=f"`{rgb}`")
        embed.add_field(name='• CMYK value:', inline=True, value=f"`{rgb_to_cmyk(rgb[0], rgb[1], rgb[2])}`")
        embed.add_field(name='• HSV value:', inline=True, value=f"`{rgb_to_hsv(rgb[0], rgb[1], rgb[2])}`")
        embed.add_field(name='• HSL value:', inline=True, value=f"`{rgb_to_hsl(rgb[0], rgb[1], rgb[2])}`")
        embed.add_field(name="• COLOR accuracy:", inline=True, value=f"`{random.randint(96, 99)}%`")

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Random Color: {ctx.author}")

    @commands.command()
    async def remind(self, ctx, time, time_measurement, *, reminder):
        if str(time_measurement) == "s":
            if float(time) <= 1:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Second!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Seconds!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)

            embed2 = discord.Embed(
                color=self.bot.embed_color,
                title="→ Time Is Up!",
                description=f"• Reminder set: `{reminder}`"
                            f"\n• Time set for: `{time} Second(s)`"
            )

            await asyncio.sleep(float(time))
            await ctx.send(embed=embed2)

            ping = await ctx.send(ctx.author.mention)
            await ping.delete()

            logger.info(
                f"Utility | Sent Remind: {ctx.author} | Time: {time} | Time Measurement: {time_measurement} | Reminder: {reminder}")

        elif str(time_measurement) == "m":
            if float(time) <= 1:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Minute!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Minutes!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)

            embed3 = discord.Embed(
                color=self.bot.embed_color,
                title="→ Time Is Up!",
                description=f"• Reminder set: `{reminder}`"
                            f"\n• Time set for: `{time} Minute(s)`"
            )

            seconds_to_minutes = float(time) * 60

            await asyncio.sleep(seconds_to_minutes)
            await ctx.send(embed=embed3)

            ping = await ctx.send(ctx.author.mention)
            await ping.delete()

            logger.info(
                f"Utility | Sent Remind: {ctx.author} | Time: {time} | Time Measurement: {time_measurement} | Reminder: {reminder}")

        elif str(time_measurement) == "h":
            if float(time) <= 1:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Hour!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    color=self.bot.embed_color,
                    title=f"→ Reminder Set For {time} Hours!",
                    description=f"• Reminder: `{reminder}`"
                )

                await ctx.send(embed=embed)

            embed4 = discord.Embed(
                color=self.bot.embed_color,
                title="→ Time Is Up!",
                description=f"• Reminder set: `{reminder}`"
                            f"\n• Time set for: `{time} Hour(s)`"
            )

            seconds_to_hours = (10 * 360) * float(time)

            await asyncio.sleep(seconds_to_hours)
            await ctx.send(embed=embed4)

            ping = await ctx.send(ctx.author.mention)
            await ping.delete()

            logger.info(
                f"Utility | Sent Remind: {ctx.author} | Time: {time} | Time Measurement: {time_measurement} | Reminder: {reminder}")
        else:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!remind <time> <time measurement> "
                            "<reminder>` "
                            "\n• Units of time: `s = seconds`, `m = minutes`, `h = hours`"
                            "\n• Real world example: `!remind 20 m this reminder will go off in 20 minutes.`"
            )

            await ctx.send(embed=embed)

    @remind.error
    async def remind_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!remind <time> <time measurement> "
                            "<reminder>` "
                            "\n• Units of time: `s = seconds`, `m = minutes`, `h = hours`"
                            "\n• Real world example: `!remind 20 m this reminder will go off in 20 minutes.`"
            )
            await ctx.send(embed=embed)

    @commands.group(aliases=["temp"], invoke_without_command=True)
    async def temperature(self, ctx):
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invalid Argument!",
            description="• Please put in a valid option! Example: `!temperature <fahrenheit / celsius> <number>`"
        )

        await ctx.send(embed=embed)

    @temperature.command(aliases=["fahrenheit"])
    async def fahrenheit_to_celsius(self, ctx, fahrenheit):
        celsius = (int(fahrenheit) - 32) * 5 / 9
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Fahrenheit To Celsius",
            description=f"• Celsius Temperature: `{int(celsius)}`"
        )
        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Temperatures: {ctx.author}")

    @temperature.command(aliases=["celsius"])
    async def celsius_to_fahrenheit(self, ctx, celsius):
        fahrenheit = (int(celsius) * 9 / 5) + 32
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Celsius To Fahrenheit",
            description=f"• Fahrenheit Temperature: `{int(fahrenheit)}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Temperatures: {ctx.author}")

    @commands.command(aliases=["gt", "trans"])
    async def translate(self, ctx, lang, *, sentence):
        data = await self.t.translate(sentence, dest=lang)
        translated = data.src.upper()
        translation = data.text
        language = lang.upper()
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Translation",
            description=f"• Input Language: `{translated}`"
                        f"\n• Translated Language: `{language}`"
                        f"\n• Translated Text: `{translation}`"
        )

        await ctx.send(embed=embed)

        logger.info(f"Utility | Sent Translate: {ctx.author} | Language: {lang} | Sentence: {sentence}")

    @translate.error
    async def translate_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!translate <language> <message>`"
                            "\n• Real world example: `translate english Hola`"
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def weather(self, ctx, *, location: str):
        try:
            OPENWEATHER_API_KEY = KSOFT_API
            # Assume location is a city name for simplicity; you might want to handle other types of location input
            async with aiohttp.ClientSession() as cs:
                async with cs.get(
                        "https://api.openweathermap.org/data/2.5/weather",
                        params={"q": location, "appid": OPENWEATHER_API_KEY, "units": "imperial"}
                ) as r:
                    res = await r.json()
                    if r.status != 200:
                        raise Exception(f"Failed to retrieve weather data: {res.get('message', 'Unknown error')}")

                    # Extract data from the response
                    temp_f = res["main"]["temp"]
                    temp_c = (temp_f - 32) * 5 / 9
                    humidity = res["main"]["humidity"]
                    wind_speed = res["wind"]["speed"]
                    cloud_coverage = res["clouds"]["all"]
                    # ... extract other data as needed

                    # Create and send the embed
                    embed = discord.Embed(
                        color=self.bot.embed_color,
                        title="→ Weather Command"
                    )
                    embed.set_thumbnail(url=f"http://openweathermap.org/img/w/{res['weather'][0]['icon']}.png")
                    embed.add_field(name="• Temperature:", value=f"{temp_f}℉ — ({temp_c:.2f}℃)")
                    embed.add_field(name="• Humidity:", value=f"{humidity}%")
                    embed.add_field(name="• Wind:", value=f"{wind_speed} MPH")
                    embed.add_field(name="• Cloud coverage:", value=f"{cloud_coverage}%")
                    embed.add_field(name="• Location:", value=res['name'])
                    # sunrise_time = datetime.utcfromtimestamp(res['sys']['sunrise']).strftime('%Y-%m-%d %H:%M:%S')
                    # sunset_time = datetime.utcfromtimestamp(res['sys']['sunset']).strftime('%Y-%m-%d %H:%M:%S')
                    # embed.add_field(name="• Sunrise time:", value=sunrise_time or 'Sunrise information not available')
                    # embed.add_field(name="• Sunset time:", value=sunset_time or 'Sunset information not available')

                    await ctx.send(embed=embed)

                    logger.info(f"Utility | Sent Weather: {ctx.author}")
        except Exception as e:
            print(f"There was an error: {str(e)}")
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid City / Zip code",
                description=f"• The city or zip code you put is not valid. Error: {e}"
            )
            await ctx.send(embed=embed)

    @weather.error
    async def weather_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!weather <city>`"
                            "\n• You can also use a zip code! Example: `!weather <zip-code>`"
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))