"""Token accounting and the running dollar budget. Pure, no HA imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .const import (
    BUDGET_LIMIT_USD,
    BUDGET_WARN_USD,
    PRICE_CACHE_READ,
    PRICE_CACHE_WRITE,
    PRICE_INPUT,
    PRICE_OUTPUT,
)


@dataclass
class Usage:
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens
        self.output_tokens += other.output_tokens
        self.requests += other.requests

    def cost_usd(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT
            + self.cache_creation_input_tokens * PRICE_CACHE_WRITE
            + self.cache_read_input_tokens * PRICE_CACHE_READ
            + self.output_tokens * PRICE_OUTPUT
        ) / 1_000_000

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "output_tokens": self.output_tokens,
            "requests": self.requests,
            "cost_usd": round(self.cost_usd(), 6),
        }


def month_key(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


class Budget:
    """Running spend for the current month; resets when the month rolls over."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        data = data or {}
        self.month: str = data.get("month", month_key())
        self.total_usd: float = float(data.get("total_usd", 0.0))

    def roll(self, now: datetime | None = None) -> None:
        current = month_key(now)
        if current != self.month:
            self.month = current
            self.total_usd = 0.0

    def exhausted(self, now: datetime | None = None) -> bool:
        self.roll(now)
        return self.total_usd >= BUDGET_LIMIT_USD

    def warning(self) -> bool:
        return self.total_usd >= BUDGET_WARN_USD

    def charge(self, usage: Usage, now: datetime | None = None) -> float:
        self.roll(now)
        self.total_usd += usage.cost_usd()
        return self.total_usd

    def as_dict(self) -> dict[str, Any]:
        return {"month": self.month, "total_usd": round(self.total_usd, 6)}


def usage_from_api(raw: dict[str, Any] | None) -> Usage:
    raw = raw or {}
    return Usage(
        input_tokens=int(raw.get("input_tokens") or 0),
        cache_creation_input_tokens=int(raw.get("cache_creation_input_tokens") or 0),
        cache_read_input_tokens=int(raw.get("cache_read_input_tokens") or 0),
        output_tokens=int(raw.get("output_tokens") or 0),
        requests=1,
    )
