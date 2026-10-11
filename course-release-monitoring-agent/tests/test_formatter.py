"""
test_formatter.py – Tests for the header/footer wrapper and the no-releases
confirmation email.

The ▶ RECENT RELEASES body is produced by Model Call #2; this module tests only
the surrounding assembly done in code.
"""

from __future__ import annotations

from src.formatter import format_no_changes_email, wrap_body

_SAMPLE_BODY = (
    "▶ RECENT RELEASES\n"
    "──────────────────────────────────────────────────────\n\n"
    "  Developing on AWS                    v4.2.1 → v5.0.0\n"
    "  Released: 2026-09-25\n\n"
    "  Full course rewrite aligned to the latest AWS SDKs."
)


# ---------------------------------------------------------------------------
# wrap_body
# ---------------------------------------------------------------------------

class TestWrapBody:
    def test_returns_string(self) -> None:
        assert isinstance(wrap_body(_SAMPLE_BODY, 7), str)

    def test_contains_body_verbatim(self) -> None:
        out = wrap_body(_SAMPLE_BODY, 7)
        assert "Developing on AWS" in out
        assert "Full course rewrite aligned to the latest AWS SDKs." in out
        assert "v4.2.1 → v5.0.0" in out

    def test_contains_heavy_rule(self) -> None:
        assert "━" in wrap_body(_SAMPLE_BODY, 7)

    def test_contains_title(self) -> None:
        assert "AWS Training & Certification" in wrap_body(_SAMPLE_BODY, 7)

    def test_contains_footer(self) -> None:
        assert "Course Release Monitoring Agent" in wrap_body(_SAMPLE_BODY, 7)

    def test_intro_line_includes_lookback_days(self) -> None:
        out = wrap_body(_SAMPLE_BODY, 14)
        assert "major or minor release in the last 14 days" in out

    def test_no_counts_or_totals(self) -> None:
        out = wrap_body(_SAMPLE_BODY, 7)
        assert "changes detected" not in out
        assert "total" not in out.lower()

    def test_body_after_intro(self) -> None:
        out = wrap_body(_SAMPLE_BODY, 7)
        assert out.index("last 7 days") < out.index("Developing on AWS")


# ---------------------------------------------------------------------------
# format_no_changes_email
# ---------------------------------------------------------------------------

class TestFormatNoChangesEmail:
    def test_returns_string(self) -> None:
        assert isinstance(format_no_changes_email(7), str)

    def test_mentions_no_releases(self) -> None:
        assert "No major or minor course releases" in format_no_changes_email(7)

    def test_includes_lookback_days(self) -> None:
        assert "last 30 days" in format_no_changes_email(30)

    def test_pipeline_ok_message(self) -> None:
        assert "pipeline" in format_no_changes_email(7).lower()

    def test_contains_title(self) -> None:
        assert "AWS Training & Certification" in format_no_changes_email(7)

    def test_no_ilt(self) -> None:
        assert "ILT" not in format_no_changes_email(7)
