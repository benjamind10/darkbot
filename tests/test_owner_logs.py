"""Tests for RollingLogHandler and the !logs command."""

import logging
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Add bot/ so relative cog imports (e.g. `from cogs.Owner import Owner`) resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

from bot.utils.log_buffer import RollingLogHandler  # noqa: E402


# ---------------------------------------------------------------------------
# RollingLogHandler unit tests
# ---------------------------------------------------------------------------


def test_rolling_handler_stores_entries():
    handler = RollingLogHandler(maxlen=10)
    logger = logging.getLogger("test.rolling")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info("entry one")
    logger.error("entry two")

    entries = handler.get_entries(10)
    assert len(entries) == 2
    assert any("entry one" in e for e in entries)
    assert any("entry two" in e for e in entries)

    logger.removeHandler(handler)


def test_rolling_handler_respects_maxlen():
    handler = RollingLogHandler(maxlen=3)
    logger = logging.getLogger("test.rolling.maxlen")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    for i in range(5):
        logger.info(f"msg {i}")

    entries = handler.get_entries(10)
    assert len(entries) == 3
    assert any("msg 2" in e for e in entries)
    assert any("msg 3" in e for e in entries)
    assert any("msg 4" in e for e in entries)

    logger.removeHandler(handler)


def test_rolling_handler_get_entries_clamps_to_available():
    handler = RollingLogHandler(maxlen=10)
    logger = logging.getLogger("test.rolling.clamp")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info("only entry")

    entries = handler.get_entries(50)
    assert len(entries) == 1

    logger.removeHandler(handler)


def test_rolling_handler_empty_buffer():
    handler = RollingLogHandler(maxlen=10)
    assert handler.get_entries(5) == []


# ---------------------------------------------------------------------------
# logs command tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def owner_cog():
    """Build a minimal Owner cog backed by a real RollingLogHandler."""
    from cogs.Owner import Owner

    log_buffer = RollingLogHandler(maxlen=500)
    bot_logger = logging.getLogger("test.owner_cog")
    bot_logger.addHandler(log_buffer)
    bot_logger.setLevel(logging.DEBUG)

    mock_bot = SimpleNamespace(
        logger=bot_logger,
        log_buffer=log_buffer,
        redis_manager=AsyncMock(),
    )

    cog = Owner.__new__(Owner)
    cog.bot = mock_bot
    cog.logger = bot_logger
    yield cog

    bot_logger.removeHandler(log_buffer)


def _make_ctx(is_slash: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.send = AsyncMock()
    if is_slash:
        ctx.interaction = MagicMock()
        ctx.interaction.response.is_done.return_value = False
        ctx.defer = AsyncMock()
    else:
        ctx.interaction = None
    return ctx


@pytest.mark.asyncio
async def test_logs_returns_entries(owner_cog):
    owner_cog.logger.info("hello from test")
    owner_cog.logger.error("an error occurred")

    ctx = _make_ctx()
    await owner_cog.logs.callback(owner_cog, ctx, 20)

    ctx.send.assert_called_once()
    sent = ctx.send.call_args[0][0]
    assert "hello from test" in sent
    assert "an error occurred" in sent


@pytest.mark.asyncio
async def test_logs_empty_buffer(owner_cog):
    ctx = _make_ctx()
    await owner_cog.logs.callback(owner_cog, ctx, 20)

    ctx.send.assert_called_once_with("No log entries recorded yet.")


@pytest.mark.asyncio
async def test_logs_clamps_n_to_max(owner_cog):
    for i in range(10):
        owner_cog.logger.info(f"msg {i}")

    ctx = _make_ctx()
    # n=999 should be clamped to 100; still returns all 10 available entries
    await owner_cog.logs.callback(owner_cog, ctx, 999)

    ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_logs_clamps_n_to_min(owner_cog):
    owner_cog.logger.info("only one")

    ctx = _make_ctx()
    await owner_cog.logs.callback(owner_cog, ctx, 0)

    ctx.send.assert_called_once()
    sent = ctx.send.call_args[0][0]
    assert "only one" in sent


@pytest.mark.asyncio
async def test_logs_defers_for_slash(owner_cog):
    owner_cog.logger.warning("slash test")

    ctx = _make_ctx(is_slash=True)
    await owner_cog.logs.callback(owner_cog, ctx, 5)

    ctx.defer.assert_awaited_once()
    ctx.send.assert_called_once()
