"""
scraper.py – Fetches and filters course release data from the AWS T&C API.

The page at https://releases.awstc.com is a JavaScript SPA; the data is served
by a JSON endpoint:

  GET https://releases.awstc.com/backend/courses.list?language=EN

This module performs ALL code-side filtering (spec §4.1), producing the
"filtered list" that is sent to the model:

  1. Keep only English (`language = "EN"`) courses.
  2. Keep only courses whose latest release date is within the recency window
     (on or after  current_utc_date − LOOKBACK_DAYS).
  3. Trim each retained course to its latest two versions, so the current and
     immediately-previous version can be compared by the model.

Each entry in the returned filtered list has:
{
    "name":             "Advanced Architecting on AWS",
    "version":          "3.11.7",      # current (versions[0])
    "previous_version": "3.11.6",      # versions[1].version, or "" if only one
    "released":         "2026-08-06",  # current release date (YYYY-MM-DD)
    "notes":            "Lab-4: ...",  # current release notes (versions[0])
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The tRPC / JSON endpoint that the SPA fetches internally.
_INPUT_PARAM = quote('{"json":null,"meta":{"values":["undefined"],"v":1}}')
API_URL = f"https://releases.awstc.com/backend/courses.list?input={_INPUT_PARAM}"

REQUEST_TIMEOUT = 30  # seconds
DEFAULT_LANGUAGE = "EN"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_filtered_releases(
    lookback_days: int,
    *,
    url: str = API_URL,
    language: str = DEFAULT_LANGUAGE,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch the catalog and return the filtered list (spec §4.1).

    Parameters
    ----------
    lookback_days : int
        Recency window size in days.
    url : str
        API endpoint (overridable for tests).
    language : str
        Language filter (default ``"EN"``).
    now : datetime, optional
        Reference "current" time (defaults to UTC now). Injectable for tests.

    Returns
    -------
    list of filtered course dicts (see module docstring).
    """
    raw_courses = _fetch_courses(url)
    filtered = filter_courses(
        raw_courses,
        lookback_days=lookback_days,
        language=language,
        now=now,
    )
    logger.info(
        "Filtered to %d %s course(s) released within the last %d day(s).",
        len(filtered), language, lookback_days,
    )
    return filtered


def filter_courses(
    raw_courses: list[dict[str, Any]],
    *,
    lookback_days: int,
    language: str = DEFAULT_LANGUAGE,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Apply language + recency + version-trim filtering to raw API courses.
    Pure function (no network) so it is directly unit-testable.
    """
    reference = now or datetime.now(tz=timezone.utc)
    cutoff = (reference - timedelta(days=lookback_days)).date()

    result: list[dict[str, Any]] = []
    for raw in raw_courses:
        if raw.get("language", "").upper() != language.upper():
            continue

        versions: list[dict[str, Any]] = raw.get("versions", [])
        if not versions:
            continue

        latest = versions[0]
        released_str = _normalise_date(latest.get("released", raw.get("released", "")))
        released_date = _parse_date(released_str)
        if released_date is None or released_date < cutoff:
            continue  # outside the recency window (or undatable)

        # Trim to the latest two versions: current + immediately previous.
        previous_version = versions[1].get("version", "") if len(versions) > 1 else ""

        result.append({
            "name":             raw.get("name", ""),
            "version":          latest.get("version", raw.get("version", "")),
            "previous_version": previous_version,
            "released":         released_str,
            "notes":            latest.get("notes", ""),
        })

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_courses(url: str) -> list[dict[str, Any]]:
    """Call the JSON API and return the raw list of course objects."""
    logger.info("Fetching courses from %s", url)
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={
            "User-Agent": "aws-course-release-monitor/1.0",
            "Accept": "application/json",
        },
    )
    response.raise_for_status()

    payload: dict[str, Any] = response.json()
    try:
        courses: list[dict[str, Any]] = payload["result"]["data"]["json"]
    except (KeyError, TypeError) as exc:
        logger.error("Unexpected API response structure: %s", exc)
        logger.debug("Response payload: %s", json.dumps(payload)[:2000])
        raise ValueError(f"Unexpected API response structure: {exc}") from exc

    logger.info("API returned %d total course entries (all languages).", len(courses))
    return courses


def _normalise_date(date_str: str) -> str:
    """Truncate an ISO-8601 datetime string to a YYYY-MM-DD date."""
    if not date_str:
        return ""
    return date_str[:10]


def _parse_date(date_str: str):
    """Parse a YYYY-MM-DD string to a date, or None if unparseable."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
