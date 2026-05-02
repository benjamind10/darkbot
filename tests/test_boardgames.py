import logging

import pytest

from bot.utils.boardgames import BASE_URL, fetch_bgg_collection


@pytest.mark.asyncio
async def test_fetch_bgg_collection_401_logs_and_returns_none(caplog, mock_http_session):
    caplog.set_level(logging.DEBUG)
    username = "DadDialTone"
    url = f"{BASE_URL}collection/{username}?stats=1"

    mock_http_session.mocked.get(url, status=401, body=b"Unauthorized")
    res, status = await fetch_bgg_collection(
        username, logging.getLogger("test"), mock_http_session.session, max_attempts=1
    )

    assert res is None and status == 401
    assert any("Authorization error fetching BGG" in r.message for r in caplog.records)
