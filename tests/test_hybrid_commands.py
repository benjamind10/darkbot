import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

from bot.cogs.Information import Information
from bot.cogs.Utility import Utility


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
