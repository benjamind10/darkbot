import logging

import aiohttp
import pytest
from aioresponses import aioresponses

from bot.utils.boardgames import BASE_URL, fetch_bgg_collection


@pytest.mark.asyncio
async def test_fetch_bgg_collection_401_logs_and_returns_none(caplog):
    caplog.set_level(logging.DEBUG)
    username = "DadDialTone"
    url = f"{BASE_URL}collection/{username}?stats=1"

    with aioresponses() as mocked:
        mocked.get(url, status=401, body=b"Unauthorized")

        async with aiohttp.ClientSession() as session:
            res, status = await fetch_bgg_collection(
                username, logging.getLogger("test"), session, max_attempts=1
            )

    assert res is None and status == 401
    assert any("Authorization error fetching BGG" in r.message for r in caplog.records)
