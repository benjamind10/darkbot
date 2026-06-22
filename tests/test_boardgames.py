import logging
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import aiohttp
from aioresponses import CallbackResult

from bot.utils.boardgames import (
    BASE_URL,
    API2_BASE_URL,
    BGG_API_HEADERS,
    BGG_BROWSER_HEADERS,
    BGG_USER_AGENT,
    HTML_BASE_URL,
    SET_BGG_PRIVATE_SQL,
    build_bgg_lookup_headers,
    fetch_bgg_collection,
    fetch_bgg_thing,
    score_bgg_search_result,
    select_bgg_search_result,
    search_bgg_games,
    parse_bgg_search,
    parse_bgg_search_html,
    parse_bgg_thing,
    parse_bgg_collection,
    process_bgg_users,
    set_bgg_private,
)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_sends_cookie_header(mock_http_session):
    username = "DadDialTone"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")
    seen_headers = {}
    seen_params = {}

    def _callback(url_obj, **kwargs):
        seen_headers.update(kwargs.get("headers", {}))
        seen_params.update(kwargs.get("params", {}))
        return CallbackResult(status=200, body="<items></items>")

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
    assert seen_headers.get("User-Agent") == BGG_USER_AGENT
    assert seen_params == {"username": username, "stats": 1, "subtype": "boardgame", "showprivate": 1}


@pytest.mark.asyncio
async def test_fetch_bgg_collection_401_logs_and_returns_none(caplog, mock_http_session):
    caplog.set_level(logging.DEBUG)
    username = "DadDialTone"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

    mock_http_session.mocked.get(url, status=401, body=b"Unauthorized")
    res, status = await fetch_bgg_collection(
        username, logging.getLogger("test"), mock_http_session.session, max_attempts=3
    )

    assert res is None and status == 401
    assert any("Authorization error fetching BGG" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_fetch_bgg_collection_202_returns_last_status(mock_http_session, monkeypatch):
    username = "QueuedUser"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

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
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

    mock_http_session.mocked.get(url, status=429, body=b"Too Many Requests", headers={"Retry-After": "7"})
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
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

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
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

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
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

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
        <name value="Terraforming Mars" />
        <status own="1" prevowned="0" fortrade="0" want="0" wanttoplay="1" wanttobuy="0" wishlist="0" preordered="0" />
        <stats minplayers="1" maxplayers="5" minplaytime="120" maxplaytime="120">
          <rating value="8.42" />
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
        <name value="Unknown Horizons" />
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


@pytest.mark.asyncio
async def test_bgg_collection_command_uses_api2_collection_xml(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    xml_data = """
    <items>
      <item objectid="123">
        <name value="Terraforming Mars" />
        <status own="1" prevowned="0" fortrade="0" want="0" wanttoplay="1" wanttobuy="0" wishlist="0" preordered="0" />
        <stats minplayers="1" maxplayers="5" minplaytime="120" maxplaytime="120">
          <rating value="8.42" />
        </stats>
        <numplays>17</numplays>
      </item>
    </items>
    """
    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username=Terraformer.*"),
        status=200,
        body=xml_data,
    )

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection.callback(cog, ctx, "Terraformer")

    assert send.await_count == 1
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "Terraformer's BGG Collection (Page 1 of 1)"
    assert "Terraforming Mars (ID: 123" in embed.description


def test_parse_bgg_collection_malformed_xml():
    assert parse_bgg_collection("<items><item></items>") == []


def test_parse_bgg_search_normalizes_api2_items():
    xml_data = """
    <items total='1'>
      <item type='boardgame' id='13'>
        <name type='primary' value='Catan' />
        <yearpublished value='1995' />
      </item>
    </items>
    """

    assert parse_bgg_search(xml_data) == [
        {"bggid": "13", "type": "boardgame", "name": "Catan", "yearpublished": "1995"}
    ]


def test_parse_bgg_search_html_normalizes_search_page_items():
    html_data = """
    <div id='results_objectname1'>
      <a href="/boardgame/1406/monopoly" class='primary'>Monopoly</a>
      <span class='smallerfont dull'>(1935)</span>
    </div>
    <div id='results_objectname2'>
      <a href="/boardgame/40398/monopoly-deal-card-game" class='primary'>Monopoly Deal Card Game</a>
      <span class='smallerfont dull'>(2008)</span>
    </div>
    """

    assert parse_bgg_search_html(html_data) == [
        {"bggid": "1406", "type": "boardgame", "name": "Monopoly", "yearpublished": "1935"},
        {"bggid": "40398", "type": "boardgame", "name": "Monopoly Deal Card Game", "yearpublished": "2008"},
    ]


def test_select_bgg_search_result_prefers_exact_title_match():
    games = [
        {"bggid": "999", "name": "Monopoly: The Card Game", "yearpublished": "2006"},
        {"bggid": "1406", "name": "Monopoly", "yearpublished": "1935"},
    ]

    selected = select_bgg_search_result("Monopoly", games)

    assert selected is not None
    assert selected["bggid"] == "1406"
    assert score_bgg_search_result("Monopoly", games[1]) > score_bgg_search_result("Monopoly", games[0])


def test_select_bgg_search_result_penalizes_expansions():
    games = [
        {"bggid": "1", "type": "boardgameexpansion", "name": "Catan: Seafarers", "yearpublished": "1997"},
        {"bggid": "2", "type": "boardgame", "name": "Catan", "yearpublished": "1995"},
    ]

    selected = select_bgg_search_result("Catan", games)

    assert selected is not None
    assert selected["bggid"] == "2"


def test_parse_bgg_thing_normalizes_api2_details():
    xml_data = """
    <items termsofuse='...'>
      <item type='boardgame' id='13'>
        <name type='primary' value='Catan' />
        <yearpublished value='1995' />
        <minage value='10' />
        <statistics>
          <ratings>
            <usersrated value='12345' />
            <average value='7.1234' />
          </ratings>
        </statistics>
        <poll name='suggested_numplayers'>
          <results numplayers='3'>
            <result value='Best' numvotes='42' />
          </results>
        </poll>
      </item>
    </items>
    """

    assert parse_bgg_thing(xml_data) == {
        "bggid": "13",
        "name": "Catan",
        "yearpublished": "1995",
        "minage": "10",
        "users_rated": "12345",
        "avg_rating": "7.12",
        "best_count": "3",
    }


@pytest.mark.asyncio
async def test_search_boardgame_uses_api2_search(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    search_params = {}
    search_headers = {}
    thing_params = {}
    thing_headers = {}

    def _callback(url_obj, **kwargs):
        search_params.update(kwargs.get("params", {}))
        search_headers.update(kwargs.get("headers", {}))
        return CallbackResult(
            status=200,
            body="""
            <items total='1'>
              <item type='boardgame' id='13'>
                <name type='primary' value='Catan' />
                <yearpublished value='1995' />
              </item>
            </items>
            """,
        )

    def _thing_callback(url_obj, **kwargs):
        thing_params.update(kwargs.get("params", {}))
        thing_headers.update(kwargs.get("headers", {}))
        return CallbackResult(
            status=200,
            body="""
            <items>
              <item type='boardgame' id='13'>
                <name type='primary' value='Catan' />
                <yearpublished value='1995' />
                <minage value='10' />
                <statistics>
                  <ratings>
                    <usersrated value='12345' />
                    <average value='7.1234' />
                  </ratings>
                </statistics>
                <poll name='suggested_numplayers'>
                  <results numplayers='3'>
                    <result value='Best' numvotes='42' />
                  </results>
                </poll>
              </item>
            </items>
            """,
        )

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}search\?.*"), callback=_callback)
    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"), callback=_thing_callback)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.search_boardgame.callback(cog, ctx, search_query="Catan")

    assert search_params == {"query": "Catan"}
    assert search_headers.get("User-Agent") == BGG_USER_AGENT
    assert thing_params == {"id": "13", "stats": 1}
    assert thing_headers["Accept"] == BGG_API_HEADERS["Accept"]
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "**Catan**"
    assert "**Best Player Count:** 3" in embed.description


@pytest.mark.asyncio
async def test_search_boardgame_falls_back_to_html_search_on_api2_401(
    bot, mock_http_session, monkeypatch
):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    seen_params = {}
    seen_headers = {}
    thing_params = {}

    def _callback(url_obj, **kwargs):
        seen_params.update(kwargs.get("params", {}))
        seen_headers.update(kwargs.get("headers", {}))
        return CallbackResult(
            status=200,
            body="""
            <div id='results_objectname1'>
              <a href="/boardgame/1406/monopoly" class='primary'>Monopoly</a>
              <span class='smallerfont dull'>(1935)</span>
            </div>
            """,
        )

    def _thing_callback(url_obj, **kwargs):
        thing_params.update(kwargs.get("params", {}))
        return CallbackResult(
            status=200,
            body="""
            <items>
              <item type='boardgame' id='1406'>
                <name type='primary' value='Monopoly' />
                <yearpublished value='1935' />
                <minage value='8' />
                <statistics>
                  <ratings>
                    <usersrated value='999' />
                    <average value='4.1234' />
                  </ratings>
                </statistics>
                <poll name='suggested_numplayers'>
                  <results numplayers='4'>
                    <result value='Best' numvotes='15' />
                  </results>
                </poll>
              </item>
            </items>
            """,
        )

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}search\?.*"), status=401)
    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(HTML_BASE_URL)}search/boardgame\?.*"), callback=_callback
    )
    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"), callback=_thing_callback)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.search_boardgame.callback(cog, ctx, search_query="Monopoly")

    assert seen_params == {"q": "Monopoly"}
    assert seen_headers == BGG_BROWSER_HEADERS
    assert thing_params == {"id": "1406", "stats": 1}
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "**Monopoly**"


@pytest.mark.asyncio
async def test_search_boardgame_preserves_results_when_top_detail_lookup_fails(
    bot, monkeypatch
):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.search_bgg_games",
        AsyncMock(
            return_value=(
                [
                    {"bggid": "1406", "name": "Monopoly", "yearpublished": "1935"},
                    {"bggid": "13", "name": "Catan", "yearpublished": "1995"},
                ],
                "html",
                200,
            )
        ),
    )
    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_thing",
        AsyncMock(return_value=(None, 403)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.search_boardgame.callback(cog, ctx, search_query="Monopoly")

    embed = send.await_args.kwargs["embed"]
    assert embed.title == "Top 5 search results for 'Monopoly'"
    assert embed.fields[0].name == "Monopoly (1935)"
    assert embed.footer.text == "Could not fetch details for the top result."


@pytest.mark.asyncio
async def test_search_boardgame_selects_best_match_even_if_not_first(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.search_bgg_games",
        AsyncMock(
            return_value=(
                [
                    {"bggid": "999", "name": "Monopoly: The Card Game", "yearpublished": "2006"},
                    {"bggid": "1406", "name": "Monopoly", "yearpublished": "1935"},
                ],
                "html",
                200,
            )
        ),
    )
    seen_id = {}

    async def _fake_fetch(session, game_id, logger, cookie_value=None):
        seen_id["value"] = game_id
        return (
            {
                "bggid": "1406",
                "name": "Monopoly",
                "yearpublished": "1935",
                "minage": "8",
                "users_rated": "999",
                "avg_rating": "4.12",
                "best_count": "4",
            },
            200,
        )

    monkeypatch.setattr("bot.cogs.BoardGames.bg_utils.fetch_bgg_thing", _fake_fetch)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.search_boardgame.callback(cog, ctx, search_query="Monopoly")

    assert seen_id["value"] == "1406"
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "**Monopoly**"


@pytest.mark.asyncio
async def test_search_bgg_games_returns_html_results_after_api2_401(mock_http_session):
    html_params = {}

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}search\?.*"), status=401)

    def _html_callback(url_obj, **kwargs):
        html_params.update(kwargs.get("params", {}))
        return CallbackResult(
            status=200,
            body="""
            <div id='results_objectname1'>
              <a href=\"/boardgame/1406/monopoly\" class='primary'>Monopoly</a>
              <span class='smallerfont dull'>(1935)</span>
            </div>
            """,
        )

    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(HTML_BASE_URL)}search/boardgame\?.*"), callback=_html_callback
    )

    games, source, status = await search_bgg_games(
        mock_http_session.session, "Monopoly", logging.getLogger("test")
    )

    assert status == 200
    assert source == "html"
    assert games[0]["bggid"] == "1406"
    assert html_params == {"q": "Monopoly"}


@pytest.mark.asyncio
async def test_boardgame_info_uses_api2_thing(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    seen_params = {}
    seen_headers = {}

    def _callback(url_obj, **kwargs):
        seen_params.update(kwargs.get("params", {}))
        seen_headers.update(kwargs.get("headers", {}))
        return CallbackResult(
            status=200,
            body="""
            <items>
              <item type='boardgame' id='13'>
                <name type='primary' value='Catan' />
                <yearpublished value='1995' />
                <minage value='10' />
                <statistics>
                  <ratings>
                    <usersrated value='12345' />
                    <average value='7.1234' />
                  </ratings>
                </statistics>
                <poll name='suggested_numplayers'>
                  <results numplayers='3'>
                    <result value='Best' numvotes='42' />
                  </results>
                </poll>
              </item>
            </items>
            """,
        )

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"), callback=_callback)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.boardgame_info.callback(cog, ctx, "13")

    assert seen_params == {"id": "13", "stats": 1}
    assert seen_headers == BGG_API_HEADERS
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "**Catan**"
    assert "**Published:** 1995" in embed.description
    assert "**Best Player Count:** 3" in embed.description


@pytest.mark.asyncio
async def test_boardgame_info_retries_with_cookie_on_401(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie="bb=session-token"))

    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"),
        status=401,
        body="Unauthorized",
    )
    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"),
        status=200,
        body="""
        <items>
          <item type='boardgame' id='13'>
            <name type='primary' value='Catan' />
            <yearpublished value='1995' />
            <minage value='10' />
            <statistics>
              <ratings>
                <usersrated value='12345' />
                <average value='7.1234' />
              </ratings>
            </statistics>
            <poll name='suggested_numplayers'>
              <results numplayers='3'>
                <result value='Best' numvotes='42' />
              </results>
            </poll>
          </item>
        </items>
        """,
    )

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.boardgame_info.callback(cog, ctx, "13")

    embed = send.await_args.kwargs["embed"]
    assert embed.title == "**Catan**"


@pytest.mark.asyncio
async def test_boardgame_info_reports_friendly_failure_when_lookup_unavailable(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_thing",
        AsyncMock(return_value=(None, 403)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.boardgame_info.callback(cog, ctx, "13")

    send.assert_awaited_once()
    assert "Failed to retrieve game info for 13" in send.await_args.args[1]


def test_build_bgg_lookup_headers_uses_public_api_headers():
    assert build_bgg_lookup_headers() == BGG_API_HEADERS


def test_build_bgg_lookup_headers_adds_cookie_when_present():
    headers = build_bgg_lookup_headers("bb=session-token")

    assert headers["Cookie"] == "bb=session-token"
    assert headers["User-Agent"] == BGG_API_HEADERS["User-Agent"]


@pytest.mark.asyncio
async def test_fetch_bgg_thing_uses_public_request_shape(mock_http_session):
    game_id = "13"
    seen_params = {}
    seen_headers = {}

    def _callback(url_obj, **kwargs):
        seen_params.update(kwargs.get("params", {}))
        seen_headers.update(kwargs.get("headers", {}))
        return CallbackResult(
            status=200,
            body="""
            <items>
              <item type='boardgame' id='13'>
                <name type='primary' value='Catan' />
              </item>
            </items>
            """,
        )

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"), callback=_callback)

    game, status = await fetch_bgg_thing(
        mock_http_session.session,
        game_id,
        logging.getLogger("test"),
    )

    assert status == 200
    assert game is not None
    assert game["name"] == "Catan"
    assert seen_params == {"id": game_id, "stats": 1}
    assert seen_headers == BGG_API_HEADERS


@pytest.mark.asyncio
async def test_fetch_bgg_thing_retries_once_with_cookie_on_401(mock_http_session):
    game_id = "13"

    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"),
        status=401,
        body="Unauthorized",
    )
    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"),
        status=200,
        body="""
        <items>
          <item type='boardgame' id='13'>
            <name type='primary' value='Catan' />
          </item>
        </items>
        """,
    )

    game, status = await fetch_bgg_thing(
        mock_http_session.session,
        game_id,
        logging.getLogger("test"),
        cookie_value="bb=session-token",
    )

    assert status == 200
    assert game is not None
    assert game["name"] == "Catan"
    recorded = []
    for calls in mock_http_session.mocked.requests.values():
        recorded.extend(calls)
    assert len(recorded) == 2
    assert "Cookie" not in recorded[0].kwargs["headers"]
    assert recorded[1].kwargs["headers"]["Cookie"] == "bb=session-token"


@pytest.mark.asyncio
async def test_fetch_bgg_thing_does_not_retry_without_cookie(mock_http_session):
    game_id = "13"
    call_count = 0

    def _callback(url_obj, **kwargs):
        nonlocal call_count
        call_count += 1
        return CallbackResult(status=403, body="Forbidden")

    mock_http_session.mocked.get(re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"), callback=_callback)

    game, status = await fetch_bgg_thing(
        mock_http_session.session,
        game_id,
        logging.getLogger("test"),
    )

    assert game is None
    assert status == 403
    assert call_count == 1


@pytest.mark.asyncio
async def test_fetch_bgg_thing_returns_none_on_parse_failure_200(mock_http_session):
    game_id = "13"

    mock_http_session.mocked.get(
        re.compile(rf"^{re.escape(API2_BASE_URL)}thing\?.*"),
        status=200,
        body="<items><item></items>",
    )

    game, status = await fetch_bgg_thing(
        mock_http_session.session,
        game_id,
        logging.getLogger("test"),
    )

    assert game is None
    assert status == 200


@pytest.mark.asyncio
async def test_bgg_collection_command_private_message(bot, mock_http_session, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 403)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection.callback(cog, ctx, "PrivateUser")

    send.assert_awaited_once()
    assert "appears private" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_bgg_collection_command_queued_message(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 202)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection.callback(cog, ctx, "QueuedUser")

    send.assert_awaited_once()
    assert "being prepared" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_bgg_collection_command_malformed_response_message(bot, monkeypatch):
    from bot.cogs.BoardGames import BoardGames

    cog = BoardGames(bot)
    ctx = SimpleNamespace(interaction=None, send=AsyncMock())
    bot.logger = logging.getLogger("test")
    bot.config = SimpleNamespace(services=SimpleNamespace(bgg_cookie=None))

    monkeypatch.setattr(
        "bot.cogs.BoardGames.bg_utils.fetch_bgg_collection",
        AsyncMock(return_value=(None, 500)),
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.BoardGames.send_for_context", send)

    await cog.bgg_collection.callback(cog, ctx, "BrokenUser")

    send.assert_awaited_once_with(ctx, "Failed to fetch collection.")


@pytest.mark.asyncio
async def test_set_bgg_private_updates_user_flag(mock_db_pool):
    await set_bgg_private(mock_db_pool, logging.getLogger("test"), 42)

    mock_db_pool.connection.assert_called_once()
    mock_db_pool.connection_obj.cursor.assert_called_once()
    mock_db_pool.connection_obj.commit.assert_not_called()
    mock_db_pool.connection_obj.cursor.return_value.__aenter__.return_value.execute.assert_awaited_once_with(
        SET_BGG_PRIVATE_SQL,
        (True, 42),
    )


@pytest.mark.asyncio
async def test_process_bgg_users_marks_private_accounts_via_helper(mock_db_pool, mock_http_session, monkeypatch):
    username = "PrivateUser"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

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


@pytest.mark.asyncio
async def test_process_bgg_users_does_not_mark_private_when_cookie_is_configured(
    mock_db_pool, mock_http_session, monkeypatch
):
    username = "PrivateUser"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

    mock_http_session.mocked.get(url, status=403, body=b"Forbidden")
    connection_cursor = mock_db_pool.connection_obj.cursor.return_value.__aenter__.return_value
    connection_cursor.fetchall.return_value = [(7, username)]

    called = []

    async def _fake_set_bgg_private(db_pool, logger, user_id, is_private=True):
        called.append((db_pool, user_id, is_private))

    monkeypatch.setattr("bot.utils.boardgames.set_bgg_private", _fake_set_bgg_private)

    await process_bgg_users(
        mock_db_pool,
        mock_http_session.session,
        logging.getLogger("test"),
        cookie_value="bb=session-token",
    )

    assert called == []
    connection_cursor.execute.assert_any_await("SELECT id, bgguser FROM get_all_bggusers();")
    connection_cursor.fetchall.assert_awaited_once()


@pytest.mark.asyncio
async def test_backfill_skips_marking_private_when_cookie_is_configured(
    mock_db_pool, mock_http_session, monkeypatch
):
    from bot.scripts.backfill_bgg_private import _check_user_and_mark

    username = "PrivateUser"
    url = re.compile(rf"^{re.escape(API2_BASE_URL)}collection\?.*username={username}.*")

    mock_http_session.mocked.get(url, status=401, body=b"Unauthorized")

    called = []

    async def _fake_set_bgg_private(db_conn, logger, user_id, is_private=True):
        called.append((db_conn, user_id, is_private))

    monkeypatch.setattr("bot.scripts.backfill_bgg_private.set_bgg_private", _fake_set_bgg_private)

    result = await _check_user_and_mark(
        mock_db_pool.connection_obj,
        mock_http_session.session,
        7,
        username,
        cookie_value="bb=session-token",
        dry_run=False,
    )

    assert result == (7, username, 401, False)
    assert called == []
