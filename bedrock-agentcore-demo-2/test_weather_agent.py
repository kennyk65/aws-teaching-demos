# test_invoke.py
import pytest
from weather_agent import invoke  # your entrypoint

class FakeContext:
    def __init__(self, session_id=None):
        self.session_id = session_id

def test_invoke():
    payload = {"actor_id": "ken", "prompt": "What is the current temperature in Seattle, WA? Use Fahrenheit."}
    context = FakeContext(session_id="ken-session-001-abcdefghijklmnopqrstuvwxyz123")

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]
    assert "Seattle" in result["result"]
    assert "23" in result["result"]
    print(result)

    payload = {"actor_id": "ken", "prompt": "Do you think water will freeze there?"}
    context = FakeContext(session_id="ken-session-001-abcdefghijklmnopqrstuvwxyz123")

    result = invoke(payload, context)

    assert result["actor_id"] == "ken"
    assert result["session_id"].startswith("ken-session-001")
    assert not str(result["result"]).startswith("[Error invoking model:"), result["result"]

    response_text = str(result["result"]).lower()
    positive_indicators = [
        "will freeze",
        "would freeze",
        "water will freeze",
        "below freezing",
        "under 32",
        "below 32",
    ]
    uncertainty_or_failure_indicators = [
        "need to know the location",
        "need the location",
        "need a location",
        "without a location",
        "cannot determine",
        "can't determine",
        "not enough information",
        "need more information",
        "which location",
        "what location",
    ]

    assert any(indicator in response_text for indicator in positive_indicators), result["result"]
    assert not any(indicator in response_text for indicator in uncertainty_or_failure_indicators), result["result"]
    print(result)


def test_memory_isolation_across_users_and_sessions():
    secret_fact = "ORANGE-ELEPHANT-7429"

    # Session A/User A: write a specific fact that should be remembered only in this session.
    payload_a = {
        "actor_id": "alice",
        "prompt": f"Please remember this exact passphrase: {secret_fact}.",
    }
    context_a = FakeContext(
        session_id="alice-session-001-abcdefghijklmnopqrstuvwxyz123",
    )

    result_a = invoke(payload_a, context_a)
    print(result_a)

    # Session B/User B: ask for the passphrase and verify it cannot access Session A memory.
    payload_b = {
        "actor_id": "bob",
        "prompt": "What is the passphrase I told you earlier?",
    }
    context_b = FakeContext(
        session_id="bob-session-001-abcdefghijklmnopqrstuvwxyz123",
    )

    result_b = invoke(payload_b, context_b)
    assert not str(result_b["result"]).startswith("[Error invoking model:"), result_b["result"]
    response_b = str(result_b["result"]).lower()
    cannot_know_indicators = [
        "don't know",
        "do not know",
        "can't",
        "cannot",
        "not sure",
        "no information",
        "no context",
        "didn't tell me",
        "did not tell me",
    ]

    assert secret_fact.lower() not in response_b, result_b["result"]
    assert any(indicator in response_b for indicator in cannot_know_indicators), result_b["result"]
    print(result_b)

