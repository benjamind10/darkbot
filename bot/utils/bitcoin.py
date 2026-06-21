from __future__ import annotations

import asyncio
from dataclasses import dataclass

try:
    from forex_python.bitcoin import BtcConverter
    from forex_python.converter import RatesNotAvailableError
    from requests.exceptions import ConnectionError, Timeout

    FOREX_AVAILABLE = True
except ImportError:
    BtcConverter = None
    RatesNotAvailableError = ValueError
    ConnectionError = OSError
    Timeout = TimeoutError
    FOREX_AVAILABLE = False


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


async def get_bitcoin_price(currency: str) -> BitcoinLookupResult:
    normalized_currency = currency.upper()
    if BtcConverter is None:
        raise BitcoinProviderError("bitcoin dependency unavailable")

    converter = BtcConverter()

    try:
        price = await asyncio.to_thread(converter.get_latest_price, normalized_currency)
    except (ValueError, RatesNotAvailableError):
        raise InvalidBitcoinCurrencyError(normalized_currency) from None
    except Exception as exc:
        raise BitcoinProviderError("bitcoin price lookup failed") from exc

    return BitcoinLookupResult(currency=normalized_currency, price=float(price))


async def convert_currency_to_bitcoin(amount: str, currency: str) -> BitcoinConversionResult:
    normalized_currency = currency.upper()
    if BtcConverter is None:
        raise BitcoinProviderError("bitcoin dependency unavailable")

    try:
        amount_value = float(amount)
    except ValueError:
        raise ValueError("invalid amount") from None

    converter = BtcConverter()

    try:
        bitcoin_value = await asyncio.to_thread(converter.convert_to_btc, amount_value, normalized_currency)
    except (ValueError, RatesNotAvailableError):
        raise InvalidBitcoinCurrencyError(normalized_currency) from None
    except Exception as exc:
        raise BitcoinProviderError("bitcoin conversion failed") from exc

    return BitcoinConversionResult(
        amount=amount_value,
        currency=normalized_currency,
        bitcoin=round(float(bitcoin_value), 4),
    )
