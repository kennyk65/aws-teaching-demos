"""
bedrock_service.py – Amazon Bedrock client wrapper for release note summarisation.

Supports both Anthropic Claude (messages API) and Amazon Titan (completions API).
The model used is controlled by the BEDROCK_MODEL_ID environment variable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_bedrock_client = None  # module-level singleton; replaced in tests via dependency injection


def _get_client():
    global _bedrock_client  # noqa: PLW0603
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime")
    return _bedrock_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarise_changes(
    diff_result: dict[str, Any],
    model_id: str,
    *,
    client=None,
) -> str:
    """
    Build a prompt from *diff_result* and invoke Bedrock for a structured summary.

    Parameters
    ----------
    diff_result : dict
        Output of ``diff.compute_diff()`` with keys
        ``new_courses``, ``major_updates``, ``minor_updates``.
    model_id : str
        Bedrock foundation model ID (e.g. ``anthropic.claude-3-5-sonnet-…``).
    client : optional
        Injected boto3 bedrock-runtime client (used in tests).

    Returns
    -------
    str
        Plain-text / Markdown summary produced by the model.
    """
    bedrock = client or _get_client()
    prompt = build_prompt(diff_result)
    logger.info("Invoking Bedrock model %s …", model_id)

    if model_id.startswith("anthropic."):
        response_text = _invoke_claude(bedrock, model_id, prompt)
    elif model_id.startswith("amazon.titan"):
        response_text = _invoke_titan(bedrock, model_id, prompt)
    else:
        # Covers Amazon Nova (us.amazon.nova-*), Meta Llama, Mistral, and any
        # cross-region inference profile (us.* / eu.* / ap.*) — all use the
        # Bedrock Converse API.
        response_text = _invoke_converse(bedrock, model_id, prompt)

    logger.info("Bedrock summarisation complete (%d chars).", len(response_text))
    return response_text


def build_prompt(diff_result: dict[str, Any]) -> str:
    """
    Construct the summarisation prompt from the diff result.

    Each changed course entry is presented with:
      - Course name, version transition (or "new"), and release date
      - The full latest_version_entry.notes text (verbatim from the API)

    Bedrock is then asked to add an executive summary and highlight anything
    particularly significant — the raw data is always present regardless.

    This function is kept separate so it can be tested without a live model.
    """
    new_courses = diff_result.get("new_courses", [])
    major_updates = diff_result.get("major_updates", [])
    minor_updates = diff_result.get("minor_updates", [])

    sections: list[str] = []

    if new_courses:
        lines = []
        for c in new_courses:
            lv = c.get("latest_version_entry", {})
            lines.append(
                f"### {c['name']}\n"
                f"Version: {lv.get('version', c.get('version', 'N/A'))}  |  "
                f"Released: {lv.get('released', c.get('released', 'N/A'))}\n\n"
                f"{lv.get('notes', c.get('notes', '(no notes)'))}"
            )
        sections.append("## NEW COURSES\n\n" + "\n\n---\n\n".join(lines))

    if major_updates:
        lines = []
        for c in major_updates:
            lv = c.get("latest_version_entry", {})
            lines.append(
                f"### {c['name']}\n"
                f"Version: {c.get('previous_version', '?')} → {lv.get('version', c.get('version', 'N/A'))}  |  "
                f"Released: {lv.get('released', c.get('released', 'N/A'))}\n\n"
                f"{lv.get('notes', c.get('notes', '(no notes)'))}"
            )
        sections.append("## MAJOR VERSION UPDATES\n\n" + "\n\n---\n\n".join(lines))

    if minor_updates:
        lines = []
        for c in minor_updates:
            lv = c.get("latest_version_entry", {})
            lines.append(
                f"### {c['name']}\n"
                f"Version: {c.get('previous_version', '?')} → {lv.get('version', c.get('version', 'N/A'))}  |  "
                f"Released: {lv.get('released', c.get('released', 'N/A'))}\n\n"
                f"{lv.get('notes', c.get('notes', '(no notes)'))}"
            )
        sections.append("## MINOR VERSION UPDATES\n\n" + "\n\n---\n\n".join(lines))

    change_detail = "\n\n".join(sections)

    prompt = f"""You are an AWS Training & Certification update reporter.

The following course changes were detected since the last check. The raw release
details (name, version, release date, and release notes) are provided verbatim
from the AWS releases API — include them in your response exactly as shown.

{change_detail}

---

After the course details above, add the following section:

## Executive Summary
Write 2-3 sentences summarising the overall scope of changes (how many courses
updated, mix of major/minor/new, any notable themes). Keep it concise and
professional."""

    return prompt


# ---------------------------------------------------------------------------
# Model-specific invocation helpers
# ---------------------------------------------------------------------------

def _invoke_claude(client, model_id: str, prompt: str) -> str:
    """Invoke an Anthropic Claude model via the native messages API."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
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
            "maxTokenCount": 1024,
            "temperature": 0.3,
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
    """Generic fallback using the Bedrock Converse API."""
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.3},
    )
    return response["output"]["message"]["content"][0]["text"]
