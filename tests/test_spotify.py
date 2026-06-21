from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.cogs import Spotify as spotify_module


@pytest.mark.asyncio
async def test_setup_adds_spotify_cog_even_when_music_disabled():
    bot = SimpleNamespace(
        config=SimpleNamespace(
            music=SimpleNamespace(enabled=False),
            lavalink=SimpleNamespace(enabled=False),
        ),
        add_cog=AsyncMock(),
        logger=SimpleNamespace(info=AsyncMock()),
    )

    await spotify_module.setup(bot)

    bot.add_cog.assert_awaited_once()


@pytest.mark.asyncio
async def test_spplay_exits_early_when_music_disabled(monkeypatch):
    bot = SimpleNamespace(
        config=SimpleNamespace(
            music=SimpleNamespace(enabled=False),
            lavalink=SimpleNamespace(enabled=False),
            services=SimpleNamespace(spotify_client_id="id", spotify_client_secret="secret"),
        ),
        logger=SimpleNamespace(info=AsyncMock(), error=AsyncMock()),
        redis_manager=SimpleNamespace(),
        http_session=SimpleNamespace(get=AsyncMock()),
    )
    cog = spotify_module.Spotify(bot)
    ctx = SimpleNamespace(interaction=None)
    send = AsyncMock()
    get_token = AsyncMock()

    monkeypatch.setattr(spotify_module, "send_for_context", send)
    monkeypatch.setattr(cog, "_get_token", get_token)

    await cog.spplay(ctx, query="test track")

    send.assert_awaited_once_with(
        ctx, "Spotify playback is disabled because music/Lavalink is not enabled."
    )
    get_token.assert_not_awaited()
    bot.http_session.get.assert_not_awaited()
