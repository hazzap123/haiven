"""Haiven Chat: a read-only streaming chat over the Haiven data."""

from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import websocket_api as ws
from .const import DOMAIN
from .runtime import Runtime
from .usage import Budget

# A text file, so changing what Ask says needs an entry reload rather than a
# restart of the box doing the monitoring.
RULES_FILE = Path(__file__).parent / "rules.txt"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    ws.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rules = await hass.async_add_executor_job(RULES_FILE.read_text, "utf-8")
    rt = Runtime(hass, entry, async_get_clientsession(hass), rules, Budget())
    await rt.async_load()
    hass.data[DOMAIN] = rt
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rt = hass.data.pop(DOMAIN, None)
    if rt is not None:
        await rt.async_flush()
    return True
