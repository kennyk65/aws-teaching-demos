"""
test_parser.py – Unit tests for the API-based scraper module.

The scraper no longer parses HTML; it calls the JSON API at
  https://releases.awstc.com/backend/courses.list?input=...
and returns a filtered, flattened catalog dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.scraper import (
    _extract_courses,
    _fetch_courses,
    _normalise_date,
    scrape_catalog,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_payload() -> dict:
    return json.loads((FIXTURES_DIR / "sample_api_response.json").read_text(encoding="utf-8"))


@pytest.fixture()
def raw_courses(api_payload: dict) -> list[dict]:
    return api_payload["result"]["data"]["json"]


# ---------------------------------------------------------------------------
# _fetch_courses
# ---------------------------------------------------------------------------

class TestFetchCourses:
    def test_returns_list_of_courses(self, api_payload: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_payload
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            courses = _fetch_courses("https://example.com")

        assert isinstance(courses, list)
        assert len(courses) == 4  # all languages in fixture

    def test_raises_on_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("503")

        with patch("src.scraper.requests.get", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                _fetch_courses("https://example.com")

    def test_raises_on_unexpected_response_shape(self) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"unexpected": "shape"}
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="Unexpected API response structure"):
                _fetch_courses("https://example.com")


# ---------------------------------------------------------------------------
# _extract_courses
# ---------------------------------------------------------------------------

class TestExtractCourses:
    def test_filters_to_en_only(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        assert all(c["language"] == "EN" for c in en)

    def test_correct_en_count(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        assert len(en) == 3  # fixture has 3 EN + 1 JA

    def test_notes_taken_from_versions_0(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        adv = next(c for c in en if "Advanced Architecting" in c["name"])
        assert adv["notes"] == "Lab-4: Updated permissions to resolve crawler issues."

    def test_course_has_all_required_fields(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        required = {"name", "language", "modality", "version", "version_sort",
                    "released", "sku", "notes", "latest_version_entry"}
        for course in en:
            assert required.issubset(course.keys()), f"Missing keys in {course}"

    def test_latest_version_entry_has_required_fields(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        for course in en:
            lv = course["latest_version_entry"]
            assert {"version", "released", "notes"}.issubset(lv.keys())

    def test_latest_version_entry_version_matches_top_level(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        for course in en:
            assert course["latest_version_entry"]["version"] == course["version"]

    def test_latest_version_entry_notes_matches_notes_field(self, raw_courses: list[dict]) -> None:
        en = _extract_courses(raw_courses, language="EN")
        adv = next(c for c in en if "Advanced Architecting" in c["name"])
        assert adv["latest_version_entry"]["notes"] == adv["notes"]

    def test_released_date_is_normalised(self, raw_courses: list[dict]) -> None:
        """released should be YYYY-MM-DD, not a full ISO datetime."""
        en = _extract_courses(raw_courses, language="EN")
        for course in en:
            assert len(course["released"]) == 10
            assert course["released"].count("-") == 2

    def test_ja_filter(self, raw_courses: list[dict]) -> None:
        ja = _extract_courses(raw_courses, language="JA")
        assert len(ja) == 1
        assert ja[0]["language"] == "JA"

    def test_empty_input_returns_empty_list(self) -> None:
        assert _extract_courses([], language="EN") == []

    def test_course_with_no_versions_has_empty_notes(self) -> None:
        raw = [{"name": "Test", "language": "EN", "modality": "ILT",
                "version": "1.0.0", "version_sort": 1000000,
                "released": "2026-01-01T00:00:00.000Z",
                "sku": "SKU-TEST", "versions": []}]
        result = _extract_courses(raw, language="EN")
        assert result[0]["notes"] == ""
        assert result[0]["latest_version_entry"]["notes"] == ""


# ---------------------------------------------------------------------------
# _normalise_date
# ---------------------------------------------------------------------------

class TestNormaliseDate:
    @pytest.mark.parametrize("raw,expected", [
        ("2026-08-06T00:00:00.000Z", "2026-08-06"),
        ("2024-01-15T00:00:00.000Z", "2024-01-15"),
        ("2026-08-06",               "2026-08-06"),  # already short
        ("",                         ""),
    ])
    def test_normalise(self, raw: str, expected: str) -> None:
        assert _normalise_date(raw) == expected


# ---------------------------------------------------------------------------
# scrape_catalog (integration-style, HTTP mocked)
# ---------------------------------------------------------------------------

class TestScrapeCatalog:
    def test_returns_dict_with_scraped_at_and_courses(self, api_payload: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_payload
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            catalog = scrape_catalog()

        assert "scraped_at" in catalog
        assert "courses" in catalog
        assert len(catalog["courses"]) == 3  # 3 EN entries in fixture

    def test_scraped_at_is_iso_string(self, api_payload: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_payload
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            catalog = scrape_catalog()

        from datetime import datetime
        datetime.fromisoformat(catalog["scraped_at"])

    def test_language_filter_applied(self, api_payload: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = api_payload
        mock_resp.raise_for_status = MagicMock()

        with patch("src.scraper.requests.get", return_value=mock_resp):
            catalog = scrape_catalog(language="JA")

        assert len(catalog["courses"]) == 1
        assert catalog["courses"][0]["language"] == "JA"
