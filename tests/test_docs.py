"""
Documentation must match what the repo actually does.

Run with: pytest tests/test_docs.py -v
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
INSTALL_DOCS = ["README.md", "docs/setup/QUICKSTART.md", "docs/setup/COMPLETE_SETUP.md"]


def tracked(*patterns):
    out = subprocess.run(["git", "ls-files", *patterns], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / p for p in out.stdout.split()]


@pytest.mark.parametrize("doc", INSTALL_DOCS)
def test_never_clone_into_config(doc):
    # /config already holds the user's setup; cloning into it fails or, with
    # a copy step, overwrites their configuration.yaml.
    assert not re.search(r"git clone \S+ /config\b", (ROOT / doc).read_text())


@pytest.mark.parametrize("doc", INSTALL_DOCS)
def test_kiosk_mode_is_a_requirement_and_ai_is_described_as_optional(doc):
    text = (ROOT / doc).read_text()
    assert "kiosk-mode" in text
    assert "Privacy" in text
    # AI wording is off by default; the docs must say so and name the switch.
    assert "off by default" in text
    assert "input_boolean.haiven_ai_summaries" in text
    assert "conversation.claude_conversation" in text
    assert "Required, not optional" not in text and "This is required: the daily summaries" not in text


def test_no_claims_the_repo_contradicts():
    stale = ["No HACS", "to GitHub", "All Sensors Online", "haiven_inputs.yaml"]
    for path in tracked("*.md", "*.yaml"):
        text = path.read_text()
        for phrase in stale:
            assert phrase not in text, f"{path.relative_to(ROOT)}: {phrase!r}"


def test_british_spelling_in_docs():
    american = re.compile(r"\b(centraliz\w*|optimiz\w*|behavior\w*|stabiliz\w*|millimeter\w*)\b", re.I)
    for path in tracked("*.md"):
        found = american.findall(path.read_text())
        assert not found, f"{path.relative_to(ROOT)}: {found}"
