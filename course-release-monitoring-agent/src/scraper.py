"""
scraper.py – Fetches course release data from the AWS T&C releases API.

The page at https://releases.awstc.com is a JavaScript SPA; the actual data
is served by a JSON endpoint:

  GET https://releases.awstc.com/backend/courses.list
      ?input={"json":null,"meta":{"values":["undefined"],"v":1}}

Response shape (abbreviated):
{
  "result": {
    "data": {
      "json": [
        {
          "name":         "Advanced Architecting on AWS",
          "language":     "EN",
          "modality":     "ILT",
          "version":      "3.11.7",
          "version_sort": 3011007,
          "released":     "2026-08-06T00:00:00.000Z",
          "sku":          "ILT-TF-300-ADVARC-311-EN",
          "versions": [           # full version history, index 0 = latest
            {
              "name":         "...",
              "language":     "EN",
              "modality":     "ILT",
              "version":      "3.11.7",
              "version_sort": 3011007,
              "released":     "2026-08-06T00:00:00.000Z",
              "sku":          "...",
              "notes":        "Lab-4: Updated permissions ..."
            },
            ...
          ]
        },
        ...
      ]
    }
  }
}

Returns a catalog dict:
{
    "scraped_at": "<ISO-8601 timestamp>",
    "courses": [
        {
            "name":         "Course Title",
            "language":     "EN",
            "modality":     "ILT",
            "version":      "3.11.7",
            "version_sort": 3011007,
            "released":     "2026-08-06",
            "sku":          "ILT-TF-300-ADVARC-311-EN",
            "notes":        "Release notes for the current version.",
            "latest_version_entry": {
                "version":  "3.11.7",
                "released": "2026-08-06",
                "notes":    "Full release notes text for versions[0]."
            }
        },
        ...
    ]
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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

def scrape_catalog(
    url: str = API_URL,
    language: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    """
    Fetch the releases API and return a structured catalog dict filtered to
    *language* (default ``"EN"``).
    """
    raw_courses = _fetch_courses(url)
    courses = _extract_courses(raw_courses, language=language)
    logger.info(
        "Scraped %d %s course entries from API.", len(courses), language
    )
    return {
        "scraped_at": datetime.now(tz=timezone.utc).isoformat(),
        "courses": courses,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_courses(url: str) -> list[dict[str, Any]]:
    """
    Call the JSON API and return the raw list of course objects.
    Raises ``requests.HTTPError`` on non-2xx responses.
    """
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


def _extract_courses(
    raw_courses: list[dict[str, Any]],
    language: str,
) -> list[dict[str, Any]]:
    """
    Filter to *language* and flatten each entry into a canonical course dict.

    The ``notes`` field is taken from ``versions[0]`` (the current release)
    because the top-level object does not carry it.
    """
    result: list[dict[str, Any]] = []
    for raw in raw_courses:
        if raw.get("language", "").upper() != language.upper():
            continue

        # versions[0] is always the current (latest) release entry.
        # We store its full content as "latest_version_entry" so the diff
        # output and notification can surface name / version / date / notes
        # for exactly that entry without re-fetching the API.
        versions: list[dict[str, Any]] = raw.get("versions", [])
        latest = versions[0] if versions else {}
        latest_version_entry = {
            "version":  latest.get("version", raw.get("version", "")),
            "released": _normalise_date(latest.get("released", "")),
            "notes":    latest.get("notes", ""),
        }

        result.append({
            "name":                 raw.get("name", ""),
            "language":             raw.get("language", language),
            "modality":             raw.get("modality", ""),
            "version":              raw.get("version", ""),
            "version_sort":         raw.get("version_sort", 0),
            "released":             _normalise_date(raw.get("released", "")),
            "sku":                  raw.get("sku", ""),
            "notes":                latest_version_entry["notes"],
            "latest_version_entry": latest_version_entry,
        })

    return result


def _normalise_date(date_str: str) -> str:
    """Truncate an ISO-8601 datetime string to a YYYY-MM-DD date."""
    if not date_str:
        return ""
    # e.g. "2026-08-06T00:00:00.000Z" → "2026-08-06"
    return date_str[:10]
