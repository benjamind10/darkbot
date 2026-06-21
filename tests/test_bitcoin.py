import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest

from bot.cogs.Utility import Utility
from discord.ext import commands
from utils import bitcoin as bitcoin_utils


def coingecko_url(currency):
    return f"{bitcoin_utils.COINGECKO_SIMPLE_PRICE_URL}?ids=bitcoin&vs_currencies={currency}"


def coinbase_url():
    return f"{bitcoin_utils.COINBASE_EXCHANGE_RATES_URL}?currency=BTC"


def mock_bitcoin_price(mock_http_session, currency, price):
    mock_http_session.mocked.get(coingecko_url(currency), payload={"bitcoin": {currency: price}})


def mock_coinbase_price(mock_http_session, currency, price):
    mock_http_session.mocked.get(
        coinbase_url(), payload={"data": {"currency": "BTC", "rates": {currency: price}}}
    )


@pytest.mark.asyncio
async def test_get_bitcoin_price_normalizes_currency(mock_http_session):
    mock_bitcoin_price(mock_http_session, "cad", 12345.678)

    result = await bitcoin_utils.get_bitcoin_price("cad", mock_http_session.session)

    assert result.currency == "CAD"
    assert result.price == 12345.678


@pytest.mark.asyncio
async def test_get_bitcoin_price_invalid_currency(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("usd"), payload={"bitcoin": {}})
    mock_http_session.mocked.get(coinbase_url(), payload={"data": {"rates": {}}})

    with pytest.raises(bitcoin_utils.InvalidBitcoinCurrencyError):
        await bitcoin_utils.get_bitcoin_price("usd", mock_http_session.session)


@pytest.mark.asyncio
async def test_get_bitcoin_price_provider_failure(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("usd"), exception=aiohttp.ClientError("dns failure"))
    mock_http_session.mocked.get(coinbase_url(), status=503)

    with pytest.raises(bitcoin_utils.BitcoinProviderError) as exc_info:
        await bitcoin_utils.get_bitcoin_price("usd", mock_http_session.session)

    assert "dns failure" in str(exc_info.value)
    assert "coinbase returned HTTP 503" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_bitcoin_price_falls_back_to_coinbase(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("usd"), status=503)
    mock_coinbase_price(mock_http_session, "USD", "12345.67")

    result = await bitcoin_utils.get_bitcoin_price("usd", mock_http_session.session)

    assert result.currency == "USD"
    assert result.price == 12345.67


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_success(mock_http_session):
    mock_bitcoin_price(mock_http_session, "cad", 1000)

    result = await bitcoin_utils.convert_currency_to_bitcoin(
        "10", "cad", mock_http_session.session
    )

    assert result.amount == 10.0
    assert result.currency == "CAD"
    assert result.bitcoin == 0.01


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_invalid_amount(mock_http_session):
    with pytest.raises(ValueError):
        await bitcoin_utils.convert_currency_to_bitcoin(
            "abc", "cad", mock_http_session.session
        )


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_invalid_currency(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("usd"), payload={"bitcoin": {}})
    mock_http_session.mocked.get(coinbase_url(), payload={"data": {"rates": {}}})

    with pytest.raises(bitcoin_utils.InvalidBitcoinCurrencyError):
        await bitcoin_utils.convert_currency_to_bitcoin(
            "10", "usd", mock_http_session.session
        )


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_provider_failure(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("usd"), status=503)
    mock_http_session.mocked.get(coinbase_url(), status=503)

    with pytest.raises(bitcoin_utils.BitcoinProviderError):
        await bitcoin_utils.convert_currency_to_bitcoin(
            "10", "usd", mock_http_session.session
        )


@pytest.mark.asyncio
async def test_bitcoin_command_uses_helper_and_formats_embed(bot, monkeypatch):
    cog = Utility(bot)
    ctx = SimpleNamespace(interaction=None, author=SimpleNamespace(name="Tester"))
    bot.logger = logging.getLogger("test")

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    monkeypatch.setattr(
        "bot.cogs.Utility.get_bitcoin_price",
        AsyncMock(return_value=bitcoin_utils.BitcoinLookupResult(currency="CAD", price=12345.678)),
    )

    await cog.bitcoin.callback(cog, ctx, "cad")

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ BTC to Currency"
    assert "12345.68" in embed.description
    assert "CAD" in embed.description


@pytest.mark.asyncio
async def test_bitcoin_command_handles_invalid_currency(bot, monkeypatch):
    cog = Utility(bot)
    ctx = SimpleNamespace(interaction=None, author=SimpleNamespace(name="Tester"))
    bot.logger = logging.getLogger("test")

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    monkeypatch.setattr(
        "bot.cogs.Utility.get_bitcoin_price",
        AsyncMock(side_effect=bitcoin_utils.InvalidBitcoinCurrencyError("usd")),
    )

    await cog.bitcoin.callback(cog, ctx, "usd")

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ Currency error!"
    assert "Not a valid currency type!" in embed.description


@pytest.mark.asyncio
async def test_bitcoin_command_handles_provider_failure(bot, monkeypatch):
    cog = Utility(bot)
    ctx = SimpleNamespace(interaction=None, author=SimpleNamespace(name="Tester"))
    bot.logger = logging.getLogger("test")

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    monkeypatch.setattr(
        "bot.cogs.Utility.get_bitcoin_price",
        AsyncMock(side_effect=bitcoin_utils.BitcoinProviderError("bitcoin price lookup failed")),
    )

    await cog.bitcoin.callback(cog, ctx, "usd")

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ Currency error!"
    assert "unavailable right now" in embed.description


@pytest.mark.asyncio
async def test_currency_to_bitcoin_command_uses_helper(bot, monkeypatch):
    cog = Utility(bot)
    ctx = SimpleNamespace(interaction=None, author=SimpleNamespace(name="Tester"))
    bot.logger = logging.getLogger("test")

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    monkeypatch.setattr(
        "bot.cogs.Utility.convert_currency_to_bitcoin",
        AsyncMock(
            return_value=bitcoin_utils.BitcoinConversionResult(amount=10.0, currency="CAD", bitcoin=0.0123)
        ),
    )

    await cog.currency_to_bitcoin.callback(cog, ctx, "10", "cad")

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ Currency To Bitcoin!"
    assert "10.0 CAD" in embed.description
    assert "0.0123 Bitcoin" in embed.description


@pytest.mark.asyncio
async def test_currency_to_bitcoin_error_missing_argument(bot, monkeypatch):
    cog = Utility(bot)
    ctx = SimpleNamespace(interaction=None, author=SimpleNamespace(name="Tester"))
    bot.logger = logging.getLogger("test")

    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)

    param = SimpleNamespace(name="amount", displayed_name=None)
    await cog.currency_to_bitcoin_error(ctx, commands.MissingRequiredArgument(param=param))

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ Invalid Argument!"
    assert "Pro Tip" in embed.description
