"""
Events Cog
==========

Reads and displays Discord scheduled events from the guild.
Also handles Discord bot events like guild joins and removals.
"""

import discord
from discord.ext import commands
from datetime import datetime


class Events(commands.Cog):
    """Event management and listener cog for Discord scheduled events."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.redis = bot.redis_manager

    # ==================== Discord Bot Events ====================
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Triggered when the bot joins a new guild."""
        self.logger.info(f"Events | Joined Guild: {guild.name} | ID: {guild.id}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Triggered when the bot is removed from a guild."""
        self.logger.info(f"Events | Left Guild: {guild.name} | ID: {guild.id}")
    
    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event):
        """Triggered when a scheduled event is created."""
        self.logger.info(f"Events | New event created: {event.name} | Guild: {event.guild.name}")
    
    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before, after):
        """Triggered when a scheduled event is updated."""
        self.logger.info(f"Events | Event updated: {after.name} | Guild: {after.guild.name}")
    
    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event):
        """Triggered when a scheduled event is deleted."""
        self.logger.info(f"Events | Event deleted: {event.name} | Guild: {event.guild.name}")

    # ==================== Discord Event Commands ====================

    @commands.hybrid_command(name="events", aliases=["eventlist", "upcoming"])
    @commands.guild_only()
    async def list_events(self, ctx):
        """List all upcoming Discord scheduled events in this server."""
        try:
            # Fetch all scheduled events from the guild
            events = await ctx.guild.fetch_scheduled_events(with_counts=True)
            
            if not events:
                await ctx.send("📅 No scheduled events found in this server.")
                return

            # Filter for upcoming/active events
            active_events = [e for e in events if e.status in [discord.EventStatus.scheduled, discord.EventStatus.active]]
            
            if not active_events:
                await ctx.send("📅 No upcoming events scheduled.")
                return

            # Sort by start time
            active_events.sort(key=lambda e: e.start_time)

            embed = discord.Embed(
                title=f"📅 Upcoming Events in {ctx.guild.name}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )

            for event in active_events[:10]:  # Limit to 10 events
                # Calculate time until event
                time_until = event.start_time - datetime.now(event.start_time.tzinfo)
                
                if time_until.days > 0:
                    time_str = f"in {time_until.days} day{'s' if time_until.days != 1 else ''}"
                elif time_until.seconds // 3600 > 0:
                    hours = time_until.seconds // 3600
                    time_str = f"in {hours} hour{'s' if hours != 1 else ''}"
                else:
                    time_str = "soon"

                # Get location/channel info
                location = ""
                if event.location:
                    location = f"📍 {event.location}\n"
                elif event.channel:
                    location = f"📍 {event.channel.mention}\n"
                
                # Get interested count
                interested_count = f"👥 {event.user_count} interested" if event.user_count else ""
                
                # Status indicator
                status_emoji = "🔴 LIVE" if event.status == discord.EventStatus.active else "🟢"
                
                embed.add_field(
                    name=f"{status_emoji} {event.name}",
                    value=f"🕒 {discord.utils.format_dt(event.start_time, 'F')} ({time_str})\n"
                          f"{location}"
                          f"{interested_count}\n"
                          f"*Use `!event {event.id}` for details*",
                    inline=False
                )

            embed.set_footer(text=f"Showing {len(active_events)} upcoming event(s)")
            await ctx.send(embed=embed)
            self.logger.info(f"Events | Listed {len(active_events)} Discord events | Guild: {ctx.guild.id}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view events in this server.")
        except Exception as e:
            self.logger.error(f"Events | Error listing Discord events: {e}")
            await ctx.send("❌ Error retrieving events. Please try again later.")

    @commands.hybrid_command(name="event", aliases=["eventinfo"])
    @commands.guild_only()
    async def event_details(self, ctx, event_id: str):
        """
        Get detailed information about a specific Discord scheduled event.
        
        Args:
            event_id: The ID of the event
        """
        try:
            # Fetch the specific event
            try:
                event = await ctx.guild.fetch_scheduled_event(int(event_id), with_counts=True)
            except (ValueError, discord.NotFound):
                await ctx.send(f"❌ Event with ID `{event_id}` not found.")
                return

            # Create detailed embed
            embed = discord.Embed(
                title=f"📅 {event.name}",
                description=event.description or "*No description provided*",
                color=discord.Color.green() if event.status == discord.EventStatus.scheduled else discord.Color.gold()
            )

            # Status
            status_map = {
                discord.EventStatus.scheduled: "🟢 Scheduled",
                discord.EventStatus.active: "🔴 Live Now",
                discord.EventStatus.completed: "⚫ Ended",
                discord.EventStatus.cancelled: "❌ Cancelled"
            }
            embed.add_field(
                name="Status",
                value=status_map.get(event.status, "Unknown"),
                inline=True
            )

            # Start time
            embed.add_field(
                name="🕒 Starts",
                value=f"{discord.utils.format_dt(event.start_time, 'F')}\n{discord.utils.format_dt(event.start_time, 'R')}",
                inline=False
            )

            # End time (if set)
            if event.end_time:
                embed.add_field(
                    name="🏁 Ends",
                    value=f"{discord.utils.format_dt(event.end_time, 'F')}\n{discord.utils.format_dt(event.end_time, 'R')}",
                    inline=False
                )

            # Location
            if event.location:
                embed.add_field(name="📍 Location", value=event.location, inline=False)
            elif event.channel:
                embed.add_field(name="📍 Channel", value=event.channel.mention, inline=False)

            # Entity type (voice, stage, external)
            entity_type_map = {
                discord.EntityType.voice: "🔊 Voice Channel",
                discord.EntityType.stage_instance: "🎤 Stage Channel",
                discord.EntityType.external: "🌐 External Location"
            }
            embed.add_field(
                name="Type",
                value=entity_type_map.get(event.entity_type, "Unknown"),
                inline=True
            )

            # Interested users count
            if event.user_count:
                embed.add_field(
                    name="👥 Interested",
                    value=f"{event.user_count} user{'s' if event.user_count != 1 else ''}",
                    inline=True
                )

            # Creator
            if event.creator:
                embed.add_field(
                    name="Created by",
                    value=event.creator.mention,
                    inline=True
                )

            # Event image/cover
            if event.cover_image:
                embed.set_image(url=event.cover_image)

            # Event URL
            embed.add_field(
                name="🔗 Event Link",
                value=f"[Click to view in Discord]({event.url})",
                inline=False
            )

            embed.set_footer(text=f"Event ID: {event.id}")

            await ctx.send(embed=embed)
            self.logger.info(f"Events | Fetched details for event {event.id} | {event.name}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view this event.")
        except Exception as e:
            self.logger.error(f"Events | Error getting event details: {e}")
            await ctx.send("❌ Error retrieving event details.")

    @commands.hybrid_command(name="eventusers", aliases=["eventrsvp", "eventattendees"])
    @commands.guild_only()
    async def event_users(self, ctx, event_id: str):
        """
        List all users interested in a Discord scheduled event.
        
        Args:
            event_id: The ID of the event
        """
        try:
            # Fetch the event
            try:
                event = await ctx.guild.fetch_scheduled_event(int(event_id))
            except (ValueError, discord.NotFound):
                await ctx.send(f"❌ Event with ID `{event_id}` not found.")
                return

            # Fetch interested users
            users = []
            async for user in event.users():
                users.append(user)

            if not users:
                await ctx.send(f"📅 No users are interested in **{event.name}** yet.")
                return

            embed = discord.Embed(
                title=f"👥 Interested Users - {event.name}",
                description=f"**{len(users)}** user{'s' if len(users) != 1 else ''} interested",
                color=discord.Color.blue()
            )

            # Split users into chunks of 20 for display
            user_list = [user.mention for user in users[:50]]  # Limit to 50 to avoid embed size issues
            
            # Create formatted list
            chunk_size = 20
            for i in range(0, len(user_list), chunk_size):
                chunk = user_list[i:i + chunk_size]
                field_name = f"Users {i+1}-{min(i+chunk_size, len(user_list))}" if len(user_list) > chunk_size else "Users"
                embed.add_field(
                    name=field_name,
                    value="\n".join(chunk),
                    inline=False
                )

            if len(users) > 50:
                embed.set_footer(text=f"Showing first 50 of {len(users)} interested users")
            else:
                embed.set_footer(text=f"Event starts {discord.utils.format_dt(event.start_time, 'R')}")

            await ctx.send(embed=embed)
            self.logger.info(f"Events | Listed {len(users)} users for event {event.id}")

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view this event's users.")
        except Exception as e:
            self.logger.error(f"Events | Error getting event users: {e}")
            await ctx.send("❌ Error retrieving event users.")

    @commands.hybrid_command(name="nextevent")
    @commands.guild_only()
    async def next_event(self, ctx):
        """Show the next upcoming Discord scheduled event."""
        try:
            events = await ctx.guild.fetch_scheduled_events(with_counts=True)
            
            # Filter for scheduled events only
            upcoming = [e for e in events if e.status == discord.EventStatus.scheduled]
            
            if not upcoming:
                await ctx.send("📅 No upcoming events scheduled.")
                return

            # Sort by start time and get the first one
            upcoming.sort(key=lambda e: e.start_time)
            next_event = upcoming[0]

            embed = discord.Embed(
                title=f"⏭️ Next Event: {next_event.name}",
                description=next_event.description or "*No description*",
                color=discord.Color.green()
            )

            embed.add_field(
                name="🕒 When",
                value=f"{discord.utils.format_dt(next_event.start_time, 'F')}\n{discord.utils.format_dt(next_event.start_time, 'R')}",
                inline=False
            )

            if next_event.location:
                embed.add_field(name="📍 Where", value=next_event.location, inline=False)
            elif next_event.channel:
                embed.add_field(name="📍 Channel", value=next_event.channel.mention, inline=False)

            if next_event.user_count:
                embed.add_field(name="👥 Interested", value=f"{next_event.user_count} users", inline=True)

            if next_event.cover_image:
                embed.set_thumbnail(url=next_event.cover_image)

            embed.add_field(
                name="🔗 Link",
                value=f"[View Event]({next_event.url})",
                inline=False
            )

            embed.set_footer(text=f"Use !event {next_event.id} for full details")

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view events.")
        except Exception as e:
            self.logger.error(f"Events | Error getting next event: {e}")
            await ctx.send("❌ Error retrieving next event.")


async def setup(bot):
    """Load the Events cog."""
    await bot.add_cog(Events(bot))
