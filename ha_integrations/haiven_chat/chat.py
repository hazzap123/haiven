"""One chat turn: stream, run tools, loop, account."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from . import prompt
from .anthropic_stream import ApiError, Assembler, build_body, stream_message
from .const import MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS, MAX_TOOL_ROUNDS
from .policy import PolicyError
from .tools import TOOLS
from .usage import Usage

if TYPE_CHECKING:
    from .runtime import Runtime

_LOGGER = logging.getLogger(__name__)

Emit = Callable[[dict[str, Any]], Awaitable[None]]


def clean_history(raw: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Text-only history from the browser; the last message must be the user's."""
    out: list[dict[str, str]] = []
    for item in raw[-MAX_HISTORY_MESSAGES:]:
        role, content = item.get("role"), item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str) or not content.strip():
            raise PolicyError("invalid_messages")
        out.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    while out and out[0]["role"] != "user":
        out.pop(0)
    if not out or out[-1]["role"] != "user":
        raise PolicyError("invalid_messages")
    return out


async def run_turn(
    rt: Runtime, user_id: str, raw_messages: list[dict[str, Any]], turn_id: str, emit: Emit
) -> None:
    started = time.monotonic()
    total = Usage()
    status = "ok"
    tool_calls = 0
    fallback = False
    model: str | None = None
    first_text_s: float | None = None
    requests_ttft: list[float] = []
    try:
        history = clean_history(raw_messages)
        if rt.budget.exhausted():
            raise ApiError("budget_exhausted")
        api_key = rt.api_key()
        if not api_key:
            raise ApiError("no_api_key")

        now = dt_util.now()
        live = prompt.live_block(rt.hass, now)
        messages: list[dict[str, Any]] = [dict(m) for m in history]
        messages[-1]["content"] = f"{live}\n\n{messages[-1]['content']}"
        system = prompt.system_blocks(rt.rules)

        async def on_text(delta: str) -> None:
            nonlocal first_text_s
            if first_text_s is None:
                first_text_s = time.monotonic() - started
            await emit({"type": "text", "delta": delta})

        for round_no in range(MAX_TOOL_ROUNDS + 1):
            assembler = Assembler()
            try:
                result = await stream_message(
                    rt.session, api_key, build_body(system, TOOLS, messages), on_text, assembler
                )
            finally:
                total.add(assembler.result.usage)
                fallback = fallback or assembler.result.fallback_ran
                model = assembler.result.model or model
                if assembler.result.ttft_s is not None:
                    requests_ttft.append(assembler.result.ttft_s)

            if result.stop_reason == "refusal":
                status = "refusal"
                await emit({"type": "refusal"})
                return
            if result.stop_reason == "max_tokens":
                status = "truncated"
                await emit({"type": "truncated"})
                return
            if result.stop_reason != "tool_use":
                return
            if round_no == MAX_TOOL_ROUNDS:
                raise ApiError("tool_round_limit")

            # Echo the assistant turn unchanged (thinking signatures included),
            # then answer every tool_use in one user message.
            messages.append({"role": "assistant", "content": result.content})
            results = []
            for block in result.content:
                if block.get("type") != "tool_use":
                    continue
                tool_calls += 1
                await emit({"type": "tool", "name": block["name"]})
                results.append(await _run_tool(rt, user_id, block, result.invalid_tool_ids))
            messages.append({"role": "user", "content": results})
    except PolicyError as err:
        status = f"error:{err.code}"
        await emit({"type": "error", "code": err.code})
    except ApiError as err:
        status = f"error:{err.code}"
        await emit({"type": "error", "code": err.code})
    except BaseException as err:  # noqa: BLE001 - includes CancelledError; re-raised below
        status = "cancelled" if _is_cancel(err) else "error:internal"
        if status != "cancelled":
            _LOGGER.exception("Haiven chat turn failed")
            await emit({"type": "error", "code": "internal"})
        raise
    finally:
        record = {
            "type": "turn",
            "turn_id": turn_id,
            "user_id": user_id,
            "status": status,
            "model": model,
            "fallback": fallback,
            "tool_calls": tool_calls,
            "ttft_s": round(first_text_s, 3) if first_text_s is not None else None,
            "request_ttft_s": [round(t, 3) for t in requests_ttft],
            "duration_s": round(time.monotonic() - started, 3),
            **total.as_dict(),
        }
        await rt.record_turn(record, total)
        try:
            await emit({"type": "usage", **rt.public_usage(record)})
            await emit({"type": "done", "status": status})
        except Exception:  # noqa: BLE001 - connection may already be gone
            pass


def _is_cancel(err: BaseException) -> bool:
    import asyncio

    return isinstance(err, asyncio.CancelledError)


async def _run_tool(
    rt: Runtime, user_id: str, block: dict[str, Any], invalid: set[str]
) -> dict[str, Any]:
    out: dict[str, Any] = {"type": "tool_result", "tool_use_id": block["id"]}
    try:
        if block["id"] in invalid:
            raise PolicyError("invalid_json")
        result = await rt.toolbox.run(block["name"], block["input"], user_id)
        out["content"] = json.dumps(result, separators=(",", ":"))
    except PolicyError as err:
        out["is_error"] = True
        out["content"] = json.dumps({"error": err.code, "detail": str(err)[:200]})
    return out
