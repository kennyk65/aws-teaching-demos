"""
test_detection_integration.py – LIVE Bedrock integration test for Model Call #1.

Exercises the real compare/classify capability: it sends the recent-releases
fixture (one major, one minor, one patch) to the actual Bedrock model and
verifies the model reports ONLY the major and minor releases.

OPT-IN and skipped by default (requires AWS credentials, the model enabled in
the region, cost, latency, and calls a non-deterministic LLM). Run with:

    RUN_BEDROCK_INTEGRATION=1 BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0 \
        AWS_REGION=us-east-2 pytest -m integration

Fixture (recent_releases.json):
  * Developing on AWS             4.2.1  → 5.0.0   → MAJOR  (report)
  * Advanced Architecting on AWS  3.10.8 → 3.11.0  → MINOR  (report)
  * Architecting on AWS           7.0.4  → 7.0.5   → PATCH  (omit)

Non-determinism is tolerated by SEMANTIC assertions, but hard contracts are
enforced: the output MUST be valid JSON, MUST report exactly the major+minor
releases, MUST exclude the patch release, and each entry MUST carry the
required fields.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from src.bedrock_service import detect_releases
from src.detection import parse_detection

FIXTURES_DIR = Path(__file__).parent / "fixtures"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_BEDROCK_INTEGRATION") != "1",
        reason="Live Bedrock test; set RUN_BEDROCK_INTEGRATION=1 to run.",
    ),
]


@pytest.fixture(scope="module")
def model_id() -> str:
    return os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")


@pytest.fixture(scope="module")
def filtered_list() -> list[dict]:
    return json.loads((FIXTURES_DIR / "recent_releases.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_detection(filtered_list: list[dict], model_id: str) -> str:
    return detect_releases(filtered_list, model_id=model_id)


@pytest.fixture(scope="module")
def releases(raw_detection: str) -> list[dict]:
    return parse_detection(raw_detection)


def _names(entries: list[dict]) -> set[str]:
    return {e["name"].strip().lower() for e in entries}


def _parse_raw_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Hard contracts
# ---------------------------------------------------------------------------

class TestOutputContract:
    def test_output_is_valid_json_object(self, raw_detection: str) -> None:
        obj = _parse_raw_json(raw_detection)
        assert isinstance(obj, dict)

    def test_has_releases_list(self, raw_detection: str) -> None:
        obj = _parse_raw_json(raw_detection)
        assert isinstance(obj.get("releases"), list)

    def test_reports_exactly_major_and_minor(self, releases: list[dict]) -> None:
        assert _names(releases) == {"developing on aws", "advanced architecting on aws"}

    def test_patch_release_excluded(self, releases: list[dict]) -> None:
        assert "architecting on aws" not in _names(releases)

    def test_entries_have_required_fields(self, releases: list[dict]) -> None:
        for entry in releases:
            for field in ("name", "version", "previous_version", "released", "notes"):
                assert entry.get(field), f"missing {field}: {entry}"


# ---------------------------------------------------------------------------
# Classification detail
# ---------------------------------------------------------------------------

class TestClassification:
    def test_major_release_versions(self, releases: list[dict]) -> None:
        dev = next((r for r in releases if r["name"].lower() == "developing on aws"), None)
        assert dev is not None
        assert dev["version"] == "5.0.0"
        assert dev["previous_version"] == "4.2.1"

    def test_minor_release_versions(self, releases: list[dict]) -> None:
        adv = next((r for r in releases if r["name"].lower() == "advanced architecting on aws"), None)
        assert adv is not None
        assert adv["version"] == "3.11.0"
        assert adv["previous_version"] == "3.10.8"

    def test_exactly_two_releases(self, releases: list[dict]) -> None:
        assert len(releases) == 2
