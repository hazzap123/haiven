"""Streaming client for the Anthropic Messages API over aiohttp (no SDK)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import (
    API_URL,
    API_VERSION,
    EFFORT,
    FALLBACK_BETA,
    MAX_TOKENS,
    MODEL,
)
from .usage import Usage, usage_from_api

TIMEOUT = aiohttp.ClientTimeout(total=180, sock_connect=10, sock_read=60)


class ApiError(Exception):
    """Upstream failure. `code` is safe to show the browser; detail is not."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass
class StreamResult:
    content: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str | None = None
    stop_details: dict[str, Any] | None = None
    usage: Usage = field(default_factory=Usage)
    ttft_s: float | None = None
    model: str | None = None
    fallback_ran: bool = False
    # Tool uses whose streamed input was not valid JSON.
    invalid_tool_ids: set[str] = field(default_factory=set)


def build_body(system: list[dict], tools: list[dict], messages: list[dict]) -> dict[str, Any]:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "system": system,
        "tools": tools,
        "tool_choice": {"type": "auto"},
        "messages": messages,
        "output_config": {"effort": EFFORT},
        "fallbacks": "default",
    }


def build_headers(api_key: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "anthropic-beta": FALLBACK_BETA,
        "content-type": "application/json",
    }


async def iter_sse(lines: AsyncIterator[bytes]) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Yield (event, data) from an SSE byte-line stream."""
    event = "message"
    data: list[str] = []
    async for raw in lines:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data:
                try:
                    yield event, json.loads("\n".join(data))
                except json.JSONDecodeError as err:
                    raise ApiError("bad_stream", "undecodable event") from err
            event, data = "message", []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        yield event, json.loads("\n".join(data))


class Assembler:
    """Rebuilds content blocks from stream events.

    Blocks are kept as sent by the API (thinking signatures, fallback blocks
    and all) so they can be echoed back unchanged on the next request.
    """

    def __init__(self) -> None:
        self.result = StreamResult()
        self._json: dict[int, list[str]] = {}
        self._started = time.monotonic()

    def feed(self, event: str, data: dict[str, Any]) -> str | None:
        """Consume one event; return a text delta to show the user, if any."""
        if event == "error":
            err = data.get("error", {})
            raise ApiError(_error_code(err.get("type")), str(err.get("message", ""))[:200])

        if event == "message_start":
            msg = data.get("message", {})
            self.result.model = msg.get("model")
            self.result.usage = usage_from_api(msg.get("usage"))
            return None

        if event == "content_block_start":
            self.result.content.append(dict(data["content_block"]))
            index = data["index"]
            block = self.result.content[index]
            if block.get("type") == "tool_use":
                block["input"] = {}
                self._json[index] = []
            elif block.get("type") == "text":
                block.setdefault("text", "")
            elif block.get("type") == "thinking":
                block.setdefault("thinking", "")
            elif block.get("type") == "fallback":
                self.result.fallback_ran = True
            return None

        if event == "content_block_delta":
            index = data["index"]
            block = self.result.content[index]
            delta = data["delta"]
            kind = delta.get("type")
            if kind == "text_delta":
                block["text"] += delta["text"]
                if self.result.ttft_s is None:
                    self.result.ttft_s = time.monotonic() - self._started
                return delta["text"]
            if kind == "input_json_delta":
                self._json[index].append(delta.get("partial_json", ""))
            elif kind == "thinking_delta":
                block["thinking"] += delta.get("thinking", "")
            elif kind == "signature_delta":
                block["signature"] = block.get("signature", "") + delta.get("signature", "")
            return None

        if event == "content_block_stop":
            index = data["index"]
            block = self.result.content[index]
            if block.get("type") == "tool_use":
                raw = "".join(self._json.pop(index, [])) or "{}"
                try:
                    block["input"] = json.loads(raw)
                except json.JSONDecodeError:
                    # Eager input streaming means the API no longer guarantees
                    # valid JSON (e.g. cut off at max_tokens). Never run it.
                    block["input"] = {}
                    self.result.invalid_tool_ids.add(block["id"])
            return None

        if event == "message_delta":
            delta = data.get("delta", {})
            self.result.stop_reason = delta.get("stop_reason", self.result.stop_reason)
            self.result.stop_details = delta.get("stop_details", self.result.stop_details)
            usage = data.get("usage") or {}
            if "output_tokens" in usage:
                self.result.usage.output_tokens = int(usage["output_tokens"])
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                if usage.get(key):
                    setattr(self.result.usage, key, int(usage[key]))
            if any(i.get("type") == "fallback_message" for i in usage.get("iterations") or []):
                self.result.fallback_ran = True
        return None


def _error_code(kind: str | None) -> str:
    return {
        "overloaded_error": "overloaded",
        "rate_limit_error": "rate_limited",
        "authentication_error": "auth_failed",
        "permission_error": "auth_failed",
        "invalid_request_error": "bad_request",
    }.get(kind or "", "upstream_error")


async def stream_message(
    session: aiohttp.ClientSession,
    api_key: str,
    body: dict[str, Any],
    on_text: Callable[[str], Awaitable[None]],
    assembler: Assembler,
) -> StreamResult:
    """POST one streaming request and return the assembled result.

    Cancellation closes the connection, which stops generation and billing.
    The caller owns the assembler so partial usage survives cancellation or an
    error. Headers and request info are never logged or surfaced.
    """
    try:
        async with session.post(
            API_URL, json=body, headers=build_headers(api_key), timeout=TIMEOUT
        ) as resp:
            if resp.status != 200:
                try:
                    payload = await resp.json()
                    kind = payload.get("error", {}).get("type")
                except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
                    kind = None
                raise ApiError(_error_code(kind) if kind else f"http_{resp.status}")
            async for event, data in iter_sse(resp.content):
                text = assembler.feed(event, data)
                if text:
                    await on_text(text)
    except aiohttp.ClientError as err:
        raise ApiError("network_error", type(err).__name__) from None
    except TimeoutError:
        raise ApiError("timeout") from None
    return assembler.result
