from unittest.mock import AsyncMock

import pytest

from bot.cogs import Music as music_module
from bot.cogs.Music import Music


@pytest.mark.asyncio
async def test_music_cog_unload_closes_wavelink_once(bot, monkeypatch):
    close = AsyncMock()
    monkeypatch.setattr(music_module, "WAVELINK_AVAILABLE", True)
    monkeypatch.setattr(music_module.wavelink.Pool, "nodes", {"LOCAL": object()})
    monkeypatch.setattr(music_module.wavelink.Pool, "close", close)

    await Music(bot).cog_unload()

    close.assert_awaited_once()
