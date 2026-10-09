"""
handler.py – Lambda entrypoint for the AWS Course Release Monitoring Agent.

Flow:
  1. Scrape current catalog from releases.awstc.com
  2. Load previous catalog snapshot from S3
  3. Diff the two snapshots
  4. Notify via SNS (behaviour controlled by NOTIFY_CHANGES_ONLY):
       NOTIFY_CHANGES_ONLY=true  → only notify when changes are detected
       NOTIFY_CHANGES_ONLY=false → always notify; sends a "no changes" email
                                   when the catalog is unchanged (useful for
                                   verifying the pipeline end-to-end)
  5. Persist updated snapshot to S3
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import boto3

from src.scraper import scrape_catalog
from src.diff import compute_diff
from src.bedrock_service import summarise_changes
from src.notifier import publish_notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables (injected by SAM / CloudFormation)
# ---------------------------------------------------------------------------
S3_BUCKET = os.environ["S3_BUCKET"]
S3_KEY = os.environ["S3_KEY"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
# When "true" (default), suppress notifications on no-change runs.
# Set to "false" to always send an email — useful for pipeline smoke-testing.
NOTIFY_CHANGES_ONLY = os.environ.get("NOTIFY_CHANGES_ONLY", "true").strip().lower() == "true"

s3_client = boto3.client("s3")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_previous_state() -> dict | None:
    """Return the previous catalog dict from S3, or None on first run."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        logger.info("No existing state.json found – this appears to be the first run.")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load previous state: %s", exc)
        return None


def _save_current_state(catalog: dict) -> None:
    """Persist the current catalog snapshot to S3."""
    payload = json.dumps(catalog, indent=2, default=str)
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=payload.encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Saved updated state to s3://%s/%s", S3_BUCKET, S3_KEY)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context) -> dict:
    """Main Lambda handler."""
    logger.info("Course Release Monitor invoked. event=%s", json.dumps(event))

    # 1. Scrape current catalog
    logger.info("Scraping releases.awstc.com …")
    current_catalog = scrape_catalog()
    logger.info("Scraped %d course entries.", len(current_catalog.get("courses", [])))

    # 2. Load previous state
    previous_catalog = _load_previous_state()

    if previous_catalog is None:
        # First run – save baseline and exit
        logger.info("First run detected. Saving baseline snapshot and exiting.")
        _save_current_state(current_catalog)
        return {
            "statusCode": 200,
            "body": "First run: baseline snapshot saved. No notification sent.",
        }

    # 3. Compute diff
    diff_result = compute_diff(previous_catalog, current_catalog)
    total_changes = (
        len(diff_result["new_courses"])
        + len(diff_result["major_updates"])
        + len(diff_result["minor_updates"])
    )
    logger.info(
        "Diff complete. new=%d, major=%d, minor=%d",
        len(diff_result["new_courses"]),
        len(diff_result["major_updates"]),
        len(diff_result["minor_updates"]),
    )

    if total_changes == 0:
        logger.info("No changes detected.")
        _save_current_state(current_catalog)

        if NOTIFY_CHANGES_ONLY:
            logger.info("NOTIFY_CHANGES_ONLY=true – skipping notification.")
            return {"statusCode": 200, "body": "No changes detected. No notification sent."}

        # NOTIFY_CHANGES_ONLY=false – send a "no changes" confirmation email
        logger.info("NOTIFY_CHANGES_ONLY=false – sending no-change confirmation email.")
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        subject = f"[AWS Course Updates] No Changes Detected - {today}"
        message = (
            f"The AWS Course Release Monitor ran on {today} and found "
            f"no new or updated courses since the last check.\n\n"
            f"The pipeline is operating normally."
        )
        publish_notification(topic_arn=SNS_TOPIC_ARN, subject=subject, message=message)
        logger.info("No-change notification published to SNS topic %s", SNS_TOPIC_ARN)
        return {"statusCode": 200, "body": "No changes detected. Confirmation notification sent."}

    # 4. Summarise with Bedrock
    logger.info("Invoking Bedrock to summarise %d change(s) …", total_changes)
    summary_text = summarise_changes(diff_result, model_id=BEDROCK_MODEL_ID)

    # 5. Publish to SNS
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    subject = f"[AWS Course Updates] New Releases Detected - {today}"
    publish_notification(
        topic_arn=SNS_TOPIC_ARN,
        subject=subject,
        message=summary_text,
    )
    logger.info("Notification published to SNS topic %s", SNS_TOPIC_ARN)

    # 6. Persist updated state
    _save_current_state(current_catalog)

    return {
        "statusCode": 200,
        "body": f"Detected {total_changes} change(s). Notification sent.",
    }
