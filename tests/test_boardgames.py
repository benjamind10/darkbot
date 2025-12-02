import asyncio
import logging

import pytest
from aioresponses import aioresponses

from bot.utils.boardgames import fetch_bgg_collection, BASE_URL


@pytest.mark.asyncio
async def test_fetch_bgg_collection_401_logs_and_returns_none(caplog):
    caplog.set_level(logging.DEBUG)
    username = "DadDialTone"
    url = f"{BASE_URL}collection/{username}?stats=1"

    with aioresponses() as mocked:
        mocked.get(url, status=401, body=b"Unauthorized")

        res, status = await fetch_bgg_collection(
            username, logging.getLogger("test"), max_attempts=1
        )

    assert res is None and status == 401
    assert any("Authorization error fetching BGG" in r.message for r in caplog.records)
