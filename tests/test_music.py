from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import logging
import pytest

from bot.cogs import Music as music_module
from bot.cogs.Music import Music


@pytest.mark.asyncio
async def test_music_cog_unload_closes_wavelink_once(bot, monkeypatch):
    close = AsyncMock()
    monkeypatch.setattr(music_module, "WAVELINK_AVAILABLE", True)
    monkeypatch.setattr(music_module.wavelink.Pool, "nodes", {"LOCAL": object()})
    monkeypatch.setattr(music_module.wavelink.Pool, "close", close)
    bot.config.music = SimpleNamespace(enabled=True)
    bot.config.lavalink = SimpleNamespace(enabled=True)

    await Music(bot).cog_unload()

    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_music_cog_unload_skips_when_wavelink_unavailable(bot, monkeypatch):
    monkeypatch.setattr(music_module, "WAVELINK_AVAILABLE", False)
    bot.config.music = SimpleNamespace(enabled=True)
    bot.config.lavalink = SimpleNamespace(enabled=True)

    await Music(bot).cog_unload()


@pytest.mark.asyncio
async def test_music_cog_load_logs_connection_failure(bot, monkeypatch, caplog):
    monkeypatch.setattr(music_module, "WAVELINK_AVAILABLE", True)
    monkeypatch.setattr(
        music_module.wavelink.Pool,
        "connect",
        AsyncMock(side_effect=RuntimeError("lavalink down")),
    )
    bot.config.music = SimpleNamespace(enabled=True)
    bot.config.lavalink = SimpleNamespace(
        enabled=True,
        host="http://localhost:2333",
        password="pass",
    )

    with caplog.at_level(logging.ERROR):
        await Music(bot).cog_load()

    assert "Failed to connect to Lavalink" in caplog.text


@pytest.mark.asyncio
async def test_track_start_sends_now_playing_embed(bot):
    channel = MagicMock()
    channel.send = AsyncMock()
    bot.get_channel = MagicMock(return_value=channel)
    bot.config.music = SimpleNamespace(enabled=True)
    bot.config.lavalink = SimpleNamespace(enabled=True)
    payload = SimpleNamespace(
        player=SimpleNamespace(channel=SimpleNamespace(id=123)),
        track=SimpleNamespace(
            title="Song",
            author="Artist",
            length=120000,
            uri="https://example.com/song",
            artwork=None,
        ),
    )

    await Music(bot).on_wavelink_track_start(payload)

    channel.send.assert_awaited_once()
