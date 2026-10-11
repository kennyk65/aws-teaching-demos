"""
formatter.py – Assembles the plain-text notification email.

Model Call #2 (``bedrock_service.format_email_body``) produces the
``▶ RECENT RELEASES`` body section; this module wraps it with a header
(title + date) and the "last X days" intro line and footer, and produces the
standalone "no releases" confirmation email.

SNS email subscriptions deliver plain text only, so formatting relies on
unicode box-drawing characters and consistent spacing rather than HTML.

Assembled structure:

  ━━━ header (title, date) ━━━

  The following courses had a major or minor release in the last X days:

  <Model-generated ▶ RECENT RELEASES section>

  ━━━ footer ━━━
"""

from __future__ import annotations

from datetime import datetime, timezone

_WIDTH = 54
_RULE_HEAVY = "━" * _WIDTH
_TITLE = "  AWS Training & Certification — Course Releases"
_FOOTER_TEXT = "Sent by the AWS Course Release Monitoring Agent."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wrap_body(body: str, lookback_days: int) -> str:
    """
    Wrap the model-generated *body* with the header, the "last X days" intro
    line, and the footer.

    Parameters
    ----------
    body : str
        The ``▶ RECENT RELEASES`` section from Model Call #2.
    lookback_days : int
        The recency window size, used in the intro line.
    """
    lines: list[str] = [
        *_header_lines(),
        "",
        f"The following courses had a major or minor release in the last "
        f"{lookback_days} days:",
        "",
        "",
        body.strip(),
        "",
        "",
        *_footer_lines(),
    ]
    return "\n".join(lines)


def format_no_changes_email(lookback_days: int) -> str:
    """Plain-text confirmation email when no major/minor releases are found."""
    return "\n".join([
        *_header_lines(),
        "",
        f"No major or minor course releases were found in the last "
        f"{lookback_days} days.",
        "",
        "The pipeline is operating normally.",
        "",
        *_footer_lines(),
    ])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _header_lines() -> list[str]:
    today = datetime.now(tz=timezone.utc).strftime("%B %d, %Y").replace(" 0", " ")
    return [_RULE_HEAVY, _TITLE, f"  {today}", _RULE_HEAVY]


def _footer_lines() -> list[str]:
    return [_RULE_HEAVY, _FOOTER_TEXT, _RULE_HEAVY]
