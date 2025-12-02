"""
Utility Cog
===========

Handles various utility commands like cryptocurrency prices, currency conversion,
weather, translations, IP lookup, polls, reminders, and more.
"""

import asyncio
import datetime
import os
import random
import discord
from discord.ext import commands

# Optional imports with graceful fallback
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import asyncurban
    ASYNCURBAN_AVAILABLE = True
except ImportError:
    ASYNCURBAN_AVAILABLE = False

try:
    import aiogoogletrans
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

try:
    from forex_python.bitcoin import BtcConverter
    from forex_python.converter import CurrencyRates
    FOREX_AVAILABLE = True
except ImportError:
    FOREX_AVAILABLE = False

try:
    import ipinfo
    IPINFO_AVAILABLE = True
except ImportError:
    IPINFO_AVAILABLE = False

from utils.color_converting import rgb_to_cmyk, rgb_to_hsv, rgb_to_hsl
from utils.decimal_formatting import truncate


class Utility(commands.Cog):
    """Utility commands for various helpful functions."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        self.bot_start_time = datetime.datetime.now()
        
        # Initialize optional services
        if ASYNCURBAN_AVAILABLE:
            self.u = asyncurban.UrbanDictionary()
        if TRANSLATOR_AVAILABLE:
            self.t = aiogoogletrans.Translator
        
        # Get API keys from environment
        self.ip_info_token = os.getenv("IP_INFO")
        self.openweather_api_key = os.getenv("KSOFT_API")

    # ========== Cryptocurrency Commands ==========

    @commands.command(aliases=["btc"])
    async def bitcoin(self, ctx, currency="USD"):
        """
        Get current Bitcoin price in specified currency.
        
        Usage: !bitcoin [currency]
        Example: !bitcoin CAD
        """
        if not FOREX_AVAILABLE:
            await ctx.send("❌ forex-python library not installed.")
            return

        try:
            b = BtcConverter()
            amount = round(b.get_latest_price(currency), 2)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ BTC to Currency",
                description=f"• One Bitcoin is: `{amount}` {currency}"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Bitcoin: {ctx.author}")
        except Exception as e:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency error!",
                description=f"• Not a valid currency type!\n• Example: `!bitcoin CAD`"
            )
            await ctx.send(embed=embed)
            self.logger.error(f"Utility | Bitcoin error: {e}")

    @commands.command(aliases=["ltc"])
    async def litecoin(self, ctx):
        """
        Get current Litecoin price in USD.
        
        Usage: !litecoin
        """
        if not AIOHTTP_AVAILABLE:
            await ctx.send("❌ aiohttp library not installed.")
            return

        try:
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
                    self.logger.info(f"Utility | Sent Litecoin: {ctx.author}")
        except Exception as e:
            await ctx.send("❌ Failed to fetch Litecoin price.")
            self.logger.error(f"Utility | Litecoin error: {e}")

    # ========== Currency Conversion ==========

    @commands.command(aliases=["convert"])
    async def currency(self, ctx, amount, currency1, currency2):
        """
        Convert between different currencies.
        
        Usage: !currency <amount> <from_currency> <to_currency>
        Example: !currency 10 USD CAD
        """
        if not FOREX_AVAILABLE:
            await ctx.send("❌ forex-python library not installed.")
            return

        try:
            c = CurrencyRates()
            amount_float = float(amount)
            converted = float(c.convert(currency1, currency2, amount_float))
            
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency Converting",
                description=f"• {amount_float} {currency1} is about {truncate(converted, 2)} {currency2}!"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Currency: {ctx.author}")
        except ValueError:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Money Error!",
                description="• Not a valid amount of money!"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency Error!",
                description=f"• Not a valid currency type!\n• Example: `!currency 10 USD CAD`"
            )
            await ctx.send(embed=embed)
            self.logger.error(f"Utility | Currency conversion error: {e}")

    @currency.error
    async def currency_error(self, ctx, error):
        """Handle errors for currency command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a valid option! Example: `!currency 10 USD CAD`"
            )
            await ctx.send(embed=embed)

    @commands.command(aliases=["tobtc"])
    async def currency_to_bitcoin(self, ctx, amount, currency="USD"):
        """
        Convert currency to Bitcoin.
        
        Usage: !tobtc <amount> [currency]
        Example: !tobtc 100 USD
        """
        if not FOREX_AVAILABLE:
            await ctx.send("❌ forex-python library not installed.")
            return

        try:
            b = BtcConverter()
            amount_int = int(amount)
            btc = round(b.convert_to_btc(amount_int, currency), 4)
            
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency To Bitcoin!",
                description=f"• {amount_int} {currency} is around {btc} Bitcoin!"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Currency_To_btc: {ctx.author}")
        except ValueError:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Money Error!",
                description="• Not a valid amount of money!"
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Currency Error!",
                description=f"• Not a valid currency!\n• Example: `!tobtc 10 CAD`"
            )
            await ctx.send(embed=embed)
            self.logger.error(f"Utility | Currency to BTC error: {e}")

    @currency_to_bitcoin.error
    async def currency_to_bitcoin_error(self, ctx, error):
        """Handle errors for currency_to_bitcoin command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a valid option! Example: `!tobtc 10 CAD`\n• Pro Tip: If you use USD currency, you do not have to specify the currency."
            )
            await ctx.send(embed=embed)

    # ========== Urban Dictionary ==========

    @commands.group(invoke_without_command=True)
    async def word(self, ctx):
        """Urban Dictionary word lookup."""
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invalid Argument!",
            description="• Please put in a valid option! Example: `!word <random / search> [Word name]`"
        )
        await ctx.send(embed=embed)

    @word.command()
    async def random(self, ctx):
        """Get a random Urban Dictionary word."""
        if not ASYNCURBAN_AVAILABLE:
            await ctx.send("❌ asyncurban library not installed.")
            return

        try:
            word = await self.u.get_random()
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Random Word",
                description=f"Word: `{word}`\nDefinition: `{word.definition}`"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Word Random: {ctx.author}")
        except Exception as e:
            await ctx.send("❌ Failed to fetch random word.")
            self.logger.error(f"Utility | Random word error: {e}")

    @word.command()
    async def search(self, ctx, *, query):
        """Search for a word in Urban Dictionary."""
        if not ASYNCURBAN_AVAILABLE:
            await ctx.send("❌ asyncurban library not installed.")
            return

        try:
            word = await self.u.get_word(query)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Searched word",
                description=f"Word: `{word}`\nDefinition: `{word.definition}`"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Word Search: {ctx.author} | Searched: {query}")
        except Exception as e:
            await ctx.send(f"❌ Couldn't find word: {query}")
            self.logger.error(f"Utility | Word search error: {e}")

    # ========== IP Lookup ==========

    @commands.command(aliases=["ip"])
    async def ip_lookup(self, ctx, ip):
        """
        Look up information about an IP address.
        
        Usage: !ip <ip_address>
        Example: !ip 8.8.8.8
        """
        if not IPINFO_AVAILABLE:
            await ctx.send("❌ ipinfo library not installed.")
            return

        if not self.ip_info_token:
            await ctx.send("❌ IP_INFO token not configured.")
            return

        try:
            handler = ipinfo.getHandler(self.ip_info_token)
            details = handler.getDetails(ip)
            info = details.all

            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ IP Address Lookup"
            )
            embed.set_footer(text="— Note: Locations and Latitude & Longitude may not be 100% accurate.")
            embed.add_field(name="• IP Address:", value=f"`{info.get('ip', 'N/A')}`")
            
            lat = info.get('latitude', '')
            lon = info.get('longitude', '')
            if lat and lon:
                embed.add_field(name="• Latitude & Longitude", value=f"`{lat}, {lon}`")
            else:
                embed.add_field(name="• Latitude & Longitude", value="`Not found`")
            
            embed.add_field(name="• City:", value=f"`{info.get('city', 'Not found')}`")
            embed.add_field(name="• Region / State:", value=f"`{info.get('region', 'Not found')}`")
            embed.add_field(name="• Country:", value=f"`{info.get('country_name', 'Not found')}`")
            embed.add_field(name="• Postal code:", value=f"`{info.get('postal', 'Not found')}`")
            embed.add_field(name="• ISP-Name:", value=f"`{info.get('org', 'Not found')}`")

            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent IP: {ctx.author} | IP Address: {ip}")

        except Exception as e:
            embed_error = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid IP Address!",
                description="• The IP address you entered is not valid."
            )
            await ctx.send(embed_error)
            self.logger.error(f"Utility | IP lookup error: {e}")

    @ip_lookup.error
    async def ip_lookup_error(self, ctx, error):
        """Handle errors for ip_lookup command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put in a IP Address! Example: `!ip 172.217.2.238`"
            )
            await ctx.send(embed=embed)

    # ========== Poll Command ==========

    @commands.command()
    async def poll(self, ctx, channel: discord.TextChannel, *, question):
        """
        Create a poll in a specific channel.
        
        Usage: !poll <#channel> <question>
        """
        sender = ctx.author
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Quick Poll 📊"
        )
        embed.add_field(name="• Question", inline=False, value=question)
        embed.set_footer(text=f"— Poll from {sender}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.message.delete()
        message = await channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        
        self.logger.info(f"Utility | Sent Poll: {ctx.author}")

    @poll.error
    async def poll_error(self, ctx, error):
        """Handle errors for poll command."""
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

    # ========== Color Commands ==========

    @commands.command(aliases=["randomcolor"])
    async def random_color(self, ctx):
        """Generate a random color with various color space conversions."""
        r = lambda: random.randint(0, 255)
        hex_color = f'{f"{r():x}":0>2}{f"{r():x}":0>2}{f"{r():x}":0>2}'
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        embed = discord.Embed(
            color=discord.Color(int(f"0x{hex_color}", 16)),
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
        self.logger.info(f"Utility | Sent Random Color: {ctx.author}")

    # ========== Reminder Command ==========

    @commands.command()
    async def remind(self, ctx, time, time_measurement, *, reminder):
        """
        Set a reminder.
        
        Usage: !remind <time> <s/m/h> <reminder>
        Example: !remind 20 m Check the oven
        """
        time_float = float(time)
        time_unit = time_measurement.lower()
        
        if time_unit == "s":
            sleep_seconds = time_float
            unit_name = "Second" if time_float <= 1 else "Seconds"
        elif time_unit == "m":
            sleep_seconds = time_float * 60
            unit_name = "Minute" if time_float <= 1 else "Minutes"
        elif time_unit == "h":
            sleep_seconds = time_float * 3600
            unit_name = "Hour" if time_float <= 1 else "Hours"
        else:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!remind <time> <time measurement> <reminder>`\n• Units of time: `s = seconds`, `m = minutes`, `h = hours`\n• Real world example: `!remind 20 m this reminder will go off in 20 minutes.`"
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            color=self.bot.embed_color,
            title=f"→ Reminder Set For {time} {unit_name}!",
            description=f"• Reminder: `{reminder}`"
        )
        await ctx.send(embed=embed)

        await asyncio.sleep(sleep_seconds)

        embed2 = discord.Embed(
            color=self.bot.embed_color,
            title="→ Time Is Up!",
            description=f"• Reminder set: `{reminder}`\n• Time set for: `{time} {unit_name}`"
        )
        await ctx.send(embed2)
        
        ping = await ctx.send(ctx.author.mention)
        await ping.delete()

        self.logger.info(f"Utility | Sent Remind: {ctx.author} | Time: {time} | Unit: {time_unit} | Reminder: {reminder}")

    @remind.error
    async def remind_error(self, ctx, error):
        """Handle errors for remind command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!remind <time> <time measurement> <reminder>`\n• Units of time: `s = seconds`, `m = minutes`, `h = hours`\n• Real world example: `!remind 20 m this reminder will go off in 20 minutes.`"
            )
            await ctx.send(embed=embed)

    # ========== Temperature Conversion ==========

    @commands.group(aliases=["temp"], invoke_without_command=True)
    async def temperature(self, ctx):
        """Temperature conversion commands."""
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Invalid Argument!",
            description="• Please put in a valid option! Example: `!temperature <fahrenheit / celsius> <number>`"
        )
        await ctx.send(embed=embed)

    @temperature.command(aliases=["fahrenheit"])
    async def fahrenheit_to_celsius(self, ctx, fahrenheit):
        """Convert Fahrenheit to Celsius."""
        celsius = (int(fahrenheit) - 32) * 5 / 9
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Fahrenheit To Celsius",
            description=f"• Celsius Temperature: `{int(celsius)}`"
        )
        await ctx.send(embed=embed)
        self.logger.info(f"Utility | Sent Temperatures: {ctx.author}")

    @temperature.command(aliases=["celsius"])
    async def celsius_to_fahrenheit(self, ctx, celsius):
        """Convert Celsius to Fahrenheit."""
        fahrenheit = (int(celsius) * 9 / 5) + 32
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Celsius To Fahrenheit",
            description=f"• Fahrenheit Temperature: `{int(fahrenheit)}`"
        )
        await ctx.send(embed=embed)
        self.logger.info(f"Utility | Sent Temperatures: {ctx.author}")

    # ========== Translation ==========

    @commands.command(aliases=["gt", "trans"])
    async def translate(self, ctx, lang, *, sentence):
        """
        Translate text to another language.
        
        Usage: !translate <language_code> <text>
        Example: !translate es Hello world
        """
        if not TRANSLATOR_AVAILABLE:
            await ctx.send("❌ aiogoogletrans library not installed.")
            return

        try:
            translator = self.t()
            data = await translator.translate(sentence, dest=lang)
            translated_from = data.src.upper()
            translation = data.text
            language = lang.upper()
            
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Translation",
                description=f"• Input Language: `{translated_from}`\n• Translated Language: `{language}`\n• Translated Text: `{translation}`"
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Utility | Sent Translate: {ctx.author} | Language: {lang} | Sentence: {sentence}")
        except Exception as e:
            await ctx.send("❌ Translation failed.")
            self.logger.error(f"Utility | Translation error: {e}")

    @translate.error
    async def translate_error(self, ctx, error):
        """Handle errors for translate command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!translate <language> <message>`\n• Real world example: `!translate en Hola`"
            )
            await ctx.send(embed=embed)

    # ========== Weather ==========

    @commands.command()
    async def weather(self, ctx, *, location: str):
        """
        Get weather information for a location.
        
        Usage: !weather <city or zip code>
        Example: !weather New York
        """
        if not AIOHTTP_AVAILABLE:
            await ctx.send("❌ aiohttp library not installed.")
            return

        if not self.openweather_api_key:
            await ctx.send("❌ OpenWeather API key not configured (KSOFT_API).")
            return

        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": location, "appid": self.openweather_api_key, "units": "imperial"}
                ) as r:
                    res = await r.json()
                    if r.status != 200:
                        raise Exception(f"Failed to retrieve weather data: {res.get('message', 'Unknown error')}")
                    
                    # Extract data
                    temp_f = res["main"]["temp"]
                    temp_c = (temp_f - 32) * 5 / 9
                    humidity = res["main"]["humidity"]
                    wind_speed = res["wind"]["speed"]
                    cloud_coverage = res["clouds"]["all"]

                    # Create embed
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
                    
                    await ctx.send(embed=embed)
                    self.logger.info(f"Utility | Sent Weather: {ctx.author}")
        except Exception as e:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid City / Zip code",
                description=f"• The city or zip code you put is not valid. Error: {e}"
            )
            await ctx.send(embed=embed)
            self.logger.error(f"Utility | Weather error: {e}")

    @weather.error
    async def weather_error(self, ctx, error):
        """Handle errors for weather command."""
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Invalid Argument!",
                description="• Please put a valid option! Example: `!weather <city>`\n• You can also use a zip code! Example: `!weather <zip-code>`"
            )
            await ctx.send(embed=embed)


async def setup(bot):
    """Load the Utility cog."""
    await bot.add_cog(Utility(bot))
