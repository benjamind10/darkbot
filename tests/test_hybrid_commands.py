import sys
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

from bot.cogs.Information import Information
from bot.cogs.Music import Music
from bot.cogs.Utility import Utility
from bot.utils.discord_context import defer_if_interaction, has_origin_message, send_for_context


def make_interaction(is_done=False):
    response = MagicMock()
    response.is_done.return_value = is_done
    return SimpleNamespace(response=response)


def make_author():
    author = MagicMock()
    author.send = AsyncMock()
    author.display_avatar = SimpleNamespace(url="https://example.com/avatar.png")
    return author


@pytest.mark.asyncio
async def test_defer_if_interaction_skips_prefix_context():
    ctx = MagicMock()
    ctx.interaction = None
    ctx.defer = AsyncMock()

    assert await defer_if_interaction(ctx) is False
    ctx.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_defer_if_interaction_skips_already_deferred_interaction():
    ctx = MagicMock()
    ctx.interaction = make_interaction(is_done=True)
    ctx.defer = AsyncMock()

    assert await defer_if_interaction(ctx) is False
    ctx.defer.assert_not_awaited()


@pytest.mark.asyncio
async def test_defer_if_interaction_defers_slash_context():
    ctx = MagicMock()
    ctx.interaction = make_interaction(is_done=False)
    ctx.defer = AsyncMock()

    assert await defer_if_interaction(ctx) is True
    ctx.defer.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_defer_if_interaction_handles_expired_interaction(caplog):
    ctx = MagicMock()
    ctx.interaction = make_interaction(is_done=False)
    ctx.defer = AsyncMock(
        side_effect=discord.NotFound(
            response=SimpleNamespace(status=404, reason="Unknown interaction"),
            message="expired",
        )
    )
    ctx.bot = SimpleNamespace(logger=logging.getLogger("tests.hybrid"))

    with caplog.at_level(logging.WARNING):
        assert await defer_if_interaction(ctx) is False
    assert "Interaction expired before defer could be sent" in caplog.text
    assert getattr(ctx, "_darkbot_interaction_expired", False) is True


@pytest.mark.asyncio
async def test_send_for_context_uses_followup_after_acknowledged_interaction():
    ctx = MagicMock()
    ctx.interaction = SimpleNamespace(
        response=make_interaction(is_done=True).response,
        followup=SimpleNamespace(send=AsyncMock(return_value="sent")),
    )
    ctx.send = AsyncMock()

    assert await send_for_context(ctx, "hello") == "sent"
    ctx.send.assert_not_awaited()
    ctx.interaction.followup.send.assert_awaited_once_with("hello", wait=True)


@pytest.mark.asyncio
async def test_send_for_context_uses_followup_after_acknowledgement_error():
    ctx = MagicMock()
    ctx.interaction = SimpleNamespace(
        response=make_interaction(is_done=False).response,
        followup=SimpleNamespace(send=AsyncMock(return_value="sent")),
    )
    ctx.send = AsyncMock(
        side_effect=discord.HTTPException(
            response=SimpleNamespace(status=400, reason="acknowledged"),
            message={"code": 40060, "message": "Interaction has already been acknowledged."},
        )
    )

    assert await send_for_context(ctx, "hello") == "sent"
    ctx.send.assert_awaited_once_with("hello")
    ctx.interaction.followup.send.assert_awaited_once_with("hello", wait=True)


@pytest.mark.asyncio
async def test_send_for_context_uses_channel_fallback_after_expired_defer(caplog):
    ctx = MagicMock()
    ctx.interaction = make_interaction(is_done=False)
    ctx.defer = AsyncMock(
        side_effect=discord.NotFound(
            response=SimpleNamespace(status=404, reason="Unknown interaction"),
            message="expired",
        )
    )
    ctx.send = AsyncMock()
    ctx.channel = SimpleNamespace(send=AsyncMock(return_value="fallback"))
    ctx.bot = SimpleNamespace(logger=logging.getLogger("tests.hybrid"))

    with caplog.at_level(logging.WARNING):
        assert await defer_if_interaction(ctx) is False
        assert await send_for_context(ctx, "hello") == "fallback"

    ctx.send.assert_not_awaited()
    ctx.channel.send.assert_awaited_once_with("hello")
    assert "Sent channel fallback after interaction response failure" in caplog.text


@pytest.mark.asyncio
async def test_send_for_context_uses_interaction_channel_fallback_when_ctx_channel_missing(caplog):
    interaction_channel = SimpleNamespace(send=AsyncMock(return_value="fallback"))
    ctx = MagicMock()
    ctx.interaction = make_interaction(is_done=False)
    ctx.defer = AsyncMock(
        side_effect=discord.NotFound(
            response=SimpleNamespace(status=404, reason="Unknown interaction"),
            message="expired",
        )
    )
    ctx.send = AsyncMock()
    ctx.bot = SimpleNamespace(logger=logging.getLogger("tests.hybrid"))
    ctx.interaction.channel = interaction_channel

    with caplog.at_level(logging.WARNING):
        assert await defer_if_interaction(ctx) is False
        assert await send_for_context(ctx, "hello") == "fallback"

    ctx.send.assert_not_awaited()
    interaction_channel.send.assert_awaited_once_with("hello")
    assert "Sent channel fallback after interaction response failure" in caplog.text


def test_has_origin_message_handles_missing_message():
    ctx = MagicMock()
    ctx.message = None

    assert has_origin_message(ctx) is False


@pytest.mark.asyncio
async def test_botstats_defers_for_slash_context(bot):
    bot.get_stats = AsyncMock(return_value={"guild_count": 3, "user_count": 7})
    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = "tester"
    ctx.guild = "guild"

    await Information.botstats.callback(Information(bot), ctx)

    ctx.defer.assert_awaited_once()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_botstats_does_not_defer_for_prefix_context(bot):
    bot.get_stats = AsyncMock(return_value={"guild_count": 3, "user_count": 7})
    ctx = MagicMock()
    ctx.interaction = None
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = "tester"
    ctx.guild = "guild"

    await Information.botstats.callback(Information(bot), ctx)

    ctx.defer.assert_not_awaited()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_invite_slash_context_does_not_require_message(bot):
    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = make_author()
    ctx.message = None

    await Information.invite.callback(Information(bot), ctx)

    ctx.defer.assert_awaited_once()
    ctx.author.send.assert_awaited_once()
    ctx.send.assert_awaited_once_with("✅ I sent you the invite link in DMs.")


@pytest.mark.asyncio
async def test_invite_prefix_context_adds_reaction(bot):
    ctx = MagicMock()
    ctx.interaction = None
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = make_author()
    ctx.message = MagicMock()
    ctx.message.add_reaction = AsyncMock()

    await Information.invite.callback(Information(bot), ctx)

    ctx.defer.assert_not_awaited()
    ctx.author.send.assert_awaited_once()
    ctx.message.add_reaction.assert_awaited_once_with("🤖")
    ctx.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_ping_defers_for_slash_context(bot):
    bot.latency = 0.123
    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = "tester"

    await Information.ping.callback(Information(bot), ctx)

    ctx.defer.assert_awaited_once_with()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_ping_does_not_defer_for_prefix_context(bot):
    bot.latency = 0.123
    ctx = MagicMock()
    ctx.interaction = None
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.author = "tester"

    await Information.ping.callback(Information(bot), ctx)

    ctx.defer.assert_not_awaited()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_slash_context_does_not_require_message(bot):
    bot.config.services = SimpleNamespace(ip_info=None, ksoft_api=None)
    poll_message = MagicMock()
    poll_message.add_reaction = AsyncMock()
    channel = MagicMock()
    channel.send = AsyncMock(return_value=poll_message)

    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.author = make_author()
    ctx.message = None

    await Utility.poll.callback(Utility(bot), ctx, channel, question="Ship it?")

    ctx.defer.assert_awaited_once()
    channel.send.assert_awaited_once()
    poll_message.add_reaction.assert_any_await("👍")
    poll_message.add_reaction.assert_any_await("👎")


@pytest.mark.asyncio
async def test_poll_prefix_context_deletes_origin_message(bot):
    bot.config.services = SimpleNamespace(ip_info=None, ksoft_api=None)
    poll_message = MagicMock()
    poll_message.add_reaction = AsyncMock()
    channel = MagicMock()
    channel.send = AsyncMock(return_value=poll_message)

    ctx = MagicMock()
    ctx.interaction = None
    ctx.defer = AsyncMock()
    ctx.author = make_author()
    ctx.message = MagicMock()
    ctx.message.delete = AsyncMock()

    await Utility.poll.callback(Utility(bot), ctx, channel, question="Ship it?")

    ctx.defer.assert_not_awaited()
    ctx.message.delete.assert_awaited_once()
    channel.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_play_defers_before_wavelink_unavailable(bot, monkeypatch):
    from bot.cogs import Music as music_module

    monkeypatch.setattr(music_module, "WAVELINK_AVAILABLE", False)
    bot.config.music = SimpleNamespace(enabled=True)
    bot.config.lavalink = SimpleNamespace(enabled=True)
    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()

    music = Music(bot)
    await music.play.callback(music, ctx, query="test")

    ctx.defer.assert_awaited_once_with()
    ctx.send.assert_awaited_once()
