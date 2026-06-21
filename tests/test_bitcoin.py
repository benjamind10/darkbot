import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.cogs.Utility import Utility
from bot.utils import bitcoin as bitcoin_utils
from discord.ext import commands


class FakeConverter:
    def __init__(self, price=None, error=None):
        self.price = price
        self.error = error
        self.calls = []

    def get_latest_price(self, currency):
        self.calls.append(currency)
        if self.error is not None:
            raise self.error
        return self.price

    def convert_to_btc(self, amount, currency):
        self.calls.append((amount, currency))
        if self.error is not None:
            raise self.error
        return self.price


@pytest.mark.asyncio
async def test_get_bitcoin_price_normalizes_currency(monkeypatch):
    fake = FakeConverter(price=12345.678)
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    result = await bitcoin_utils.get_bitcoin_price("cad")

    assert result.currency == "CAD"
    assert result.price == 12345.678
    assert fake.calls == ["CAD"]


@pytest.mark.asyncio
async def test_get_bitcoin_price_invalid_currency(monkeypatch):
    fake = FakeConverter(error=ValueError("bad currency"))
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    with pytest.raises(bitcoin_utils.InvalidBitcoinCurrencyError):
        await bitcoin_utils.get_bitcoin_price("usd")


@pytest.mark.asyncio
async def test_get_bitcoin_price_provider_failure(monkeypatch):
    fake = FakeConverter(error=OSError("dns failure"))
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    with pytest.raises(bitcoin_utils.BitcoinProviderError):
        await bitcoin_utils.get_bitcoin_price("usd")


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_success(monkeypatch):
    fake = FakeConverter(price=0.01234567)
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    result = await bitcoin_utils.convert_currency_to_bitcoin("10", "cad")

    assert result.amount == 10.0
    assert result.currency == "CAD"
    assert result.bitcoin == 0.0123
    assert fake.calls == [(10.0, "CAD")]


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_invalid_amount(monkeypatch):
    fake = FakeConverter(price=0.1)
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    with pytest.raises(ValueError):
        await bitcoin_utils.convert_currency_to_bitcoin("abc", "cad")


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_invalid_currency(monkeypatch):
    fake = FakeConverter(error=ValueError("bad currency"))
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    with pytest.raises(bitcoin_utils.InvalidBitcoinCurrencyError):
        await bitcoin_utils.convert_currency_to_bitcoin("10", "usd")


@pytest.mark.asyncio
async def test_convert_currency_to_bitcoin_provider_failure(monkeypatch):
    fake = FakeConverter(error=RuntimeError("boom"))
    monkeypatch.setattr(bitcoin_utils, "BtcConverter", lambda: fake)

    with pytest.raises(bitcoin_utils.BitcoinProviderError):
        await bitcoin_utils.convert_currency_to_bitcoin("10", "usd")


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

    await cog.bitcoin(ctx, "cad")

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

    await cog.bitcoin(ctx, "usd")

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

    await cog.bitcoin(ctx, "usd")

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

    await cog.currency_to_bitcoin(ctx, "10", "cad")

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

    await cog.currency_to_bitcoin_error(ctx, commands.MissingRequiredArgument(param=SimpleNamespace(name="amount")))

    send.assert_awaited_once()
    embed = send.await_args.kwargs["embed"]
    assert embed.title == "→ Invalid Argument!"
    assert "Pro Tip" in embed.description
