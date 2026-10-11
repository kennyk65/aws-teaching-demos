"""
test_detection.py – Tests for parsing/validating Model Call #1 output.

detection.parse_detection turns the model's raw text response into the
canonical list of reported releases, failing safe to an empty list.
"""

from __future__ import annotations

import json

from src.detection import parse_detection


def _release(name, version, previous="", released="2026-09-25", notes="Notes.") -> dict:
    return {
        "name": name,
        "version": version,
        "previous_version": previous,
        "released": released,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Object form {"releases": [...]}
# ---------------------------------------------------------------------------

class TestParseObjectForm:
    def test_empty_releases(self) -> None:
        assert parse_detection(json.dumps({"releases": []})) == []

    def test_single_release(self) -> None:
        raw = json.dumps({"releases": [_release("Developing on AWS", "5.0.0", "4.2.1")]})
        result = parse_detection(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Developing on AWS"
        assert result[0]["previous_version"] == "4.2.1"

    def test_multiple_releases(self) -> None:
        raw = json.dumps({"releases": [
            _release("A", "2.0.0", "1.9.0"),
            _release("B", "3.1.0", "3.0.5"),
        ]})
        assert len(parse_detection(raw)) == 2

    def test_all_fields_carried(self) -> None:
        raw = json.dumps({"releases": [_release("A", "2.0.0", "1.0.0",
                                                released="2026-01-02", notes="Hi.")]})
        r = parse_detection(raw)[0]
        assert r == {"name": "A", "version": "2.0.0", "previous_version": "1.0.0",
                     "released": "2026-01-02", "notes": "Hi."}


# ---------------------------------------------------------------------------
# Bare array form
# ---------------------------------------------------------------------------

class TestParseArrayForm:
    def test_bare_array_accepted(self) -> None:
        raw = json.dumps([_release("A", "2.0.0", "1.0.0")])
        assert len(parse_detection(raw)) == 1


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_strips_whitespace(self) -> None:
        raw = json.dumps({"releases": [{"name": "  A  ", "version": " 2.0.0 ",
                                        "previous_version": " 1.0.0 ",
                                        "released": " 2026-01-02 ", "notes": "  Hi.  "}]})
        r = parse_detection(raw)[0]
        assert r["name"] == "A"
        assert r["version"] == "2.0.0"
        assert r["notes"] == "Hi."

    def test_entry_without_name_skipped(self) -> None:
        raw = json.dumps({"releases": [{"version": "2.0.0"}, _release("Valid", "1.0.0")]})
        result = parse_detection(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Valid"

    def test_missing_previous_version_defaults_empty(self) -> None:
        raw = json.dumps({"releases": [{"name": "A", "version": "1.0.0",
                                        "released": "2026-01-02", "notes": "n"}]})
        assert parse_detection(raw)[0]["previous_version"] == ""


# ---------------------------------------------------------------------------
# Tolerant extraction
# ---------------------------------------------------------------------------

class TestTolerantExtraction:
    def test_markdown_fence(self) -> None:
        inner = json.dumps({"releases": [_release("A", "2.0.0", "1.0.0")]})
        raw = f"Here you go:\n```json\n{inner}\n```\nThanks!"
        assert len(parse_detection(raw)) == 1

    def test_surrounding_prose(self) -> None:
        inner = json.dumps({"releases": [_release("A", "2.0.0", "1.0.0")]})
        raw = f"Sure. {inner} Done."
        assert len(parse_detection(raw)) == 1

    def test_braces_in_notes(self) -> None:
        raw = json.dumps({"releases": [_release("A", "2.0.0", "1.0.0",
                                                notes="Use the {placeholder} token.")]})
        assert "{placeholder}" in parse_detection(raw)[0]["notes"]


# ---------------------------------------------------------------------------
# Fail-safe
# ---------------------------------------------------------------------------

class TestFailSafe:
    def test_empty_string(self) -> None:
        assert parse_detection("") == []

    def test_non_json(self) -> None:
        assert parse_detection("no releases this week") == []

    def test_malformed_json(self) -> None:
        assert parse_detection('{"releases": [') == []

    def test_releases_not_a_list(self) -> None:
        assert parse_detection(json.dumps({"releases": "nope"})) == []
