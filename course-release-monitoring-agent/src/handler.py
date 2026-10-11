"""
handler.py – Lambda entrypoint for the AWS Course Release Monitoring Agent.

Stateless flow (no S3, no prior-state snapshot):

  1. Fetch the catalog and apply code-side filtering (language, recency window,
     latest-two-versions trim) → the "filtered list".
  2. If the filtered list is empty → no releases in the window.
  3. Model Call #1: Bedrock returns ONLY the major/minor releases (patch
     releases excluded); the response is parsed/validated in code.
  4. If no major/minor releases → no notification (unless NOTIFY_CHANGES_ONLY
     is "false", which sends a confirmation email).
  5. Model Call #2: Bedrock formats the releases into the email body; wrap with
     header/footer and publish to SNS.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from src.scraper import get_filtered_releases
from src.detection import parse_detection
from src.bedrock_service import detect_releases, format_email_body
from src.formatter import wrap_body, format_no_changes_email
from src.notifier import publish_notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables (injected by SAM / CloudFormation)
# ---------------------------------------------------------------------------
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
# When "true" (default), suppress notifications when no major/minor releases are
# found. Set to "false" to always send an email — useful for pipeline testing.
NOTIFY_CHANGES_ONLY = os.environ.get("NOTIFY_CHANGES_ONLY", "true").strip().lower() == "true"


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    """Main Lambda handler."""
    logger.info("Course Release Monitor invoked. event=%s", json.dumps(event))
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # 1. Fetch + code-side filter (language / recency / latest-two-versions)
    logger.info("Fetching and filtering catalog (lookback=%d days) …", LOOKBACK_DAYS)
    filtered = get_filtered_releases(LOOKBACK_DAYS)
    logger.info("Filtered list contains %d recent course(s).", len(filtered))

    if not filtered:
        logger.info("No courses released within the last %d day(s).", LOOKBACK_DAYS)
        return _handle_no_releases(today)

    # 2. Model Call #1 — detect major/minor releases (patch excluded)
    logger.info("Invoking Bedrock to detect major/minor releases …")
    detection_raw = detect_releases(filtered, model_id=BEDROCK_MODEL_ID)
    releases = parse_detection(detection_raw)
    logger.info("Detected %d major/minor release(s).", len(releases))

    if not releases:
        logger.info("No major/minor releases in the window.")
        return _handle_no_releases(today)

    # 3. Model Call #2 — format the email body, wrap, and publish
    logger.info("Invoking Bedrock to format %d release(s) …", len(releases))
    body = format_email_body(releases, model_id=BEDROCK_MODEL_ID)
    message = wrap_body(body, LOOKBACK_DAYS)

    subject = f"[AWS Course Updates] New Releases Detected - {today}"
    publish_notification(topic_arn=SNS_TOPIC_ARN, subject=subject, message=message)
    logger.info("Notification published to SNS topic %s", SNS_TOPIC_ARN)

    return {
        "statusCode": 200,
        "body": f"Detected {len(releases)} major/minor release(s). Notification sent.",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _handle_no_releases(today: str) -> dict:
    """
    Common path when there are no major/minor releases to report. Honours
    NOTIFY_CHANGES_ONLY: silent by default, confirmation email when "false".
    """
    if NOTIFY_CHANGES_ONLY:
        logger.info("NOTIFY_CHANGES_ONLY=true – skipping notification.")
        return {"statusCode": 200, "body": "No major/minor releases. No notification sent."}

    logger.info("NOTIFY_CHANGES_ONLY=false – sending confirmation email.")
    subject = f"[AWS Course Updates] No Changes Detected - {today}"
    message = format_no_changes_email(LOOKBACK_DAYS)
    publish_notification(topic_arn=SNS_TOPIC_ARN, subject=subject, message=message)
    logger.info("No-change notification published to SNS topic %s", SNS_TOPIC_ARN)
    return {"statusCode": 200, "body": "No major/minor releases. Confirmation notification sent."}
