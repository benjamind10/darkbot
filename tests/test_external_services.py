"""Tests for the litecoin, currency, weather and ChatGPT integrations."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import httpx
import openai
import pytest

from bot.cogs.Chatgpt import DEFAULT_OPENAI_MODEL, ChatGPT
from bot.cogs.Utility import Utility
from utils import bitcoin as bitcoin_utils
from utils import currency as currency_utils


def coingecko_url(coin_id, currency):
    return f"{bitcoin_utils.COINGECKO_SIMPLE_PRICE_URL}?ids={coin_id}&vs_currencies={currency}"


def coinbase_url(symbol):
    return f"{bitcoin_utils.COINBASE_EXCHANGE_RATES_URL}?currency={symbol}"


def frankfurter_url(base, symbol):
    return f"{currency_utils.FRANKFURTER_LATEST_URL}?base={base}&symbols={symbol}"


def make_ctx():
    return SimpleNamespace(interaction=None, author="tester")


# ---------- litecoin ----------


@pytest.mark.asyncio
async def test_get_crypto_price_litecoin_uses_coingecko(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("litecoin", "usd"), payload={"litecoin": {"usd": 81.5}})

    result = await bitcoin_utils.get_crypto_price(bitcoin_utils.LITECOIN, "usd", mock_http_session.session)

    assert (result.currency, result.price) == ("USD", 81.5)


@pytest.mark.asyncio
async def test_get_crypto_price_litecoin_falls_back_to_coinbase(mock_http_session):
    mock_http_session.mocked.get(coingecko_url("litecoin", "usd"), status=429)
    mock_http_session.mocked.get(coinbase_url("LTC"), payload={"data": {"rates": {"USD": "80.25"}}})

    result = await bitcoin_utils.get_crypto_price(bitcoin_utils.LITECOIN, "USD", mock_http_session.session)

    assert result.price == 80.25


@pytest.mark.asyncio
async def test_litecoin_command_sends_formatted_price(bot, mock_http_session, monkeypatch):
    mock_http_session.mocked.get(coingecko_url("litecoin", "usd"), payload={"litecoin": {"usd": 1234.5}})
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    cog = Utility(bot)

    await cog.litecoin.callback(cog, make_ctx())

    assert "`1,234.50` USD" in send.await_args.kwargs["embed"].description


# ---------- currency ----------


@pytest.mark.asyncio
async def test_convert_currency_success(mock_http_session):
    mock_http_session.mocked.get(
        frankfurter_url("USD", "CAD"),
        payload={"amount": 1.0, "base": "USD", "date": "2026-11-27", "rates": {"CAD": 1.4}},
    )

    result = await currency_utils.convert_currency("10", "usd", "cad", mock_http_session.session)

    assert (result.source, result.target, result.rate, result.date) == ("USD", "CAD", 1.4, "2026-11-27")
    assert result.converted == pytest.approx(14.0)


@pytest.mark.asyncio
async def test_convert_currency_same_code_skips_request(mock_http_session):
    result = await currency_utils.convert_currency("5", "eur", "EUR", mock_http_session.session)

    assert result.converted == 5.0
    assert mock_http_session.mocked.requests == {}


@pytest.mark.asyncio
async def test_convert_currency_unknown_code(mock_http_session):
    mock_http_session.mocked.get(frankfurter_url("USD", "ZZZ"), status=404, payload={"message": "not found"})

    with pytest.raises(currency_utils.InvalidCurrencyError):
        await currency_utils.convert_currency("1", "USD", "ZZZ", mock_http_session.session)


@pytest.mark.asyncio
async def test_convert_currency_provider_down(mock_http_session):
    mock_http_session.mocked.get(frankfurter_url("USD", "CAD"), exception=aiohttp.ClientError("boom"))

    with pytest.raises(currency_utils.CurrencyProviderError):
        await currency_utils.convert_currency("1", "USD", "CAD", mock_http_session.session)


@pytest.mark.asyncio
async def test_convert_currency_rejects_bad_amount(mock_http_session):
    with pytest.raises(ValueError):
        await currency_utils.convert_currency("ten", "USD", "CAD", mock_http_session.session)


@pytest.mark.asyncio
async def test_currency_command_success(bot, mock_http_session, monkeypatch):
    mock_http_session.mocked.get(
        frankfurter_url("USD", "CAD"),
        payload={"base": "USD", "date": "2026-11-27", "rates": {"CAD": 1.5}},
    )
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    cog = Utility(bot)

    await cog.currency.callback(cog, make_ctx(), "10", "USD", "CAD")

    embed = send.await_args.kwargs["embed"]
    assert "10.00 USD is about 15.00 CAD" in embed.description
    assert "2026-11-27" in embed.footer.text


@pytest.mark.asyncio
async def test_currency_command_provider_down_message(bot, mock_http_session, monkeypatch):
    mock_http_session.mocked.get(frankfurter_url("USD", "CAD"), status=503)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Utility.send_for_context", send)
    cog = Utility(bot)

    await cog.currency.callback(cog, make_ctx(), "10", "USD", "CAD")

    assert "unavailable" in send.await_args.args[1]


# ---------- weather key ----------


def test_weather_prefers_weather_api_key(bot):
    bot.config.services.weather_api_key = "weather-key"
    bot.config.services.ksoft_api = "legacy-key"

    assert Utility(bot).openweather_api_key == "weather-key"


def test_weather_falls_back_to_legacy_ksoft_key(bot):
    bot.config.services.ksoft_api = "legacy-key"

    assert Utility(bot).openweather_api_key == "legacy-key"


# ---------- ChatGPT ----------


def make_chatgpt_bot(bot, **services):
    bot.config = SimpleNamespace(services=SimpleNamespace(**services))
    return bot


def openai_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.mark.asyncio
async def test_askgpt_without_key_explains_setup(bot, monkeypatch):
    cog = ChatGPT(make_chatgpt_bot(bot, openai_api_key=None, chatgpt_secret=None))
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Chatgpt.send_for_context", send)

    await cog.askgpt.callback(cog, make_ctx(), question="hi")

    assert cog.client is None
    assert "OPENAI_API_KEY" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_askgpt_uses_async_client_and_configured_model(bot, monkeypatch):
    cog = ChatGPT(make_chatgpt_bot(bot, openai_api_key="sk-test", openai_model="gpt-test"))
    create = AsyncMock(return_value=openai_response("  Hello!  "))
    cog.client = MagicMock()
    cog.client.chat.completions.create = create
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Chatgpt.send_for_context", send)

    await cog.askgpt.callback(cog, make_ctx(), question="hi")

    assert create.await_args.kwargs["model"] == "gpt-test"
    assert create.await_args.kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert send.await_args.args[1] == "Hello!"


def test_chatgpt_defaults_model_and_accepts_legacy_secret(bot):
    cog = ChatGPT(make_chatgpt_bot(bot, chatgpt_secret="sk-legacy"))

    assert cog.api_key == "sk-legacy"
    assert cog.model == DEFAULT_OPENAI_MODEL
    assert isinstance(cog.client, openai.AsyncOpenAI)


@pytest.mark.asyncio
async def test_askgpt_reports_invalid_key(bot, monkeypatch):
    cog = ChatGPT(make_chatgpt_bot(bot, openai_api_key="sk-bad"))
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = openai.AuthenticationError(
        "bad key", response=httpx.Response(401, request=request), body=None
    )
    cog.client = MagicMock()
    cog.client.chat.completions.create = AsyncMock(side_effect=error)
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Chatgpt.send_for_context", send)

    await cog.askgpt.callback(cog, make_ctx(), question="hi")

    assert "invalid API key" in send.await_args.args[1]


@pytest.mark.asyncio
async def test_askgpt_truncates_long_answers(bot, monkeypatch):
    cog = ChatGPT(make_chatgpt_bot(bot, openai_api_key="sk-test"))
    cog.client = MagicMock()
    cog.client.chat.completions.create = AsyncMock(return_value=openai_response("x" * 5000))
    send = AsyncMock()
    monkeypatch.setattr("bot.cogs.Chatgpt.send_for_context", send)

    await cog.askgpt.callback(cog, make_ctx(), question="hi")

    assert len(send.await_args.args[1]) == 2000
