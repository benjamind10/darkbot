import re
import os
import discord
import math
import lavalink
from discord.ext import commands
from lavalink.filters import LowPass

url_rx = re.compile(r'https?://(?:www\.)?.+')
LAVALINK_PASS = os.getenv("LAVALINK_PASS")
LAVALINK_SERVER = os.getenv("LAVALINK_SERVER")


class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        # ensure a client already exists
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink
        else:
            self.client.lavalink = lavalink.Client(client.user.id)
            self.client.lavalink.add_node(
                str(LAVALINK_SERVER),
                2333,
                str(LAVALINK_PASS),
                'us',
                'default-node'
            )
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        # ensure there is a player_manager when creating a new voice_client
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self.lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        self.cleanup()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user.id)
            bot.lavalink.add_node('lavalink-app', 2333, 'Musicboy12?', 'us', 'default-node')  # Host, Port, Password, Region, Name

        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        #  This is essentially the same as `@commands.guild_only()`
        #  except it saves us repeating ourselves (and also a few lines).

        if guild_check:
            await self.ensure_voice(ctx)
            #  Ensure that the bot and command author share a mutual voicechannel.

        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)
            # The above handles errors thrown in this cog and shows them to the user.
            # This shouldn't be a problem as the only errors thrown in this cog are from `ensure_voice`
            # which contain a reason string, such as "Join a voicechannel" etc. You can modify the above
            # if you want to do things differently.

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id)
        # Create returns a player if one exists, otherwise creates.
        # This line is important because it ensures that a player always exists for a guild.

        # Most people might consider this a waste of resources for guilds that aren't playing, but this is
        # the easiest and simplest way of ensuring players are created.

        # These are commands that require the bot to join a voicechannel (i.e. initiating playback).
        # Commands such as volume/skip etc don't require the bot to be in a voicechannel so don't need listing here.
        should_connect = ctx.command.name in ('play',)

        if not ctx.author.voice or not ctx.author.voice.channel:
            # Our cog_command_error handler catches this and sends it to the voicechannel.
            # Exceptions allow us to "short-circuit" command invocation via checks so the
            # execution state of the command goes no further.
            raise commands.CommandInvokeError('Join a voicechannel first.')

        v_client = ctx.voice_client
        if not v_client:
            if not should_connect:
                raise commands.CommandInvokeError('Not connected.')

            permissions = ctx.author.voice.channel.permissions_for(ctx.me)

            if not permissions.connect or not permissions.speak:  # Check user limit too?
                raise commands.CommandInvokeError('I need the `CONNECT` and `SPEAK` permissions.')

            player.store('channel', ctx.channel.id)
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient)
        else:
            if v_client.channel.id != ctx.author.voice.channel.id:
                raise commands.CommandInvokeError('You need to be in my voicechannel.')

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            # When this track_hook receives a "QueueEndEvent" from lavalink.py
            # it indicates that there are no tracks left in the player's queue.
            # To save on resources, we can tell the bot to disconnect from the voicechannel.
            guild_id = event.player.guild_id
            guild = self.bot.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query: str):
        """ Searches and plays a song from a given query. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
        query = query.strip('<>')

        # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
        # SoundCloud searching is possible by prefixing "scsearch:" instead.
        if not url_rx.match(query):
            query = f'ytsearch:{query}'

        # Get the results for the query from Lavalink.
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
        if not results or not results.tracks:
            return await ctx.send('Nothing found!')

        embed = discord.Embed(color=discord.Color.blurple())

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results.load_type == 'PLAYLIST_LOADED':
            tracks = results.tracks

            for track in tracks:
                # Add all of the tracks from the playlist to the queue.
                player.add(requester=ctx.author.id, track=track)

            embed.title = 'Playlist Enqueued!'
            embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
        else:
            track = results.tracks[0]
            embed.title = 'Track Enqueued'
            embed.description = f'[{track.title}]({track.uri})'

            player.add(requester=ctx.author.id, track=track)
             


        await ctx.send(embed=embed)

        # We don't want to call .play() if the player is playing as that will effectively skip
        # the current track.
        if not player.is_playing:
            await player.play()

    @commands.command(aliases=['lp'])
    async def lowpass(self, ctx, strength: float):
        """ Sets the strength of the low pass filter. """
        # Get the player for this guild from cache.
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        # This enforces that strength should be a minimum of 0.
        # There's no upper limit on this filter.
        strength = max(0.0, strength)

        # Even though there's no upper limit, we will enforce one anyway to prevent
        # extreme values from being entered. This will enforce a maximum of 100.
        strength = min(100, strength)

        embed = discord.Embed(color=discord.Color.blurple(), title='Low Pass Filter')

        # A strength of 0 effectively means this filter won't function, so we can disable it.
        if strength == 0.0:
            await player.remove_filter('lowpass')
            embed.description = 'Disabled **Low Pass Filter**'
            return await ctx.send(embed=embed)

        # Lets create our filter.
        low_pass = LowPass()
        low_pass.update(smoothing=strength)  # Set the filter strength to the user's desired level.

        # This applies our filter. If the filter is already enabled on the player, then this will
        # just overwrite the filter with the new values.
        await player.set_filter(low_pass)

        embed.description = f'Set **Low Pass Filter** strength to {strength}.'
        await ctx.send(embed=embed)

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        """ Disconnects the player from the voice channel and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not ctx.voice_client:
            # We can't disconnect, if we're not connected.
            return await ctx.send('Not connected.')

        if not ctx.author.voice or (player.is_connected and ctx.author.voice.channel.id != int(player.channel_id)):
            # Abuse prevention. Users not in voice channels, or not in the same voice channel as the bot
            # may not disconnect the bot.
            return await ctx.send('You\'re not in my voicechannel!')

        # Clear the queue to ensure old tracks don't start playing
        # when someone else queues something.
        player.queue.clear()
        # Stop the current track so Lavalink consumes less resources.
        await player.stop()
        # Disconnect from the voice channel.
        await ctx.voice_client.disconnect(force=True)
        await ctx.send('*⃣ | Disconnected.')

    @commands.command(aliases=['vol', 'v'])
    async def volume(self, ctx, volume: int=None):
        """ Changes the player's volume (0-100). """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not volume:
            return await ctx.send(f'🔊 | The current volume is: **{player.volume}%**')

        await player.set_volume(volume)  # Set the volume
        await ctx.send(f'🔊 | Volume set to: **{volume}%**')

    @commands.command(aliases=['s'])
    async def skip(self, ctx):
        """ Skips the current track. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        await player.skip()
        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Skipped",
            description="• The current song you have requested has been **skipped!**"
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def stop(self, ctx):
        """ Stops the player and clears its queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ No Songs!",
                description="• Nothing is playing at the moment!"
            )
            return await ctx.send(embed=embed)

        player.queue.clear()
        await player.stop()

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ Stopped!",
            description="• The music has been stopped!"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=['np', 'n', 'playing'])
    async def now(self, ctx):
        """ Shows some stats about the currently playing song. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.current:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ No Songs!",
                description="• Nothing is playing at the moment!"
            )
            return await ctx.send(embed=embed)

        position = lavalink.utils.format_time(player.position)
        if player.current.stream:
            duration = '🔴 Live Video'
        else:
            duration = lavalink.utils.format_time(player.current.duration)
        song = f'**• [{player.current.title}]({player.current.uri})**'

        embed = discord.Embed(
            color=self.bot.embed_color,
            title='→ Currently Playing:',
            description=f"{song}"
                        f"\n**•** Current time: **({position}/{duration})**"
        )
        embed.set_thumbnail(url=f'https://img.youtube.com/vi/{player.current.identifier}/default.jpg')
        await ctx.send(embed=embed)

    @commands.command(aliases=['q'])
    async def queue(self, ctx, page: int = 1):
        """ Shows the player's queue. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.queue:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ No Queue!",
                description="• No songs are in the queue at the moment!"
            )
            return await ctx.send(embed=embed)

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ''
        for index, track in enumerate(player.queue[start:end], start=start):
            queue_list += f'`{index + 1}.` [**{track.title}**]({track.uri})\n'

        embed = discord.Embed(
            color=self.bot.embed_color,
            title="→ List Of Songs:",
            description=f"\n{queue_list}"
        )
        # embed.set_author(name=f'→ List of songs: {len(player.queue)} \n\n{queue_list}')
        embed.set_footer(text=f'• On page: {page}/{pages}')
        await ctx.send(embed=embed)

    @commands.command(aliases=['resume'])
    async def pause(self, ctx):
        """ Pauses/Resumes the current track. """
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        if not player.is_playing:
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Not Playing!",
                description="• No song is playing is currently playing!"
            )
            return await ctx.send(embed=embed)

        if player.paused:
            await player.set_pause(False)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Resumed!",
                description="• The current song has been **resumed successfully!**"
            )
            await ctx.send(embed=embed)
        else:
            await player.set_pause(True)
            embed = discord.Embed(
                color=self.bot.embed_color,
                title="→ Paused!",
                description="• The current song has been **paused successfully!**"
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
