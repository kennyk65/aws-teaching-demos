# test_weather_agent.py
import random
import re
from collections import Counter

from weather_agent import invoke  # your entrypoint

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


# Basic behavioral test of the weather agent.
# 1. Asking for the temperature in Seattle should return ~23F
#    (the weather tool hard-codes -5C, which converts to 23F).
# 2. A self-contained freezing question should be answered correctly using
#    the freezing point of water.  This demo has no memory, so the prompt
#    supplies its own temperature context.
def test_invoke():
    ken_session_id = f"ken-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"
    payload = {"actor_id": "ken", "prompt": "What is the current temperature in Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]
    assert "Seattle" in result["result"]
    assert "23" in result["result"]
    print(result)

    payload = {"actor_id": "ken", "prompt": "If it is 23 degrees Fahrenheit outside, do you think water will freeze?"}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]

    response_text = str(result["result"])
    freeze_positive_refs = [
        "Yes, water will freeze there because 23 degrees Fahrenheit is below the freezing point of 32 degrees.",
        "At 23F, water freezes. That temperature is below 32F.",
        "Water would freeze since 23 degrees Fahrenheit is under freezing.",
        "Given a temperature of 23F, yes, it should freeze.",
    ]
    freeze_negative_groups = {
        "uncertainty": [
            "I need the location before I can tell if water will freeze.",
            "I cannot determine that without more information.",
            "There is not enough context to answer whether water will freeze.",
        ],
        "conditional_only": [
            "Water freezes only if temperature is below 32F.",
            "It depends on whether the temperature is under freezing.",
            "If it is below 32F then it would freeze.",
        ],
    }
    semantically_correct, semantic_debug = _semantic_compare(
        response_text,
        freeze_positive_refs,
        freeze_negative_groups,
        min_positive=0.24,
        min_margin=0.05,
    )
    assert semantically_correct, (
        f"Semantic check failed. Debug: {semantic_debug}. Response: {response_text}"
    )

    print(result)
