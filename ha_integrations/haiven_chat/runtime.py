"""Per-entry runtime: key lookup, budget, usage log, admission limits."""

from __future__ import annotations

import json
import time
from collections import deque
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_ANTHROPIC_ENTRY_ID,
    MAX_STREAMS_PER_USER,
    MAX_STREAMS_TOTAL,
    MAX_TURNS_PER_MINUTE,
    STORE_KEY,
    STORE_VERSION,
    USAGE_LOG,
)
from .policy import PolicyError
from .tools import Toolbox
from .usage import Budget, Usage


class Runtime:
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: aiohttp.ClientSession,
        rules: str,
        budget: Budget,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.session = session
        self.rules = rules
        self.budget = budget
        self.toolbox = Toolbox(hass)
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, STORE_KEY)
        self._log_path = hass.config.path(USAGE_LOG)
        self._active: dict[str, int] = {}
        self._turns: deque[float] = deque()

    def api_key(self) -> str | None:
        """Read the key live from the core Anthropic entry; never copied."""
        source = self.hass.config_entries.async_get_entry(self.entry.data[CONF_ANTHROPIC_ENTRY_ID])
        return source.data.get(CONF_API_KEY) if source else None

    # -- admission -------------------------------------------------------

    def admit(self, user_id: str) -> None:
        now = time.monotonic()
        while self._turns and now - self._turns[0] > 60:
            self._turns.popleft()
        if len(self._turns) >= MAX_TURNS_PER_MINUTE:
            raise PolicyError("rate_limited")
        if (
            self._active.get(user_id, 0) >= MAX_STREAMS_PER_USER
            or sum(self._active.values()) >= MAX_STREAMS_TOTAL
        ):
            raise PolicyError("busy")
        self._turns.append(now)
        self._active[user_id] = self._active.get(user_id, 0) + 1

    def release(self, user_id: str) -> None:
        left = self._active.get(user_id, 0) - 1
        if left > 0:
            self._active[user_id] = left
        else:
            self._active.pop(user_id, None)

    # -- accounting ------------------------------------------------------

    async def async_load(self) -> None:
        self.budget = Budget(await self._store.async_load())

    async def record_turn(self, record: dict[str, Any], usage: Usage) -> None:
        total = self.budget.charge(usage)
        record["ts"] = time.time()
        record["month"] = self.budget.month
        record["month_total_usd"] = round(total, 6)
        self._store.async_delay_save(self.budget.as_dict, 5)
        await self.append_log(record)

    async def append_log(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, separators=(",", ":")) + "\n"
        await self.hass.async_add_executor_job(self._append, line)

    def _append(self, line: str) -> None:
        with open(self._log_path, "a", encoding="utf-8") as handle:
            handle.write(line)

    def public_usage(self, record: dict[str, Any]) -> dict[str, Any]:
        keep = (
            "turn_id",
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
            "cost_usd",
            "ttft_s",
            "duration_s",
            "month_total_usd",
        )
        out = {k: record.get(k) for k in keep}
        out["budget_warning"] = self.budget.warning()
        return out

    async def async_flush(self) -> None:
        await self._store.async_save(self.budget.as_dict())
