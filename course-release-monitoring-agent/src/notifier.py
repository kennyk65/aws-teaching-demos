"""
notifier.py – Amazon SNS notification dispatcher.

Publishes a formatted message to an SNS topic (which delivers it to
subscribed email addresses).
"""

from __future__ import annotations

import logging

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_sns_client = None  # module-level singleton; replaced in tests via dependency injection


def _get_client():
    global _sns_client  # noqa: PLW0603
    if _sns_client is None:
        _sns_client = boto3.client("sns")
    return _sns_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def publish_notification(
    topic_arn: str,
    subject: str,
    message: str,
    *,
    client=None,
) -> dict:
    """
    Publish *message* to the SNS *topic_arn* with *subject*.

    Parameters
    ----------
    topic_arn : str
        ARN of the target SNS topic.
    subject : str
        Email subject line (max 100 chars for SNS).
    message : str
        Plain-text / Markdown message body.
    client : optional
        Injected boto3 SNS client (used in tests).

    Returns
    -------
    dict
        The raw SNS publish response.
    """
    sns = client or _get_client()

    # SNS subject has a 100-character limit; truncate safely.
    truncated_subject = subject[:100]

    logger.info(
        "Publishing SNS notification to %s  subject=%r  message_len=%d",
        topic_arn,
        truncated_subject,
        len(message),
    )

    response = sns.publish(
        TopicArn=topic_arn,
        Subject=truncated_subject,
        Message=message,
    )

    logger.info("SNS publish response MessageId=%s", response.get("MessageId"))
    return response
