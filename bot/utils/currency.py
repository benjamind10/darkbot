"""Fiat currency conversion via the Frankfurter API (ECB reference rates, no key)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

FRANKFURTER_LATEST_URL = "https://api.frankfurter.dev/v1/latest"


class CurrencyError(Exception):
    """Base class for currency conversion failures."""


class InvalidCurrencyError(CurrencyError):
    """Raised when a currency code is not supported by the rates provider."""


class CurrencyProviderError(CurrencyError):
    """Raised when the rates provider cannot be reached or responds badly."""


@dataclass(slots=True)
class CurrencyConversion:
    amount: float
    source: str
    target: str
    rate: float
    converted: float
    date: str


async def convert_currency(
    amount: str | float, source: str, target: str, session: Any
) -> CurrencyConversion:
    """Convert `amount` from `source` to `target` using the latest ECB rates.

    Raises ValueError for a non-numeric amount, InvalidCurrencyError for an
    unknown code, and CurrencyProviderError when Frankfurter is unavailable.
    """
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("invalid amount") from None

    source_code = source.strip().upper()
    target_code = target.strip().upper()
    if source_code == target_code:
        return CurrencyConversion(amount_value, source_code, target_code, 1.0, amount_value, "")

    try:
        async with session.get(
            FRANKFURTER_LATEST_URL,
            params={"base": source_code, "symbols": target_code},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status in (404, 422):
                raise InvalidCurrencyError(f"{source_code}->{target_code}")
            if response.status >= 400:
                raise CurrencyProviderError(f"frankfurter returned HTTP {response.status}")
            payload = await response.json()
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise CurrencyProviderError(f"frankfurter request failed: {exc}") from exc

    try:
        rate = float(payload["rates"][target_code])
    except (KeyError, TypeError, ValueError):
        raise InvalidCurrencyError(f"{source_code}->{target_code}") from None

    return CurrencyConversion(
        amount=amount_value,
        source=source_code,
        target=target_code,
        rate=rate,
        converted=amount_value * rate,
        date=str(payload.get("date", "")),
    )
