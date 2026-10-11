"""
test_parser.py – API retrieval & filtering tests (spec §4.1).

Covers scraper.filter_courses (pure) and scraper.get_filtered_releases (HTTP
mocked): EN language filter, recency window, latest-two-versions trim, and the
shape of the emitted "filtered list".
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.scraper import filter_courses, get_filtered_releases, _parse_date

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Reference "now" chosen so the 2026 fixture dates fall inside/outside windows
# deterministically. Fixture latest-release dates:
#   Advanced Architecting on AWS : 2026-08-06
#   Architecting on AWS          : 2026-09-10
#   Agentic AI Foundations       : 2026-09-30
#   (JA) Advanced Architecting    : 2026-06-01  (excluded by language)
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


@pytest.fixture()
def raw_courses() -> list[dict]:
    payload = json.loads((FIXTURES_DIR / "sample_api_response.json").read_text(encoding="utf-8"))
    return payload["result"]["data"]["json"]


# ---------------------------------------------------------------------------
# Language filtering
# ---------------------------------------------------------------------------

class TestLanguageFilter:
    def test_excludes_non_en(self, raw_courses: list[dict]) -> None:
        # Wide window so only language filters anything out.
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        names_langs = {(c["name"]) for c in result}
        # The JA "Advanced Architecting on AWS" must not appear as a JA entry;
        # there is an EN one with the same name, so assert count of JA excluded
        # by checking total EN courses == 3.
        assert len(result) == 3

    def test_only_en_versions_considered(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        # The retained "Advanced Architecting on AWS" must be the EN 3.11.7 one.
        adv = next(c for c in result if c["name"] == "Advanced Architecting on AWS")
        assert adv["version"] == "3.11.7"


# ---------------------------------------------------------------------------
# Recency filtering
# ---------------------------------------------------------------------------

class TestRecencyFilter:
    def test_keeps_within_window(self, raw_courses: list[dict]) -> None:
        # 7-day window from 2026-10-01 → cutoff 2026-09-24.
        # Only Agentic AI (2026-09-30) qualifies.
        result = filter_courses(raw_courses, lookback_days=7, now=NOW)
        names = {c["name"] for c in result}
        assert names == {"Agentic AI Foundations"}

    def test_wider_window_keeps_more(self, raw_courses: list[dict]) -> None:
        # 30-day window from 2026-10-01 → cutoff 2026-09-01.
        # Agentic AI (09-30) and Architecting (09-10) qualify; Advanced (08-06) does not.
        result = filter_courses(raw_courses, lookback_days=30, now=NOW)
        names = {c["name"] for c in result}
        assert names == {"Agentic AI Foundations", "Architecting on AWS"}

    def test_boundary_exactly_cutoff_is_kept(self) -> None:
        raw = [{
            "name": "Edge Course", "language": "EN", "version": "1.0.0",
            "versions": [{"version": "1.0.0", "released": "2026-09-24T00:00:00.000Z", "notes": "n"}],
        }]
        # cutoff for 7-day window from 2026-10-01 is exactly 2026-09-24
        result = filter_courses(raw, lookback_days=7, now=NOW)
        assert len(result) == 1

    def test_empty_when_nothing_recent(self, raw_courses: list[dict]) -> None:
        # 0-day window from 2026-10-01 → cutoff 2026-10-01; newest release is
        # 2026-09-30, so nothing qualifies.
        result = filter_courses(raw_courses, lookback_days=0, now=NOW)
        assert result == []


# ---------------------------------------------------------------------------
# Version trimming / emitted shape
# ---------------------------------------------------------------------------

class TestVersionTrimAndShape:
    def test_previous_version_from_versions_1(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        agentic = next(c for c in result if c["name"] == "Agentic AI Foundations")
        assert agentic["version"] == "1.1.9"
        assert agentic["previous_version"] == "1.0.0"

    def test_previous_version_empty_when_single_version(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        arch = next(c for c in result if c["name"] == "Architecting on AWS")
        assert arch["previous_version"] == ""

    def test_entry_has_required_fields(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        required = {"name", "version", "previous_version", "released", "notes"}
        for c in result:
            assert required == set(c.keys())

    def test_released_is_normalised_date(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        for c in result:
            assert len(c["released"]) == 10
            assert c["released"].count("-") == 2

    def test_notes_from_latest_version(self, raw_courses: list[dict]) -> None:
        result = filter_courses(raw_courses, lookback_days=100000, now=NOW)
        adv = next(c for c in result if c["name"] == "Advanced Architecting on AWS")
        assert adv["notes"] == "Lab-4: Updated permissions to resolve crawler issues."

    def test_course_with_no_versions_skipped(self) -> None:
        raw = [{"name": "Empty", "language": "EN", "versions": []}]
        assert filter_courses(raw, lookback_days=100000, now=NOW) == []


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid(self) -> None:
        assert _parse_date("2026-08-06").isoformat() == "2026-08-06"

    def test_empty_returns_none(self) -> None:
        assert _parse_date("") is None

    def test_garbage_returns_none(self) -> None:
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# get_filtered_releases (HTTP mocked)
# ---------------------------------------------------------------------------

class TestGetFilteredReleases:
    def test_fetches_and_filters(self, raw_courses: list[dict]) -> None:
        payload = {"result": {"data": {"json": raw_courses}}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            result = get_filtered_releases(lookback_days=30, now=NOW)

        names = {c["name"] for c in result}
        assert names == {"Agentic AI Foundations", "Architecting on AWS"}

    def test_raises_on_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("503")
        with patch("src.scraper.requests.get", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                get_filtered_releases(lookback_days=7, now=NOW)

    def test_raises_on_unexpected_shape(self) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"unexpected": "shape"}
        mock_resp.raise_for_status = MagicMock()
        with patch("src.scraper.requests.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="Unexpected API response structure"):
                get_filtered_releases(lookback_days=7, now=NOW)
