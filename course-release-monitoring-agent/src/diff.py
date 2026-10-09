"""
diff.py – Compares two catalog snapshots and identifies changes.

The catalog uses the real API field names:
  - "name"         : course title
  - "version"      : semantic version string, e.g. "3.11.7"
  - "version_sort" : integer representation, e.g. 3011007 (major * 1_000_000
                     + minor * 1_000 + patch)
  - "sku"          : unique course SKU (used as a stable identity key)

Returns a diff_result dict:
{
    "new_courses":   [ <course dict>, ... ],  # SKUs absent from previous state
    "major_updates": [ <course dict>, ... ],  # same SKU, major version bumped
    "minor_updates": [ <course dict>, ... ],  # same SKU, minor/patch bump only
}
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_diff(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """
    Compare *previous* and *current* catalog snapshots.

    Identity is established by the course ``sku`` field, which is unique per
    course + language + modality combination and stable across version bumps.

    Major vs. minor classification uses ``version_sort``:
      version_sort = major * 1_000_000 + minor * 1_000 + patch
    A change in the *major* component (millions digit block) is a Major update;
    any other version change is Minor.

    Parameters
    ----------
    previous : dict
        Catalog snapshot loaded from S3 (state.json).
    current : dict
        Freshly scraped catalog snapshot.

    Returns
    -------
    dict with keys ``new_courses``, ``major_updates``, ``minor_updates``.
    """
    prev_courses: list[dict[str, Any]] = previous.get("courses", [])
    curr_courses: list[dict[str, Any]] = current.get("courses", [])

    # Build lookup maps keyed by SKU (stable, unique identity).
    # Fall back to normalised name if SKU is absent (e.g. in tests).
    prev_map: dict[str, dict[str, Any]] = {
        _identity_key(c): c for c in prev_courses
    }
    curr_map: dict[str, dict[str, Any]] = {
        _identity_key(c): c for c in curr_courses
    }

    new_courses: list[dict[str, Any]] = []
    major_updates: list[dict[str, Any]] = []
    minor_updates: list[dict[str, Any]] = []

    for key, course in curr_map.items():
        if key not in prev_map:
            new_courses.append(course)
            logger.debug("New course: %s", course.get("name", key))
            continue

        prev_course = prev_map[key]
        if course["version"] != prev_course["version"]:
            augmented = {**course, "previous_version": prev_course["version"]}
            if _is_major_bump(prev_course, course):
                major_updates.append(augmented)
                logger.debug(
                    "Major update: %s  %s → %s",
                    course.get("name", key),
                    prev_course["version"],
                    course["version"],
                )
            else:
                minor_updates.append(augmented)
                logger.debug(
                    "Minor update: %s  %s → %s",
                    course.get("name", key),
                    prev_course["version"],
                    course["version"],
                )

    logger.info(
        "Diff result: new=%d, major=%d, minor=%d",
        len(new_courses),
        len(major_updates),
        len(minor_updates),
    )

    return {
        "new_courses": new_courses,
        "major_updates": major_updates,
        "minor_updates": minor_updates,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _identity_key(course: dict[str, Any]) -> str:
    """
    Return a stable identity key for a course entry.

    Course name is used as the identity key because it is stable across all
    version bumps, including major releases where the SKU changes.
    SKU is intentionally excluded — it encodes the version number and will
    differ between e.g. ``ILT-TF-300-ADVARC-310-EN`` and
    ``ILT-TF-300-ADVARC-311-EN`` for the same course.
    """
    return course.get("name", "").strip().lower()


def _is_major_bump(prev: dict[str, Any], curr: dict[str, Any]) -> bool:
    """
    Return True when the *major* version component changed.

    version_sort encodes:  major * 1_000_000 + minor * 1_000 + patch
    So the major component is  version_sort // 1_000_000.
    """
    prev_sort = int(prev.get("version_sort", 0))
    curr_sort = int(curr.get("version_sort", 0))
    return (curr_sort // 1_000_000) != (prev_sort // 1_000_000)
