"""
detection.py – Parses and validates the output of Model Call #1.

Change detection is performed by the model (see
``bedrock_service.detect_releases``). This module is the code-side safety net:
it extracts the JSON from the model's raw text response, validates the schema,
and normalises it into the canonical structure the formatting step consumes.

Canonical structure (a flat list of reported major/minor releases):

[
    {
        "name":             "Advanced Architecting on AWS",
        "version":          "3.11.7",
        "previous_version": "3.10.0",
        "released":         "2026-08-06",
        "notes":            "Lab-4: ...",
    },
    ...
]

The model is asked to return a JSON object of the form
``{"releases": [ ... ]}``; a bare top-level array is also accepted. Malformed
or chatty output degrades to an empty list (fail-safe → "no releases").
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_detection(raw_response: str) -> list[dict[str, Any]]:
    """
    Parse the model's detection *raw_response* into the canonical list of
    reported releases. Fails safe to an empty list on any parse/validation
    problem.
    """
    data = _extract_json(raw_response)
    if data is None:
        logger.warning("Could not parse JSON from detection response; treating as no releases.")
        return []

    # Accept {"releases": [...]} or a bare [...] array.
    if isinstance(data, dict):
        entries = data.get("releases", [])
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    if not isinstance(entries, list):
        logger.warning("Detection 'releases' is not a list; treating as no releases.")
        return []

    releases: list[dict[str, Any]] = []
    for entry in entries:
        normalised = _normalise_entry(entry)
        if normalised is not None:
            releases.append(normalised)

    logger.info("Parsed detection: %d release(s).", len(releases))
    return releases


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Any | None:
    """
    Extract and parse the first JSON value (object or array) from *text*.
    Handles clean JSON, ```json fences, and surrounding prose.
    """
    if not text:
        return None

    # Strip a markdown code fence if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    span = _first_balanced_span(candidate)
    if span is None:
        return None
    try:
        return json.loads(span)
    except json.JSONDecodeError:
        return None


def _first_balanced_span(text: str) -> str | None:
    """
    Return the first balanced ``{...}`` or ``[...]`` span in *text*, respecting
    strings and escapes, or None if none is found.
    """
    first_obj = text.find("{")
    first_arr = text.find("[")
    candidates = [i for i in (first_obj, first_arr) if i != -1]
    if not candidates:
        return None
    start = min(candidates)
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _normalise_entry(entry: Any) -> dict[str, Any] | None:
    """Normalise one reported release; return None if it has no usable name."""
    if not isinstance(entry, dict):
        logger.warning("Skipping non-dict detection entry: %r", entry)
        return None

    name = str(entry.get("name", "")).strip()
    if not name:
        logger.warning("Skipping detection entry with no name: %r", entry)
        return None

    return {
        "name":             name,
        "version":          str(entry.get("version", "")).strip(),
        "previous_version": str(entry.get("previous_version", "")).strip(),
        "released":         str(entry.get("released", "")).strip(),
        "notes":            str(entry.get("notes", "")).strip(),
    }
