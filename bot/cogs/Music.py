"""
Music Cog
=========

Modern music playback using Wavelink and Lavalink.
Supports YouTube, Spotify, SoundCloud, and more.
"""

import discord
from discord.ext import commands
from typing import cast, Optional
import asyncio
import datetime

try:
    import wavelink
    WAVELINK_AVAILABLE = True
except ImportError:
    WAVELINK_AVAILABLE = False


class Music(commands.Cog):
    """Music playback commands using Wavelink."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager
        
        if not WAVELINK_AVAILABLE:
            self.logger.error("Music | Wavelink not installed - music commands disabled")

    async def cog_load(self):
        """Called when the cog is loaded. Sets up Wavelink nodes."""
        if not WAVELINK_AVAILABLE:
            return
            
        try:
            # Connect to Lavalink node (use 'lavalink' service name in Docker, localhost for local dev)
            import os
            lavalink_host = os.getenv('LAVALINK_SERVER', 'http://lavalink:2333')
            lavalink_pass = os.getenv('LAVALINK_PASS', 'youshallnotpass')
            
            nodes = [
                wavelink.Node(
                    uri=lavalink_host,
                    password=lavalink_pass,
                    identifier="LOCAL"
                )
            ]
            
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            self.logger.info("Music | Connected to Lavalink successfully")
        except Exception as e:
            self.logger.error(f"Music | Failed to connect to Lavalink: {e}")

    async def cog_unload(self):
        """Called when the cog is unloaded. Cleanup Wavelink."""
        if WAVELINK_AVAILABLE:
            await wavelink.Pool.close()

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Event fired when a Wavelink node is ready."""
        self.logger.info(f"Music | Lavalink node '{payload.node.identifier}' is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Event fired when a track starts playing."""
        player: wavelink.Player = payload.player
        track = payload.track
        
        if not player:
            return
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track.title}**",
            color=self.bot.embed_color
        )
        
        if track.author:
            embed.add_field(name="Artist", value=track.author, inline=True)
        
        if track.length:
            duration = str(datetime.timedelta(milliseconds=track.length))
            embed.add_field(name="Duration", value=duration, inline=True)
        
        if track.uri:
            embed.add_field(name="URL", value=f"[Link]({track.uri})", inline=True)
        
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        
        channel = self.bot.get_channel(player.channel.id)
        if channel:
            await channel.send(embed=embed)

    @commands.hybrid_command(name="play", aliases=["p"], help="Play a song from YouTube, Spotify, or other sources.")
    async def play(self, ctx: commands.Context, *, query: str):
        """
        Play a song or add it to the queue.
        
        Usage: !play <song name or URL>
        Examples:
            !play Bohemian Rhapsody
            !play https://www.youtube.com/watch?v=...
            !play spotify:track:...
        """
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink is not installed. Please run `pip install wavelink`")
            return

        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return

        # Get or create player
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        
        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                self.logger.info(f"Music | Connected to voice channel: {ctx.author.voice.channel.name}")
            except Exception as e:
                await ctx.send(f"❌ Failed to connect to voice channel: {e}")
                self.logger.error(f"Music | Failed to connect: {e}")
                return

        # Lock the player to this channel
        player.autoplay = wavelink.AutoPlayMode.enabled

        # Search for tracks
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
            
            if not tracks:
                await ctx.send(f"❌ No tracks found for: `{query}`")
                return

            # If it's a playlist, add all tracks
            if isinstance(tracks, wavelink.Playlist):
                added: int = await player.queue.put_wait(tracks)
                await ctx.send(f"✅ Added playlist **{tracks.name}** with `{added}` tracks to the queue.")
                
                # Start playing if not already
                if not player.playing:
                    await player.play(player.queue.get(), volume=30)
            else:
                # Add first track
                track: wavelink.Playable = tracks[0]
                
                if player.playing:
                    # Add to queue if already playing
                    await player.queue.put_wait(track)
                    await ctx.send(f"✅ Added to queue: **{track.title}**")
                else:
                    # Play immediately if nothing is playing
                    await player.play(track, volume=30)
                    await ctx.send(f"🎵 Playing: **{track.title}**")
                
            self.logger.info(f"Music | {ctx.author} requested: {query}")

        except Exception as e:
            await ctx.send(f"❌ An error occurred: {e}")
            self.logger.error(f"Music | Play error: {e}", exc_info=True)

    @commands.hybrid_command(name="pause", help="Pause the currently playing track.")
    async def pause(self, ctx: commands.Context):
        """Pause the current track."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        await player.pause(not player.paused)
        
        if player.paused:
            await ctx.send("⏸️ Paused playback.")
        else:
            await ctx.send("▶️ Resumed playback.")

    @commands.hybrid_command(name="skip", aliases=["next"], help="Skip the current track.")
    async def skip(self, ctx: commands.Context):
        """Skip to the next track in the queue."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        await player.skip(force=True)
        await ctx.send("⏭️ Skipped to next track.")

    @commands.hybrid_command(name="stop", help="Stop playback and clear the queue.")
    async def stop(self, ctx: commands.Context):
        """Stop playback and disconnect."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        await player.disconnect()
        await ctx.send("⏹️ Stopped playback and disconnected.")

    @commands.hybrid_command(name="queue", aliases=["q"], help="Show the current queue.")
    async def queue(self, ctx: commands.Context):
        """Display the current queue."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        if player.queue.is_empty:
            await ctx.send("📭 The queue is empty.")
            return

        embed = discord.Embed(
            title="🎵 Current Queue",
            color=self.bot.embed_color,
            timestamp=datetime.datetime.utcnow()
        )

        # Show currently playing
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"**{player.current.title}** by {player.current.author}",
                inline=False
            )

        # Show next tracks in queue (up to 10)
        queue_list = []
        for i, track in enumerate(player.queue[:10], start=1):
            duration = str(datetime.timedelta(milliseconds=track.length))
            queue_list.append(f"`{i}.` **{track.title}** ({duration})")

        if queue_list:
            embed.add_field(
                name=f"Up Next ({len(player.queue)} tracks)",
                value="\n".join(queue_list),
                inline=False
            )

        if len(player.queue) > 10:
            embed.set_footer(text=f"And {len(player.queue) - 10} more tracks...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="nowplaying", aliases=["np"], help="Show the currently playing track.")
    async def nowplaying(self, ctx: commands.Context):
        """Display information about the current track."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player or not player.current:
            await ctx.send("❌ Nothing is playing right now.")
            return

        track = player.current
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{track.title}**",
            color=self.bot.embed_color
        )

        if track.author:
            embed.add_field(name="Artist", value=track.author, inline=True)

        if track.length:
            duration = str(datetime.timedelta(milliseconds=track.length))
            position = str(datetime.timedelta(milliseconds=player.position))
            embed.add_field(name="Duration", value=f"{position} / {duration}", inline=True)

        if track.uri:
            embed.add_field(name="URL", value=f"[Link]({track.uri})", inline=True)

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        # Show progress bar
        if track.length:
            progress = int((player.position / track.length) * 20)
            bar = "▬" * progress + "🔘" + "▬" * (20 - progress)
            embed.add_field(name="Progress", value=bar, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="volume", aliases=["vol"], help="Set the player volume (0-100).")
    async def volume(self, ctx: commands.Context, volume: int):
        """
        Set the player volume.
        
        Usage: !volume <0-100>
        """
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        if not 0 <= volume <= 100:
            await ctx.send("❌ Volume must be between 0 and 100.")
            return

        await player.set_volume(volume)
        await ctx.send(f"🔊 Set volume to {volume}%")

    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave"], help="Disconnect the bot from voice.")
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        await player.disconnect()
        await ctx.send("👋 Disconnected from voice channel.")

    @commands.hybrid_command(name="clear", help="Clear the queue.")
    async def clear(self, ctx: commands.Context):
        """Clear all tracks from the queue."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        player.queue.clear()
        await ctx.send("🗑️ Cleared the queue.")

    @commands.hybrid_command(name="shuffle", help="Shuffle the queue.")
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the current queue."""
        if not WAVELINK_AVAILABLE:
            await ctx.send("❌ Wavelink not available.")
            return

        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("❌ Not connected to a voice channel.")
            return

        if player.queue.is_empty:
            await ctx.send("❌ The queue is empty.")
            return

        player.queue.shuffle()
        await ctx.send("🔀 Shuffled the queue.")


async def setup(bot):
    """Load the Music cog."""
    await bot.add_cog(Music(bot))
