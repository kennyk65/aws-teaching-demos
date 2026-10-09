"""
test_lambda_handler.py – End-to-end handler tests with mocked boto3 calls.

All AWS service calls (S3 get_object / put_object, SNS publish, Bedrock
invoke_model) are mocked so these tests run without any AWS credentials.

Rather than reloading the module (which causes boto3 to attempt real connections),
we patch the module-level s3_client, scrape_catalog, summarise_changes, and
publish_notification symbols after import.
"""

from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Environment setup  (must happen before src.handler is imported)
# ---------------------------------------------------------------------------

ENV_DEFAULTS = {
    "S3_BUCKET": "test-bucket",
    "S3_KEY": "awstc-monitor/state.json",
    "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
    "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "NOTIFY_CHANGES_ONLY": "true",
}


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV_DEFAULTS.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------------------
# Catalog fixtures
# ---------------------------------------------------------------------------

def _catalog_v1() -> dict:
    return {
        "scraped_at": "2026-09-01T12:00:00+00:00",
        "courses": [
            {
                "name": "Advanced Architecting on AWS",
                "language": "EN",
                "modality": "ILT",
                "version": "3.10.0",
                "version_sort": 3_010_000,
                "released": "2026-05-01",
                "sku": "ILT-TF-300-ADVARC-3-EN",
                "notes": "Previous version notes.",
                "latest_version_entry": {
                    "version": "3.10.0",
                    "released": "2026-05-01",
                    "notes": "Previous version notes.",
                },
            }
        ],
    }


def _catalog_v2() -> dict:
    """v1 course gets a minor bump; a brand new course is added."""
    return {
        "scraped_at": "2026-10-08T12:00:00+00:00",
        "courses": [
            {
                "name": "Advanced Architecting on AWS",
                "language": "EN",
                "modality": "ILT",
                "version": "3.11.7",
                "version_sort": 3_011_007,
                "released": "2026-08-06",
                "sku": "ILT-TF-300-ADVARC-3-EN",  # same SKU = update, not new
                "notes": "Lab-4: Updated permissions to resolve crawler issues.",
                "latest_version_entry": {
                    "version": "3.11.7",
                    "released": "2026-08-06",
                    "notes": "Lab-4: Updated permissions to resolve crawler issues.",
                },
            },
            {
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
            },
        ],
    }


# ---------------------------------------------------------------------------
# Mock factories
# ---------------------------------------------------------------------------

def _mock_s3_with_state(state_dict: dict) -> MagicMock:
    body_bytes = json.dumps(state_dict).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": BytesIO(body_bytes)}
    mock_s3.put_object.return_value = {}

    class _NoSuchKey(Exception):
        pass

    mock_s3.exceptions.NoSuchKey = _NoSuchKey
    return mock_s3


def _mock_s3_no_state() -> MagicMock:
    class _NoSuchKey(Exception):
        pass

    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = _NoSuchKey("NoSuchKey")
    mock_s3.put_object.return_value = {}
    mock_s3.exceptions.NoSuchKey = _NoSuchKey
    return mock_s3


def _mock_bedrock_claude(summary: str = "## Executive Summary\nAll good.") -> MagicMock:
    body_bytes = json.dumps({"content": [{"text": summary}]}).encode()
    mock_bedrock = MagicMock()
    mock_bedrock.invoke_model.return_value = {"body": BytesIO(body_bytes)}
    return mock_bedrock


def _mock_sns() -> MagicMock:
    mock_sns = MagicMock()
    mock_sns.publish.return_value = {"MessageId": "test-message-id"}
    return mock_sns


# ---------------------------------------------------------------------------
# Helper: invoke the handler with every external call patched
# ---------------------------------------------------------------------------

def _invoke_handler(
    mock_s3: MagicMock,
    mock_bedrock: MagicMock | None = None,
    mock_sns: MagicMock | None = None,
    current_catalog: dict | None = None,
) -> dict:
    if current_catalog is None:
        current_catalog = _catalog_v2()
    if mock_bedrock is None:
        mock_bedrock = _mock_bedrock_claude()
    if mock_sns is None:
        mock_sns = _mock_sns()

    # Patch at the module attribute level so no boto3.client() calls fire
    with (
        patch("src.handler.s3_client", mock_s3),
        patch("src.handler.scrape_catalog", return_value=current_catalog),
        patch("src.handler.summarise_changes", return_value="## Summary\nMocked summary."),
        patch("src.handler.publish_notification") as mock_pub,
    ):
        mock_pub.return_value = {"MessageId": "test-id"}
        # Capture the SNS subject/message via publish_notification so we can inspect them
        mock_sns._publish_notification = mock_pub

        import src.handler as handler_module
        return handler_module.lambda_handler({}, SimpleNamespace())


# ---------------------------------------------------------------------------
# Variant that uses a real mock_sns for subject inspection
# ---------------------------------------------------------------------------

def _invoke_handler_sns(
    mock_s3: MagicMock,
    current_catalog: dict | None = None,
) -> tuple[dict, MagicMock]:
    """Returns (result, mock for publish_notification)."""
    if current_catalog is None:
        current_catalog = _catalog_v2()

    with (
        patch("src.handler.s3_client", mock_s3),
        patch("src.handler.scrape_catalog", return_value=current_catalog),
        patch("src.handler.summarise_changes", return_value="## Summary\nMocked."),
        patch("src.handler.publish_notification") as mock_pub,
    ):
        mock_pub.return_value = {"MessageId": "test-id"}
        import src.handler as handler_module
        result = handler_module.lambda_handler({}, SimpleNamespace())

    return result, mock_pub


# ---------------------------------------------------------------------------
# First run (no existing state)
# ---------------------------------------------------------------------------

class TestFirstRun:
    def test_returns_200(self) -> None:
        assert _invoke_handler(mock_s3=_mock_s3_no_state())["statusCode"] == 200

    def test_saves_baseline_to_s3(self) -> None:
        mock_s3 = _mock_s3_no_state()
        _invoke_handler(mock_s3=mock_s3)
        mock_s3.put_object.assert_called_once()
        kwargs = mock_s3.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == "awstc-monitor/state.json"

    def test_saved_state_contains_courses(self) -> None:
        mock_s3 = _mock_s3_no_state()
        _invoke_handler(mock_s3=mock_s3, current_catalog=_catalog_v2())
        saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"])
        assert len(saved["courses"]) == 2

    def test_no_notification_on_first_run(self) -> None:
        with (
            patch("src.handler.s3_client", _mock_s3_no_state()),
            patch("src.handler.scrape_catalog", return_value=_catalog_v2()),
            patch("src.handler.publish_notification") as mock_pub,
        ):
            import src.handler as handler_module
            handler_module.lambda_handler({}, SimpleNamespace())
        mock_pub.assert_not_called()

    def test_response_body_mentions_first_run_or_baseline(self) -> None:
        result = _invoke_handler(mock_s3=_mock_s3_no_state())
        body_lower = result["body"].lower()
        assert "first run" in body_lower or "baseline" in body_lower


# ---------------------------------------------------------------------------
# No changes detected
# ---------------------------------------------------------------------------

class TestNoChanges:
    def test_returns_200(self) -> None:
        existing = _catalog_v1()
        assert _invoke_handler(mock_s3=_mock_s3_with_state(existing), current_catalog=existing)["statusCode"] == 200

    def test_no_notification_when_no_changes(self) -> None:
        existing = _catalog_v1()
        with (
            patch("src.handler.s3_client", _mock_s3_with_state(existing)),
            patch("src.handler.scrape_catalog", return_value=existing),
            patch("src.handler.publish_notification") as mock_pub,
        ):
            import src.handler as handler_module
            handler_module.lambda_handler({}, SimpleNamespace())
        mock_pub.assert_not_called()

    def test_state_still_saved_when_no_changes(self) -> None:
        existing = _catalog_v1()
        mock_s3 = _mock_s3_with_state(existing)
        _invoke_handler(mock_s3=mock_s3, current_catalog=existing)
        mock_s3.put_object.assert_called_once()

    def test_response_body_mentions_no_changes(self) -> None:
        existing = _catalog_v1()
        result = _invoke_handler(mock_s3=_mock_s3_with_state(existing), current_catalog=existing)
        assert "no changes" in result["body"].lower()


# ---------------------------------------------------------------------------
# Changes detected
# ---------------------------------------------------------------------------

class TestChangesDetected:
    def test_returns_200(self) -> None:
        result = _invoke_handler(mock_s3=_mock_s3_with_state(_catalog_v1()), current_catalog=_catalog_v2())
        assert result["statusCode"] == 200

    def test_bedrock_invoked_when_changes_found(self) -> None:
        with (
            patch("src.handler.s3_client", _mock_s3_with_state(_catalog_v1())),
            patch("src.handler.scrape_catalog", return_value=_catalog_v2()),
            patch("src.handler.summarise_changes") as mock_bedrock,
            patch("src.handler.publish_notification"),
        ):
            mock_bedrock.return_value = "## Summary"
            import src.handler as handler_module
            handler_module.lambda_handler({}, SimpleNamespace())
        mock_bedrock.assert_called_once()

    def test_notification_published_when_changes_found(self) -> None:
        result, mock_pub = _invoke_handler_sns(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            current_catalog=_catalog_v2(),
        )
        mock_pub.assert_called_once()

    def test_notification_subject_contains_aws_course_updates_prefix(self) -> None:
        _, mock_pub = _invoke_handler_sns(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            current_catalog=_catalog_v2(),
        )
        subject = mock_pub.call_args.kwargs["subject"]
        assert "[AWS Course Updates]" in subject

    def test_notification_subject_contains_date(self) -> None:
        import re
        _, mock_pub = _invoke_handler_sns(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            current_catalog=_catalog_v2(),
        )
        subject = mock_pub.call_args.kwargs["subject"]
        assert re.search(r"\d{4}-\d{2}-\d{2}", subject)

    def test_notification_topic_arn_matches_env(self) -> None:
        _, mock_pub = _invoke_handler_sns(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            current_catalog=_catalog_v2(),
        )
        assert mock_pub.call_args.kwargs["topic_arn"] == ENV_DEFAULTS["SNS_TOPIC_ARN"]

    def test_updated_state_saved_with_current_courses(self) -> None:
        mock_s3 = _mock_s3_with_state(_catalog_v1())
        _invoke_handler(mock_s3=mock_s3, current_catalog=_catalog_v2())
        saved = json.loads(mock_s3.put_object.call_args.kwargs["Body"])
        assert len(saved["courses"]) == 2

    def test_response_body_mentions_change_count(self) -> None:
        result = _invoke_handler(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            current_catalog=_catalog_v2(),
        )
        assert any(char.isdigit() for char in result["body"])


# ---------------------------------------------------------------------------
# NOTIFY_CHANGES_ONLY behaviour
# ---------------------------------------------------------------------------

def _invoke_handler_with_env(
    mock_s3: MagicMock,
    notify_changes_only: str,
    current_catalog: dict | None = None,
) -> tuple[dict, MagicMock]:
    """Invoke the handler with an explicit NOTIFY_CHANGES_ONLY value."""
    if current_catalog is None:
        current_catalog = _catalog_v1()  # same as previous → no changes

    with (
        patch("src.handler.s3_client", mock_s3),
        patch("src.handler.scrape_catalog", return_value=current_catalog),
        patch("src.handler.summarise_changes", return_value="## Summary\nMocked."),
        patch("src.handler.NOTIFY_CHANGES_ONLY", notify_changes_only == "true"),
        patch("src.handler.publish_notification") as mock_pub,
    ):
        mock_pub.return_value = {"MessageId": "test-id"}
        import src.handler as handler_module
        result = handler_module.lambda_handler({}, SimpleNamespace())

    return result, mock_pub


class TestNotifyChangesOnly:
    # ── NOTIFY_CHANGES_ONLY=true (default) ──────────────────────────────────

    def test_true_no_changes_no_notification(self) -> None:
        existing = _catalog_v1()
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="true",
            current_catalog=existing,
        )
        mock_pub.assert_not_called()

    def test_true_no_changes_response_mentions_no_notification(self) -> None:
        existing = _catalog_v1()
        result, _ = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="true",
            current_catalog=existing,
        )
        assert "no notification" in result["body"].lower()

    def test_true_with_changes_still_notifies(self) -> None:
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            notify_changes_only="true",
            current_catalog=_catalog_v2(),
        )
        mock_pub.assert_called_once()

    # ── NOTIFY_CHANGES_ONLY=false ────────────────────────────────────────────

    def test_false_no_changes_sends_confirmation_email(self) -> None:
        existing = _catalog_v1()
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="false",
            current_catalog=existing,
        )
        mock_pub.assert_called_once()

    def test_false_no_changes_subject_says_no_changes(self) -> None:
        existing = _catalog_v1()
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="false",
            current_catalog=existing,
        )
        subject = mock_pub.call_args.kwargs["subject"]
        assert "No Changes Detected" in subject

    def test_false_no_changes_subject_contains_date(self) -> None:
        import re
        existing = _catalog_v1()
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="false",
            current_catalog=existing,
        )
        subject = mock_pub.call_args.kwargs["subject"]
        assert re.search(r"\d{4}-\d{2}-\d{2}", subject)

    def test_false_no_changes_message_confirms_pipeline_ok(self) -> None:
        existing = _catalog_v1()
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(existing),
            notify_changes_only="false",
            current_catalog=existing,
        )
        message = mock_pub.call_args.kwargs["message"]
        assert "no new or updated courses" in message.lower() or "pipeline" in message.lower()

    def test_false_with_changes_still_notifies(self) -> None:
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            notify_changes_only="false",
            current_catalog=_catalog_v2(),
        )
        mock_pub.assert_called_once()

    def test_false_with_changes_subject_says_new_releases(self) -> None:
        _, mock_pub = _invoke_handler_with_env(
            mock_s3=_mock_s3_with_state(_catalog_v1()),
            notify_changes_only="false",
            current_catalog=_catalog_v2(),
        )
        subject = mock_pub.call_args.kwargs["subject"]
        assert "New Releases Detected" in subject
