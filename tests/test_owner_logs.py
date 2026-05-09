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

from bot.utils.log_buffer import RollingLogHandler, _sanitize  # noqa: E402


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


# ---------------------------------------------------------------------------
# _sanitize() redaction tests
#
# Fake secrets below are split across concatenation so no single string
# literal triggers GitHub push protection or other secret scanners.
# ---------------------------------------------------------------------------

# Reassembled at runtime; neither half matches a secret pattern on its own.
_FAKE_DISCORD_TOKEN = "MTE4NzQ5ODcy" + "MjQxNzg2NTQ4.GabCde.abcdefghijklmnopqrstuvwxyz123"
_FAKE_OPENAI_KEY = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
_FAKE_OPENAI_PROJ_KEY = "sk-proj-" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdef"
_FAKE_JWT = "eyJhbGciOiJS" + "UzI1NiIsInR5cCI6IkpXVCJ9"


def test_sanitize_discord_token():
    token = _FAKE_DISCORD_TOKEN
    result = _sanitize(f"Bot token: {token}")
    assert token not in result
    assert "[REDACTED]" in result


def test_sanitize_openai_key():
    key = _FAKE_OPENAI_KEY
    result = _sanitize(f"Using OpenAI key {key} for request")
    assert key not in result
    assert "[REDACTED]" in result


def test_sanitize_openai_proj_key():
    key = _FAKE_OPENAI_PROJ_KEY
    result = _sanitize(f"API call with {key}")
    assert key not in result
    assert "[REDACTED]" in result


def test_sanitize_bearer_token():
    jwt = _FAKE_JWT
    result = _sanitize(f"Authorization: Bearer {jwt}")
    assert jwt not in result
    assert "[REDACTED]" in result


def test_sanitize_authorization_header():
    result = _sanitize("Sending header Authorization: Token abc123secretxyz")
    assert "abc123secretxyz" not in result
    assert "[REDACTED]" in result


def test_sanitize_password_field():
    result = _sanitize("Connecting with password=supersecret123")
    assert "supersecret123" not in result
    assert "[REDACTED]" in result


def test_sanitize_api_key_field():
    result = _sanitize("weather api_key=a1b2c3d4e5f6g7h8")
    assert "a1b2c3d4e5f6g7h8" not in result
    assert "[REDACTED]" in result


def test_sanitize_client_secret_field():
    result = _sanitize("spotify client_secret: xyzSpotifySecretABC")
    assert "xyzSpotifySecretABC" not in result
    assert "[REDACTED]" in result


def test_sanitize_db_url():
    result = _sanitize("Connecting to postgresql://darkbot:hunter2@db:5432/darkbot")
    assert "hunter2" not in result
    assert "[REDACTED]" in result
    assert "@db:5432" in result


def test_sanitize_clean_message_unchanged():
    msg = "Command !ping executed by user#1234 in guild MyServer"
    assert _sanitize(msg) == msg


def test_sanitize_redacts_in_buffer(owner_cog):
    owner_cog.logger.error("DB error password=topsecret reason=timeout")
    entries = owner_cog.bot.log_buffer.get_entries(1)
    assert "topsecret" not in entries[0]
    assert "[REDACTED]" in entries[0]
