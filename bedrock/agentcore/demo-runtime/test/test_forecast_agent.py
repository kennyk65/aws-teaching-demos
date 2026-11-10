# test_forecast_agent.py
import random
import re
from collections import Counter

from forecast_agent import invoke  # your entrypoint

class FakeContext:
    def __init__(self, session_id=None):
        self.session_id = session_id

def _random_suffix() -> str:
    return f"{random.randint(1000, 9999)}"

# Used to turn a String into tokens to allow for similarity comparisons.
def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

# Used to compare the semantic similarity of two strings.
def _cosine_similarity(a: str, b: str) -> float:
    a_counts = Counter(_tokenize(a))
    b_counts = Counter(_tokenize(b))
    if not a_counts or not b_counts:
        return 0.0

    shared = set(a_counts).intersection(b_counts)
    numerator = sum(a_counts[t] * b_counts[t] for t in shared)
    a_norm = sum(v * v for v in a_counts.values()) ** 0.5
    b_norm = sum(v * v for v in b_counts.values()) ** 0.5
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return numerator / (a_norm * b_norm)


def _max_similarity(text: str, refs: list[str]) -> float:
    if not refs:
        return 0.0
    return max(_cosine_similarity(text.lower(), ref.lower()) for ref in refs)


def _semantic_compare(
    response_text: str,
    positive_refs: list[str],
    negative_ref_groups: dict[str, list[str]] | None = None,
    min_positive: float = 0.24,
    min_margin: float = 0.05,
) -> tuple[bool, dict]:
    positive_score = _max_similarity(response_text, positive_refs)
    negative_ref_groups = negative_ref_groups or {}
    negative_scores = {
        name: _max_similarity(response_text, refs)
        for name, refs in negative_ref_groups.items()
    }
    strongest_negative = max(negative_scores.values(), default=0.0)

    is_match = (
        positive_score >= min_positive
        and positive_score > strongest_negative + min_margin
    )

    debug = {
        "positive_similarity": round(positive_score, 4),
        "strongest_negative_similarity": round(strongest_negative, 4),
        "negative_similarity_by_group": {
            k: round(v, 4) for k, v in negative_scores.items()
        },
        "min_positive": min_positive,
        "min_margin": min_margin,
    }
    return is_match, debug


# Basic behavioral test of the forecast agent.
# Asking for the forecast in a location should return a multi-day forecast for
# that location, presented in Fahrenheit.  This demo has no memory, so the
# single prompt is self-contained.
def test_invoke():
    ken_session_id = f"ken-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"
    payload = {"actor_id": "ken", "prompt": "What is the weather forecast for Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]
    assert "Seattle" in result["result"]
    print(result)

    response_text = str(result["result"])
    forecast_positive_refs = [
        "Here is the 5-day forecast for Seattle: day one sunny, day two partly cloudy, day three snow, then cloudy and sunny.",
        "The upcoming forecast shows sunny, partly cloudy, snow, cloudy, and sunny days with highs and lows in Fahrenheit.",
        "Over the next several days expect sunny skies, clouds, and snow, with daily high and low temperatures.",
        "The multi-day forecast includes sunny, cloudy, and snowy days with Fahrenheit highs and lows.",
    ]
    forecast_negative_groups = {
        "uncertainty": [
            "I need a location before I can provide a forecast.",
            "I cannot determine the forecast without more information.",
            "There is not enough context to give a forecast.",
        ],
        "refusal": [
            "I am unable to provide weather forecasts.",
            "I do not have access to forecast data.",
        ],
    }
    semantically_correct, semantic_debug = _semantic_compare(
        response_text,
        forecast_positive_refs,
        forecast_negative_groups,
        min_positive=0.24,
        min_margin=0.05,
    )
    assert semantically_correct, (
        f"Semantic check failed. Debug: {semantic_debug}. Response: {response_text}"
    )

    print(result)
