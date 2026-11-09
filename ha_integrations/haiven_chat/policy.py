"""What the model may read. Pure, no HA imports. There is no write path at all."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any

# Domains get_state may read. Cameras, media players, people and trackers carry
# tokens or location, so they are never readable. input_text holds the care
# circle's phone numbers, so it stays out apart from ALLOWED_IDS.
READABLE_DOMAINS = frozenset(
    {
        "sensor",
        "binary_sensor",
        "input_boolean",
        "input_number",
        "input_select",
        "weather",
    }
)
# Readable domains still carry location and network identity in some sensors
# (companion-app geocoding, Wi-Fi names). The model never needs them.
DENY_ID_PARTS = (
    "geocoded",
    "ssid",
    "bssid",
    "location",
    "latitude",
    "longitude",
    "address",
    "external_ip",
    "phone",
    # The care circle: how far each carer is from the person, and who is
    # nearest, is their whereabouts in another form.
    "contact",
    "care_circle",
    "carer",
    "nearest",
    "nearby",
    "proximity",
)
# The room and the summary are the point of the feature; both are exact ids so
# the carers' own location sensors stay denied.
ALLOWED_IDS = frozenset({"sensor.elderly_person_location", "input_text.current_summary"})

STRIPPED_ATTRIBUTES = frozenset({"entity_picture", "access_token", "entity_picture_local"})
# Attribute names are as open-ended as entity ids, so they get the same screen.
DENY_ATTRIBUTE_PARTS = ("latitude", "longitude", "gps", "phone", "ssid", "address", "email", "token")


class PolicyError(Exception):
    """A request was refused. `code` is safe to show the browser."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code


def domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def is_denied(entity_id: str) -> bool:
    if entity_id in ALLOWED_IDS:
        return False
    low = entity_id.lower()
    return domain_of(low) not in READABLE_DOMAINS or any(part in low for part in DENY_ID_PARTS)


def check_readable(entity_id: str) -> None:
    if not isinstance(entity_id, str) or "." not in entity_id:
        raise PolicyError("invalid_entity")
    if is_denied(entity_id):
        raise PolicyError("not_readable", entity_id)


def clean_attributes(attrs: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in attrs.items():
        if key in STRIPPED_ATTRIBUTES or any(part in key.lower() for part in DENY_ATTRIBUTE_PARTS):
            continue
        if isinstance(value, str) and len(value) > 200:
            value = value[:200] + "…"
        elif isinstance(value, (list, dict)):
            text = str(value)
            value = text if len(text) <= 200 else text[:200] + "…"
        out[key] = value
        if len(out) >= limit:
            break
    return out


@dataclass
class SeriesStore:
    """Chart data kept server-side so it never passes through the model."""

    ttl: float
    clock: Any = time.monotonic
    _items: dict[str, tuple[str, float, dict]] = field(default_factory=dict)

    def put(self, user_id: str, data: dict) -> str:
        now = self.clock()
        for key in [k for k, v in self._items.items() if v[1] < now]:
            del self._items[key]
        series_id = secrets.token_urlsafe(9)
        self._items[series_id] = (user_id, now + self.ttl, data)
        return series_id

    def get(self, user_id: str, series_id: str) -> dict:
        item = self._items.get(series_id)
        if item is None or item[0] != user_id or item[1] < self.clock():
            raise PolicyError("unknown_series")
        return item[2]
