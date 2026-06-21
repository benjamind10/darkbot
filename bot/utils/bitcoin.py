from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False


COINGECKO_SIMPLE_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINBASE_EXCHANGE_RATES_URL = "https://api.coinbase.com/v2/exchange-rates"


@dataclass(slots=True)
class BitcoinLookupResult:
    currency: str
    price: float


@dataclass(slots=True)
class BitcoinConversionResult:
    amount: float
    currency: str
    bitcoin: float


class BitcoinLookupError(Exception):
    """Base class for bitcoin lookup failures."""


class InvalidBitcoinCurrencyError(BitcoinLookupError):
    """Raised when the requested currency is not supported."""


class BitcoinProviderError(BitcoinLookupError):
    """Raised when the upstream provider cannot be reached or responds poorly."""


def _coerce_price(price: Any, provider: str) -> float:
    try:
        price_value = float(price)
    except (TypeError, ValueError):
        raise BitcoinProviderError(f"{provider} returned invalid bitcoin price") from None

    if price_value <= 0:
        raise BitcoinProviderError(f"{provider} returned invalid bitcoin price")

    return price_value


async def _fetch_coingecko_price(currency: str, session: Any) -> float:
    provider = "coingecko"
    async with session.get(
        COINGECKO_SIMPLE_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": currency.lower()},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as response:
        if response.status >= 400:
            raise BitcoinProviderError(f"{provider} returned HTTP {response.status}")

        payload = await response.json()

    try:
        price = payload["bitcoin"][currency.lower()]
    except (KeyError, TypeError):
        raise InvalidBitcoinCurrencyError(currency) from None

    return _coerce_price(price, provider)


async def _fetch_coinbase_price(currency: str, session: Any) -> float:
    provider = "coinbase"
    async with session.get(
        COINBASE_EXCHANGE_RATES_URL,
        params={"currency": "BTC"},
        timeout=aiohttp.ClientTimeout(total=10),
    ) as response:
        if response.status >= 400:
            raise BitcoinProviderError(f"{provider} returned HTTP {response.status}")

        payload = await response.json()

    try:
        price = payload["data"]["rates"][currency]
    except (KeyError, TypeError):
        raise InvalidBitcoinCurrencyError(currency) from None

    return _coerce_price(price, provider)


async def _fetch_bitcoin_price(currency: str, session: Any | None = None) -> float:
    if not AIOHTTP_AVAILABLE:
        raise BitcoinProviderError("bitcoin HTTP dependency unavailable")

    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    provider_errors: list[str] = []
    invalid_currency = False

    try:
        for provider, fetch_price in (
            ("coingecko", _fetch_coingecko_price),
            ("coinbase", _fetch_coinbase_price),
        ):
            try:
                return await fetch_price(currency, session)
            except InvalidBitcoinCurrencyError:
                invalid_currency = True
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                provider_errors.append(f"{provider}: {exc}")
            except BitcoinProviderError as exc:
                provider_errors.append(str(exc))
    finally:
        if close_session:
            await session.close()

    if provider_errors:
        details = "; ".join(provider_errors)
        raise BitcoinProviderError(f"bitcoin price lookup failed ({details})")

    if invalid_currency:
        raise InvalidBitcoinCurrencyError(currency)

    raise BitcoinProviderError("bitcoin price lookup failed")


async def get_bitcoin_price(currency: str, session: Any | None = None) -> BitcoinLookupResult:
    normalized_currency = currency.upper()
    price = await _fetch_bitcoin_price(normalized_currency, session)

    return BitcoinLookupResult(currency=normalized_currency, price=float(price))


async def convert_currency_to_bitcoin(
    amount: str, currency: str, session: Any | None = None
) -> BitcoinConversionResult:
    normalized_currency = currency.upper()
    try:
        amount_value = float(amount)
    except ValueError:
        raise ValueError("invalid amount") from None

    price = await _fetch_bitcoin_price(normalized_currency, session)
    bitcoin_value = amount_value / price

    return BitcoinConversionResult(
        amount=amount_value,
        currency=normalized_currency,
        bitcoin=round(float(bitcoin_value), 4),
    )
