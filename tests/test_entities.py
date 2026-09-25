"""
Every entity the dashboard, automations, scripts, cards and entity reference
point at must be one this repo defines, or one the installer supplies (their
sensors, phones and people). A reference to anything else is a card that
shows "unavailable", an alert that never fires, or a doc row that sends
someone looking for an entity that was never created.

Run with: pytest tests/test_entities.py -v
"""

import glob
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent

DOMAINS = ("sensor", "binary_sensor", "input_boolean", "input_number", "input_text",
           "input_datetime", "input_select", "input_button", "counter", "timer",
           "script", "camera", "event", "person", "zone", "automation")
REF = re.compile(r"(?<![\w.])((?:%s)\.[a-z0-9_]+)\b" % "|".join(DOMAINS))

# Supplied by the installer, not by this repo: the three room sensors and
# their extras, and HA's own home zone. Service calls share the entity-id
# shape and are listed too.
SUPPLIED = re.compile(
    r"^(binary_sensor|sensor)\.haiven_(bedroom|bathroom)_[a-z0-9_]+$"
    r"|^event\.kitchen_motion$|^zone\.home$"
    r"|^(input_\w+|counter|script|automation)\.(turn_on|turn_off|toggle|set_value|set_datetime"
    r"|select_option|increment|decrement|reset|reload|trigger|press)$"
)


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _slug(name):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(name).lower())).strip("_")


def _defined():
    out = set()
    files = [ROOT / "configuration.yaml", ROOT / "haiven_sensors_3sensor.yaml",
             *map(Path, sorted(glob.glob(str(ROOT / "packages" / "*.yaml"))))]
    for f in files:
        doc = yaml.load(f.read_text(), Loader=_Loader) or {}
        for dom in ("input_boolean", "input_number", "input_text", "input_datetime",
                    "input_select", "input_button", "counter", "timer", "script"):
            out |= {f"{dom}.{k}" for k in (doc.get(dom) or {})}
        for block in doc.get("template") or []:
            for platform, items in block.items():
                if isinstance(items, list):
                    out |= {f"{platform}.{_slug(i['name'])}" for i in items if "name" in i}
        for item in doc.get("command_line") or []:
            out |= {f"{p}.{_slug(c['name'])}" for p, c in item.items()}
        for item in doc.get("sql") or []:
            out.add(f"sensor.{_slug(item['name'])}")
        for platform in ("sensor", "binary_sensor"):
            for item in doc.get(platform) or []:
                if isinstance(item, dict) and "name" in item:
                    out.add(f"{platform}.{_slug(item['name'])}")
    for p in yaml.load((ROOT / "haiven_persons.yaml").read_text(), Loader=_Loader) or []:
        out.add(f"person.{p['id']}")
    out |= {f"script.{k}" for k in yaml.load((ROOT / "scripts.yaml").read_text(), Loader=_Loader)}
    for a in yaml.load((ROOT / "automations.yaml").read_text(), Loader=_Loader):
        out |= {f"automation.{a['id']}", f"automation.{_slug(a['alias'])}"}
    return out


DEFINED = _defined()


@pytest.mark.parametrize("path", [
    "lovelace/haiven_default.yaml",
    "automations.yaml",
    "scripts.yaml",
    "www-src/haiven-cards.js",
    "docs/reference/ENTITY_REFERENCE.md",
])
def test_references_resolve(path):
    # "Filter: input_text.contact_" lines are search prefixes, not entities.
    text = "\n".join(l for l in (ROOT / path).read_text().splitlines() if "Filter:" not in l)
    refs = set(REF.findall(text))
    unknown = sorted(r for r in refs if r not in DEFINED and not SUPPLIED.match(r))
    assert not unknown, f"{path} references entities nothing creates: {unknown}"
