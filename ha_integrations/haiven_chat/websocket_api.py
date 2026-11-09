"""Websocket commands: stream (subscription), series, status. All admin-only."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .chat import run_turn
from .const import DOMAIN, FLUSH_CHARS, FLUSH_INTERVAL_S
from .policy import PolicyError
from .runtime import Runtime

_LOGGER = logging.getLogger(__name__)


def _runtime(hass: HomeAssistant, connection, msg) -> Runtime | None:
    rt = hass.data.get(DOMAIN)
    if rt is None:
        connection.send_error(msg["id"], "not_loaded", "Haiven Chat is not set up")
    return rt


class Emitter:
    """Sends events to one subscription; batches text so a token never costs a message."""

    def __init__(self, connection, msg_id: int) -> None:
        self._connection = connection
        self._id = msg_id
        self._buf: list[str] = []
        self._chars = 0
        self._last = 0.0
        self._first = True

    def _send(self, payload: dict[str, Any]) -> None:
        # After the socket closes send_message only logs; skip so a stray task is obvious.
        if self._id in self._connection.subscriptions:
            self._connection.send_message(websocket_api.event_message(self._id, payload))

    def flush(self) -> None:
        if self._buf:
            self._send({"type": "text", "delta": "".join(self._buf)})
            self._buf.clear()
            self._chars = 0
            self._last = time.monotonic()

    async def __call__(self, event: dict[str, Any]) -> None:
        if event["type"] == "text":
            self._buf.append(event["delta"])
            self._chars += len(event["delta"])
            now = time.monotonic()
            if self._first or self._chars >= FLUSH_CHARS or now - self._last >= FLUSH_INTERVAL_S:
                self._first = False
                self.flush()
            return
        self.flush()
        self._send(event)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "haiven_chat/stream",
        vol.Required("messages"): vol.All(
            [{vol.Required("role"): str, vol.Required("content"): str}], vol.Length(min=1, max=40)
        ),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_stream(hass: HomeAssistant, connection, msg) -> None:
    rt = _runtime(hass, connection, msg)
    if rt is None:
        return
    user_id = connection.user.id
    try:
        rt.admit(user_id)
    except PolicyError as err:
        connection.send_error(msg["id"], err.code, "")
        return

    turn_id = secrets.token_urlsafe(8)
    emit = Emitter(connection, msg["id"])

    async def _run() -> None:
        try:
            await emit({"type": "turn", "turn_id": turn_id})
            await run_turn(rt, user_id, msg["messages"], turn_id, emit)
        finally:
            rt.release(user_id)

    # Not eager: the cancel hook must be registered before the task first runs.
    task = rt.entry.async_create_background_task(
        hass, _run(), f"{DOMAIN}_stream", eager_start=False
    )
    connection.subscriptions[msg["id"]] = task.cancel
    task.add_done_callback(lambda _t: connection.subscriptions.pop(msg["id"], None))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "haiven_chat/series", vol.Required("series_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_series(hass: HomeAssistant, connection, msg) -> None:
    rt = _runtime(hass, connection, msg)
    if rt is None:
        return
    try:
        data = rt.toolbox.series.get(connection.user.id, msg["series_id"])
    except PolicyError as err:
        connection.send_error(msg["id"], err.code, "")
        return
    connection.send_result(msg["id"], data)


@websocket_api.websocket_command({vol.Required("type"): "haiven_chat/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_status(hass: HomeAssistant, connection, msg) -> None:
    rt = _runtime(hass, connection, msg)
    if rt is None:
        return
    connection.send_result(
        msg["id"],
        {
            "loaded": True,
            "month": rt.budget.month,
            "month_total_usd": round(rt.budget.total_usd, 4),
            "budget_warning": rt.budget.warning(),
            "budget_exhausted": rt.budget.exhausted(),
            "has_key": bool(rt.api_key()),
        },
    )


def async_register(hass: HomeAssistant) -> None:
    for handler in (ws_stream, ws_series, ws_status):
        websocket_api.async_register_command(hass, handler)
