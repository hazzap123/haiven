"""System prompt and live-state block.

Cache order is tools, system, messages. rules.txt never changes between turns;
anything that moves (time, states) goes in the user turn via `live_block`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import KEY_SENSORS

def system_blocks(rules: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": rules, "cache_control": {"type": "ephemeral"}}]


def live_block(hass: HomeAssistant, now: datetime) -> str:
    lines = [f"<live_state now=\"{now.isoformat(timespec='minutes')}\">"]
    for entity_id, label in KEY_SENSORS.items():
        state = hass.states.get(entity_id)
        if state is not None:
            unit = state.attributes.get("unit_of_measurement", "")
            lines.append(f"{label} ({entity_id}) = {str(state.state)[:300]}{unit}")
    lines.append("</live_state>")
    return "\n".join(lines)
