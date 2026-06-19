import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import logging
import discord
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

from bot.cogs.Events import Events


def make_event(name="Raid Night"):
    return SimpleNamespace(name=name, guild=SimpleNamespace(name="Guild", id=123))


def make_interaction(is_done=False):
    response = MagicMock()
    response.is_done.return_value = is_done
    return SimpleNamespace(response=response)


@pytest.mark.asyncio
async def test_scheduled_event_create_logs(bot, caplog):
    cog = Events(bot)

    with caplog.at_level(logging.INFO):
        await cog.on_scheduled_event_create(make_event())

    assert "New event created" in caplog.text


@pytest.mark.asyncio
async def test_scheduled_event_update_logs(bot, caplog):
    cog = Events(bot)

    with caplog.at_level(logging.INFO):
        await cog.on_scheduled_event_update(make_event("Old"), make_event("New"))

    assert "Event updated" in caplog.text


@pytest.mark.asyncio
async def test_scheduled_event_delete_logs(bot, caplog):
    cog = Events(bot)

    with caplog.at_level(logging.INFO):
        await cog.on_scheduled_event_delete(make_event())

    assert "Event deleted" in caplog.text


@pytest.mark.asyncio
async def test_event_details_defers_for_slash_context(bot):
    event = SimpleNamespace(
        id=123,
        name="Raid Night",
        description="Bring snacks",
        status=discord.EventStatus.scheduled,
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        end_time=None,
        location=None,
        channel=None,
        entity_type=discord.EntityType.external,
        user_count=0,
        creator=None,
        cover_image=None,
        url="https://example.com/event",
    )
    ctx = MagicMock()
    ctx.interaction = make_interaction()
    ctx.defer = AsyncMock()
    ctx.send = AsyncMock()
    ctx.guild = MagicMock()
    ctx.guild.fetch_scheduled_event = AsyncMock(return_value=event)

    await Events.event_details.callback(Events(bot), ctx, "123")

    ctx.defer.assert_awaited_once_with()
    ctx.send.assert_awaited_once()
