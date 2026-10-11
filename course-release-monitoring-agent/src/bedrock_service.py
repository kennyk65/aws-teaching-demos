"""
bedrock_service.py – Amazon Bedrock client wrapper (two model calls).

  1. detect_releases(filtered_list, model_id)
     Model Call #1. Given the code-filtered recent-releases list (each entry
     has current version + previous version), the model returns ONLY the major
     and minor releases as JSON. Patch releases MUST be excluded.

  2. format_email_body(releases, model_id)
     Model Call #2. Formats the detected releases into the plain-text
     ``▶ RECENT RELEASES`` section of the email (header/footer added in code).

Supports Anthropic Claude (messages API), Amazon Titan (completions API), and
Amazon Nova / any model reachable via the Bedrock Converse API. The model is
selected via the BEDROCK_MODEL_ID environment variable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Section width used for the rule line under section headers.
_WIDTH = 54

_bedrock_client = None  # module-level singleton; injectable in tests


def _get_client():
    global _bedrock_client  # noqa: PLW0603
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime")
    return _bedrock_client


# ---------------------------------------------------------------------------
# Model Call #1 — detect major/minor releases
# ---------------------------------------------------------------------------

def detect_releases(
    filtered_list: list[dict[str, Any]],
    model_id: str,
    *,
    client=None,
) -> str:
    """
    Invoke Bedrock to classify the filtered list and return ONLY the major and
    minor releases as a JSON string (patch releases excluded).

    Returns the model's raw text response; parse with
    ``detection.parse_detection``.
    """
    prompt = build_detection_prompt(filtered_list)
    logger.info("Invoking Bedrock model %s for release detection …", model_id)
    response_text = _invoke_model(model_id, prompt, client=client)
    logger.info("Bedrock detection complete (%d chars).", len(response_text))
    return response_text.strip()


def build_detection_prompt(filtered_list: list[dict[str, Any]]) -> str:
    """
    Build the Model Call #1 prompt. The filtered list is supplied as JSON; the
    model classifies each course by comparing its current ``version`` against
    its ``previous_version`` and returns only major/minor releases.
    """
    data = json.dumps(_detection_rows(filtered_list), indent=2, ensure_ascii=False)

    prompt = f"""You review a list of recently released AWS Training & Certification courses
and report ONLY the ones whose latest release is a MAJOR or MINOR release.

Each course below has a current "version" and the immediately prior
"previous_version". Versions use the form MAJOR.MINOR.PATCH (e.g. "3.11.7" →
major=3, minor=11, patch=7). Split BOTH versions on the dots and compare each
component:

  • MAJOR release — the MAJOR (first) number changed  (e.g. 4.2.1 → 5.0.0)  → REPORT
  • MINOR release — MAJOR same, MINOR (second) changed (e.g. 3.10.8 → 3.11.0) → REPORT
  • PATCH release — MAJOR and MINOR both same, only PATCH (third) changed
                    (e.g. 7.0.4 → 7.0.5)                                     → DO NOT REPORT
  • If "previous_version" is empty, the course is brand new                  → REPORT

*** A PATCH RELEASE IS NOT REPORTABLE. ***
If MAJOR and MINOR are identical and only the PATCH (third) number differs, the
course MUST be omitted entirely. We do not care about patch releases. This is
the single most important rule.

Worked examples:
  "4.2.1"  → "5.0.0"   major 4→5                 → MAJOR  → REPORT
  "3.10.0" → "3.11.7"  major same, minor 10→11   → MINOR  → REPORT
  "7.0.4"  → "7.0.5"   major & minor same, patch → PATCH  → OMIT
  "1.4.9"  → "1.4.12"  major & minor same, patch → PATCH  → OMIT
  ""       → "1.0.0"   brand new course          → REPORT

COURSES:
{data}

Produce a SINGLE JSON object of the form:

{{
  "releases": [
    {{
      "name":             "<course name>",
      "version":          "<current version>",
      "previous_version": "<previous version, or empty string if new>",
      "released":         "<YYYY-MM-DD>",
      "notes":            "<release notes, verbatim>"
    }}
  ]
}}

Final checks before answering:
- Did you OMIT every course whose only version difference is the PATCH number?
- Does every reported course have a changed MAJOR or MINOR number (or no previous version)?
- Output ONLY the JSON object — no prose, no markdown fences, no backticks."""

    return prompt


def _detection_rows(filtered_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape the filtered list into compact rows for the detection prompt."""
    rows = []
    for c in filtered_list:
        rows.append({
            "name": c.get("name", ""),
            "version": c.get("version", ""),
            "previous_version": c.get("previous_version", ""),
            "released": c.get("released", ""),
            "notes": c.get("notes", ""),
        })
    return rows


# ---------------------------------------------------------------------------
# Model Call #2 — format the email body
# ---------------------------------------------------------------------------

def format_email_body(
    releases: list[dict[str, Any]],
    model_id: str,
    *,
    client=None,
) -> str:
    """
    Invoke Bedrock to render the detected *releases* as the plain-text
    ``▶ RECENT RELEASES`` section. The header/footer are added by the caller.
    """
    prompt = build_format_prompt(releases)
    logger.info("Invoking Bedrock model %s for email formatting …", model_id)
    response_text = _invoke_model(model_id, prompt, client=client)
    logger.info("Bedrock formatting complete (%d chars).", len(response_text))
    return response_text.strip()


def build_format_prompt(releases: list[dict[str, Any]]) -> str:
    """Build the Model Call #2 formatting prompt."""
    data = json.dumps(releases, indent=2, ensure_ascii=False)
    rule_light = "─" * _WIDTH

    prompt = f"""You format a list of AWS Training & Certification course releases into a
plain-text email body section.

RELEASES (JSON):
{data}

Produce ONLY the body section as PLAIN TEXT, following these rules EXACTLY:

1. Begin with the section header line followed by a rule line:
   ▶ RECENT RELEASES
   {rule_light}
2. For each release, render:
     <two-space indent><Course Name><spaces><version label>
     <two-space indent>Released: <YYYY-MM-DD>
     <blank line>
     <two-space indent><release notes, verbatim, wrapped to ~{_WIDTH} chars>
3. The version label shows the transition: "v<previous_version> → v<version>".
   If previous_version is empty, show just "v<version>".
4. Separate multiple releases with a line: "  ·  ·  ·"
5. Do NOT include any counts or totals, an executive summary, a header banner,
   a footer, or a modality label (e.g. "ILT").
6. Reproduce the release notes verbatim — do not summarise or rewrite them.
7. Output plain text only — no markdown code fences, no backticks."""

    return prompt


# ---------------------------------------------------------------------------
# Shared model dispatch
# ---------------------------------------------------------------------------

def _invoke_model(model_id: str, prompt: str, *, client=None) -> str:
    """Dispatch *prompt* to the correct model family and return the text."""
    bedrock = client or _get_client()
    if model_id.startswith("anthropic."):
        return _invoke_claude(bedrock, model_id, prompt)
    if model_id.startswith("amazon.titan"):
        return _invoke_titan(bedrock, model_id, prompt)
    # Amazon Nova (us.amazon.nova-*), Meta Llama, Mistral, and cross-region
    # inference profiles (us.* / eu.* / ap.*) all use the Converse API.
    return _invoke_converse(bedrock, model_id, prompt)


def _invoke_claude(client, model_id: str, prompt: str) -> str:
    """Invoke an Anthropic Claude model via the native messages API."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def _invoke_titan(client, model_id: str, prompt: str) -> str:
    """Invoke an Amazon Titan Text model."""
    body = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 4096,
            "temperature": 0.2,
            "topP": 0.9,
        },
    }
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["results"][0]["outputText"]


def _invoke_converse(client, model_id: str, prompt: str) -> str:
    """Generic Bedrock Converse API call (Nova, Llama, Mistral, etc.)."""
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 4096, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"]
