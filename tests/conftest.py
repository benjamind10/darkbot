import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses


@pytest.fixture
def mock_db_pool():
    cursor = AsyncMock()

    cursor_context = MagicMock()
    cursor_context.__aenter__ = AsyncMock(return_value=cursor)
    cursor_context.__aexit__ = AsyncMock(return_value=None)

    connection = MagicMock()
    connection.cursor.return_value = cursor_context
    connection.commit = AsyncMock()
    connection.rollback = AsyncMock()

    connection_context = MagicMock()
    connection_context.__aenter__ = AsyncMock(return_value=connection)
    connection_context.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.connection.return_value = connection_context
    pool.connection_obj = connection
    pool.cursor = cursor

    return pool


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock(return_value=None)
    return redis


@pytest_asyncio.fixture
async def mock_http_session():
    with aioresponses() as mocked:
        async with aiohttp.ClientSession() as session:
            yield SimpleNamespace(session=session, mocked=mocked)


@pytest_asyncio.fixture
async def bot(mock_db_pool, mock_http_session, mock_redis):
    yield SimpleNamespace(
        config=SimpleNamespace(
            services=SimpleNamespace(ip_info=None, ksoft_api=None, bgg_cookie=None)
        ),
        db_pool=mock_db_pool,
        embed_color=0x5865F2,
        http_session=mock_http_session.session,
        logger=logging.getLogger("tests.bot"),
        redis=mock_redis,
        redis_manager=mock_redis,
    )
