"""
test_bedrock_formatter.py – Tests for the two Bedrock prompts and the
per-model-family invocation dispatch (mocked boto3 clients).
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock

from src.bedrock_service import (
    build_detection_prompt,
    build_format_prompt,
    detect_releases,
    format_email_body,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _course(name, version, previous="", released="2026-09-25", notes="Notes.") -> dict:
    return {
        "name": name, "version": version, "previous_version": previous,
        "released": released, "notes": notes,
    }


_MAJOR = _course("Developing on AWS", "5.0.0", "4.2.1")
_MINOR = _course("Advanced Architecting on AWS", "3.11.0", "3.10.8")
_PATCH = _course("Architecting on AWS", "7.0.5", "7.0.4")
_NEW = _course("Agentic AI Foundations", "1.0.0", "")


# ---------------------------------------------------------------------------
# build_detection_prompt (Model Call #1)
# ---------------------------------------------------------------------------

class TestBuildDetectionPrompt:
    def test_returns_string(self) -> None:
        assert isinstance(build_detection_prompt([_MAJOR]), str)

    def test_includes_course_names(self) -> None:
        prompt = build_detection_prompt([_MAJOR, _MINOR, _PATCH])
        assert "Developing on AWS" in prompt
        assert "Advanced Architecting on AWS" in prompt
        assert "Architecting on AWS" in prompt

    def test_includes_current_and_previous_versions(self) -> None:
        prompt = build_detection_prompt([_MAJOR])
        assert "5.0.0" in prompt
        assert "4.2.1" in prompt

    def test_states_patch_rule(self) -> None:
        prompt = build_detection_prompt([_PATCH]).upper()
        assert "PATCH RELEASE IS NOT REPORTABLE" in prompt

    def test_includes_patch_worked_example(self) -> None:
        prompt = build_detection_prompt([_PATCH])
        assert "7.0.4" in prompt and "7.0.5" in prompt
        assert "OMIT" in prompt

    def test_mentions_major_minor_classification(self) -> None:
        prompt = build_detection_prompt([_MAJOR])
        assert "MAJOR" in prompt and "MINOR" in prompt

    def test_brand_new_course_reportable(self) -> None:
        prompt = build_detection_prompt([_NEW])
        assert "brand new" in prompt.lower()

    def test_asks_for_releases_json(self) -> None:
        prompt = build_detection_prompt([_MAJOR])
        assert '"releases"' in prompt


# ---------------------------------------------------------------------------
# build_format_prompt (Model Call #2)
# ---------------------------------------------------------------------------

class TestBuildFormatPrompt:
    def test_returns_string(self) -> None:
        assert isinstance(build_format_prompt([_MAJOR]), str)

    def test_includes_section_header(self) -> None:
        assert "▶ RECENT RELEASES" in build_format_prompt([_MAJOR])

    def test_instructs_version_transition(self) -> None:
        prompt = build_format_prompt([_MAJOR])
        assert "previous_version" in prompt and "→" in prompt

    def test_forbids_counts_and_modality(self) -> None:
        prompt = build_format_prompt([_MAJOR]).lower()
        assert "counts" in prompt
        assert "ilt" in prompt  # appears in the "do NOT include modality (ILT)" rule

    def test_includes_release_data(self) -> None:
        prompt = build_format_prompt([_MAJOR])
        assert "Developing on AWS" in prompt


# ---------------------------------------------------------------------------
# detect_releases — invocation per model family
# ---------------------------------------------------------------------------

class TestDetectReleasesInvocation:
    _JSON = '{"releases": []}'

    def test_claude(self) -> None:
        body_bytes = json.dumps({"content": [{"text": self._JSON}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}
        result = detect_releases([_MAJOR], model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                                 client=mock_client)
        mock_client.invoke_model.assert_called_once()
        assert result == self._JSON

    def test_titan(self) -> None:
        body_bytes = json.dumps({"results": [{"outputText": self._JSON}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}
        result = detect_releases([_MAJOR], model_id="amazon.titan-text-express-v1",
                                 client=mock_client)
        assert result == self._JSON

    def test_nova_uses_converse(self) -> None:
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": self._JSON}]}}
        }
        result = detect_releases([_MAJOR], model_id="us.amazon.nova-lite-v1:0",
                                 client=mock_client)
        mock_client.converse.assert_called_once()
        assert result == self._JSON

    def test_prompt_carries_course_data(self) -> None:
        body_bytes = json.dumps({"content": [{"text": self._JSON}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}
        detect_releases([_MAJOR], model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        client=mock_client)
        sent = json.loads(mock_client.invoke_model.call_args.kwargs["body"])
        assert any("Developing on AWS" in m["content"] for m in sent["messages"])

    def test_result_stripped(self) -> None:
        body_bytes = json.dumps({"content": [{"text": "\n  " + self._JSON + "  \n"}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}
        result = detect_releases([_MAJOR], model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                                 client=mock_client)
        assert result == self._JSON


# ---------------------------------------------------------------------------
# format_email_body — invocation
# ---------------------------------------------------------------------------

class TestFormatEmailBodyInvocation:
    _BODY = "▶ RECENT RELEASES\n  Developing on AWS  v4.2.1 → v5.0.0"

    def test_claude(self) -> None:
        body_bytes = json.dumps({"content": [{"text": self._BODY}]}).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": BytesIO(body_bytes)}
        result = format_email_body([_MAJOR], model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                                   client=mock_client)
        assert result == self._BODY

    def test_nova_uses_converse(self) -> None:
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": self._BODY}]}}
        }
        result = format_email_body([_MAJOR], model_id="us.amazon.nova-lite-v1:0",
                                   client=mock_client)
        mock_client.converse.assert_called_once()
        assert result == self._BODY

    def test_model_id_passed(self) -> None:
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": self._BODY}]}}
        }
        format_email_body([_MAJOR], model_id="us.amazon.nova-lite-v1:0", client=mock_client)
        assert mock_client.converse.call_args.kwargs["modelId"] == "us.amazon.nova-lite-v1:0"
