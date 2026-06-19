from __future__ import annotations

import discord
from discord.ext import commands


EXPIRED_INTERACTION_ATTR = "_darkbot_interaction_expired"


async def defer_if_interaction(ctx: commands.Context, *, ephemeral: bool = False) -> bool:
    """Defer a hybrid-command interaction if it is still pending."""
    interaction = getattr(ctx, "interaction", None)
    if interaction is None:
        return False

    response = getattr(interaction, "response", None)
    if response is not None and response.is_done():
        return False

    try:
        if ephemeral:
            await ctx.defer(ephemeral=True)
        else:
            await ctx.defer()
    except discord.NotFound:
        setattr(ctx, EXPIRED_INTERACTION_ATTR, True)
        _log_interaction_warning(ctx, "Interaction expired before defer could be sent")
        return False
    except discord.HTTPException as exc:
        if exc.code == 40060:
            _log_interaction_warning(ctx, "Interaction was already acknowledged before defer")
            return True
        raise

    return True


def has_origin_message(ctx: commands.Context) -> bool:
    """Return whether the command context has an originating message."""
    return getattr(ctx, "message", None) is not None


async def send_for_context(ctx: commands.Context, *args, **kwargs):
    """Send a response that works for both prefix and slash contexts."""
    interaction = getattr(ctx, "interaction", None)
    if interaction is None:
        return await ctx.send(*args, **kwargs)

    if vars(ctx).get(EXPIRED_INTERACTION_ATTR, False):
        return await _send_channel_fallback(ctx, *args, **kwargs)

    response = getattr(interaction, "response", None)
    if response is not None and response.is_done():
        return await _send_followup_or_fallback(ctx, *args, **kwargs)

    try:
        return await ctx.send(*args, **kwargs)
    except discord.NotFound:
        _log_interaction_warning(ctx, "Interaction expired before response could be sent")
        return await _send_channel_fallback(ctx, *args, **kwargs)
    except discord.HTTPException as exc:
        if exc.code == 40060:
            return await _send_followup_or_fallback(ctx, *args, **kwargs)
        if exc.code == 10062:
            _log_interaction_warning(ctx, "Interaction expired before response could be sent")
            return await _send_channel_fallback(ctx, *args, **kwargs)
        raise


async def _send_followup_or_fallback(ctx: commands.Context, *args, **kwargs):
    interaction = getattr(ctx, "interaction", None)
    followup = getattr(interaction, "followup", None)
    if followup is None:
        return await _send_channel_fallback(ctx, *args, **kwargs)

    followup_kwargs = dict(kwargs)
    followup_kwargs.setdefault("wait", True)
    try:
        return await followup.send(*args, **followup_kwargs)
    except discord.NotFound:
        _log_interaction_warning(ctx, "Interaction expired before follow-up could be sent")
        return await _send_channel_fallback(ctx, *args, **kwargs)
    except discord.HTTPException as exc:
        if exc.code in {10062, 40060}:
            _log_interaction_warning(ctx, "Falling back to channel send after interaction response failure")
            return await _send_channel_fallback(ctx, *args, **kwargs)
        raise


async def _send_channel_fallback(ctx: commands.Context, *args, **kwargs):
    channel = vars(ctx).get("channel")
    if channel is None:
        interaction = getattr(ctx, "interaction", None)
        channel = getattr(interaction, "channel", None)
    if channel is None:
        interaction = getattr(ctx, "interaction", None)
        channel_id = getattr(interaction, "channel_id", None)
        bot = getattr(ctx, "bot", None)
        if channel_id is not None and bot is not None:
            channel = bot.get_channel(channel_id)
    if channel is None:
        _log_interaction_warning(ctx, "No channel fallback available for expired interaction response")
        return None

    fallback_kwargs = dict(kwargs)
    fallback_kwargs.pop("ephemeral", None)
    fallback_kwargs.pop("wait", None)
    message = await channel.send(*args, **fallback_kwargs)
    _log_interaction_warning(ctx, "Sent channel fallback after interaction response failure")
    return message


def _log_interaction_warning(ctx: commands.Context, message: str) -> None:
    logger = getattr(ctx, "bot", None)
    logger = getattr(logger, "logger", None)
    if logger is not None:
        logger.warning(message)
