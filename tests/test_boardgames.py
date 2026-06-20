import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import aiohttp

from bot.utils.boardgames import (
    BASE_URL,
    fetch_bgg_collection,
    parse_bgg_collection,
    process_bgg_users,
    set_bgg_private,
)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_sends_cookie_header(mock_http_session):
    username = "DadDialTone"
    url = f"{BASE_URL}collection/{username}?stats=1"
    seen_headers = {}

    def _callback(url_obj, **kwargs):
        seen_headers.update(kwargs.get("headers", {}))
        return {
            "status": 200,
            "body": "<items></items>",
        }

    mock_http_session.mocked.get(url, callback=_callback)

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        cookie_value="bb=session-token; foo=bar",
        max_attempts=1,
    )

    assert status == 200
    assert res == "<items></items>"
    assert seen_headers.get("Cookie") == "bb=session-token; foo=bar"


@pytest.mark.asyncio
async def test_fetch_bgg_collection_401_logs_and_returns_none(caplog, mock_http_session):
    caplog.set_level(logging.DEBUG)
    username = "DadDialTone"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=401, body=b"Unauthorized")
    res, status = await fetch_bgg_collection(
        username, logging.getLogger("test"), mock_http_session.session, max_attempts=3
    )

    assert res is None and status == 401
    assert any("Authorization error fetching BGG" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_202_returns_last_status(mock_http_session, monkeypatch):
    username = "QueuedUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=202, body=b"Queued")
    sleep = AsyncMock()
    monkeypatch.setattr("bot.utils.boardgames.asyncio.sleep", sleep)

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        max_attempts=1,
    )

    assert res is None and status == 202
    sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_429_respects_retry_after(mock_http_session, monkeypatch):
    username = "RateLimitedUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(
        url, status=429, body=b"Too Many Requests", headers={"Retry-After": "7"}
    )
    sleep = AsyncMock()
    monkeypatch.setattr("bot.utils.boardgames.asyncio.sleep", sleep)

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        max_attempts=1,
    )

    assert res is None and status == 429
    sleep.assert_awaited_once_with(7.0)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_5xx_returns_last_status(mock_http_session, monkeypatch):
    username = "ServerErrorUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=503, body=b"Unavailable")
    sleep = AsyncMock()
    monkeypatch.setattr("bot.utils.boardgames.asyncio.sleep", sleep)

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        max_attempts=1,
    )

    assert res is None and status == 503
    sleep.assert_awaited_once_with(2.0)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_client_error_returns_last_status(mock_http_session, monkeypatch):
    username = "ClientErrorUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, exception=aiohttp.ClientError("boom"))
    sleep = AsyncMock()
    monkeypatch.setattr("bot.utils.boardgames.asyncio.sleep", sleep)

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        max_attempts=1,
    )

    assert res is None and status is None
    sleep.assert_awaited_once_with(2.0)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_unexpected_status_returns_status(mock_http_session):
    username = "UnexpectedUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=418, body=b"Teapot")

    res, status = await fetch_bgg_collection(
        username,
        logging.getLogger("test"),
        mock_http_session.session,
        max_attempts=3,
    )

    assert res is None and status == 418


def test_parse_bgg_collection_normal_item():
    xml_data = """
    <items>
      <item objectid="123">
        <name>Terraforming Mars</name>
        <status own="1" prevowned="0" fortrade="0" want="0" wanttoplay="1" wanttobuy="0" wishlist="0" preordered="0" />
        <stats minplayers="1" maxplayers="5" minplaytime="120" maxplaytime="120">
          <rating><average value="8.42" /></rating>
        </stats>
        <numplays>17</numplays>
      </item>
    </items>
    """

    items = parse_bgg_collection(xml_data)

    assert items == [
        {
            "name": "Terraforming Mars",
            "bggid": "123",
            "avgrating": 8.42,
            "own": True,
            "prevowned": False,
            "fortrade": False,
            "want": False,
            "wanttoplay": True,
            "wanttobuy": False,
            "wishlist": False,
            "preordered": False,
            "minplayers": 1,
            "maxplayers": 5,
            "minplaytime": 120,
            "maxplaytime": 120,
            "numplays": 17,
        }
    ]


def test_parse_bgg_collection_missing_optional_fields():
    xml_data = """
    <items>
      <item objectid="456">
        <name>Unknown Horizons</name>
      </item>
    </items>
    """

    items = parse_bgg_collection(xml_data)

    assert items == [
        {
            "name": "Unknown Horizons",
            "bggid": "456",
            "avgrating": 0.0,
            "own": False,
            "prevowned": False,
            "fortrade": False,
            "want": False,
            "wanttoplay": False,
            "wanttobuy": False,
            "wishlist": False,
            "preordered": False,
            "minplayers": 0,
            "maxplayers": 0,
            "minplaytime": 0,
            "maxplaytime": 0,
            "numplays": 0,
        }
    ]


def test_parse_bgg_collection_malformed_xml():
    assert parse_bgg_collection("<items><item></items>") == []


@pytest.mark.asyncio
async def test_bgg_collection_command_private_message(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 403)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection(ctx, "PrivateUser")

    send.assert_awaited_once()
    assert "appears private" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_bgg_collection_command_queued_message(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 202)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection(ctx, "QueuedUser")

    send.assert_awaited_once()
    assert "being prepared" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_bgg_collection_command_malformed_response_message(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 500)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection(ctx, "BrokenUser")

    send.assert_awaited_once_with(ctx, "Failed to fetch collection.")


@pytest.mark.asyncio
async def test_set_bgg_private_calls_sql_helper(mock_db_pool):
    await set_bgg_private(mock_db_pool, logging.getLogger("test"), 42)

    mock_db_pool.connection.assert_called_once()
    mock_db_pool.connection_obj.cursor.assert_called_once()
    mock_db_pool.connection_obj.commit.assert_not_called()
    mock_db_pool.connection_obj.cursor.return_value.__aenter__.return_value.execute.assert_awaited_once_with(
        "SELECT set_bgg_private(%s, %s);",
        (42, True),
    )


@pytest.mark.asyncio
async def test_process_bgg_users_marks_private_accounts_via_helper(mock_db_pool, mock_http_session, monkeypatch):
    username = "PrivateUser"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=401, body=b"Unauthorized")
    connection_cursor = mock_db_pool.connection_obj.cursor.return_value.__aenter__.return_value
    connection_cursor.fetchall.return_value = [(7, username)]

    called = []

    async def _fake_set_bgg_private(db_pool, logger, user_id, is_private=True):
        called.append((db_pool, user_id, is_private))

    monkeypatch.setattr("bot.utils.boardgames.set_bgg_private", _fake_set_bgg_private)

    await process_bgg_users(mock_db_pool, mock_http_session.session, logging.getLogger("test"))

    assert called == [(mock_db_pool, 7, True)]
    connection_cursor.execute.assert_any_await("SELECT id, bgguser FROM get_all_bggusers();")
    connection_cursor.fetchall.assert_awaited_once()
    assert connection_cursor.execute.await_count == 1
