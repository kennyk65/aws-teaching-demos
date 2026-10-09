"""
test_diff.py – Unit tests for the diff / state-comparison module.

Course identity is keyed on the normalised course NAME, not SKU.
SKUs can and do change when a major version is released; using name ensures
the same course is recognised regardless of SKU changes.

Major vs. minor classification uses version_sort:
  version_sort = major * 1_000_000 + minor * 1_000 + patch
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.diff import _identity_key, _is_major_bump, compute_diff

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def state_v1() -> dict:
    return json.loads((FIXTURES_DIR / "state_v1.json").read_text(encoding="utf-8"))


@pytest.fixture()
def state_v2() -> dict:
    return json.loads((FIXTURES_DIR / "state_v2.json").read_text(encoding="utf-8"))


def _make_catalog(*courses) -> dict:
    return {"scraped_at": "2026-01-01T00:00:00+00:00", "courses": list(courses)}


def _course(
    name: str = "Test Course",
    version: str = "1.0.0",
    version_sort: int = 1_000_000,
    sku: str = "SKU-TEST-10-EN",
) -> dict:
    return {
        "name": name,
        "language": "EN",
        "modality": "ILT",
        "version": version,
        "version_sort": version_sort,
        "released": "2026-01-01",
        "sku": sku,
        "notes": "Test notes.",
    }


# ---------------------------------------------------------------------------
# Identical states
# ---------------------------------------------------------------------------

class TestIdenticalStates:
    def test_no_changes_when_catalogs_match(self, state_v1: dict) -> None:
        result = compute_diff(state_v1, state_v1)
        assert result["new_courses"] == []
        assert result["major_updates"] == []
        assert result["minor_updates"] == []

    def test_empty_catalogs_produce_no_changes(self) -> None:
        empty = _make_catalog()
        result = compute_diff(empty, empty)
        assert result == {"new_courses": [], "major_updates": [], "minor_updates": []}


# ---------------------------------------------------------------------------
# New courses
# ---------------------------------------------------------------------------

class TestNewCourses:
    def test_detects_new_course_by_name(self) -> None:
        prev = _make_catalog(_course(name="Course A"))
        curr = _make_catalog(_course(name="Course A"), _course(name="Course B"))
        result = compute_diff(prev, curr)
        assert len(result["new_courses"]) == 1
        assert result["new_courses"][0]["name"] == "Course B"

    def test_same_name_different_sku_is_update_not_new(self) -> None:
        """SKU changes on a major version bump — must be treated as an update."""
        prev = _make_catalog(_course(name="Developing on AWS", version="4.2.1",
                                     version_sort=4_002_001, sku="ILT-TF-300-DEVAWS-42-EN"))
        curr = _make_catalog(_course(name="Developing on AWS", version="5.0.0",
                                     version_sort=5_000_000, sku="ILT-TF-300-DEVAWS-50-EN"))
        result = compute_diff(prev, curr)
        assert result["new_courses"] == []
        assert len(result["major_updates"]) == 1

    def test_multiple_new_courses(self) -> None:
        prev = _make_catalog(_course(name="Course A"))
        curr = _make_catalog(
            _course(name="Course A"),
            _course(name="Course B"),
            _course(name="Course C"),
        )
        result = compute_diff(prev, curr)
        assert len(result["new_courses"]) == 2

    def test_new_course_contains_all_fields(self) -> None:
        prev = _make_catalog()
        new_c = _course(name="Brand New Course")
        curr = _make_catalog(new_c)
        result = compute_diff(prev, curr)
        assert result["new_courses"][0] == new_c

    def test_course_removed_from_current_not_flagged(self) -> None:
        prev = _make_catalog(_course(name="Course A"), _course(name="Course B"))
        curr = _make_catalog(_course(name="Course A"))
        result = compute_diff(prev, curr)
        assert result == {"new_courses": [], "major_updates": [], "minor_updates": []}


# ---------------------------------------------------------------------------
# Major version updates
# ---------------------------------------------------------------------------

class TestMajorUpdates:
    def test_detects_major_version_bump(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="3.0.0",
                                     version_sort=3_000_000, sku="SKU-X-30"))
        curr = _make_catalog(_course(name="Course X", version="4.0.0",
                                     version_sort=4_000_000, sku="SKU-X-40"))
        result = compute_diff(prev, curr)
        assert len(result["major_updates"]) == 1
        assert result["major_updates"][0]["version"] == "4.0.0"

    def test_major_update_includes_previous_version(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="3.0.0",
                                     version_sort=3_000_000, sku="SKU-X-30"))
        curr = _make_catalog(_course(name="Course X", version="4.0.0",
                                     version_sort=4_000_000, sku="SKU-X-40"))
        result = compute_diff(prev, curr)
        assert result["major_updates"][0]["previous_version"] == "3.0.0"

    def test_major_update_not_in_minor_list(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="3.0.0",
                                     version_sort=3_000_000, sku="SKU-X-30"))
        curr = _make_catalog(_course(name="Course X", version="4.0.0",
                                     version_sort=4_000_000, sku="SKU-X-40"))
        result = compute_diff(prev, curr)
        assert result["minor_updates"] == []


# ---------------------------------------------------------------------------
# Minor version updates
# ---------------------------------------------------------------------------

class TestMinorUpdates:
    def test_detects_minor_version_bump(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="3.10.0",
                                     version_sort=3_010_000, sku="SKU-X-310"))
        curr = _make_catalog(_course(name="Course X", version="3.11.7",
                                     version_sort=3_011_007, sku="SKU-X-311"))
        result = compute_diff(prev, curr)
        assert len(result["minor_updates"]) == 1
        assert result["minor_updates"][0]["version"] == "3.11.7"

    def test_patch_bump_classified_as_minor(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="7.0.4",
                                     version_sort=7_000_004, sku="SKU-X-704"))
        curr = _make_catalog(_course(name="Course X", version="7.0.5",
                                     version_sort=7_000_005, sku="SKU-X-705"))
        result = compute_diff(prev, curr)
        assert len(result["minor_updates"]) == 1

    def test_minor_update_includes_previous_version(self) -> None:
        prev = _make_catalog(_course(name="Course X", version="3.10.0",
                                     version_sort=3_010_000, sku="SKU-X-310"))
        curr = _make_catalog(_course(name="Course X", version="3.11.7",
                                     version_sort=3_011_007, sku="SKU-X-311"))
        result = compute_diff(prev, curr)
        assert result["minor_updates"][0]["previous_version"] == "3.10.0"


# ---------------------------------------------------------------------------
# Combined diff using real fixtures
# ---------------------------------------------------------------------------

class TestFixtureDiff:
    def test_v1_to_v2_new_course(self, state_v1: dict, state_v2: dict) -> None:
        result = compute_diff(state_v1, state_v2)
        new_names = [c["name"] for c in result["new_courses"]]
        assert "Agentic AI Foundations" in new_names

    def test_v1_to_v2_major_update(self, state_v1: dict, state_v2: dict) -> None:
        result = compute_diff(state_v1, state_v2)
        # Developing on AWS: 4.2.1 → 5.0.0  (major component 4 → 5)
        major_names = [c["name"] for c in result["major_updates"]]
        assert "Developing on AWS" in major_names

    def test_v1_to_v2_major_update_sku_changed(self, state_v1: dict, state_v2: dict) -> None:
        """Verify the major update is detected even though the SKU changed."""
        result = compute_diff(state_v1, state_v2)
        dev = next(c for c in result["major_updates"] if c["name"] == "Developing on AWS")
        assert dev["previous_version"] == "4.2.1"
        assert dev["version"] == "5.0.0"

    def test_v1_to_v2_minor_updates(self, state_v1: dict, state_v2: dict) -> None:
        result = compute_diff(state_v1, state_v2)
        minor_names = [c["name"] for c in result["minor_updates"]]
        # Advanced Architecting: 3.10.0 → 3.11.7 (same major=3)
        assert "Advanced Architecting on AWS" in minor_names
        # Architecting on AWS: 7.0.4 → 7.0.5 (patch)
        assert "Architecting on AWS" in minor_names

    def test_v1_to_v2_unchanged_course_not_flagged(self, state_v1: dict, state_v2: dict) -> None:
        result = compute_diff(state_v1, state_v2)
        all_changed = (
            [c["name"] for c in result["new_courses"]]
            + [c["name"] for c in result["major_updates"]]
            + [c["name"] for c in result["minor_updates"]]
        )
        assert "AWS Security Essentials" not in all_changed

    def test_v1_to_v2_total_change_count(self, state_v1: dict, state_v2: dict) -> None:
        result = compute_diff(state_v1, state_v2)
        total = (
            len(result["new_courses"])
            + len(result["major_updates"])
            + len(result["minor_updates"])
        )
        assert total == 4  # 1 new + 1 major + 2 minor


# ---------------------------------------------------------------------------
# _identity_key
# ---------------------------------------------------------------------------

class TestIdentityKey:
    def test_uses_course_name(self) -> None:
        c = _course(name="Advanced Architecting on AWS", sku="ILT-TF-300-ADVARC-311-EN")
        assert _identity_key(c) == "advanced architecting on aws"

    def test_lowercases_name(self) -> None:
        c = _course(name="AWS Security Essentials", sku="ANY-SKU")
        assert _identity_key(c) == "aws security essentials"

    def test_strips_whitespace(self) -> None:
        c = {**_course(), "name": "  Developing on AWS  "}
        assert _identity_key(c) == "developing on aws"

    def test_different_skus_same_name_are_equal(self) -> None:
        """A course whose SKU changed (major bump) must still match itself."""
        old = _course(name="Developing on AWS", version="4.2.1",
                      version_sort=4_002_001, sku="ILT-TF-300-DEVAWS-42-EN")
        new = _course(name="Developing on AWS", version="5.0.0",
                      version_sort=5_000_000, sku="ILT-TF-300-DEVAWS-50-EN")
        assert _identity_key(old) == _identity_key(new)


# ---------------------------------------------------------------------------
# _is_major_bump
# ---------------------------------------------------------------------------

class TestIsMajorBump:
    def test_major_component_change_is_major(self) -> None:
        prev = _course(version_sort=3_000_000)
        curr = _course(version_sort=4_000_000)
        assert _is_major_bump(prev, curr) is True

    def test_minor_component_change_is_not_major(self) -> None:
        prev = _course(version_sort=3_010_000)
        curr = _course(version_sort=3_011_007)
        assert _is_major_bump(prev, curr) is False

    def test_patch_only_change_is_not_major(self) -> None:
        prev = _course(version_sort=7_000_004)
        curr = _course(version_sort=7_000_005)
        assert _is_major_bump(prev, curr) is False
