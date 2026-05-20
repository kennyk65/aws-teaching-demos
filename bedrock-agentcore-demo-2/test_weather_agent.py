# test_invoke.py
import pytest
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


# Main test of memory; 
# Details from the first prompt should be known to the agent when answering the second prompt.
# The weather agent's tool has hard-coded the returned temperature to 23F 
def test_invoke():
    ken_session_id = f"ken-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"
    payload = {"actor_id": "ken", "prompt": "What is the current temperature in Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id=ken_session_id)

    result = invoke(payload, context)

    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]
    assert "Seattle" in result["result"]
    assert "23" in result["result"]
    print(result)

    payload = {"actor_id": "ken", "prompt": "Do you think water will freeze there?"}
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
        "Given the earlier temperature of 23F, yes, it should freeze.",
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


def test_memory_isolation_across_users_and_sessions():
    alice_session_id = f"alice-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"
    bob_session_id = f"bob-session-001-abcdefghijklmnopqrstuvwxyz{_random_suffix()}"


    important_fact_1 = "Beavers mate for life."
    important_fact_2 = "Saturn is less dense than water."
    important_fact_3 = "Tom Brady won the super bowl 7 times."

    # Session A/User A: write a specific fact that should be remembered only in this session.
    payload_a = {
        "actor_id": "alice",
        "prompt": f"Please remember these important facts: {important_fact_1} {important_fact_2} {important_fact_3}",
    }
    context_a = FakeContext(
        session_id=alice_session_id,
    )

    result_a = invoke(payload_a, context_a)
    print(result_a)

    # See if it remembers these simple facts.
    payload_a = {      
        "actor_id": "alice",
        "prompt": "What are the important facts I asked you to remember?",
    }   
    
    result_a = invoke(payload_a, context_a)
    print(result_a)

    assert not str(result_a["result"]).startswith("[Error invoking model:"), result_a["result"]
    response_a = str(result_a["result"]).lower()
    assert important_fact_1.lower() in response_a, result_a["result"]
    assert important_fact_2.lower() in response_a, result_a["result"]
    assert important_fact_3.lower() in response_a, result_a["result"]


    # Session B/User B: Bob should NOT know the important facts from Alice's session.
    payload_b = {
        "actor_id": "bob",
        "prompt": "What are the important facts I asked you to remember?",
    }
    context_b = FakeContext(
        session_id=bob_session_id,
    )

    result_b = invoke(payload_b, context_b)
    response_b = str(result_b["result"])
    assert not response_b.startswith("[Error invoking model:"), result_b["result"]
    response_b_lower = response_b.lower()
    assert important_fact_1.lower() not in response_b_lower, result_b["result"]
    assert important_fact_2.lower() not in response_b_lower, result_b["result"]
    assert important_fact_3.lower() not in response_b_lower, result_b["result"]

    # Use semantic comparison for more complete verification.
    cannot_know_positive_refs = [
        "I do not know because you have not told me those facts in this session.",
        "I do not have enough information to list those facts.",
        "You have not shared any important facts with me in this conversation.",
        "I cannot recall any facts from you in this session.",
    ]
    cannot_know_negative_groups = {
        "claims_to_know": [
            f"The important facts were {important_fact_1} {important_fact_2} {important_fact_3}",
            f"You told me: {important_fact_1} {important_fact_2} {important_fact_3}",
            "You told me several important facts and here they are.",
        ]
    }

    bob_isolation_ok, bob_debug = _semantic_compare(
        response_b,
        cannot_know_positive_refs,
        cannot_know_negative_groups,
        min_positive=0.22,
        min_margin=0.04,
    )
    assert bob_isolation_ok, (
        f"Bob isolation semantic check failed. Debug: {bob_debug}. Response: {response_b}"
    )
    print(result_b)

    # add extra logic here to verify that Alice can still access the secret fact in her own session, and that Bob cannot access it in his session, even after both have made multiple calls to the agent. This will help confirm that memory is properly isolated across sessions and users.
    # Session A/User A: ask for the important facts again to confirm they're still remembered.
    payload_a = {      
        "actor_id": "alice",
        "prompt": "What are the important facts I asked you to remember?",
    }   
    
    result_a = invoke(payload_a, context_a)
    print(result_a)

    assert not str(result_a["result"]).startswith("[Error invoking model:"), result_a["result"]
    response_a = str(result_a["result"])
    response_a_lower = response_a.lower()
    assert important_fact_1.lower() in response_a_lower, result_a["result"]
    assert important_fact_2.lower() in response_a_lower, result_a["result"]
    assert important_fact_3.lower() in response_a_lower, result_a["result"]

    remembers_positive_refs = [
        f"You asked me to remember: {important_fact_1} {important_fact_2} {important_fact_3}",
        f"The important facts were {important_fact_1} {important_fact_2} {important_fact_3}",
        "Yes, I remember the important facts you shared.",
    ]
    remembers_negative_groups = {
        "uncertainty": cannot_know_positive_refs,
    }
    alice_memory_ok, alice_debug = _semantic_compare(
        response_a,
        remembers_positive_refs,
        remembers_negative_groups,
        min_positive=0.22,
        min_margin=0.04,
    )
    assert alice_memory_ok, (
        f"Alice memory semantic check failed. Debug: {alice_debug}. Response: {response_a}"
    )
