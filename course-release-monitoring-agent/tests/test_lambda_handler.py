"""
test_lambda_handler.py – End-to-end handler tests (stateless; no S3).

All external calls are mocked:
  * get_filtered_releases → the code-side filtered list
  * detect_releases       → Model Call #1 raw JSON (real parse_detection runs)
  * format_email_body     → Model Call #2 body text
  * publish_notification  → SNS
"""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ENV_DEFAULTS = {
    "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
    "BEDROCK_MODEL_ID": "us.amazon.nova-lite-v1:0",
    "LOOKBACK_DAYS": "7",
    "NOTIFY_CHANGES_ONLY": "true",
}


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in ENV_DEFAULTS.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _filtered_entry(name, version, previous) -> dict:
    return {
        "name": name, "version": version, "previous_version": previous,
        "released": "2026-09-25", "notes": f"Notes for {name}.",
    }


_FILTERED = [
    _filtered_entry("Developing on AWS", "5.0.0", "4.2.1"),
    _filtered_entry("Architecting on AWS", "7.0.5", "7.0.4"),
]

_DETECTION_WITH_RELEASES = json.dumps({"releases": [
    {"name": "Developing on AWS", "version": "5.0.0", "previous_version": "4.2.1",
     "released": "2026-09-25", "notes": "Full rewrite."},
]})
_DETECTION_EMPTY = json.dumps({"releases": []})


# ---------------------------------------------------------------------------
# Invoke helper
# ---------------------------------------------------------------------------

def _invoke(
    *,
    filtered: list[dict] | None = None,
    detection_json: str = _DETECTION_WITH_RELEASES,
    notify_changes_only: str = "true",
):
    """Returns (result, mock_detect, mock_format, mock_publish)."""
    if filtered is None:
        filtered = _FILTERED

    with (
        patch("src.handler.get_filtered_releases", return_value=filtered) as mock_filter,
        patch("src.handler.detect_releases", return_value=detection_json) as mock_detect,
        patch("src.handler.format_email_body", return_value="▶ RECENT RELEASES\n  body.") as mock_format,
        patch("src.handler.NOTIFY_CHANGES_ONLY", notify_changes_only == "true"),
        patch("src.handler.publish_notification") as mock_pub,
    ):
        mock_pub.return_value = {"MessageId": "test-id"}
        import src.handler as h
        result = h.lambda_handler({}, SimpleNamespace())
    return result, mock_filter, mock_detect, mock_format, mock_pub


# ---------------------------------------------------------------------------
# Empty recency window → no Model Call #1
# ---------------------------------------------------------------------------

class TestEmptyWindow:
    def test_returns_200(self) -> None:
        result, *_ = _invoke(filtered=[])
        assert result["statusCode"] == 200

    def test_no_detection_call(self) -> None:
        _, _, mock_detect, _, _ = _invoke(filtered=[])
        mock_detect.assert_not_called()

    def test_no_format_call(self) -> None:
        _, _, _, mock_format, _ = _invoke(filtered=[])
        mock_format.assert_not_called()

    def test_no_notification_when_notify_only(self) -> None:
        _, _, _, _, mock_pub = _invoke(filtered=[], notify_changes_only="true")
        mock_pub.assert_not_called()

    def test_confirmation_email_when_notify_false(self) -> None:
        _, _, _, _, mock_pub = _invoke(filtered=[], notify_changes_only="false")
        mock_pub.assert_called_once()
        assert "No Changes Detected" in mock_pub.call_args.kwargs["subject"]


# ---------------------------------------------------------------------------
# Window non-empty but Model Call #1 returns no major/minor releases
# ---------------------------------------------------------------------------

class TestNoReleasesDetected:
    def test_detection_called(self) -> None:
        _, _, mock_detect, _, _ = _invoke(detection_json=_DETECTION_EMPTY)
        mock_detect.assert_called_once()

    def test_no_format_call(self) -> None:
        _, _, _, mock_format, _ = _invoke(detection_json=_DETECTION_EMPTY)
        mock_format.assert_not_called()

    def test_no_notification_when_notify_only(self) -> None:
        _, _, _, _, mock_pub = _invoke(detection_json=_DETECTION_EMPTY, notify_changes_only="true")
        mock_pub.assert_not_called()

    def test_confirmation_email_when_notify_false(self) -> None:
        _, _, _, _, mock_pub = _invoke(detection_json=_DETECTION_EMPTY, notify_changes_only="false")
        mock_pub.assert_called_once()
        assert "No Changes Detected" in mock_pub.call_args.kwargs["subject"]


# ---------------------------------------------------------------------------
# Major/minor releases found → both calls, notification sent
# ---------------------------------------------------------------------------

class TestReleasesFound:
    def test_returns_200(self) -> None:
        result, *_ = _invoke()
        assert result["statusCode"] == 200

    def test_both_model_calls_invoked(self) -> None:
        _, _, mock_detect, mock_format, _ = _invoke()
        mock_detect.assert_called_once()
        mock_format.assert_called_once()

    def test_notification_published(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        mock_pub.assert_called_once()

    def test_subject_new_releases(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        assert "New Releases Detected" in mock_pub.call_args.kwargs["subject"]

    def test_subject_has_date(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        assert re.search(r"\d{4}-\d{2}-\d{2}", mock_pub.call_args.kwargs["subject"])

    def test_subject_aws_prefix(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        assert "[AWS Course Updates]" in mock_pub.call_args.kwargs["subject"]

    def test_topic_arn_matches_env(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        assert mock_pub.call_args.kwargs["topic_arn"] == ENV_DEFAULTS["SNS_TOPIC_ARN"]

    def test_message_wraps_body(self) -> None:
        _, _, _, _, mock_pub = _invoke()
        msg = mock_pub.call_args.kwargs["message"]
        assert "AWS Training & Certification" in msg  # header
        assert "▶ RECENT RELEASES" in msg             # body
        assert "last 7 days" in msg                   # intro w/ lookback

    def test_filtered_list_passed_to_detection(self) -> None:
        _, _, mock_detect, _, _ = _invoke()
        passed = mock_detect.call_args.args[0]
        assert passed == _FILTERED

    def test_no_s3_import(self) -> None:
        """The handler must not reference boto3/S3 at module level."""
        import src.handler as h
        assert not hasattr(h, "s3_client")
