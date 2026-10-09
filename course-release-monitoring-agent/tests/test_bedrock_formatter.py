"""
test_bedrock_formatter.py – Tests for Bedrock prompt construction and
model invocation via mocked boto3 clients.

The prompt now includes name, version (with transition), release date, and the
full latest_version_entry.notes verbatim so the notification carries all the
factual information the user needs.
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from src.bedrock_service import build_prompt, summarise_changes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _diff_result(new_courses=None, major_updates=None, minor_updates=None) -> dict:
    return {
        "new_courses":   new_courses   or [],
        "major_updates": major_updates or [],
        "minor_updates": minor_updates or [],
    }


def _new_course() -> dict:
    return {
        "name": "Agentic AI Foundations",
        "language": "EN",
        "modality": "ILT",
        "version": "1.1.9",
        "version_sort": 1_001_009,
        "released": "2026-09-30",
        "sku": "ILT-TF-100-MLAGAF-11-EN",
        "notes": "New hands-on lab added to Module 5.",
        "latest_version_entry": {
            "version": "1.1.9",
            "released": "2026-09-30",
            "notes": "New hands-on lab added to Module 5.",
        },
    }


def _major_update() -> dict:
    return {
        "name": "Developing on AWS",
        "language": "EN",
        "modality": "ILT",
        "version": "5.0.0",
        "version_sort": 5_000_000,
        "released": "2026-09-25",
        "sku": "ILT-TF-300-DEVAWS-EN",
        "notes": "Full course rewrite aligned to the latest AWS SDKs.",
        "latest_version_entry": {
            "version": "5.0.0",
            "released": "2026-09-25",
            "notes": "Full course rewrite aligned to the latest AWS SDKs.",
        },
        "previous_version": "4.2.1",
    }


def _minor_update() -> dict:
    return {
        "name": "Advanced Architecting on AWS",
        "language": "EN",
        "modality": "ILT",
        "version": "3.11.7",
        "version_sort": 3_011_007,
        "released": "2026-08-06",
        "sku": "ILT-TF-300-ADVARC-3-EN",
        "notes": "Lab-4: Updated permissions to resolve crawler issues.",
        "latest_version_entry": {
            "version": "3.11.7",
            "released": "2026-08-06",
            "notes": "Lab-4: Updated permissions to resolve crawler issues.",
        },
        "previous_version": "3.10.0",
    }


# ---------------------------------------------------------------------------
# build_prompt – content presence
# ---------------------------------------------------------------------------

class TestBuildPromptContent:
    def test_contains_new_course_name(self) -> None:
        assert "Agentic AI Foundations" in build_prompt(_diff_result(new_courses=[_new_course()]))

    def test_contains_major_update_name(self) -> None:
        assert "Developing on AWS" in build_prompt(_diff_result(major_updates=[_major_update()]))

    def test_contains_minor_update_name(self) -> None:
        assert "Advanced Architecting on AWS" in build_prompt(_diff_result(minor_updates=[_minor_update()]))

    def test_contains_new_courses_section_header(self) -> None:
        assert "NEW COURSES" in build_prompt(_diff_result(new_courses=[_new_course()]))

    def test_contains_major_section_header(self) -> None:
        assert "MAJOR VERSION UPDATES" in build_prompt(_diff_result(major_updates=[_major_update()]))

    def test_contains_minor_section_header(self) -> None:
        assert "MINOR VERSION UPDATES" in build_prompt(_diff_result(minor_updates=[_minor_update()]))

    def test_contains_version_transition_for_major(self) -> None:
        prompt = build_prompt(_diff_result(major_updates=[_major_update()]))
        assert "4.2.1" in prompt  # previous_version
        assert "5.0.0" in prompt  # new version

    def test_contains_version_transition_for_minor(self) -> None:
        prompt = build_prompt(_diff_result(minor_updates=[_minor_update()]))
        assert "3.10.0" in prompt
        assert "3.11.7" in prompt

    def test_contains_release_date(self) -> None:
        prompt = build_prompt(_diff_result(new_courses=[_new_course()]))
        assert "2026-09-30" in prompt

    def test_contains_full_notes_text(self) -> None:
        prompt = build_prompt(_diff_result(minor_updates=[_minor_update()]))
        assert "Lab-4: Updated permissions to resolve crawler issues." in prompt

    def test_latest_version_entry_notes_used(self) -> None:
        """latest_version_entry.notes should appear, not a truncated fallback."""
        course = _new_course()
        course["latest_version_entry"]["notes"] = "Detailed release note from versions[0]."
        course["notes"] = "Detailed release note from versions[0]."
        prompt = build_prompt(_diff_result(new_courses=[course]))
        assert "Detailed release note from versions[0]." in prompt

    def test_executive_summary_instruction_present(self) -> None:
        prompt = build_prompt(_diff_result(new_courses=[_new_course()]))
        assert "Executive Summary" in prompt

    def test_all_change_types_in_single_prompt(self) -> None:
        diff = _diff_result(
            new_courses=[_new_course()],
            major_updates=[_major_update()],
            minor_updates=[_minor_update()],
        )
        prompt = build_prompt(diff)
        assert "NEW COURSES" in prompt
        assert "MAJOR VERSION UPDATES" in prompt
        assert "MINOR VERSION UPDATES" in prompt

    def test_returns_string(self) -> None:
        assert isinstance(build_prompt(_diff_result(new_courses=[_new_course()])), str)


# ---------------------------------------------------------------------------
# summarise_changes – Claude model
# ---------------------------------------------------------------------------

class TestSummariseChangesClaude:
    def test_invokes_claude_model(self) -> None:
        expected_text = "## Advanced Architecting on AWS\nVersion: 3.11.7 | Released: 2026-08-06"
        body_bytes = json.dumps({"content": [{"text": expected_text}]}).encode()

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}

        result = summarise_changes(
            _diff_result(minor_updates=[_minor_update()]),
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            client=mock_client,
        )

        mock_client.invoke_model.assert_called_once()
        assert result == expected_text

    def test_claude_body_contains_course_name(self) -> None:
        body_bytes = json.dumps({"content": [{"text": "ok"}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}

        summarise_changes(
            _diff_result(new_courses=[_new_course()]),
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
            client=mock_client,
        )

        call_body = json.loads(mock_client.invoke_model.call_args.kwargs["body"])
        assert any("Agentic AI Foundations" in m["content"] for m in call_body["messages"])

    def test_claude_model_id_passed_correctly(self) -> None:
        body_bytes = json.dumps({"content": [{"text": "ok"}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}

        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        summarise_changes(_diff_result(new_courses=[_new_course()]), model_id=model_id, client=mock_client)

        assert mock_client.invoke_model.call_args.kwargs["modelId"] == model_id


# ---------------------------------------------------------------------------
# summarise_changes – Titan model
# ---------------------------------------------------------------------------

class TestSummariseChangesTitan:
    def test_invokes_titan_model(self) -> None:
        expected_text = "Titan summary output."
        body_bytes = json.dumps({"results": [{"outputText": expected_text}]}).encode()

        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}

        result = summarise_changes(
            _diff_result(minor_updates=[_minor_update()]),
            model_id="amazon.titan-text-express-v1",
            client=mock_client,
        )

        assert result == expected_text
        assert mock_client.invoke_model.call_args.kwargs["modelId"] == "amazon.titan-text-express-v1"


# ---------------------------------------------------------------------------
# summarise_changes – Generic converse fallback
# ---------------------------------------------------------------------------

class TestSummariseChangesConverse:
    def test_invokes_converse_api_for_unknown_model(self) -> None:
        expected_text = "Generic model summary."
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": expected_text}]}}
        }

        result = summarise_changes(
            _diff_result(major_updates=[_major_update()]),
            model_id="meta.llama3-70b-instruct-v1:0",
            client=mock_client,
        )

        mock_client.converse.assert_called_once()
        assert result == expected_text
