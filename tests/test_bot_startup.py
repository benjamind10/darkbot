import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

psycopg_module = sys.modules.setdefault("psycopg", ModuleType("psycopg"))
psycopg_rows_module = sys.modules.setdefault("psycopg.rows", ModuleType("psycopg.rows"))
psycopg_rows_module.dict_row = object()
psycopg_module.rows = psycopg_rows_module

psycopg_pool_module = sys.modules.setdefault("psycopg_pool", ModuleType("psycopg_pool"))
psycopg_pool_module.AsyncConnectionPool = type("AsyncConnectionPool", (), {})
psycopg_pool_module.ConnectionPool = type("ConnectionPool", (), {})
psycopg_pool_module.AsyncConnection = SimpleNamespace

from bot.core.bot import CogLoadResult, DarkBot
from bot.core.exceptions import DarkBotException


def make_bot_stub(*, failing=None):
    bot = SimpleNamespace(
        REQUIRED_COGS=set(DarkBot.REQUIRED_COGS),
        OPTIONAL_COGS=set(DarkBot.OPTIONAL_COGS),
        logger=logging.getLogger("tests.startup"),
        load_extension=AsyncMock(),
    )
    failing = failing or set()

    async def load_extension(name):
        if name in failing:
            raise RuntimeError(f"boom: {name}")

    bot.load_extension.side_effect = load_extension
    return bot


@pytest.mark.asyncio
async def test_load_cogs_returns_success_results(monkeypatch):
    monkeypatch.setattr("bot.core.bot.os.listdir", lambda _: ["Information.py"])
    bot = make_bot_stub()

    results = await DarkBot.load_cogs(bot)

    assert results == [CogLoadResult("cogs.Information", True, True)]


@pytest.mark.asyncio
async def test_load_cogs_raises_for_required_failure(monkeypatch):
    monkeypatch.setattr("bot.core.bot.os.listdir", lambda _: ["Information.py"])
    bot = make_bot_stub(failing={"cogs.Information"})

    with pytest.raises(DarkBotException, match="cogs.Information"):
        await DarkBot.load_cogs(bot)


@pytest.mark.asyncio
async def test_load_cogs_allows_optional_failure(monkeypatch):
    monkeypatch.setattr("bot.core.bot.os.listdir", lambda _: ["Music.py"])
    bot = make_bot_stub(failing={"cogs.Music"})

    results = await DarkBot.load_cogs(bot)

    assert results == [
        CogLoadResult("cogs.Music", False, False, results[0].error),
    ]
    assert isinstance(results[0].error, RuntimeError)


@pytest.mark.asyncio
async def test_load_cogs_treats_unknown_cogs_as_required(monkeypatch):
    monkeypatch.setattr("bot.core.bot.os.listdir", lambda _: ["Custom.py"])
    bot = make_bot_stub(failing={"cogs.Custom"})

    with pytest.raises(DarkBotException, match="cogs.Custom"):
        await DarkBot.load_cogs(bot)


@pytest.mark.asyncio
async def test_sync_command_tree_returns_synced_count():
    bot = SimpleNamespace(
        tree=SimpleNamespace(sync=AsyncMock(return_value=[object(), object()])),
        logger=logging.getLogger("tests.startup"),
    )

    assert await DarkBot.sync_command_tree(bot) == 2


@pytest.mark.asyncio
async def test_sync_command_tree_logs_and_returns_zero_on_failure(caplog):
    bot = SimpleNamespace(
        tree=SimpleNamespace(sync=AsyncMock(side_effect=RuntimeError("sync failed"))),
        logger=logging.getLogger("tests.startup"),
    )

    with caplog.at_level(logging.ERROR):
        assert await DarkBot.sync_command_tree(bot) == 0
    assert "Failed to sync slash commands" in caplog.text


@pytest.mark.asyncio
async def test_sync_command_tree_handles_http_exception(caplog):
    response = SimpleNamespace(status=500, reason="boom")
    bot = SimpleNamespace(
        tree=SimpleNamespace(
            sync=AsyncMock(
                side_effect=discord.HTTPException(response=response, message="sync rejected")
            )
        ),
        logger=logging.getLogger("tests.startup"),
    )

    with caplog.at_level(logging.ERROR):
        assert await DarkBot.sync_command_tree(bot) == 0
    assert "Discord rejected slash command sync" in caplog.text
